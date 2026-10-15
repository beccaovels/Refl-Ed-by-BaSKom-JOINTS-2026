"""Worked-example endpoints: upload a photo, read it in the background, confirm it, see the check."""

import pymupdf
import pytest
from sqlmodel import Session, select

from app.models import WorkedExample
from app.services import examples


def png() -> bytes:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 40), False)
    pix.clear_with(255)
    return pix.tobytes("png")


def jpg() -> bytes:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 40), False)
    pix.clear_with(200)
    return pix.tobytes("jpeg")


def pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page()
    return doc.tobytes()


@pytest.fixture
def me(login):
    return login()


@pytest.fixture
def material(client, me):
    """A material with a one-page PDF, so photos are numbered from page 2."""
    return client.post("/api/materials", files={"file": ("bab.pdf", pdf(), "application/pdf")}, headers=me).json()


def photo(client, headers, material_id, data=None, name="papan.png"):
    return client.post(
        f"/api/materials/{material_id}/examples", files={"file": (name, png() if data is None else data, "image/png")}, headers=headers
    )


def test_an_uploaded_photo_is_read_in_the_background(client, me, material):
    r = photo(client, me, material["id"])
    assert r.status_code == 202
    example = r.json()
    assert example["page"] == 2 and example["material_id"] == material["id"]  # numbered after the PDF's one page
    assert example["status"] == "reading" and example["check"] is None

    listed = client.get(f"/api/materials/{material['id']}/examples", headers=me).json()
    assert [e["id"] for e in listed] == [example["id"]]
    assert listed[0]["status"] == "unconfirmed"  # the background job has finished the reading
    assert listed[0]["reading"]["question"] and listed[0]["check"] is None  # nothing is checked before confirming


def test_photos_are_numbered_in_upload_order_and_jpg_is_accepted(client, me, material):
    first = photo(client, me, material["id"]).json()
    second = photo(client, me, material["id"], data=jpg(), name="foto.jpg").json()
    assert (first["page"], second["page"]) == (2, 3)
    assert [e["page"] for e in client.get(f"/api/materials/{material['id']}/examples", headers=me).json()] == [2, 3]


def test_a_photo_works_on_a_material_without_a_pdf(client, me):
    empty = client.post("/api/materials", headers=me).json()
    assert photo(client, me, empty["id"]).json()["page"] == 1


def test_the_photo_can_be_fetched_back(client, me, material):
    example = photo(client, me, material["id"]).json()
    r = client.get(f"/api/examples/{example['id']}/file", headers=me)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content == png()


def test_confirming_with_nothing_sent_checks_the_working(client, me, material):
    example = photo(client, me, material["id"]).json()
    r = client.post(f"/api/examples/{example['id']}/confirm", json={}, headers=me)
    assert r.status_code == 200
    confirmed = r.json()
    assert confirmed["status"] == "confirmed" and confirmed["check"]["steps"]
    assert all(not s["unclear"] for s in confirmed["reading"]["steps"])  # the teacher's own statement: nothing is "unsure"


def test_confirming_with_an_edit_replaces_only_what_was_sent(client, me, material):
    example = photo(client, me, material["id"]).json()
    before = client.get(f"/api/materials/{material['id']}/examples", headers=me).json()[0]["reading"]
    r = client.post(f"/api/examples/{example['id']}/confirm", json={"final_answer": "P(A) = 1/6"}, headers=me).json()
    assert r["reading"]["final_answer"] == "P(A) = 1/6" and r["reading"]["question"] == before["question"]
    again = client.post(f"/api/examples/{example['id']}/confirm", json={"steps": ["n(S) = 36", "n(A) = 6"]}, headers=me).json()
    assert [s["text"] for s in again["reading"]["steps"]] == ["n(S) = 36", "n(A) = 6"]  # can be confirmed again


def test_a_photo_that_could_not_be_read_can_be_typed_in(client, me, material, engine):
    example = photo(client, me, material["id"]).json()
    with Session(engine) as db:
        row = db.get(WorkedExample, example["id"])
        row.status, row.reading = "unreadable", None
        db.add(row)
        db.commit()
    assert client.post(f"/api/examples/{example['id']}/confirm", json={}, headers=me).status_code == 400  # nothing to confirm
    typed = {"question": "Peluang dadu bermata 7?", "steps": ["n(S) = 36", "n(A) = 6"], "final_answer": "1/6"}
    assert client.post(f"/api/examples/{example['id']}/confirm", json=typed, headers=me).json()["status"] == "confirmed"


def test_confirming_while_still_reading_is_409(client, me, material, engine):
    example = photo(client, me, material["id"]).json()
    with Session(engine) as db:
        row = db.get(WorkedExample, example["id"])
        row.status = "reading"
        db.add(row)
        db.commit()
    assert client.post(f"/api/examples/{example['id']}/confirm", json={}, headers=me).status_code == 409


def test_a_failed_reading_never_leaves_the_photo_stuck(client, me, material, monkeypatch):
    def boom(db, example_id, subject=""):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(examples, "read", boom)
    photo(client, me, material["id"])
    assert client.get(f"/api/materials/{material['id']}/examples", headers=me).json()[0]["status"] == "failed"


@pytest.mark.parametrize("data", [b"just some text", b"%PDF-1.7 not a photo", b"\x89PNG\r\n\x1a\nbroken"])
def test_a_file_that_is_not_a_photo_is_400(client, me, material, data):
    assert photo(client, me, material["id"], data=data).status_code == 400


def test_a_photo_over_8_mb_is_413(client, me, material, monkeypatch):
    from app.api import examples as api

    monkeypatch.setattr(api, "MAX_BYTES", 100)
    assert photo(client, me, material["id"]).status_code == 413


def test_invalid_confirm_bodies_are_422(client, me, material):
    example = photo(client, me, material["id"]).json()
    url = f"/api/examples/{example['id']}/confirm"
    assert client.post(url, json={"verdict": "salah"}, headers=me).status_code == 422
    assert client.post(url, json={"steps": ["x"] * 31}, headers=me).status_code == 422


def test_another_teacher_sees_nothing_of_it(client, login, me, material):
    example = photo(client, me, material["id"]).json()
    other = login("Pak Budi", "budi@example.com")
    assert photo(client, other, material["id"]).status_code == 404
    assert client.get(f"/api/materials/{material['id']}/examples", headers=other).status_code == 404
    assert client.get(f"/api/examples/{example['id']}/file", headers=other).status_code == 404
    assert client.post(f"/api/examples/{example['id']}/confirm", json={}, headers=other).status_code == 404


def test_examples_need_a_logged_in_teacher(client, me, material):
    example = photo(client, me, material["id"]).json()
    assert client.get(f"/api/materials/{material['id']}/examples").status_code == 401
    assert client.post(f"/api/examples/{example['id']}/confirm", json={}).status_code == 401


def test_a_photo_page_can_be_put_on_stage_and_nothing_is_stored_unchecked(client, me, material, engine):
    example = photo(client, me, material["id"]).json()
    body = {"profile_id": "matematika-fase-e", "class_name": "X-1", "subject": "Matematika", "chapter": "Peluang",
            "material_id": material["id"]}  # fmt: skip
    session = client.post("/api/sessions", json=body, headers=me).json()
    r = client.post(f"/api/sessions/{session['id']}/slides", json={"page": example["page"], "t_ms": 1000}, headers=me)
    assert r.status_code == 204
    with Session(engine) as db:
        assert db.exec(select(WorkedExample)).one().check_result is None  # putting it on stage checks nothing
