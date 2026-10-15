"""AI student questions: when one is asked, and what it says.

Called once per audio chunk. The timing rules are plain code; only the wording
of a question comes from the LLM.
"""

import json
import logging
from pathlib import Path
from string import Template

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.models import Question, SlideEvent, TeachingSession, TranscriptSegment
from app.services import llm, profiles, rag

log = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

DEMO_INTERVAL_MS = 75_000  # demo mode: a question every 60-90 s of speech
NORMAL_INTERVAL_MS = 240_000
SILENCE_NUDGE_MS = 30_000
WINDOW_MS = 120_000  # how much recent speech the model reads
SLIDE_CHARS = 1_500
# The teacher is mid-lesson while this runs, so a slow provider is cut off.
LLM_TIMEOUT_S = 12

STUDENT_NAMES = ["Dimas", "Sari", "Rizky"]
DEFAULT_STYLE = "Murid yang bertanya singkat dengan bahasa sehari-hari."

NUDGE_TEXT = "Silakan lanjutkan kapan pun Anda siap. Kami masih menyimak."

# Used with LLM_PROVIDER=fake, and when the provider fails, so the room never stalls.
CANNED_QUESTIONS = [
    "Maaf, boleh diberi satu contoh lagi untuk bagian yang tadi?",
    "Kalau di kehidupan sehari-hari, ini dipakainya untuk apa ya?",
    "Kenapa caranya harus seperti itu? Ada cara lain tidak?",
]
CANNED_CAPSTONE = "Jadi kalau dirangkum dalam satu kalimat, hal terpenting dari pelajaran hari ini apa ya?"


class StudentQuestion(BaseModel):
    text: str = Field(min_length=5, description="Pertanyaan murid, satu atau dua kalimat pendek")
    refers_to_line: int = Field(description="Nomor baris transkrip yang ditanyakan")


def next_event(db: Session, session_id: str, now_ms: int) -> dict | None:
    """The Event to send with this audio reply, or None.

    `now_ms` is the end_ms of the chunk that was just received, with or without speech in it.
    """
    session = _session(db, session_id)
    if session.status != "active":
        return None
    segments = _segments(db, session_id)
    asked = _asked(db, session_id)
    students = [q for q in asked if q.kind != "nudge"]
    last = students[-1] if students else None
    spoken_since = [s for s in segments if s.start_ms >= (last.asked_at_ms if last else 0)]

    # The first words after a student's question are the start of the answer.
    if last and last.answered_at_ms is None:
        if not spoken_since:
            return None
        last.answered_at_ms = spoken_since[0].start_ms
        db.add(last)
        db.commit()

    # One nudge per silence: the next one needs speech in between.
    last_speech_ms = segments[-1].end_ms if segments else 0
    already_nudged = bool(asked) and asked[-1].kind == "nudge" and asked[-1].asked_at_ms >= last_speech_ms
    if now_ms - last_speech_ms >= SILENCE_NUDGE_MS:
        if already_nudged:
            return None
        return _save(db, session, kind="nudge", text=NUDGE_TEXT, asked_at_ms=now_ms)

    interval = DEMO_INTERVAL_MS if session.demo_mode else NORMAL_INTERVAL_MS
    if sum(s.end_ms - s.start_ms for s in spoken_since) < interval:
        return None
    count = sum(1 for q in students if q.kind == "regular")
    persona = _persona(session, count)
    recent = [s for s in segments if s.end_ms >= now_ms - WINDOW_MS]
    text, refers_to_ms = _write_question(db, session, persona, recent, students)
    if text is None:
        text, refers_to_ms = CANNED_QUESTIONS[count % len(CANNED_QUESTIONS)], spoken_since[-1].start_ms
    return _save(
        db, session, kind="regular", text=text, asked_at_ms=now_ms, refers_to_ms=refers_to_ms, persona=persona
    )


