"""A lesson's material holds several items (PDFs, JPEG and PNG pictures); each owns a range of page numbers."""

import pymupdf
import pytest
from sqlmodel import Session, select

from app.api import materials as api
from app.models import MaterialChunk, MaterialFile, SlideEvent
from app.services import examples, questions, rag, scoring


def pdf(*pages: str) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        doc.new_page().insert_text((72, 72), text)
    return doc.tobytes()


def png(shade: int = 255) -> bytes:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 40), False)
    pix.clear_with(shade)
    return pix.tobytes("png")


def jpg() -> bytes:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 40), False)
    pix.clear_with(200)
    return pix.tobytes("jpeg")


@pytest.fixture
def me(login):
    return login()


@pytest.fixture
def bundle(client, me):
    return client.post("/api/materials", headers=me).json()


def add(client, headers, material_id, data, name="bab.pdf", kind="application/pdf"):
    return client.post(f"/api/materials/{material_id}/files", files={"file": (name, data, kind)}, headers=headers)


def listing(client, headers, material_id):
    return client.get(f"/api/materials/{material_id}/files", headers=headers).json()


# --- adding items ---


def test_pdfs_and_pictures_get_their_own_page_ranges(client, me, bundle, engine):
    a = add(client, me, bundle["id"], pdf("Peluang A1", "Peluang A2", "Peluang A3"), "a.pdf")
    picture = add(client, me, bundle["id"], png(), "tabel.png", "image/png")
    b = add(client, me, bundle["id"], pdf("Ruang sampel B1", "Ruang sampel B2"), "b.pdf")
    assert (a.status_code, picture.status_code, b.status_code) == (201, 202, 201)
    a, picture, b = a.json(), picture.json(), b.json()
    assert (a["first_page"], a["page_count"]) == (1, 3)
    assert (picture["first_page"], picture["page_count"], picture["kind"]) == (4, 1, "image")
    assert (b["first_page"], b["page_count"]) == (5, 2)
    with Session(engine) as db:
        assert rag.page_text(db, bundle["id"], 2) == "Peluang A2"
        assert rag.page_text(db, bundle["id"], 6) == "Ruang sampel B2"  # B's second page, after A and the picture
        assert "(Contoh)" in rag.page_text(db, bundle["id"], 4)  # the picture was read in the background


def test_a_picture_is_read_in_the_background_and_then_ready(client, me, bundle):
    item = add(client, me, bundle["id"], jpg(), "papan.jpg", "image/jpeg").json()
    assert item["status"] == "reading" and item["status_text"]
    listed = listing(client, me, bundle["id"])["files"][0]
    assert listed["status"] == "ready" and listed["status_text"] == ""


def test_a_picture_that_cannot_be_read_still_works_on_stage(client, me, bundle, monkeypatch):
    monkeypatch.setattr(examples, "_read_picture", lambda path, subject: [])  # nothing legible on it
    item = add(client, me, bundle["id"], png(), "buram.png", "image/png").json()
    listed = listing(client, me, bundle["id"])["files"][0]
    assert listed["status"] == "unreadable" and listed["status_text"]
    assert client.get(f"/api/files/{item['id']}/content", headers=me).status_code == 200


def test_a_reading_that_crashes_marks_the_picture_failed(client, me, bundle, monkeypatch):
    def boom(db, file_id, subject=""):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(examples, "read_picture", boom)
    add(client, me, bundle["id"], png(), "x.png", "image/png")
    assert listing(client, me, bundle["id"])["files"][0]["status"] == "failed"


def test_items_are_served_back_with_their_own_type(client, me, bundle):
    a = add(client, me, bundle["id"], pdf("x"), "a.pdf").json()
    p = add(client, me, bundle["id"], png(), "p.png", "image/png").json()
    j = add(client, me, bundle["id"], jpg(), "j.jpg", "image/jpeg").json()
    for item, media in ((a, "application/pdf"), (p, "image/png"), (j, "image/jpeg")):
        r = client.get(f"/api/files/{item['id']}/content", headers=me)
        assert r.status_code == 200 and r.headers["content-type"] == media


@pytest.mark.parametrize("data", [b"just text", b"\x89PNG\r\n\x1a\nbroken", b"%PDF-1.7 not really"])
def test_files_that_are_not_a_pdf_jpg_or_png_are_400(client, me, bundle, data):
    assert add(client, me, bundle["id"], data, "x.png").status_code == 400


