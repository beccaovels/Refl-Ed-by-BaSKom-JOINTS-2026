"""Material lookup: split the teacher's material into chunks and find the ones closest to the transcript.

A lesson's material holds several items (PDFs and pictures), each owning a range of page numbers given out
by `allocate_pages`. A picture or a photo of a worked example is a page too: `examples.py` reads it and stores
its text here with `index_page`.
"""

import math
import re
from collections import Counter
from threading import Lock

import pymupdf
from sqlalchemy import func
from sqlmodel import Session, delete, select

from app.models import Material, MaterialChunk, MaterialFile, WorkedExample

MAX_CHUNK_CHARS = 700
MIN_BLOCK_CHARS = 3


def index_material(db: Session, material_id: str) -> None:
    """Fill material_chunks for an uploaded PDF. Safe to call again.

    Embeddings are left empty for now; chunk text and page numbers are enough
    for the slide on screen and for the reading share.
    """
    material = db.get(Material, material_id)
    if material is None:
        raise ValueError(f"Material {material_id} not found")
    if not material.path:
        return  # photos only: there is no PDF to split
    with pymupdf.open(material.path) as pdf:
        # Pages after the PDF's last one are photos of worked examples; their text stays.
        db.exec(delete(MaterialChunk).where(MaterialChunk.material_id == material_id, MaterialChunk.page <= len(pdf)))
        for page_number, page in enumerate(pdf, start=1):
            for order, text in enumerate(_chunks(page)):
                db.add(MaterialChunk(material_id=material_id, page=page_number, order=order, text=text))
    db.commit()


# Page numbers are handed out under this lock: two uploads at once must never get the same pages.
_pages_lock = Lock()


def allocate_pages(db: Session, material: Material, count: int) -> int:
    """Reserve `count` page numbers in the material for a new item and return the first one.

    Every item gets its own range after everything given out so far (PDF pages, pictures,
    photos of worked examples), so numbers never collide and stay stable when an item is removed.
    """
    with _pages_lock:
        db.refresh(material)
        last_example = db.exec(select(func.max(WorkedExample.page)).where(WorkedExample.material_id == material.id)).one()
        last_file = db.exec(
            select(func.max(MaterialFile.first_page + MaterialFile.page_count - 1)).where(MaterialFile.material_id == material.id)
        ).one()
        first = max(material.page_count, last_example or 0, last_file or 0) + 1
        material.page_count = first + count - 1
        db.add(material)
        db.commit()
        return first


def index_pdf(db: Session, material_id: str, path: str, first_page: int) -> int:
    """Split one PDF into chunks stored from `first_page` on. Returns its number of pages. Safe to call again."""
    with pymupdf.open(path) as pdf:
        last = first_page + len(pdf) - 1
        db.exec(
            delete(MaterialChunk).where(
                MaterialChunk.material_id == material_id, MaterialChunk.page >= first_page, MaterialChunk.page <= last
            )
        )
        for offset, page in enumerate(pdf):
            for order, text in enumerate(_chunks(page)):
                db.add(MaterialChunk(material_id=material_id, page=first_page + offset, order=order, text=text))
        db.commit()
        return len(pdf)


def forget_pages(db: Session, material_id: str, first_page: int, last_page: int) -> None:
    """Remove the text of a range of pages, for an item the teacher took out."""
    db.exec(
        delete(MaterialChunk).where(
            MaterialChunk.material_id == material_id, MaterialChunk.page >= first_page, MaterialChunk.page <= last_page
        )
    )
    db.commit()


def index_page(db: Session, material_id: str, page: int, texts: list[str]) -> None:
    """Replace the chunks of one page with `texts`. For a page that is not PDF text, such as a photo that was read."""
    db.exec(delete(MaterialChunk).where(MaterialChunk.material_id == material_id, MaterialChunk.page == page))
    for order, text in enumerate(texts):
        db.add(MaterialChunk(material_id=material_id, page=page, order=order, text=text))
    db.commit()


def page_text(db: Session, material_id: str, page: int) -> str:
    """All text on one page, in reading order."""
    chunks = db.exec(
        select(MaterialChunk)
        .where(MaterialChunk.material_id == material_id, MaterialChunk.page == page)
        .order_by(MaterialChunk.order)
    ).all()
    return "\n".join(chunk.text for chunk in chunks)


def closest_chunks(db: Session, material_id: str, text: str, k: int = 3, skip_page: int | None = None) -> list[MaterialChunk]:
    """The `k` chunks of the material that share the most words with `text`.

    Words that appear in many chunks count for less, so "adalah" matters less
    than "diskriminan". Plain word overlap for now; embeddings can replace the
    scoring without changing callers.
    """
    chunks = db.exec(select(MaterialChunk).where(MaterialChunk.material_id == material_id)).all()
    if not chunks:
        return []
    chunk_words = [set(_words(chunk.text)) for chunk in chunks]
    seen_in = Counter(word for words in chunk_words for word in words)
    wanted = set(_words(text))
    scored = []
    for chunk, words in zip(chunks, chunk_words):
        if chunk.page == skip_page:
            continue
        score = sum(math.log(1 + len(chunks) / seen_in[word]) for word in wanted & words)
        if score > 0:
            scored.append((score / math.sqrt(len(words) or 1), chunk))
    scored.sort(key=lambda pair: -pair[0])
    return [chunk for _, chunk in scored[:k]]


def _words(text: str) -> list[str]:
    return [word for word in re.findall(r"[^\W_]+", text.lower()) if len(word) > 2]


def _chunks(page) -> list[str]:
    """Text blocks of a page, merged until they reach about a paragraph."""
    chunks: list[str] = []
    current = ""
    for block in page.get_text("blocks"):
        text = " ".join(block[4].split())
        if block[6] != 0 or len(text) < MIN_BLOCK_CHARS:  # block[6] != 0 is an image
            continue
        if current and len(current) + len(text) > MAX_CHUNK_CHARS:
            chunks.append(current)
            current = ""
        current = f"{current} {text}".strip()
    if current:
        chunks.append(current)
    return chunks
