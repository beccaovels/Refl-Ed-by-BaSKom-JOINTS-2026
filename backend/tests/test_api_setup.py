"""Setup endpoints: health, login, profiles, materials, creating and listing sessions."""

import pymupdf
import pytest
from sqlmodel import Session, select

from app.core.config import settings
from app.models import Material, MaterialChunk, Report, TeachingSession
from app.services import rag

PROFILE = "matematika-fase-e"


def pdf_bytes(*pages: str) -> bytes:
    pdf = pymupdf.open()
    for text in pages:
        pdf.new_page().insert_text((72, 72), text)
    data = pdf.tobytes()
    pdf.close()
    return data


def upload(client, headers, data=None, name="bab7.pdf"):
    data = pdf_bytes("Peluang suatu kejadian.", "Ruang sampel.") if data is None else data
    return client.post("/api/materials", files={"file": (name, data, "application/pdf")}, headers=headers)


def new_session(client, headers, **fields):
    body = {"profile_id": PROFILE, "class_name": "X-1", "subject": "Matematika", "chapter": "Peluang"} | fields
    return client.post("/api/sessions", json=body, headers=headers)


# --- health and login ---


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_login_creates_a_new_teacher_then_returns_the_same_one(client):
    first = client.post("/api/auth/login", json={"name": "Bu Rina", "email": "Rina@Example.com "}).json()
    assert first["email"] == "rina@example.com" and first["tier"] == "free" and first["id"]
    again = client.post("/api/auth/login", json={"name": "Rina", "email": "rina@example.com"}).json()
    assert again == first


@pytest.mark.parametrize(
    "body", [{"name": "Bu Rina"}, {"email": "rina@example.com"}, {"name": "", "email": "rina@example.com"},
             {"name": "Bu Rina", "email": "bukan-email"}],
)  # fmt: skip
def test_login_rejects_missing_or_invalid_fields(client, body):
    assert client.post("/api/auth/login", json=body).status_code == 422


# --- profiles ---


def test_untested_profiles_are_hidden_unless_switched_on(client, monkeypatch):
    monkeypatch.setattr(settings, "show_untested_profiles", False)  # whatever backend/.env says
    assert client.get("/api/profiles").json() == []  # no profile is marked tested yet
    monkeypatch.setattr(settings, "show_untested_profiles", True)
    listed = client.get("/api/profiles").json()
    assert {"id": PROFILE, "subject": "Matematika", "grade": 10, "phase": "E", "label": "Matematika Kelas X"} in listed


# --- materials ---


def test_pdf_is_saved_indexed_and_served_back(client, login, engine):
    me = login()
    r = upload(client, me)
    assert r.status_code == 200
    material = r.json()
    assert material["filename"] == "bab7.pdf" and material["page_count"] == 2
    with Session(engine) as db:
        assert rag.page_text(db, material["id"], 2) == "Ruang sampel."

    served = client.get(f"/api/materials/{material['id']}/file", headers=me)
    assert served.status_code == 200 and served.headers["content-type"] == "application/pdf"
    assert served.content.startswith(b"%PDF-")


def test_a_file_that_is_not_a_pdf_is_400(client, login):
    assert upload(client, login(), data=b"hello, not a pdf", name="catatan.pdf").status_code == 400


def test_a_broken_pdf_is_400(client, login):
    assert upload(client, login(), data=b"%PDF-1.7 then nothing useful").status_code == 400


def test_a_pdf_over_20_mb_is_413(client, login, monkeypatch):
    from app.api import materials

    monkeypatch.setattr(materials, "MAX_BYTES", 1_000)
    assert upload(client, login(), data=b"%PDF-" + b"0" * 2_000).status_code == 413


def test_failed_indexing_leaves_no_row_and_no_file(client, login, engine, monkeypatch, tmp_path):
    def broken(db, material_id):
        db.add(MaterialChunk(material_id=material_id, page=1, order=0, text="half done"))
        db.flush()
        raise RuntimeError("index failed")

    monkeypatch.setattr(rag, "index_material", broken)
    assert upload(client, login()).status_code == 500
    with Session(engine) as db:
        assert db.exec(select(Material)).all() == [] and db.exec(select(MaterialChunk)).all() == []
    assert list((tmp_path / "uploads").glob("*")) == []


