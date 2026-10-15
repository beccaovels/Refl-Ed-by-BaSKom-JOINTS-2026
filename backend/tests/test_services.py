"""AI services: provider wrappers, question timing, and the shapes handed to app/api/."""

import httpx
import pymupdf
import pytest
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings
from app.models import Material, MaterialChunk, Question, TeachingSession, TranscriptSegment, User
from app.services import llm, profiles, questions, rag, scoring, stt


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests never call a provider, whatever is in the local .env."""
    monkeypatch.setattr(settings, "stt_provider", "fake")
    monkeypatch.setattr(settings, "llm_provider", "fake")


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def lesson(db):
    user = User(name="Bu Rina", email="rina@example.com")
    db.add(user)
    db.commit()
    session = TeachingSession(
        user_id=user.id, profile_id="matematika-fase-e", class_name="X-1", subject="Matematika", chapter="Fungsi kuadrat"
    )
    db.add(session)
    db.commit()
    return session


def speak(db, lesson, seq, start_ms, end_ms):
    db.add(TranscriptSegment(session_id=lesson.id, seq=seq, start_ms=start_ms, end_ms=end_ms, text="penjelasan"))
    db.commit()


class Answer(BaseModel):
    score: int


# --- llm ---


def test_valid_reply_is_parsed_without_retry(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    replies = iter(['```json\n{"score": 4}\n```'])
    monkeypatch.setattr(llm, "_complete", lambda *args: next(replies))
    assert llm.generate_json("nilai", Answer).score == 4


def test_invalid_reply_triggers_exactly_one_retry(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    prompts = []

    def complete(prompt, *args):
        prompts.append(prompt)
        return '{"score": "empat"}' if len(prompts) == 1 else '{"score": 4}'

    monkeypatch.setattr(llm, "_complete", complete)
    assert llm.generate_json("nilai", Answer).score == 4
    assert len(prompts) == 2
    assert "ditolak" in prompts[1]


def test_busy_gemini_model_falls_back_to_the_next_one(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_model", "gemini-sibuk")
    monkeypatch.setattr(settings, "openai_api_key", "")
    tried = []

    def call(provider, model, *args):
        tried.append(model)
        if model == "gemini-sibuk":
            raise httpx.ReadTimeout("sibuk")
        return '{"score": 4}'

    monkeypatch.setattr(llm, "_call", call)
    assert llm.generate_json("nilai", Answer).score == 4
    assert tried == ["gemini-sibuk", llm.GEMINI_FALLBACK_MODELS[0]]


def test_every_model_busy_raises_llm_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "openai_api_key", "")

    def call(*args):
        raise httpx.ReadTimeout("sibuk")

    monkeypatch.setattr(llm, "_call", call)
    with pytest.raises(llm.LLMError):
        llm.generate_json("nilai", Answer)


def test_two_invalid_replies_raise(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    calls = []
    monkeypatch.setattr(llm, "_complete", lambda *args: calls.append(1) or "bukan json")
    with pytest.raises(llm.LLMError):
        llm.generate_json("nilai", Answer)
    assert len(calls) == 2


# --- stt ---


def test_silent_segments_and_stock_phrases_are_dropped():
    payload = {
        "segments": [
            {"text": " Hari ini kita belajar fungsi kuadrat.", "no_speech_prob": 0.02},
            {"text": " Terima kasih telah menonton.", "no_speech_prob": 0.91},
        ]
    }
    assert stt.clean(payload) == "Hari ini kita belajar fungsi kuadrat."
    assert stt.clean({"text": "Terima kasih telah menonton."}) == ""
    assert stt.clean({"segments": [{"text": " ...", "no_speech_prob": 0.8}]}) == ""


def test_fake_provider_needs_no_key(monkeypatch):
    monkeypatch.setattr(settings, "stt_provider", "fake")
    assert stt.transcribe(b"")


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(settings, "stt_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "")
    with pytest.raises(stt.STTError, match="STT_PROVIDER=fake"):
        stt.transcribe(b"")


# --- profiles ---


def test_untested_profiles_are_hidden():
    everything = profiles.list_tested(include_untested=True)
    assert {"id", "subject", "grade", "phase", "label"} == set(everything[0])
    assert all(profiles.get(p["id"])["tested"] for p in profiles.list_tested())


# --- questions ---


def test_no_question_before_the_interval(db, lesson):
    speak(db, lesson, 0, 0, 40_000)
    assert questions.next_event(db, lesson.id, now_ms=40_000) is None


def test_question_after_enough_speech_then_waits_for_the_answer(db, lesson):
    speak(db, lesson, 0, 0, 40_000)
    speak(db, lesson, 1, 41_000, 80_000)
    event = questions.next_event(db, lesson.id, now_ms=80_000)
    assert event["kind"] == "regular"
    assert set(event) == {"id", "kind", "persona", "text", "asked_at_ms", "refers_to_ms"}
    assert set(event["persona"]) == {"name", "style"}
    assert event["refers_to_ms"] == 41_000

    # a silent chunk while the question is open: nothing new, not even a nudge
    assert questions.next_event(db, lesson.id, now_ms=120_000) is None

    speak(db, lesson, 2, 121_000, 130_000)
    assert questions.next_event(db, lesson.id, now_ms=130_000) is None
    assert db.get(Question, event["id"]).answered_at_ms == 121_000


def test_question_wording_comes_from_the_llm(db, lesson, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    prompts = []

    def generate(prompt, schema, **kwargs):
        prompts.append(prompt)
        return schema(text="Kenapa grafiknya melengkung?", refers_to_line=1)

    monkeypatch.setattr(llm, "generate_json", generate)
    speak(db, lesson, 0, 0, 40_000)
    speak(db, lesson, 1, 41_000, 80_000)
    event = questions.next_event(db, lesson.id, now_ms=80_000)
    assert event["text"] == "Kenapa grafiknya melengkung?"
    assert event["refers_to_ms"] == 0
    assert "1. penjelasan\n2. penjelasan" in prompts[0] and "Fungsi kuadrat" in prompts[0]


def test_provider_failure_falls_back_to_a_canned_question(db, lesson, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")

    def fail(*args, **kwargs):
        raise llm.LLMError("503")

    monkeypatch.setattr(llm, "generate_json", fail)
    speak(db, lesson, 0, 0, 80_000)
    assert questions.next_event(db, lesson.id, now_ms=80_000)["text"] in questions.CANNED_QUESTIONS


def test_one_nudge_per_silence(db, lesson):
    speak(db, lesson, 0, 0, 10_000)
    assert questions.next_event(db, lesson.id, now_ms=45_000)["kind"] == "nudge"
    assert questions.next_event(db, lesson.id, now_ms=80_000) is None
    speak(db, lesson, 1, 81_000, 90_000)
    assert questions.next_event(db, lesson.id, now_ms=90_000) is None


def test_capstone_is_stored(db, lesson):
    speak(db, lesson, 0, 0, 10_000)
    event = questions.capstone(db, lesson.id)
    assert event["kind"] == "capstone" and event["asked_at_ms"] == 10_000
    assert db.exec(select(Question).where(Question.kind == "capstone")).one().id == event["id"]


# --- rag ---


def test_pdf_is_split_into_chunks_per_page(db, lesson, tmp_path):
    path = tmp_path / "bab.pdf"
    pdf = pymupdf.open()
    for text in ("Fungsi kuadrat berbentuk parabola.", "Titik puncak adalah titik balik grafik."):
        pdf.new_page().insert_text((72, 72), text)
    pdf.save(path)
    material = Material(user_id=lesson.user_id, filename="bab.pdf", path=str(path), page_count=2)
    db.add(material)
    db.commit()

    rag.index_material(db, material.id)
    rag.index_material(db, material.id)  # a second call replaces, never duplicates

    assert len(db.exec(select(MaterialChunk)).all()) == 2
    assert rag.page_text(db, material.id, 2) == "Titik puncak adalah titik balik grafik."


# --- scoring ---

BANNED = ("lacking", "poor", "weak", "should", "kurang", "lemah", "seharusnya")


def test_report_shape_and_feedback_rules(db, lesson):
    questions.capstone(db, lesson.id)
    report = scoring.build_report(db, lesson.id)

    assert set(report) == {
        "id", "session_id", "created_at", "overall", "strengths", "dimensions", "ideas", "metrics", "questions",
    }  # fmt: skip
    assert [d["key"] for d in report["dimensions"]] == [
        "content_accuracy", "teaching_flow", "clarity", "engagement", "pacing", "on_camera_presence",
    ]  # fmt: skip
    assert report["strengths"] and report["strengths"][0]["kind"] == "worked"
    assert len(report["ideas"]) <= 3
    assert not any(word in str(report).lower() for word in BANNED)

    by_key = {d["key"]: d for d in report["dimensions"]}
    assert by_key["pacing"]["locked"] and by_key["pacing"]["score"] is None  # free tier
    assert not by_key["on_camera_presence"]["available"]  # camera off
    assert len(report["questions"]) == 1
