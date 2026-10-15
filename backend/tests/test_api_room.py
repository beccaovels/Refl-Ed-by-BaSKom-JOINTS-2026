"""Room endpoints: audio pieces, page turns, signal bins, ending the lesson, and one whole lesson."""

import io
import wave

import pymupdf
import pytest
from sqlmodel import Session, select

from app.models import AudioChunk, Question, SignalBin, SlideEvent, TranscriptSegment
from app.services import stt


def wav() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16_000)
        w.writeframes(b"\x00\x00" * 1_600)
    return buffer.getvalue()


@pytest.fixture
def speech(monkeypatch):
    """stt.transcribe replaced by a script: each call returns the next line, and calls are counted."""
    calls = []

    def script(*lines):
        lines = list(lines)

        def transcribe(wav_bytes, language="id"):
            calls.append(1)
            return lines.pop(0) if lines else "penjelasan berlanjut"

        monkeypatch.setattr(stt, "transcribe", transcribe)
        return calls

    return script


@pytest.fixture
def room(client, login):
    me = login()
    body = {"profile_id": "matematika-fase-e", "class_name": "X-1", "subject": "Matematika", "chapter": "Peluang"}
    session = client.post("/api/sessions", json=body, headers=me).json()
    return {"headers": me, "id": session["id"]}


def send(client, room, seq, start_ms, end_ms, data=None, headers=None):
    return client.post(
        f"/api/sessions/{room['id']}/audio",
        data={"seq": seq, "start_ms": start_ms, "end_ms": end_ms},
        files={"file": ("piece.wav", wav() if data is None else data, "audio/wav")},
        headers=room["headers"] if headers is None else headers,
    )


def count(engine, model):
    with Session(engine) as db:
        return len(db.exec(select(model)).all())


# --- audio ---


def test_speech_is_transcribed_and_stored(client, room, speech, engine):
    speech("Hari ini kita belajar peluang.")
    r = send(client, room, 0, 0, 4_000)
    assert r.status_code == 200
    assert r.json() == {
        "seq": 0, "segment": {"seq": 0, "start_ms": 0, "end_ms": 4_000, "text": "Hari ini kita belajar peluang."},
        "event": None,
    }  # fmt: skip
    assert count(engine, TranscriptSegment) == 1


def test_a_resent_piece_gets_the_first_reply_and_nothing_else_happens(client, room, speech, engine):
    calls = speech("Hari ini kita belajar peluang.")
    first = send(client, room, 0, 0, 4_000).json()
    again = send(client, room, 0, 0, 4_000).json()
    assert again == first and len(calls) == 1 and count(engine, TranscriptSegment) == 1


def test_a_silent_piece_has_no_segment_and_its_repeat_is_still_recognised(client, room, speech, engine):
    calls = speech("")
    assert send(client, room, 0, 0, 3_000).json() == {"seq": 0, "segment": None, "event": None}
    assert send(client, room, 0, 0, 3_000).json() == {"seq": 0, "segment": None, "event": None}
    assert len(calls) == 1 and count(engine, TranscriptSegment) == 0 and count(engine, AudioChunk) == 1


def test_silence_still_reaches_the_question_engine_and_brings_one_nudge(client, room, speech, engine):
    speech("Baik, kita mulai.", "")
    send(client, room, 0, 0, 2_000)
    event = send(client, room, 1, 2_000, 40_000).json()["event"]
    assert event["kind"] == "nudge" and event["persona"] is None
    assert send(client, room, 1, 2_000, 40_000).json()["event"]["id"] == event["id"]  # retry: same nudge
    assert count(engine, Question) == 1


def test_enough_speech_brings_a_student_question_once(client, room, speech, engine):
    speech()
    replies = [send(client, room, i, i * 20_000, i * 20_000 + 19_000).json() for i in range(5)]
    events = [r["event"] for r in replies if r["event"]]
    assert len(events) == 1 and events[0]["kind"] == "regular" and events[0]["persona"]["name"]
    seq = next(r["seq"] for r in replies if r["event"])
    assert send(client, room, seq, seq * 20_000, seq * 20_000 + 19_000).json()["event"] == events[0]
    assert count(engine, Question) == 1


