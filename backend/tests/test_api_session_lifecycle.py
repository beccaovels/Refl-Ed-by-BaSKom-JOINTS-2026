"""A lesson's material is optional: a session without one is created, ended, saved and listed like any other."""

from sqlmodel import Session, select

from app.models import Report, TeachingSession

PROFILE = "matematika-fase-e"


def start(client, headers, **fields):
    body = {"profile_id": PROFILE, "class_name": "X-1", "subject": "Matematika", "chapter": "Peluang"} | fields
    return client.post("/api/sessions", json=body, headers=headers)


def test_a_session_without_material_is_ended_saved_and_listed(client, login, engine):
    me = login()
    session = start(client, me).json()  # no material_id at all
    assert session["material_id"] is None and session["status"] == "active"

    end = client.post(f"/api/sessions/{session['id']}/end", headers=me)
    assert end.status_code == 200 and end.json()["event"]["kind"] == "capstone"  # materials are not needed to end
    assert client.post(f"/api/sessions/{session['id']}/finish", headers=me).status_code == 202

    listed = client.get("/api/sessions", headers=me).json()
    assert [s["id"] for s in listed] == [session["id"]]
    assert listed[0]["status"] == "ended" and listed[0]["ended_at"] and listed[0]["material_id"] is None
    assert listed[0]["overall_score"] is None  # nobody spoke in this test, and a recording that short is not scored by design
    with Session(engine) as db:
        assert db.exec(select(Report)).one().session_id == session["id"]
        assert db.get(TeachingSession, session["id"]).status == "ended"


def test_a_session_started_from_a_schedule_without_material_works_the_same(client, login):
    # a scheduled practice carries no material: the room starts it with material_id null, exactly like a manual one
    me = login()
    session = start(client, me, material_id=None, sub_chapter="Ruang sampel").json()
    client.post(f"/api/sessions/{session['id']}/end", headers=me)
    client.post(f"/api/sessions/{session['id']}/finish", headers=me)
    assert client.get(f"/api/sessions/{session['id']}", headers=me).json()["status"] == "ended"


def test_an_empty_bundle_is_not_a_reason_to_refuse_ending(client, login):
    me = login()
    bundle = client.post("/api/materials", headers=me).json()  # a material with no files in it
    session = start(client, me, material_id=bundle["id"]).json()
    assert client.post(f"/api/sessions/{session['id']}/end", headers=me).status_code == 200
    assert client.post(f"/api/sessions/{session['id']}/finish", headers=me).status_code == 202


def test_a_material_that_is_not_the_teachers_is_refused_when_the_session_is_created(client, login):
    # the root of "materi tidak ditemukan": a stale id. The session is not created at all, so the room starts it
    # again without the material (frontend) instead of leaving a lesson that can never be ended.
    bundle = client.post("/api/materials", headers=login()).json()
    other = login("Pak Budi", "budi@example.com")
    assert start(client, other, material_id=bundle["id"]).status_code == 404
    assert client.get("/api/sessions", headers=other).json() == []
    assert start(client, other, material_id=None).status_code == 200  # and without it, it works
