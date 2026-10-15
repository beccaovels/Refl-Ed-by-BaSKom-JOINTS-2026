"""Handwritten worked examples: reading a photo, the teacher's confirmation, the check, and its use in a lesson."""

import struct

import httpx
import pymupdf
import pytest
from pydantic import BaseModel
from sqlmodel import select

from app.core.config import settings
from app.models import Material, MaterialChunk, SlideEvent, TranscriptSegment
from app.services import examples, llm, metrics, questions, rag
from app.services.examples import Check, Reading, Step, StepCheck

SLIDE = "Peluang suatu kejadian adalah perbandingan banyak anggota kejadian dengan banyak anggota ruang sampel percobaan itu."

# Two dice, sum of seven. The second step is where a slip or a smudge is planted.
WRITTEN = Reading(
    readable=True,
    question="Dua dadu dilempar bersama. Berapa peluang jumlah mata dadu 7?",
    steps=[Step(text="n(S) = 36"), Step(text="n(A) = 5"), Step(text="P(A) = 5/36")],
    final_answer="5/36",
)
SMUDGED = WRITTEN.model_copy(
    update={"steps": [Step(text="n(S) = 36"), Step(text="n(A) = 5", unclear=True), Step(text="P(A) = 5/36")], "answer_unclear": True}
)
SLIP_FOUND = Check(
    our_answer="1/6.",
    answer="recheck",
    steps=[
        StepCheck(n=1, status="follows"),
        StepCheck(n=2, status="recheck", note="Tertulis n(A) = 5, sedangkan hitungan kami mendapat 6 pasangan."),
        StepCheck(n=3, status="follows"),
    ],
)
AGREES = Check(our_answer="1/6", answer="follows", steps=[StepCheck(n=n, status="follows") for n in (1, 2, 3)])


@pytest.fixture
def material(db, lesson, tmp_path):
    path = tmp_path / "bab.pdf"
    pdf = pymupdf.open()
    pdf.new_page().insert_textbox((50, 50, 550, 300), SLIDE)
    pdf.save(path)
    material = Material(user_id=lesson.user_id, filename="bab.pdf", path=str(path), page_count=1)
    db.add(material)
    db.commit()
    rag.index_material(db, material.id)
    return material


def photo(folder, name="contoh.png", width=400, height=300) -> str:
    picture = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, width, height), False)
    picture.clear_with(255)
    path = folder / name
    picture.save(path)
    return str(path)


def scripted(monkeypatch, reading, check=None) -> list:
    """Switch the provider on and script its two replies. Returns the calls it received."""
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    calls = []

    def generate(prompt, schema, **kwargs):
        calls.append({"schema": schema, "prompt": prompt, "images": kwargs.get("images", ()), "model": kwargs.get("model")})
        reply = reading if schema is Reading else check
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(llm, "generate_json", generate)
    return calls


def added(db, material, tmp_path, **kwargs):
    return examples.add(db, material.id, "contoh.png", photo(tmp_path, **kwargs))


def confirmed(db, material, tmp_path):
    """A photo that was read and then confirmed as read."""
    return examples.confirm(db, examples.read(db, added(db, material, tmp_path).id).id)


# --- llm ---


def test_a_photo_is_sent_to_gemini_with_the_prompt(monkeypatch):
    class Seen(BaseModel):
        text: str

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_model", "gemini-uji")
    monkeypatch.setattr(settings, "gemini_api_key", "kunci")
    sent = {}

    def post(url, **kwargs):
        sent.update(kwargs["json"])
        body = {"candidates": [{"content": {"parts": [{"text": '{"text": "n(S) = 36"}'}]}}]}
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    assert llm.generate_json("Salin tulisan ini", Seen, images=[(b"\xff\xd8foto", "image/jpeg")]).text == "n(S) = 36"
    picture, prompt = sent["contents"][0]["parts"]
    assert picture == {"inline_data": {"mime_type": "image/jpeg", "data": "/9hmb3Rv"}}
    assert prompt["text"].startswith("Salin tulisan ini")