# --- limits ---


def test_at_most_ten_items_per_lesson(client, me, bundle, monkeypatch):
    monkeypatch.setattr(api, "MAX_FILES", 3)
    for n in range(3):
        assert add(client, me, bundle["id"], pdf(f"p{n}"), f"{n}.pdf").status_code == 201
    r = add(client, me, bundle["id"], pdf("one too many"), "4.pdf")
    assert r.status_code == 409 and "3" in r.json()["detail"]


def test_the_lesson_total_size_is_limited(client, me, bundle, monkeypatch):
    first = pdf("a")
    monkeypatch.setattr(api, "MAX_TOTAL_BYTES", len(first) + 100)
    assert add(client, me, bundle["id"], first, "a.pdf").status_code == 201
    assert add(client, me, bundle["id"], pdf("b"), "b.pdf").status_code == 413


def test_each_type_has_its_own_size_limit(client, me, bundle, monkeypatch):
    monkeypatch.setattr(api, "MAX_IMAGE_BYTES", 50)
    assert add(client, me, bundle["id"], png(), "p.png", "image/png").status_code == 413
    assert add(client, me, bundle["id"], pdf("a"), "a.pdf").status_code == 201  # a PDF of that size is fine
    monkeypatch.setattr(api, "MAX_PDF_BYTES", 50)
    assert add(client, me, bundle["id"], pdf("b"), "b.pdf").status_code == 413


def test_pdf_pages_per_lesson_are_limited(client, me, bundle, monkeypatch):
    monkeypatch.setattr(api, "MAX_PDF_PAGES", 3)
    assert add(client, me, bundle["id"], pdf("1", "2"), "a.pdf").status_code == 201
    assert add(client, me, bundle["id"], pdf("3", "4"), "b.pdf").status_code == 413
    assert add(client, me, bundle["id"], png(), "p.png", "image/png").status_code == 202  # a picture is not a PDF page


def test_usage_and_limits_are_listed(client, me, bundle):
    add(client, me, bundle["id"], pdf("a", "b"), "a.pdf")
    add(client, me, bundle["id"], png(), "p.png", "image/png")
    body = listing(client, me, bundle["id"])
    assert [f["filename"] for f in body["files"]] == ["a.pdf", "p.png"]
    assert body["used"]["files"] == 2 and body["used"]["pdf_pages"] == 2 and body["used"]["bytes"] > 0
    assert body["limits"] == {"files": 10, "bytes": 50 * 1024 * 1024, "pdf_bytes": 20 * 1024 * 1024,
                              "image_bytes": 8 * 1024 * 1024, "pdf_pages": 300}  # fmt: skip


def test_worked_example_photos_count_toward_the_same_limits(client, me, bundle, monkeypatch):
    monkeypatch.setattr(api, "MAX_FILES", 2)
    add(client, me, bundle["id"], pdf("a"), "a.pdf")
    photo = client.post(f"/api/materials/{bundle['id']}/examples", files={"file": ("w.png", png(), "image/png")}, headers=me)
    assert photo.status_code == 202 and photo.json()["page"] == 2  # numbered after the PDF, by the same allocator
    assert add(client, me, bundle["id"], pdf("b"), "b.pdf").status_code == 409
    again = client.post(f"/api/materials/{bundle['id']}/examples", files={"file": ("x.png", png(), "image/png")}, headers=me)
    assert again.status_code == 409


def test_files_and_photos_never_share_a_page(client, me, bundle):
    add(client, me, bundle["id"], pdf("a", "b"), "a.pdf")
    photo = client.post(f"/api/materials/{bundle['id']}/examples", files={"file": ("w.png", png(), "image/png")}, headers=me).json()
    later = add(client, me, bundle["id"], pdf("c"), "c.pdf").json()
    assert photo["page"] == 3 and later["first_page"] == 4


# --- removing ---


def test_an_item_can_be_removed_before_a_lesson_and_its_pages_are_forgotten(client, me, bundle, engine, tmp_path):
    a = add(client, me, bundle["id"], pdf("hapus saya"), "a.pdf").json()
    b = add(client, me, bundle["id"], pdf("tetap"), "b.pdf").json()
    assert client.delete(f"/api/materials/{bundle['id']}/files/{a['id']}", headers=me).status_code == 204
    assert [f["id"] for f in listing(client, me, bundle["id"])["files"]] == [b["id"]]
    assert client.get(f"/api/files/{a['id']}/content", headers=me).status_code == 404
    with Session(engine) as db:
        assert rag.page_text(db, bundle["id"], 1) == "" and rag.page_text(db, bundle["id"], 2) == "tetap"  # pages stay stable
    c = add(client, me, bundle["id"], pdf("baru"), "c.pdf").json()
    assert c["first_page"] == 3  # a removed range is not handed out again


