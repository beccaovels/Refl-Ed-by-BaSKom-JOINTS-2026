"""One audio piece during the lesson: transcribe it, maybe let a student speak, reply.

POST /sessions/{id}/audio  multipart: seq, start_ms, end_ms, file (WAV, 16 kHz mono)
→ { seq, segment, event }

A resent seq gets the first reply back and nothing else happens, so the browser can retry
freely after a network drop. The audio is only held in memory while it is transcribed.
"""

from threading import Lock

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from app.core.auth import current_user, own_session
from app.core.db import get_session
from app.models import AudioChunk, Question, TranscriptSegment, User
from app.schemas.audio import AudioReply, SegmentOut
from app.services import llm, questions, stt

router = APIRouter(tags=["audio"])

MAX_BYTES = 10 * 1024 * 1024  # about 5 minutes of 16 kHz mono; a piece is cut at the teacher's pauses
READ_BLOCK = 256 * 1024

# (session_id, seq) pieces being transcribed right now, so a retry that arrives
# before the first attempt has finished does not transcribe the same piece twice.
_processing: set[tuple[str, int]] = set()
_processing_lock = Lock()


@router.post("/sessions/{session_id}/audio", response_model=AudioReply)
def receive_audio(
    session_id: str,
    seq: int = Form(ge=0),
    start_ms: int = Form(ge=0),
    end_ms: int = Form(ge=0),
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
):
    session = own_session(db, session_id, user)
    stored = _stored_reply(db, session_id, seq)
    if stored is not None:
        return stored
    if session.status != "active":
        raise HTTPException(status_code=409, detail="Sesi ini sudah selesai.")
    if end_ms < start_ms:
        raise HTTPException(status_code=422, detail="end_ms tidak boleh lebih kecil dari start_ms.")
    wav = _read_wav(file)

    key = (session_id, seq)
    with _processing_lock:
        if key in _processing:
            raise HTTPException(status_code=409, detail="Potongan audio ini masih diproses. Kirim ulang sebentar lagi.")
        _processing.add(key)
    try:
        return _process(db, session_id, seq, start_ms, end_ms, wav)
    finally:
        with _processing_lock:
            _processing.discard(key)


def _process(db: Session, session_id: str, seq: int, start_ms: int, end_ms: int, wav: bytes) -> AudioReply:
    stored = _stored_reply(db, session_id, seq)  # finished while this request waited
    if stored is not None:
        return stored

    # A transcript row without a reply record means an earlier attempt stopped half-way: reuse its text.
    segment = _segment(db, session_id, seq)
    new_segment = segment is None
    if new_segment:
        try:
            text = stt.transcribe(wav).strip()
        except stt.STTError:
            raise HTTPException(
                status_code=502, detail="Transkripsi sedang tidak tersedia. Potongan ini akan dikirim ulang."
            ) from None
        if text:
            segment = TranscriptSegment(session_id=session_id, seq=seq, start_ms=start_ms, end_ms=end_ms, text=text)
            db.add(segment)
            db.commit()

    try:
        # called on silence too: that is how the 30-second nudge works
        event = questions.next_event(db, session_id, now_ms=end_ms)
    except Exception as err:
        if new_segment and segment is not None:  # undo, so the retry starts clean
            db.delete(segment)
            db.commit()
        if isinstance(err, llm.LLMError):
            raise HTTPException(status_code=502, detail="Layanan AI sedang sibuk. Potongan ini akan dikirim ulang.") from None
        raise

    db.add(AudioChunk(session_id=session_id, seq=seq, segment_id=segment.id if segment else None,
                      event_id=event["id"] if event else None))  # fmt: skip
    db.commit()
    return AudioReply(seq=seq, segment=_segment_out(segment), event=event)


def _stored_reply(db: Session, session_id: str, seq: int) -> AudioReply | None:
    chunk = db.exec(select(AudioChunk).where(AudioChunk.session_id == session_id, AudioChunk.seq == seq)).first()
    if chunk is None:
        return None
    segment = db.get(TranscriptSegment, chunk.segment_id) if chunk.segment_id else None
    event = db.get(Question, chunk.event_id) if chunk.event_id else None
    return AudioReply(seq=seq, segment=_segment_out(segment), event=questions.to_event(event) if event else None)


def _segment(db: Session, session_id: str, seq: int) -> TranscriptSegment | None:
    return db.exec(
        select(TranscriptSegment).where(TranscriptSegment.session_id == session_id, TranscriptSegment.seq == seq)
    ).first()


def _segment_out(segment: TranscriptSegment | None) -> SegmentOut | None:
    if segment is None:
        return None
    return SegmentOut(seq=segment.seq, start_ms=segment.start_ms, end_ms=segment.end_ms, text=segment.text)


def _read_wav(file: UploadFile) -> bytes:
    chunks, size = [], 0
    while block := file.file.read(READ_BLOCK):
        size += len(block)
        if size > MAX_BYTES:
            raise HTTPException(status_code=413, detail="Potongan audio terlalu besar.")
        chunks.append(block)
    data = b"".join(chunks)
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise HTTPException(status_code=400, detail="Audio harus berupa berkas WAV.")
    return data