def test_a_preferred_model_is_tried_first_and_the_usual_ones_follow(monkeypatch):
    class Seen(BaseModel):
        text: str

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_model", "gemini-biasa")
    monkeypatch.setattr(settings, "openai_api_key", "")
    tried = []

    def call(provider, model, *args):
        tried.append(model)
        if model == "gemini-baca":
            raise httpx.ReadTimeout("sibuk")
        return '{"text": "ok"}'

    monkeypatch.setattr(llm, "_call", call)
    assert llm.generate_json("salin", Seen, model="gemini-baca").text == "ok"
    assert tried == ["gemini-baca", "gemini-biasa"]

    tried.clear()
    llm._resting_until.clear()
    llm.generate_json("salin", Seen, model="gemini-biasa")  # naming the usual model does not try it twice
    llm.generate_json("salin", Seen)
    assert tried == ["gemini-biasa", "gemini-biasa"]


# --- a photo is a page ---


def test_a_photo_becomes_the_next_page_after_the_pdf(db, material, tmp_path):
    first, second = added(db, material, tmp_path), added(db, material, tmp_path)
    assert (first.page, second.page) == (2, 3)
    assert first.status == "reading"
    assert examples.public(first)["status_text"] == "Sedang dibaca…"


def test_fake_provider_reads_confirms_and_checks_without_a_key(db, material, tmp_path):
    example = examples.read(db, added(db, material, tmp_path).id)
    shown = examples.public(example)
    assert set(shown) == {"id", "material_id", "page", "status", "status_text", "reading", "check"}
    assert (shown["status"], shown["check"]) == ("unconfirmed", None)
    assert shown["status_text"].startswith("Apakah ini yang Anda tulis?")
    assert shown["reading"]["question"].startswith("(Contoh)")
    assert any(step["unclear"] for step in shown["reading"]["steps"])  # so the page can be built with a highlighted step

    shown = examples.public(examples.confirm(db, example.id))
    assert (shown["status"], shown["status_text"]) == ("confirmed", "")
    assert shown["check"]["answer"] == "follows"
    assert not any(step["unclear"] for step in shown["reading"]["steps"])


def test_splitting_the_pdf_again_keeps_the_text_of_a_photo(db, material, tmp_path):
    example = confirmed(db, material, tmp_path)
    rag.index_material(db, material.id)
    assert rag.page_text(db, material.id, 1) == SLIDE
    assert "Jawaban akhir: 1/6" in rag.page_text(db, material.id, example.page)
    assert len(db.exec(select(MaterialChunk).where(MaterialChunk.page == 1)).all()) == 1  # replaced, not doubled


def test_a_material_can_hold_photos_and_no_pdf(db, lesson, tmp_path):
    holder = Material(user_id=lesson.user_id)
    db.add(holder)
    db.commit()
    rag.index_material(db, holder.id)  # nothing to split, and no error
    example = examples.read(db, added(db, holder, tmp_path).id)
    assert example.page == 1
    assert rag.page_text(db, holder.id, 1).startswith("Contoh soal yang ditulis tangan oleh guru.")


# --- reading: the photo is copied, nothing is checked ---


def test_reading_copies_the_photo_and_checks_nothing(db, material, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "llm_vision_model", "gemini-baca")
    calls = scripted(monkeypatch, WRITTEN, SLIP_FOUND)
    example = examples.read(db, added(db, material, tmp_path, width=3_000, height=2_000).id, subject="Matematika")
    (reader,) = calls  # one call: the working is not compared with anything yet
    assert (reader["schema"], reader["model"]) == (Reading, "gemini-baca")
    ((data, kind),) = reader["images"]
    sent = pymupdf.Pixmap(data)
    assert kind == "image/jpeg" and (sent.width, sent.height) == (1_600, 1_067)  # a phone photo is sent smaller
    assert (example.status, example.check_result) == ("unconfirmed", None)
    assert examples.public(example)["check"] is None