def capstone(db: Session, session_id: str) -> dict:
    """The one closing question, asked when the teacher presses "Selesai mengajar"."""
    session = _session(db, session_id)
    segments = _segments(db, session_id)
    asked = _asked(db, session_id)
    asked_at_ms = max(segments[-1].end_ms if segments else 0, asked[-1].asked_at_ms if asked else 0)
    return _save(
        db, session, kind="capstone", text=CANNED_CAPSTONE, asked_at_ms=asked_at_ms, persona=_persona(session, len(asked))
    )


def _write_question(
    db: Session, session: TeachingSession, persona: dict, recent: list[TranscriptSegment], asked: list[Question]
) -> tuple[str | None, int | None]:
    """The question's wording and the moment it refers to, or (None, None) to use a canned one."""
    if llm.is_fake() or not recent:
        return None, None
    profile = profiles.get(session.profile_id) or {}
    prompt = Template((PROMPT_DIR / "question.md").read_text(encoding="utf-8")).substitute(
        name=persona["name"],
        style=persona["style"],
        label=profile.get("label", session.class_name),
        age=profile.get("student_persona", {}).get("age", "15-17"),
        subject=session.subject,
        chapter=" - ".join(part for part in (session.chapter, session.sub_chapter) if part),
        slide=_slide_text(db, session) or "(tidak ada materi yang ditampilkan)",
        transcript="\n".join(f"{line}. {s.text}" for line, s in enumerate(recent, start=1)),
        asked="\n".join(f"- {q.text}" for q in asked) or "(belum ada)",
    )
    try:
        reply = llm.generate_json(prompt, StudentQuestion, timeout_s=LLM_TIMEOUT_S)
    except llm.LLMError as err:
        log.warning("Question wording failed, using a canned question: %s", err)
        return None, None
    line = reply.refers_to_line if 1 <= reply.refers_to_line <= len(recent) else len(recent)
    return reply.text.strip(), recent[line - 1].start_ms


def _slide_text(db: Session, session: TeachingSession) -> str:
    """Text of the page on screen right now, from the last page turn."""
    if not session.material_id:
        return ""
    turn = db.exec(
        select(SlideEvent).where(SlideEvent.session_id == session.id).order_by(SlideEvent.t_ms.desc())
    ).first()
    return rag.page_text(db, session.material_id, turn.page if turn else 1)[:SLIDE_CHARS]


def _session(db: Session, session_id: str) -> TeachingSession:
    session = db.get(TeachingSession, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")
    return session


def _segments(db: Session, session_id: str) -> list[TranscriptSegment]:
    return list(
        db.exec(
            select(TranscriptSegment).where(TranscriptSegment.session_id == session_id).order_by(TranscriptSegment.seq)
        )
    )


def _asked(db: Session, session_id: str) -> list[Question]:
    return list(db.exec(select(Question).where(Question.session_id == session_id).order_by(Question.asked_at_ms)))


def _persona(session: TeachingSession, index: int) -> dict:
    profile = profiles.get(session.profile_id) or {}
    style = profile.get("student_persona", {}).get("style", DEFAULT_STYLE)
    return {"name": STUDENT_NAMES[index % len(STUDENT_NAMES)], "style": style}


def _save(
    db: Session,
    session: TeachingSession,
    *,
    kind: str,
    text: str,
    asked_at_ms: int,
    refers_to_ms: int | None = None,
    persona: dict | None = None,
) -> dict:
    question = Question(
        session_id=session.id,
        kind=kind,
        persona=json.dumps(persona, ensure_ascii=False) if persona else None,
        text=text,
        asked_at_ms=asked_at_ms,
        refers_to_ms=refers_to_ms,
    )
    db.add(question)
    db.commit()
    return to_event(question)


def to_event(question: Question) -> dict:
    """A stored question in the Event shape of docs/api-contract.md."""
    return {
        "id": question.id,
        "kind": question.kind,
        "persona": json.loads(question.persona) if question.persona else None,
        "text": question.text,
        "asked_at_ms": question.asked_at_ms,
        "refers_to_ms": question.refers_to_ms,
    }
