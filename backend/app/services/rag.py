"""Material lookup: split the teacher's PDF into chunks and find the ones closest to the transcript."""

import pymupdf
from sqlmodel import Session, delete, select

from app.models import Material, MaterialChunk

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
    db.exec(delete(MaterialChunk).where(MaterialChunk.material_id == material_id))
    with pymupdf.open(material.path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            for order, text in enumerate(_chunks(page)):
                db.add(MaterialChunk(material_id=material_id, page=page_number, order=order, text=text))
    db.commit()


def page_text(db: Session, material_id: str, page: int) -> str:
    """All text on one page, in reading order."""
    chunks = db.exec(
        select(MaterialChunk)
        .where(MaterialChunk.material_id == material_id, MaterialChunk.page == page)
        .order_by(MaterialChunk.order)
    ).all()
    return "\n".join(chunk.text for chunk in chunks)


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
