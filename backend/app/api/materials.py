"""The teacher's chapter PDF: uploaded once in Setup, shown on the stage, used for questions and scoring."""

import logging
from pathlib import Path

import pymupdf
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session, delete

from app.core.auth import current_user
from app.core.config import settings
from app.core.db import get_session
from app.models import Material, MaterialChunk, User, new_id
from app.schemas.materials import MaterialOut
from app.services import rag

log = logging.getLogger(__name__)
router = APIRouter(tags=["materials"])

MAX_BYTES = 20 * 1024 * 1024
READ_BLOCK = 1024 * 1024
PDF_SIGNATURE = b"%PDF-"


@router.post("/materials", response_model=MaterialOut)
def upload_material(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
):
    data = _read_limited(file)
    if not data.startswith(PDF_SIGNATURE):
        raise HTTPException(status_code=400, detail="Berkas harus berupa PDF.")
    try:
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            page_count = pdf.page_count
    except Exception:
        raise HTTPException(status_code=400, detail="PDF tidak bisa dibaca. Coba ekspor ulang berkasnya.") from None
    if page_count == 0:
        raise HTTPException(status_code=400, detail="PDF ini tidak memiliki halaman.")

    # Stored under a generated name: the teacher's filename never becomes part of a path.
    material_id = new_id()
    folder = Path(settings.upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{material_id}.pdf"
    path.write_bytes(data)
    material = Material(
        id=material_id,
        user_id=user.id,
        filename=Path(file.filename or "materi.pdf").name[:200],
        path=str(path),
        page_count=page_count,
    )
    try:
        db.add(material)
        db.commit()
        rag.index_material(db, material_id)
    except Exception:
        log.exception("Indexing material %s failed", material_id)
        db.rollback()
        # leave nothing half-made behind: no chunks, no row, no file
        db.exec(delete(MaterialChunk).where(MaterialChunk.material_id == material_id))
        stored = db.get(Material, material_id)
        if stored is not None:
            db.delete(stored)
        db.commit()
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Materi belum berhasil diproses. Silakan coba lagi.")
    return MaterialOut(id=material.id, filename=material.filename, page_count=material.page_count)


@router.get("/materials/{material_id}/file", response_class=FileResponse)
def material_file(material_id: str, user: User = Depends(current_user), db: Session = Depends(get_session)):
    material = db.get(Material, material_id)
    if material is None or material.user_id != user.id or not Path(material.path).is_file():
        raise HTTPException(status_code=404, detail="Materi tidak ditemukan.")
    return FileResponse(material.path, media_type="application/pdf", filename=material.filename)


def _read_limited(file: UploadFile) -> bytes:
    """The upload's bytes, stopping as soon as it is over the limit instead of reading it all."""
    chunks, size = [], 0
    while block := file.file.read(READ_BLOCK):
        size += len(block)
        if size > MAX_BYTES:
            raise HTTPException(status_code=413, detail="Berkas lebih dari 20 MB.")
        chunks.append(block)
    return b"".join(chunks)
