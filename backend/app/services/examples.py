"""Handwritten worked examples: read a photo of the teacher's own working, let them confirm it, then check it.

The order matters, because a misread must never be held against the teacher:
1. read     the photo is copied into text, nothing more             -> `unconfirmed`
2. confirm  the teacher says "yes, that is what I wrote", or edits   -> `confirmed`
3. check    only now is the working compared with our own, on exactly the text the teacher confirmed

Reading and checking are two separate LLM calls. The reader sees only the photo
and is told to copy, never to correct. The checker sees only the confirmed text,
never the photo. A reader that also checks tends to "see" the number that ought
to be there.

A photo is a page of the material, numbered after the PDF's last page, so the AI
students and the report find its text the same way they find a slide's.
"""

import logging
import re
from collections.abc import Iterable
from pathlib import Path
from string import Template
from typing import Literal

import pymupdf
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.config import settings
from app.models import Material, MaterialFile, WorkedExample
from app.services import evidence, llm, rag

log = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

MAX_SIDE_PX = 1_600  # enough to read handwriting; keeps a phone photo to a quick upload
JPEG_QUALITY = 85

# A check note that passes a verdict is replaced by the plain line. "salah satu" (one of) is ordinary speech.
_VERDICT = re.compile(r"\b(salah(?! satu)|keliru)\b")
# Teachers often head the question "Soal:" or "Soal 1."; the label is ours to add, once.
_LABEL = re.compile(r"^(soal|pertanyaan)\s*\d*\s*[:.)]\s*", re.IGNORECASE)

STATUS_TEXT = {
    "reading": "Sedang dibaca…",
    "unconfirmed": "Apakah ini yang Anda tulis? Anda bisa memperbaikinya dulu.",
    "confirmed": "",
    "unreadable": "Tulisan pada foto ini belum terbaca. Foto tetap bisa ditampilkan, dan Anda bisa mengetik isinya sendiri.",
    "failed": "Foto belum sempat dibaca. Foto tetap bisa ditampilkan, dan Anda bisa mengetik isinya sendiri.",
}
ALL_FOLLOW = "Langkah-langkah Anda sejalan dengan hitungan kami."
NOT_CHECKED = "Kami belum bisa memeriksa contoh ini. Anda tetap bisa memakainya saat mengajar."

# Used with LLM_PROVIDER=fake so the pages can be built without a key.
CANNED_READING = {
    "question": "(Contoh) Dua dadu dilempar bersama. Berapa peluang jumlah mata dadu 7?",
    "steps": [
        {"n": 1, "text": "n(S) = 6 × 6 = 36", "unclear": False},
        {"n": 2, "text": "A = {(1,6), (2,5), (3,4), (4,3), (5,2), (6,1)}, jadi n(A) = 6", "unclear": True},
        {"n": 3, "text": "P(A) = n(A) / n(S) = 6/36", "unclear": False},
    ],
    "final_answer": "1/6",
    "answer_unclear": False,
}

Verdict = Literal["follows", "recheck", "cannot_tell"]


# A picture the teacher shows as material (not a worked example), used with LLM_PROVIDER=fake.
CANNED_PICTURE = ["(Contoh) Tabel ruang sampel pelemparan dua koin: AA, AG, GA, GG. Peluang muncul dua angka = 1/4."]
MAX_PICTURE_CHARS = 4_000  # what a picture can add to a prompt


class PictureText(BaseModel):
    readable: bool = True
    texts: list[str] = Field(default_factory=list, description="Teks pada gambar, satu bagian per butir, urut seperti dibaca")


class NotAPicture(ValueError):
    """The uploaded file is missing, damaged, or not a JPEG or PNG."""


class Step(BaseModel):
    text: str = Field(description="Satu langkah, disalin persis")
    unclear: bool = Field(default=False, description="Ada bagian langkah ini yang tidak terbaca dengan yakin")


