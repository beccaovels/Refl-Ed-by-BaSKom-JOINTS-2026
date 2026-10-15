"""The teacher's material for a lesson: several items (PDFs, JPEG/PNG pictures), shown on the stage one at a time.

A material is the lesson's bundle. Each item owns a range of the material's page numbers (rag.allocate_pages),
so the AI students, page turns and the report treat every PDF page and every picture like a slide.

POST   /materials                          a new, empty bundle (with a PDF: the bundle and that PDF, as before)
POST   /materials/{id}/files               add one PDF or picture; a picture is read for text in the background
GET    /materials/{id}/files               the items, what is used and the limits
GET    /files/{id}/content                 the item itself, for the stage
DELETE /materials/{id}/files/{file_id}     take an item out, before a lesson has used the bundle
GET    /materials/{id}/file                the first PDF (kept for older clients)
"""

import logging
from pathlib import Path
from threading import Lock

import pymupdf
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.engine import Engine
from sqlmodel import Session, func, select

from app.core.auth import current_user, own_material
from app.core.config import settings
from app.core.db import get_session
from app.models import Material, MaterialFile, TeachingSession, User, WorkedExample, new_id
from app.schemas.materials import Limits, MaterialFileOut, MaterialFilesOut, MaterialOut, Usage
from app.services import examples, rag

log = logging.getLogger(__name__)
router = APIRouter(tags=["materials"])

MB = 1024 * 1024
MAX_PDF_BYTES = 20 * MB
MAX_IMAGE_BYTES = 8 * MB
MAX_FILES = 10  # per lesson: PDFs, pictures and worked-example photos together
MAX_TOTAL_BYTES = 50 * MB  # per lesson
MAX_PDF_PAGES = 300  # per lesson: indexing time and prompt size
READ_BLOCK = 1024 * 1024

# What a file really is, from its first bytes, whatever it is called: (kind, extension, media type)
SIGNATURES = {
    b"%PDF-": ("pdf", "pdf", "application/pdf"),
    b"\xff\xd8\xff": ("image", "jpg", "image/jpeg"),
    b"\x89PNG\r\n\x1a\n": ("image", "png", "image/png"),
}
MEDIA = {"pdf": "application/pdf", "jpg": "image/jpeg", "png": "image/png"}
STATUS_TEXT = {
    "ready": "",
    "reading": "Teks pada gambar sedang dibaca…",
    "unreadable": "Teks pada gambar ini belum terbaca. Gambar tetap bisa ditampilkan.",
    "failed": "Gambar belum sempat dibaca. Gambar tetap bisa ditampilkan.",
}

# Checking the limits and adding the item happen together, so two uploads at once cannot both pass the last free place.
_adding = Lock()
# Pictures are read one at a time, so ten uploads do not send ten requests to the AI provider at once.
_reading = Lock()