def test_a_sideways_phone_photo_is_turned_upright(tmp_path):
    plain = tmp_path / "datar.jpg"
    pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 400, 200), False).save(plain, jpg_quality=90)
    data = plain.read_bytes()
    # The flag a phone writes when it is held upright: "turn this picture a quarter turn to show it".
    flag = b"Exif\x00\x00II*\x00\x08\x00\x00\x00" + struct.pack("<HHHIHHI", 1, 0x0112, 3, 1, 6, 0, 0)
    turned = tmp_path / "tegak.jpg"
    turned.write_bytes(data[:2] + b"\xff\xe1" + struct.pack(">H", len(flag) + 2) + flag + data[2:])
    sent = pymupdf.Pixmap(examples._photo(str(turned))[0])
    assert (sent.width, sent.height) == (200, 400)


def test_the_teachers_own_heading_is_not_repeated(db, material, tmp_path, monkeypatch):
    scripted(monkeypatch, WRITTEN.model_copy(update={"question": "Soal 1: Dua dadu dilempar bersama."}))
    example = examples.read(db, added(db, material, tmp_path).id)
    assert example.reading["question"] == "Dua dadu dilempar bersama."
    assert "Soal: Dua dadu dilempar bersama." in rag.page_text(db, material.id, example.page)


def test_a_part_that_was_not_read_clearly_stays_out_until_the_teacher_confirms(db, material, tmp_path, monkeypatch):
    scripted(monkeypatch, SMUDGED, AGREES)
    example = examples.read(db, added(db, material, tmp_path).id)
    text = rag.page_text(db, material.id, example.page)
    assert "Langkah 1: n(S) = 36" in text and "Langkah 3" in text
    assert "n(A) = 5" not in text and "Jawaban akhir" not in text  # an AI student never asks about a guess

    examples.confirm(db, example.id)
    text = rag.page_text(db, material.id, example.page)
    assert "Langkah 2: n(A) = 5" in text and "Jawaban akhir: 5/36" in text


# --- confirming: the teacher says what they wrote, then the check runs ---


def test_confirming_as_read_checks_exactly_that_text(db, material, tmp_path, monkeypatch):
    scripted(monkeypatch, SMUDGED)
    example = examples.read(db, added(db, material, tmp_path).id)

    calls = scripted(monkeypatch, WRITTEN, SLIP_FOUND)
    example = examples.confirm(db, example.id, subject="Matematika")
    (checker,) = calls  # the photo is not read again
    assert (checker["schema"], checker["images"], checker["model"]) == (Check, (), None)  # and never shown to the checker
    assert "2. n(A) = 5" in checker["prompt"] and "pada pelajaran Matematika" in checker["prompt"]
    assert example.status == "confirmed"
    assert not any(step["unclear"] for step in example.reading["steps"]) and not example.reading["answer_unclear"]
    assert examples.public(example)["check"]["steps"][1]["status"] == "recheck"  # the teacher vouched for this step


def test_the_teacher_can_fix_one_part_and_the_rest_stays(db, material, tmp_path, monkeypatch):
    scripted(monkeypatch, WRITTEN)
    example = examples.read(db, added(db, material, tmp_path).id)

    calls = scripted(monkeypatch, WRITTEN, AGREES)
    example = examples.confirm(db, example.id, steps=["n(S) = 36", " n(A) = 6 ", "", "P(A) = 6/36"], final_answer="1/6")
    assert example.reading["question"] == WRITTEN.question
    assert [step["text"] for step in example.reading["steps"]] == ["n(S) = 36", "n(A) = 6", "P(A) = 6/36"]
    assert "2. n(A) = 6" in calls[0]["prompt"] and "Jawaban akhir guru: 1/6" in calls[0]["prompt"]
    assert example.check_result["summary"] == "Langkah-langkah Anda sejalan dengan hitungan kami."
    text = rag.page_text(db, material.id, example.page)
    assert "Langkah 2: n(A) = 6" in text and "n(A) = 5" not in text


def test_an_edit_after_confirming_is_checked_again(db, material, tmp_path, monkeypatch):
    scripted(monkeypatch, WRITTEN, SLIP_FOUND)
    example = examples.confirm(db, examples.read(db, added(db, material, tmp_path).id).id)
    assert example.check_result["answer"] == "recheck"

    scripted(monkeypatch, WRITTEN, AGREES)
    example = examples.confirm(db, example.id, steps=["n(S) = 36", "n(A) = 6", "P(A) = 6/36"], final_answer="1/6")
    assert example.check_result["answer"] == "follows"