class Reading(BaseModel):
    readable: bool = Field(description="Apakah sebagian besar tulisan terbaca")
    question: str = ""
    steps: list[Step] = Field(default_factory=list)
    final_answer: str = ""
    answer_unclear: bool = False


class StepCheck(BaseModel):
    n: int
    status: Verdict
    note: str = ""


class Check(BaseModel):
    our_answer: str = Field(default="", description="Hasil hitungan sendiri, singkat")
    answer: Verdict
    steps: list[StepCheck] = Field(default_factory=list)


def add(db: Session, material_id: str, filename: str, path: str) -> WorkedExample:
    """Register an uploaded photo as the next page of the material. Call `read` afterwards, in the background."""
    material = db.get(Material, material_id)
    if material is None:
        raise ValueError(f"Material {material_id} not found")
    page = rag.allocate_pages(db, material, 1)  # the next free page, after every item in the material
    example = WorkedExample(material_id=material_id, page=page, filename=filename, path=path)
    db.add(example)
    db.commit()
    return example


def read(db: Session, example_id: str, subject: str = "") -> WorkedExample:
    """Copy what is written on the photo. Nothing is checked here: that waits for `confirm`. Safe to call again.

    Never raises for a photo or provider problem: the example ends as `unreadable`
    or `failed`, can still be shown on stage, and the teacher can type its text in `confirm`.
    """
    example = _example(db, example_id)
    try:
        reading = _read(example.path, subject)
    except llm.LLMError as err:
        log.warning("reading example %s failed: %s", example_id, err)
        return _store(db, example, "failed")
    except NotAPicture as err:
        log.warning("example %s could not be opened: %s", example_id, err)
        return _store(db, example, "unreadable")
    return _store(db, example, "unconfirmed" if reading else "unreadable", reading)


def confirm(
    db: Session,
    example_id: str,
    question: str | None = None,
    steps: list[str] | None = None,
    final_answer: str | None = None,
    subject: str = "",
) -> WorkedExample:
    """The teacher says what they wrote; only then is the working checked.

    With no text given, the reading stands as it is. Any text given replaces
    that part, so a teacher can fix one number or type the whole example. Either
    way the result is the teacher's own statement: nothing in it is marked unsure
    any more. Can be called again after a further edit.
    """
    example = _example(db, example_id)
    read_before = example.reading or {"question": "", "steps": [], "final_answer": ""}
    if not example.reading and question is None and steps is None:
        raise ValueError(f"Example {example_id} has no reading to confirm; send the text")
    said = [step["text"] for step in read_before["steps"]] if steps is None else steps
    reading = {
        "question": (read_before["question"] if question is None else question).strip(),
        "steps": [{"n": n, "text": text, "unclear": False} for n, text in enumerate(_filled(said), start=1)],
        "final_answer": (read_before["final_answer"] if final_answer is None else final_answer).strip(),
        "answer_unclear": False,
    }
    return _store(db, example, "confirmed", reading, _check(reading, subject))


def read_picture(db: Session, file_id: str, subject: str = "") -> MaterialFile | None:
    """Copy the text of a picture the teacher brought as material, so the AI students and the report can use it.

    Unlike a worked example nothing is checked or confirmed: the picture is reference material, like a PDF page.
    Never raises for a photo or provider problem: the item ends as `unreadable` or `failed` and can still be
    shown on stage. Returns None when the item was removed while it was being read.
    """
    item = db.get(MaterialFile, file_id)
    if item is None:
        return None
    try:
        texts, status = _read_picture(item.path, subject), "ready"
    except llm.LLMError as err:
        log.warning("reading picture %s failed: %s", file_id, err)
        texts, status = [], "failed"
    except NotAPicture as err:
        log.warning("picture %s could not be opened: %s", file_id, err)
        texts, status = [], "unreadable"
    if not texts and status == "ready":
        status = "unreadable"
    db.expire_all()
    item = db.get(MaterialFile, file_id)
    if item is None:  # the teacher removed it meanwhile
        return None
    rag.index_page(db, item.material_id, item.first_page, texts)
    item.status = status
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def for_material(db: Session, material_id: str) -> list[WorkedExample]:
    """The material's worked examples, in the order they are shown."""
    return list(
        db.exec(select(WorkedExample).where(WorkedExample.material_id == material_id).order_by(WorkedExample.page))
    )