@router.post("/materials", response_model=MaterialOut)
def create_material(
    background: BackgroundTasks,
    file: UploadFile | None = File(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
):
    """A new bundle. With a file (a PDF, as before), the bundle is created with that PDF in it."""
    material = Material(user_id=user.id)
    db.add(material)
    db.commit()
    if file is None or (not file.filename and not file.size):  # no file chosen: an empty bundle
        return MaterialOut(id=material.id, filename=None, page_count=0)
    try:
        item = _add(db, material, file, background, only_pdf=True)
    except BaseException:
        db.rollback()
        db.delete(db.get(Material, material.id))  # nothing half-made is left behind
        db.commit()
        raise
    return MaterialOut(id=material.id, filename=item.filename, page_count=item.page_count)


@router.post("/materials/{material_id}/files", response_model=MaterialFileOut, status_code=201)
def add_file(
    material_id: str,
    response: Response,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
):
    """Add one PDF (201, ready) or picture (202, read for text in the background)."""
    item = _add(db, own_material(db, material_id, user), file, background)
    if item.status == "reading":
        response.status_code = 202
    return _public(item)


@router.get("/materials/{material_id}/files", response_model=MaterialFilesOut)
def list_files(material_id: str, user: User = Depends(current_user), db: Session = Depends(get_session)):
    material = own_material(db, material_id, user)
    items = db.exec(select(MaterialFile).where(MaterialFile.material_id == material.id).order_by(MaterialFile.first_page)).all()
    files, used_bytes, pdf_pages = _usage(db, material.id)
    return MaterialFilesOut(
        files=[_public(item) for item in items],
        used=Usage(files=files, bytes=used_bytes, pdf_pages=pdf_pages),
        limits=Limits(files=MAX_FILES, bytes=MAX_TOTAL_BYTES, pdf_bytes=MAX_PDF_BYTES, image_bytes=MAX_IMAGE_BYTES,
                      pdf_pages=MAX_PDF_PAGES),  # fmt: skip
    )


@router.get("/files/{file_id}/content", response_class=FileResponse)
def file_content(file_id: str, user: User = Depends(current_user), db: Session = Depends(get_session)):
    item = _own_file(db, file_id, user)
    if not Path(item.path).is_file():
        raise HTTPException(status_code=404, detail="Materi tidak ditemukan.")
    return FileResponse(item.path, media_type=MEDIA[Path(item.path).suffix.lstrip(".")], filename=item.filename)


@router.delete("/materials/{material_id}/files/{file_id}", status_code=204)
def remove_file(material_id: str, file_id: str, user: User = Depends(current_user), db: Session = Depends(get_session)):
    material = own_material(db, material_id, user)
    item = db.get(MaterialFile, file_id)
    if item is None or item.material_id != material.id:
        raise HTTPException(status_code=404, detail="Materi tidak ditemukan.")
    if db.exec(select(TeachingSession).where(TeachingSession.material_id == material.id)).first():
        # a lesson has used this bundle: its page turns and report point at these pages
        raise HTTPException(status_code=409, detail="Materi ini sudah dipakai dalam sesi, jadi tidak bisa dihapus.")
    rag.forget_pages(db, material.id, item.first_page, item.first_page + item.page_count - 1)
    path = Path(item.path)
    db.delete(item)
    db.commit()
    path.unlink(missing_ok=True)
    return Response(status_code=204)


@router.get("/materials/{material_id}/file", response_class=FileResponse)
def material_file(material_id: str, user: User = Depends(current_user), db: Session = Depends(get_session)):
    """The bundle's first PDF, for clients written before a material could hold several items."""
    material = own_material(db, material_id, user)
    first = db.exec(
        select(MaterialFile).where(MaterialFile.material_id == material.id, MaterialFile.kind == "pdf").order_by(MaterialFile.first_page)
    ).first()
    path, name = (first.path, first.filename) if first else (material.path, material.filename)
    if not path or not Path(path).is_file():
        raise HTTPException(status_code=404, detail="Materi tidak ditemukan.")
    return FileResponse(path, media_type="application/pdf", filename=name)


# --- adding an item ---


def _add(db: Session, material: Material, file: UploadFile, background: BackgroundTasks, only_pdf: bool = False) -> MaterialFile:
    data = _read_limited(file, max(MAX_PDF_BYTES, MAX_IMAGE_BYTES))
    found = next((kind for magic, kind in SIGNATURES.items() if data.startswith(magic)), None)
    if found is None or (only_pdf and found[0] != "pdf"):
        raise HTTPException(status_code=400, detail="Berkas harus berupa PDF." if only_pdf else "Berkas harus berupa PDF, JPG, atau PNG.")
    kind, extension, _ = found
    if kind == "pdf" and len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF lebih dari 20 MB.")
    if kind == "image" and len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Gambar lebih dari 8 MB.")
    pages = _pages(data) if kind == "pdf" else _check_picture(data)

    # Stored under a generated name: the teacher's filename never becomes part of a path.
    folder = Path(settings.upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{new_id()}.{extension}"
    with _adding:
        files, used_bytes, pdf_pages = _usage(db, material.id)
        if files + 1 > MAX_FILES:
            raise HTTPException(status_code=409, detail=f"Satu pelajaran bisa memuat paling banyak {MAX_FILES} berkas.")
        if used_bytes + len(data) > MAX_TOTAL_BYTES:
            raise HTTPException(status_code=413, detail=f"Total materi satu pelajaran paling banyak {MAX_TOTAL_BYTES // MB} MB.")
        if kind == "pdf" and pdf_pages + pages > MAX_PDF_PAGES:
            raise HTTPException(status_code=413, detail=f"Total halaman PDF satu pelajaran paling banyak {MAX_PDF_PAGES}.")
        path.write_bytes(data)
        first = rag.allocate_pages(db, material, pages)
        item = MaterialFile(
            material_id=material.id, kind=kind, filename=Path(file.filename or f"materi.{extension}").name[:200],
            path=str(path), size_bytes=len(data), first_page=first, page_count=pages,
            status="ready" if kind == "pdf" else "reading",
        )  # fmt: skip
        db.add(item)
        db.commit()
    if kind == "image":
        background.add_task(_read, db.get_bind(), item.id, _subject(db, material.id))
        return item
    try:
        rag.index_pdf(db, material.id, item.path, item.first_page)
    except Exception:
        log.exception("Indexing %s failed", item.id)
        db.rollback()
        rag.forget_pages(db, material.id, item.first_page, item.first_page + item.page_count - 1)
        db.delete(db.get(MaterialFile, item.id))
        db.commit()
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Materi belum berhasil diproses. Silakan coba lagi.") from None
    return item


def _read(engine: Engine, file_id: str, subject: str) -> None:
    """Background job: read a picture's text, with its own database session (the request's one is closed by now)."""
    with _reading:
        try:
            with Session(engine) as db:
                examples.read_picture(db, file_id, subject)
        except Exception:
            log.exception("Reading picture %s failed", file_id)
            with Session(engine) as db:  # never leave a picture "reading" for ever
                item = db.get(MaterialFile, file_id)
                if item is not None and item.status == "reading":
                    item.status = "failed"
                    db.add(item)
                    db.commit()


def usage_allows_photo(db: Session, material_id: str, size: int) -> None:
    """For a photo of a worked example: the same per-lesson limits as any other item."""
    files, used_bytes, _ = _usage(db, material_id)
    if files + 1 > MAX_FILES:
        raise HTTPException(status_code=409, detail=f"Satu pelajaran bisa memuat paling banyak {MAX_FILES} berkas.")
    if used_bytes + size > MAX_TOTAL_BYTES:
        raise HTTPException(status_code=413, detail=f"Total materi satu pelajaran paling banyak {MAX_TOTAL_BYTES // MB} MB.")


def _usage(db: Session, material_id: str) -> tuple[int, int, int]:
    """Items, bytes and PDF pages already in the bundle, worked-example photos included."""
    items = db.exec(select(MaterialFile).where(MaterialFile.material_id == material_id)).all()
    photos = db.exec(select(WorkedExample.path).where(WorkedExample.material_id == material_id)).all()
    photo_bytes = sum(Path(p).stat().st_size for p in photos if p and Path(p).is_file())
    legacy = db.get(Material, material_id)  # a material made before items existed may hold one PDF of its own
    legacy_bytes = Path(legacy.path).stat().st_size if legacy and legacy.path and Path(legacy.path).is_file() else 0
    return (
        len(items) + len(photos) + (1 if legacy_bytes else 0),
        sum(i.size_bytes for i in items) + photo_bytes + legacy_bytes,
        sum(i.page_count for i in items if i.kind == "pdf"),
    )


def _pages(data: bytes) -> int:
    try:
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            pages = pdf.page_count
    except Exception:
        raise HTTPException(status_code=400, detail="PDF tidak bisa dibaca. Coba ekspor ulang berkasnya.") from None
    if pages == 0:
        raise HTTPException(status_code=400, detail="PDF ini tidak memiliki halaman.")
    return pages


def _check_picture(data: bytes) -> int:
    try:
        pymupdf.Pixmap(data)  # decodes the picture, so a file with only a valid header is caught here
    except Exception:
        raise HTTPException(status_code=400, detail="Gambar tidak bisa dibuka. Coba simpan ulang gambarnya.") from None
    return 1


def _own_file(db: Session, file_id: str, user: User) -> MaterialFile:
    item = db.get(MaterialFile, file_id)
    material = db.get(Material, item.material_id) if item else None
    if material is None or material.user_id != user.id:
        raise HTTPException(status_code=404, detail="Materi tidak ditemukan.")
    return item


def _public(item: MaterialFile) -> MaterialFileOut:
    return MaterialFileOut(
        id=item.id, material_id=item.material_id, kind=item.kind, filename=item.filename, size_bytes=item.size_bytes,
        first_page=item.first_page, page_count=item.page_count, status=item.status, status_text=STATUS_TEXT[item.status],
    )  # fmt: skip


def _subject(db: Session, material_id: str) -> str:
    """The subject of the latest lesson that uses this material, so the reader knows what to expect."""
    session = db.exec(
        select(TeachingSession).where(TeachingSession.material_id == material_id).order_by(TeachingSession.started_at.desc())
    ).first()
    return session.subject if session else ""


def _read_limited(file: UploadFile, limit: int) -> bytes:
    """The upload's bytes, stopping as soon as it is over the limit instead of reading it all."""
    chunks, size = [], 0
    while block := file.file.read(READ_BLOCK):
        size += len(block)
        if size > limit:
            raise HTTPException(status_code=413, detail=f"Berkas lebih dari {limit // MB} MB.")
        chunks.append(block)
    return b"".join(chunks)