def test_a_photo_that_was_not_read_can_be_typed_in(db, material, tmp_path, monkeypatch):
    scripted(monkeypatch, Reading(readable=False), AGREES)
    example = examples.read(db, added(db, material, tmp_path).id)
    assert example.status == "unreadable"
    with pytest.raises(ValueError, match="no reading to confirm"):
        examples.confirm(db, example.id)

    example = examples.confirm(db, example.id, question=WRITTEN.question, steps=["n(S) = 36", "n(A) = 6", "P(A) = 6/36"], final_answer="1/6")
    assert (example.status, example.check_result["answer"]) == ("confirmed", "follows")
    assert "Langkah 3: P(A) = 6/36" in rag.page_text(db, material.id, example.page)


# --- what the check may say ---


def checked(db, material, tmp_path, monkeypatch, reading, check):
    scripted(monkeypatch, reading, check)
    return examples.confirm(db, examples.read(db, added(db, material, tmp_path).id).id).check_result


def test_a_step_that_differs_is_shown_with_a_plain_note(db, material, tmp_path, monkeypatch):
    check = checked(db, material, tmp_path, monkeypatch, WRITTEN, SLIP_FOUND)
    assert [step["status"] for step in check["steps"]] == ["follows", "recheck", "follows"]
    assert check["steps"][1]["note"] == "Tertulis n(A) = 5, sedangkan hitungan kami mendapat 6 pasangan."
    assert check["steps"][0]["note"] == ""
    assert (check["answer"], check["our_answer"]) == ("recheck", "1/6")
    assert check["summary"] == "Ada 1 langkah yang layak dicek ulang."


def test_only_the_final_answer_differs(db, material, tmp_path, monkeypatch):
    check = checked(db, material, tmp_path, monkeypatch, WRITTEN, AGREES.model_copy(update={"answer": "recheck"}))
    assert check["summary"] == "Jawaban akhir layak dicek ulang. Hitungan kami: 1/6."


def test_no_final_answer_written_means_no_verdict_on_it(db, material, tmp_path, monkeypatch):
    unfinished = WRITTEN.model_copy(update={"final_answer": ""})
    check = checked(db, material, tmp_path, monkeypatch, unfinished, AGREES.model_copy(update={"answer": "recheck"}))
    assert check["answer"] == "cannot_tell"
    assert check["summary"] == "Langkah-langkah Anda sejalan dengan hitungan kami."


@pytest.mark.parametrize(
    ("note", "shown"),
    [
        ("Langkah ini salah, n(A) adalah 6.", "Langkah 2 layak dicek ulang."),
        ("Guru seharusnya menulis 6.", "Langkah 2 layak dicek ulang."),
        ("", "Langkah 2 layak dicek ulang."),
        ("Tertulis 5, padahal salah satu pasangan belum dihitung.", "Tertulis 5, padahal salah satu pasangan belum dihitung."),
    ],
)
def test_a_note_that_passes_a_verdict_is_replaced_by_a_plain_line(db, material, tmp_path, monkeypatch, note, shown):
    found = SLIP_FOUND.model_copy(update={"steps": [StepCheck(n=2, status="recheck", note=note)]})
    check = checked(db, material, tmp_path, monkeypatch, WRITTEN, found)
    assert check["steps"][1]["note"] == shown
    assert [step["status"] for step in check["steps"]] == ["cannot_tell", "recheck", "cannot_tell"]  # skipped steps are not guessed


# --- when reading or checking does not work ---


def test_a_photo_that_cannot_be_read_has_no_text_and_no_check(db, material, tmp_path, monkeypatch):
    calls = scripted(monkeypatch, Reading(readable=False, question="Dua da"))
    example = examples.read(db, added(db, material, tmp_path).id)
    assert (example.status, example.reading, example.check_result) == ("unreadable", None, None)
    assert rag.page_text(db, material.id, example.page) == ""
    assert len(calls) == 1
    assert "tetap bisa ditampilkan" in examples.public(example)["status_text"]