def public(example: WorkedExample) -> dict:
    """The `Example` object of docs/api-contract.md. `check` is null until the teacher has confirmed."""
    return {
        "id": example.id,
        "material_id": example.material_id,
        "page": example.page,
        "status": example.status,
        "status_text": STATUS_TEXT[example.status],
        "reading": example.reading,
        "check": example.check_result if example.status == "confirmed" else None,
    }


# --- reading ---


def _read(path: str, subject: str) -> dict | None:
    """What is written on the photo, or None when it could not be read."""
    if llm.is_fake():
        return CANNED_READING
    prompt = Template(_prompt("example_read.md")).substitute(subject=_subject(subject))
    reply = llm.generate_json(prompt, Reading, images=[_photo(path)], model=settings.llm_vision_model or None)
    written = [step for step in reply.steps if step.text.strip()]
    question = _LABEL.sub("", reply.question.strip())
    if not reply.readable or not (question or written):
        return None
    return {
        "question": question,
        "steps": [{"n": n, "text": step.text.strip(), "unclear": step.unclear} for n, step in enumerate(written, start=1)],
        "final_answer": reply.final_answer.strip(),
        "answer_unclear": reply.answer_unclear,
    }


def _read_picture(path: str, subject: str) -> list[str]:
    """The text on a picture, as chunks for `rag.index_page`; empty when nothing could be read."""
    if llm.is_fake():
        return list(CANNED_PICTURE)
    prompt = Template(_prompt("image_read.md")).substitute(subject=_subject(subject))
    reply = llm.generate_json(prompt, PictureText, images=[_photo(path)], model=settings.llm_vision_model or None)
    if not reply.readable:
        return []
    chunks, current, total = [], "", 0
    for text in (" ".join(t.split()) for t in reply.texts):
        if not text or total >= MAX_PICTURE_CHARS:
            continue
        text = text[: MAX_PICTURE_CHARS - total]
        total += len(text)
        if current and len(current) + len(text) > rag.MAX_CHUNK_CHARS:
            chunks.append(current)
            current = ""
        current = f"{current} {text}".strip()
    return chunks + ([current] if current else [])


def _photo(path: str) -> llm.Image:
    """The photo as a JPEG at most MAX_SIDE_PX wide or tall.

    Opened as a one-page document so a sideways phone photo is turned upright.
    Only the pixels are sent: where and when the photo was taken stays in the file.
    """
    try:
        pixels = pymupdf.Pixmap(path)
        longest = min(MAX_SIDE_PX, max(pixels.width, pixels.height))
        with pymupdf.open(path) as document:
            page = document[0]
            # The page is measured in points, which depend on the dpi the file states, so zoom to a size in pixels.
            zoom = longest / max(page.rect.width, page.rect.height)
            picture = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return picture.tobytes("jpeg", jpg_quality=JPEG_QUALITY), "image/jpeg"
    except (pymupdf.mupdf.FzErrorBase, RuntimeError, ValueError, OSError) as err:
        raise NotAPicture(f"{Path(path).name}: {err}") from err


# --- checking, after the teacher has confirmed ---


