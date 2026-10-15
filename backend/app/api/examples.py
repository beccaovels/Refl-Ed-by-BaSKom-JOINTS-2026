"""Photos of the teacher's handwritten worked examples: upload, read in the background, confirm, check.

POST /materials/{id}/examples   202, then the photo is read in the background (10-30 s)
GET  /materials/{id}/examples   the examples in page order; poll while any is still `reading`
GET  /examples/{id}/file        the photo
POST /examples/{id}/confirm     "yes, this is what I wrote" (or an edit); this is when the working is checked

Reading and checking are in app/services/examples.py. Nothing about whether the working is right is sent before the teacher confirms.
"""

import logging
from pathlib import Path

import pymupdf
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.materials import usage_allows_photo
from app.core.auth import current_user, own_material
from app.core.config import settings
from app.core.db import get_session
from app.models import Material, TeachingSession, User, WorkedExample, new_id
from app.schemas.examples import ConfirmIn, ExampleOut
from app.services import examples, llm

log = logging.getLogger(__name__)
router = APIRouter(tags=["examples"])

MAX_BYTES = 8 * 1024 * 1024
READ_BLOCK = 1024 * 1024
# the first bytes of a real image, whatever the file is called
SIGNATURES = {b"\xff\xd8\xff": ("jpg", "image/jpeg"), b"\x89PNG\r\n\x1a\n": ("png", "image/png")}
PAGE_RETRIES = 3


@router.post("/materials/{material_id}/examples", status_code=202, response_model=ExampleOut)
def upload_example(
    material_id: str,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
):
    material = own_material(db, material_id, user)
    data = _read_limited(file)
    kind = next((kind for magic, kind in SIGNATURES.items() if data.startswith(magic)), None)
    if kind is None:
        raise HTTPException(status_code=400, detail="Foto harus berupa JPG atau PNG.")
    try:
        pymupdf.Pixmap(data)  # decodes the picture, so a file with only a valid header is caught here
    except Exception:
        raise HTTPException(status_code=400, detail="Foto tidak bisa dibuka. Coba ambil ulang fotonya.") from None

    usage_allows_photo(db, material.id, len(data))  # a photo counts toward the lesson's limits like any item

    # Stored under a generated name: the teacher's filename never becomes part of a path.
    folder = Path(settings.upload_dir) / "examples"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{new_id()}.{kind[0]}"
    path.write_bytes(data)
    filename = Path(file.filename or f"foto.{kind[0]}").name[:200]
    example = None
    for _ in range(PAGE_RETRIES):  # two photos uploaded at once can pick the same page number
        try:
            example = examples.add(db, material.id, filename, str(path))
            break
        except IntegrityError:
            db.rollback()
    if example is None:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="Beberapa foto diunggah bersamaan. Coba lagi.")
    background.add_task(_read, db.get_bind(), example.id, _subject(db, material.id))
    return examples.public(example)


@router.get("/materials/{material_id}/examples", response_model=list[ExampleOut])
def list_examples(material_id: str, user: User = Depends(current_user), db: Session = Depends(get_session)):
    own_material(db, material_id, user)
    return [examples.public(e) for e in examples.for_material(db, material_id)]


@router.get("/examples/{example_id}/file", response_class=FileResponse)
def example_file(example_id: str, user: User = Depends(current_user), db: Session = Depends(get_session)):
    example = _own_example(db, example_id, user)
    if not Path(example.path).is_file():
        raise HTTPException(status_code=404, detail="Foto tidak ditemukan.")
    media = "image/png" if example.path.endswith(".png") else "image/jpeg"
    return FileResponse(example.path, media_type=media, filename=example.filename)


@router.post("/examples/{example_id}/confirm", response_model=ExampleOut)
def confirm_example(
    example_id: str, body: ConfirmIn, user: User = Depends(current_user), db: Session = Depends(get_session)
):
    example = _own_example(db, example_id, user)
    if example.status == "reading":  # a late reading would overwrite what the teacher confirms now
        raise HTTPException(status_code=409, detail="Foto masih dibaca. Coba lagi sebentar.")
    try:
        confirmed = examples.confirm(
            db, example_id, body.question, body.steps, body.final_answer, subject=_subject(db, example.material_id)
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Belum ada isi untuk dikonfirmasi. Ketik soal dan langkahnya.") from None
    except llm.LLMError:
        raise HTTPException(status_code=502, detail="Pemeriksaan sedang tidak tersedia. Coba lagi sebentar.") from None
    return examples.public(confirmed)


def _read(engine: Engine, example_id: str, subject: str) -> None:
    """Background job: read the photo with its own database session (the request's one is closed by now)."""
    try:
        with Session(engine) as db:
            examples.read(db, example_id, subject)
    except Exception:
        log.exception("Reading example %s failed", example_id)
        with Session(engine) as db:  # never leave a photo "reading" for ever
            example = db.get(WorkedExample, example_id)
            if example is not None and example.status == "reading":
                example.status = "failed"
                db.add(example)
                db.commit()


def _own_example(db: Session, example_id: str, user: User) -> WorkedExample:
    example = db.get(WorkedExample, example_id)
    material = db.get(Material, example.material_id) if example else None
    if material is None or material.user_id != user.id:
        raise HTTPException(status_code=404, detail="Contoh tidak ditemukan.")
    return example


def _subject(db: Session, material_id: str) -> str:
    """The subject of the latest lesson that uses this material, so the reader knows what kind of working to expect."""
    session = db.exec(
        select(TeachingSession).where(TeachingSession.material_id == material_id).order_by(TeachingSession.started_at.desc())
    ).first()
    return session.subject if session else ""


def _read_limited(file: UploadFile) -> bytes:
    chunks, size = [], 0
    while block := file.file.read(READ_BLOCK):
        size += len(block)
        if size > MAX_BYTES:
            raise HTTPException(status_code=413, detail="Foto lebih dari 8 MB.")
        chunks.append(block)
    return b"".join(chunks)