def test_a_file_that_is_not_a_picture_is_unreadable(db, material, tmp_path, monkeypatch):
    calls = scripted(monkeypatch, WRITTEN, SLIP_FOUND)
    broken = tmp_path / "bukan-foto.jpg"
    broken.write_text("ini bukan foto")
    example = examples.read(db, examples.add(db, material.id, "bukan-foto.jpg", str(broken)).id)
    assert example.status == "unreadable" and calls == []


def test_a_busy_provider_leaves_the_photo_usable(db, material, tmp_path, monkeypatch):
    scripted(monkeypatch, llm.LLMError("sibuk"))
    example = examples.read(db, added(db, material, tmp_path).id)
    assert example.status == "failed"

    scripted(monkeypatch, WRITTEN, llm.LLMError("sibuk"))
    example = examples.read(db, example.id)  # reading again works once the provider answers
    assert example.status == "unconfirmed"
    example = examples.confirm(db, example.id)  # confirming still works when the check cannot run
    assert example.status == "confirmed"
    assert {step["status"] for step in example.check_result["steps"]} == {"cannot_tell"}
    assert example.check_result["summary"] == examples.NOT_CHECKED

    scripted(monkeypatch, WRITTEN, SLIP_FOUND)
    assert examples.confirm(db, example.id).check_result["answer"] == "recheck"  # and can be asked for again


# --- in the lesson ---


def say(db, lesson, seq, start_ms, end_ms, text):
    db.add(TranscriptSegment(session_id=lesson.id, seq=seq, start_ms=start_ms, end_ms=end_ms, text=text))
    db.commit()


def test_the_ai_students_see_the_example_that_is_on_screen(db, lesson, material, tmp_path):
    example = confirmed(db, material, tmp_path)
    lesson.material_id = material.id
    db.add(lesson)
    db.add(SlideEvent(session_id=lesson.id, page=1, t_ms=0))
    db.add(SlideEvent(session_id=lesson.id, page=example.page, t_ms=30_000))
    db.commit()
    text, page = questions._slide(db, lesson)
    assert page == example.page
    assert "Soal: (Contoh) Dua dadu dilempar bersama." in text and "Langkah 3: P(A) = n(A) / n(S) = 6/36" in text


def test_walking_through_your_own_working_is_not_reading_the_slide(db, lesson, material, tmp_path, monkeypatch):
    long_step = "peluang jumlah tujuh adalah enam pasangan dari tiga puluh enam pasangan yang mungkin muncul pada dua dadu"
    scripted(monkeypatch, WRITTEN.model_copy(update={"steps": [Step(text=long_step)]}))
    example = examples.read(db, added(db, material, tmp_path).id)
    lesson.material_id = material.id
    db.add(lesson)
    db.add(SlideEvent(session_id=lesson.id, page=1, t_ms=0))
    db.add(SlideEvent(session_id=lesson.id, page=example.page, t_ms=20_000))
    db.commit()
    say(db, lesson, 0, 0, 10_000, "Coba bayangkan kalian melempar dua dadu di atas meja, apa saja yang mungkin muncul")
    say(db, lesson, 1, 21_000, 32_000, f"Jadi {long_step}")
    assert metrics.compute(db, lesson.id).reading_share == 0  # the second piece matches the photo word for word

    say(db, lesson, 2, 40_000, 50_000, "Sekarang kita kembali ke contoh tadi")
    db.add(SlideEvent(session_id=lesson.id, page=1, t_ms=52_000))
    db.commit()
    say(db, lesson, 3, 53_000, 64_000, SLIDE)
    assert metrics.compute(db, lesson.id).reading_share > 0  # reading the slide itself still counts


def test_photos_alone_give_no_reading_share(db, lesson, tmp_path):
    holder = Material(user_id=lesson.user_id)
    db.add(holder)
    db.commit()
    example = examples.read(db, added(db, holder, tmp_path).id)
    lesson.material_id = holder.id
    db.add(lesson)
    db.add(SlideEvent(session_id=lesson.id, page=example.page, t_ms=0))
    db.commit()
    say(db, lesson, 0, 0, 10_000, "Dua dadu dilempar bersama, berapa peluang jumlah mata dadu tujuh")
    assert metrics.compute(db, lesson.id).reading_share is None