def _check(reading: dict, subject: str) -> dict:
    """The `check` shown to the teacher. Every step gets a verdict; anything unsure is `cannot_tell`."""
    if llm.is_fake():
        agrees = [StepCheck(n=step["n"], status="follows") for step in reading["steps"]]
        return _fair(reading, Check(our_answer=reading["final_answer"], answer="follows", steps=agrees))
    if not reading["question"] or not reading["steps"]:
        return _fair(reading, None)  # nothing to work out, or nothing to compare with
    prompt = Template(_prompt("example_check.md")).substitute(
        subject=_subject(subject),
        question=reading["question"],
        steps="\n".join(f"{step['n']}. {step['text']}" for step in reading["steps"]),
        final_answer=reading["final_answer"] or "(tidak tertulis)",
    )
    try:
        return _fair(reading, llm.generate_json(prompt, Check))  # the photo is deliberately not sent
    except llm.LLMError as err:
        log.warning("checking an example failed: %s", err)
        return _fair(reading, None)


def _fair(reading: dict, found: Check | None) -> dict:
    """Keep only what may fairly be said to the teacher.

    - A step the model skipped is `cannot_tell`, never a guess.
    - The final answer has a verdict only when one was written.
    - A note that judges, or uses a banned word, is replaced by a plain line.
    """
    replied = {step.n: step for step in found.steps} if found else {}
    steps = []
    for written in reading["steps"]:
        step = replied.get(written["n"])
        status = step.status if step else "cannot_tell"
        note = ""
        if status == "recheck":
            note = " ".join(step.note.split())
            if not note or evidence.unkind(note) or _VERDICT.search(note.lower()):
                note = f"Langkah {written['n']} layak dicek ulang."
        steps.append({"n": written["n"], "status": status, "note": note})

    answer = found.answer if found and reading["final_answer"] else "cannot_tell"
    our_answer = " ".join(found.our_answer.split()).rstrip(".") if found else ""
    if evidence.unkind(our_answer):
        our_answer = ""
    return {"answer": answer, "our_answer": our_answer, "steps": steps, "summary": _summary(answer, our_answer, steps)}


def _summary(answer: str, our_answer: str, steps: list[dict]) -> str:
    """One line for the teacher: what to look at again, else what agrees, else that nothing was checked."""
    flagged = sum(1 for step in steps if step["status"] == "recheck")
    if flagged:
        return f"Ada {flagged} langkah yang layak dicek ulang."
    if answer == "recheck":
        return "Jawaban akhir layak dicek ulang." + (f" Hitungan kami: {our_answer}." if our_answer else "")
    if answer == "follows" or any(step["status"] == "follows" for step in steps):
        return ALL_FOLLOW
    return NOT_CHECKED


# --- storing ---


def _store(
    db: Session, example: WorkedExample, status: str, reading: dict | None = None, check: dict | None = None
) -> WorkedExample:
    example.status, example.reading, example.check_result = status, reading, check
    db.add(example)
    db.commit()
    # The page's text is what the AI students and the report see; an unread photo has none.
    rag.index_page(db, example.material_id, example.page, _page_texts(reading) if reading else [])
    db.refresh(example)
    return example


def _page_texts(reading: dict) -> list[str]:
    """The reading as chunks: the question, each step, the final answer.

    Before the teacher confirms, a part that was not read with confidence is left
    out, so an AI student never asks about a number the teacher did not write.
    """
    texts = ["Contoh soal yang ditulis tangan oleh guru." + (f" Soal: {reading['question']}" if reading["question"] else "")]
    texts += [f"Langkah {step['n']}: {step['text']}" for step in reading["steps"] if not step["unclear"]]
    if reading["final_answer"] and not reading["answer_unclear"]:
        texts.append(f"Jawaban akhir: {reading['final_answer']}")
    return texts


# --- small helpers ---


def _example(db: Session, example_id: str) -> WorkedExample:
    example = db.get(WorkedExample, example_id)
    if example is None:
        raise ValueError(f"Example {example_id} not found")
    return example


def _prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def _subject(subject: str) -> str:
    return f" pada pelajaran {subject.strip()}" if subject.strip() else ""


def _filled(texts: Iterable[str]) -> list[str]:
    return [text.strip() for text in texts if text.strip()]
