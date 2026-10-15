"""AI services: provider wrappers, question timing, and the shapes handed to app/api/."""

import httpx
import pymupdf
import pytest
from pydantic import BaseModel
from sqlmodel import select

from app.core.config import settings
from app.models import Material, MaterialChunk
from app.services import llm, profiles, rag, stt


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


def test_a_model_that_just_failed_is_skipped_next_time(monkeypatch):
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
    llm.generate_json("nilai", Answer)
    llm.generate_json("nilai", Answer)
    assert tried.count("gemini-sibuk") == 1  # the second call goes straight to the model that works


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


def test_whisper_echoing_its_own_prompt_is_dropped():
    assert stt.clean({"text": "Ada yang tahu kenapa hasilnya begitu?"}) == ""  # the style prompt, repeated on silence
    assert stt.clean({"text": "Ada yang tahu kenapa peluangnya setengah?"}) == "Ada yang tahu kenapa peluangnya setengah?"


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
    assert {"id", "subject", "grade", "phase", "label", "chapters"} == set(everything[0])
    assert all(profiles.get(p["id"])["tested"] for p in profiles.list_tested())


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


def test_closest_chunks_finds_the_page_being_talked_about(db, lesson, tmp_path):
    path = tmp_path / "bab.pdf"
    pdf = pymupdf.open()
    for text in (
        "Ruang sampel adalah himpunan semua hasil yang mungkin.",
        "Frekuensi harapan adalah banyaknya kejadian yang diperkirakan muncul.",
        "Dua kejadian saling lepas tidak dapat terjadi bersamaan.",
    ):
        pdf.new_page().insert_text((72, 72), text)
    pdf.save(path)
    material = Material(user_id=lesson.user_id, filename="bab.pdf", path=str(path), page_count=3)
    db.add(material)
    db.commit()
    rag.index_material(db, material.id)

    said = "Sekarang kita hitung frekuensi harapan dari percobaan tadi"
    assert [chunk.page for chunk in rag.closest_chunks(db, material.id, said, k=1)] == [2]
    assert rag.closest_chunks(db, material.id, said, k=1, skip_page=2) == []  # nothing else shares a word
    assert rag.closest_chunks(db, material.id, "selamat pagi semuanya") == []