def test_a_provider_failure_is_502_and_the_retry_works(client, room, monkeypatch, engine):
    def down(wav_bytes, language="id"):
        raise stt.STTError("groq is down")

    monkeypatch.setattr(stt, "transcribe", down)
    r = send(client, room, 0, 0, 4_000)
    assert r.status_code == 502 and r.json()["detail"]
    assert count(engine, AudioChunk) == 0 and count(engine, TranscriptSegment) == 0

    monkeypatch.setattr(stt, "transcribe", lambda wav_bytes, language="id": "Sudah kembali.")
    assert send(client, room, 0, 0, 4_000).json()["segment"]["text"] == "Sudah kembali."


def test_a_half_finished_earlier_attempt_is_completed_without_transcribing_again(client, room, speech, engine):
    calls = speech("tidak dipakai")
    with Session(engine) as db:
        db.add(TranscriptSegment(session_id=room["id"], seq=0, start_ms=0, end_ms=4_000, text="Sudah ditranskripsi."))
        db.commit()
    assert send(client, room, 0, 0, 4_000).json()["segment"]["text"] == "Sudah ditranskripsi."
    assert calls == [] and count(engine, TranscriptSegment) == 1


@pytest.mark.parametrize(
    "fields, data, status",
    [({"seq": -1, "start_ms": 0, "end_ms": 1}, None, 422), ({"seq": 0, "start_ms": 5_000, "end_ms": 1_000}, None, 422),
     ({"seq": 0, "start_ms": 0, "end_ms": 1_000}, b"not a wav file", 400)],
)  # fmt: skip
def test_invalid_audio_requests_are_rejected(client, room, fields, data, status):
    assert send(client, room, data=data, **fields).status_code == status


def test_missing_audio_fields_are_422(client, room):
    r = client.post(f"/api/sessions/{room['id']}/audio", data={"seq": 0}, headers=room["headers"])
    assert r.status_code == 422


def test_another_teachers_session_is_not_found(client, room, login):
    other = login("Pak Budi", "budi@example.com")
    assert send(client, room, 0, 0, 1_000, headers=other).status_code == 404


def test_after_finish_new_audio_is_refused_but_a_resent_piece_still_gets_its_reply(client, room, speech):
    speech("Kalimat terakhir.")
    first = send(client, room, 0, 0, 2_000).json()
    client.post(f"/api/sessions/{room['id']}/finish", headers=room["headers"])
    assert send(client, room, 1, 2_000, 4_000).status_code == 409
    assert send(client, room, 0, 0, 2_000).json() == first


# --- slides ---


def test_page_turns_are_stored_once(client, room, engine):
    url = f"/api/sessions/{room['id']}/slides"
    for body in ({"page": 1, "t_ms": 0}, {"page": 2, "t_ms": 30_000}, {"page": 2, "t_ms": 30_000}):
        assert client.post(url, json=body, headers=room["headers"]).status_code == 204
    with Session(engine) as db:
        assert [(t.page, t.t_ms) for t in db.exec(select(SlideEvent).order_by(SlideEvent.t_ms))] == [(1, 0), (2, 30_000)]


def test_invalid_page_turns_are_422(client, login):
    me = login()
    pdf = pymupdf.open()
    pdf.new_page()
    material = client.post(
        "/api/materials", files={"file": ("satu.pdf", pdf.tobytes(), "application/pdf")}, headers=me
    ).json()
    body = {"profile_id": "matematika-fase-e", "class_name": "X-1", "subject": "Matematika", "chapter": "Peluang",
            "material_id": material["id"]}  # fmt: skip
    session = client.post("/api/sessions", json=body, headers=me).json()
    url = f"/api/sessions/{session['id']}/slides"
    assert client.post(url, json={"page": 0, "t_ms": 0}, headers=me).status_code == 422
    assert client.post(url, json={"page": 2, "t_ms": 0}, headers=me).status_code == 422  # the PDF has one page