def test_an_item_cannot_be_removed_once_a_lesson_used_the_material(client, me, bundle):
    a = add(client, me, bundle["id"], pdf("x"), "a.pdf").json()
    body = {"profile_id": "matematika-fase-e", "class_name": "X", "subject": "Matematika", "chapter": "Peluang",
            "material_id": bundle["id"]}  # fmt: skip
    client.post("/api/sessions", json=body, headers=me)
    assert client.delete(f"/api/materials/{bundle['id']}/files/{a['id']}", headers=me).status_code == 409


# --- ownership and login ---


def test_another_teacher_cannot_see_add_or_remove(client, login, me, bundle):
    a = add(client, me, bundle["id"], pdf("x"), "a.pdf").json()
    other = login("Pak Budi", "budi@example.com")
    assert add(client, other, bundle["id"], pdf("y"), "b.pdf").status_code == 404
    assert client.get(f"/api/materials/{bundle['id']}/files", headers=other).status_code == 404
    assert client.get(f"/api/files/{a['id']}/content", headers=other).status_code == 404
    assert client.delete(f"/api/materials/{bundle['id']}/files/{a['id']}", headers=other).status_code == 404


def test_items_need_a_logged_in_teacher(client, me, bundle):
    assert add(client, {}, bundle["id"], pdf("x"), "a.pdf").status_code == 401
    assert client.get(f"/api/materials/{bundle['id']}/files").status_code == 401


# --- older clients and the rest of the pipeline ---


def test_the_old_single_pdf_upload_still_works(client, me, engine):
    r = client.post("/api/materials", files={"file": ("bab.pdf", pdf("Halaman satu", "Halaman dua"), "application/pdf")}, headers=me)
    assert r.status_code == 200 and r.json()["filename"] == "bab.pdf" and r.json()["page_count"] == 2
    served = client.get(f"/api/materials/{r.json()['id']}/file", headers=me)
    assert served.status_code == 200 and served.content.startswith(b"%PDF-")
    assert client.post("/api/materials", files={"file": ("p.png", png(), "image/png")}, headers=me).status_code == 400


def test_a_picture_on_stage_gives_the_students_its_text(client, me, bundle, engine):
    add(client, me, bundle["id"], pdf("x"), "a.pdf")
    picture = add(client, me, bundle["id"], png(), "tabel.png", "image/png").json()
    body = {"profile_id": "matematika-fase-e", "class_name": "X", "subject": "Matematika", "chapter": "Peluang",
            "material_id": bundle["id"]}  # fmt: skip
    session = client.post("/api/sessions", json=body, headers=me).json()
    assert client.post(f"/api/sessions/{session['id']}/slides", json={"page": picture["first_page"], "t_ms": 0}, headers=me).status_code == 204
    with Session(engine) as db:
        from app.models import TeachingSession

        text, page = questions._slide(db, db.get(TeachingSession, session["id"]))
        assert page == picture["first_page"] and "(Contoh)" in text


def test_a_report_for_a_lesson_that_switched_items_lists_their_pages(client, me, bundle, engine):
    a = add(client, me, bundle["id"], pdf("a1", "a2"), "a.pdf").json()
    picture = add(client, me, bundle["id"], png(), "p.png", "image/png").json()
    body = {"profile_id": "matematika-fase-e", "class_name": "X", "subject": "Matematika", "chapter": "Peluang",
            "material_id": bundle["id"]}  # fmt: skip
    session = client.post("/api/sessions", json=body, headers=me).json()
    for page, t in ((a["first_page"], 0), (picture["first_page"], 20_000), (0, 40_000), (a["first_page"] + 1, 60_000)):
        client.post(f"/api/sessions/{session['id']}/slides", json={"page": page, "t_ms": t}, headers=me)
    with Session(engine) as db:
        report = scoring.build_report(db, session["id"])
    pages = [s["page"] for s in report["metrics"]["time_per_slide"]]
    assert pages == [1, 2, 3]  # both PDF pages and the picture; the shared screen (page 0) is not a slide