def test_another_teachers_pdf_is_not_found(client, login):
    material = upload(client, login()).json()
    other = login("Pak Budi", "budi@example.com")
    assert client.get(f"/api/materials/{material['id']}/file", headers=other).status_code == 404


def test_materials_need_a_logged_in_teacher(client):
    assert upload(client, {}).status_code == 401


# --- sessions ---


def test_create_and_read_a_session(client, login):
    me = login()
    material = upload(client, me).json()
    r = new_session(client, me, sub_chapter="Ruang sampel", material_id=material["id"], camera_on=True)
    assert r.status_code == 200
    session = r.json()
    assert session["status"] == "active" and session["ended_at"] is None
    assert session["material_id"] == material["id"] and session["camera_on"] is True
    assert client.get(f"/api/sessions/{session['id']}", headers=me).json() == session


def test_session_with_unknown_profile_or_missing_fields_is_rejected(client, login):
    me = login()
    assert new_session(client, me, profile_id="sihir-fase-z").status_code == 422
    assert new_session(client, me, chapter="").status_code == 422


def test_session_cannot_use_another_teachers_material(client, login):
    material = upload(client, login()).json()
    other = login("Pak Budi", "budi@example.com")
    assert new_session(client, other, material_id=material["id"]).status_code == 404


def test_another_teachers_session_is_not_found(client, login):
    session = new_session(client, login()).json()
    other = login("Pak Budi", "budi@example.com")
    assert client.get(f"/api/sessions/{session['id']}", headers=other).status_code == 404
    assert client.get("/api/sessions/does-not-exist", headers=other).status_code == 404
    assert client.get("/api/sessions", headers=other).json() == []


def test_sessions_are_listed_newest_first_with_score_once_reported(client, login, engine):
    me = login()
    first = new_session(client, me, chapter="Peluang").json()
    second = new_session(client, me, chapter="Statistika").json()
    with Session(engine) as db:
        db.add(Report(session_id=first["id"], data={"overall": {"score": 72, "label": "developing"}}, overall_score=72))
        db.commit()

    listed = client.get("/api/sessions", headers=me).json()
    assert [s["id"] for s in listed] == [second["id"], first["id"]]
    assert listed[0]["overall_score"] is None and listed[0]["overall_label"] is None  # no report yet
    assert listed[1]["overall_score"] == 72 and listed[1]["overall_label"] == "developing"
    with Session(engine) as db:
        assert len(db.exec(select(TeachingSession)).all()) == 2


# --- schedule ---


def test_schedule_lists_only_my_planned_sessions_in_time_order(client, login, engine):
    from datetime import datetime, timezone

    from app.models import ScheduleEntry, User

    me = login()
    login("Pak Budi", "budi@example.com")
    assert client.get("/api/schedule", headers=me).json() == []
    with Session(engine) as db:
        rina = db.exec(select(User).where(User.email == "rina@example.com")).one()
        budi = db.exec(select(User).where(User.email == "budi@example.com")).one()
        db.add(ScheduleEntry(user_id=rina.id, planned_at=datetime(2026, 10, 20, 9, tzinfo=timezone.utc), subject="Matematika", chapter="Statistika"))
        db.add(ScheduleEntry(user_id=rina.id, planned_at=datetime(2026, 10, 16, 9, tzinfo=timezone.utc), subject="Matematika", chapter="Peluang"))
        db.add(ScheduleEntry(user_id=budi.id, planned_at=datetime(2026, 10, 17, 9, tzinfo=timezone.utc), subject="Biologi", chapter="Sel"))
        db.commit()
    listed = client.get("/api/schedule", headers=me).json()
    assert [e["chapter"] for e in listed] == ["Peluang", "Statistika"]
    assert set(listed[0]) == {"id", "datetime", "subject", "chapter", "session_id"}


def test_schedule_needs_a_logged_in_teacher(client):
    assert client.get("/api/schedule").status_code == 401


# --- materials without a PDF ---


def test_a_material_can_be_created_without_a_pdf(client, login, engine):
    me = login()
    r = client.post("/api/materials", headers=me)
    assert r.status_code == 200 and r.json()["filename"] is None and r.json()["page_count"] == 0
    assert client.get(f"/api/materials/{r.json()['id']}/file", headers=me).status_code == 404  # no PDF to serve
    assert new_session(client, me, material_id=r.json()["id"]).status_code == 200  # usable for a session