# --- signals ---


def test_camera_off_bins_are_stored_with_null_camera_values(client, room, engine):
    bins = [{"t_start_ms": 0, "volume": 0.4, "pitch_variation": 2.5}, {"t_start_ms": 10_000, "volume": 0.3,
            "pitch_variation": None}]  # fmt: skip
    assert client.post(f"/api/sessions/{room['id']}/signals", json={"bins": bins}, headers=room["headers"]).status_code == 204
    with Session(engine) as db:
        stored = db.exec(select(SignalBin).order_by(SignalBin.t_start_ms)).all()
        assert [b.volume for b in stored] == [0.4, 0.3] and stored[0].facing_pct is None and stored[0].measured


def test_repeated_bins_are_ignored(client, room, engine):
    url = f"/api/sessions/{room['id']}/signals"
    full = {"t_start_ms": 0, "facing_pct": 0.9, "posture_ok_pct": 0.8, "gesture_rate": 0.2, "expressiveness": 0.3,
            "face_visible_pct": 1.0, "volume": 0.5, "pitch_variation": 3.0, "measured": True}  # fmt: skip
    client.post(url, json={"bins": [full, full | {"facing_pct": 0.1}]}, headers=room["headers"])
    client.post(url, json={"bins": [full | {"facing_pct": 0.2}, full | {"t_start_ms": 10_000}]}, headers=room["headers"])
    with Session(engine) as db:
        stored = db.exec(select(SignalBin).order_by(SignalBin.t_start_ms)).all()
        assert [(b.t_start_ms, b.facing_pct) for b in stored] == [(0, 0.9), (10_000, 0.9)]


@pytest.mark.parametrize(
    "bin_", [{"t_start_ms": 0, "frame": "data:image/jpeg;base64,..."}, {"t_start_ms": 0, "facing_pct": 1.5},
             {"volume": 0.5}],
)  # fmt: skip
def test_anything_beyond_the_signal_numbers_is_rejected(client, room, bin_):
    r = client.post(f"/api/sessions/{room['id']}/signals", json={"bins": [bin_]}, headers=room["headers"])
    assert r.status_code == 422


# --- ending ---


def test_end_returns_one_capstone_however_often_it_is_pressed(client, room, engine):
    url = f"/api/sessions/{room['id']}/end"
    first = client.post(url, headers=room["headers"]).json()["event"]
    assert first["kind"] == "capstone" and first["text"]
    assert client.post(url, headers=room["headers"]).json()["event"] == first
    with Session(engine) as db:
        assert len(db.exec(select(Question).where(Question.kind == "capstone")).all()) == 1


def test_end_after_finish_is_409(client, room):
    client.post(f"/api/sessions/{room['id']}/finish", headers=room["headers"])
    assert client.post(f"/api/sessions/{room['id']}/end", headers=room["headers"]).status_code == 409


# --- a whole lesson ---


def test_a_whole_lesson_from_login_to_report(client, room, speech):
    speech()
    for i in range(6):
        assert send(client, room, i, i * 20_000, i * 20_000 + 19_000).status_code == 200
    client.post(f"/api/sessions/{room['id']}/signals", json={"bins": [{"t_start_ms": 0, "volume": 0.4}]},
                headers=room["headers"])  # fmt: skip
    capstone = client.post(f"/api/sessions/{room['id']}/end", headers=room["headers"]).json()["event"]
    send(client, room, 6, 125_000, 135_000)  # the answer to the closing question
    assert client.post(f"/api/sessions/{room['id']}/finish", headers=room["headers"]).status_code == 202

    report = client.get(f"/api/sessions/{room['id']}/report", headers=room["headers"])
    assert report.status_code == 200
    assert capstone["id"] in [q["event_id"] for q in report.json()["questions"]]
    session = client.get(f"/api/sessions/{room['id']}", headers=room["headers"]).json()
    assert session["status"] == "ended" and session["ended_at"]
    listed = client.get("/api/sessions", headers=room["headers"]).json()
    assert listed[0]["overall_score"] == report.json()["overall"]["score"]
