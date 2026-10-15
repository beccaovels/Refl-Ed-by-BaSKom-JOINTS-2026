"""Report endpoints: /finish starts it, GET /report polls it, /flags hides an item."""

import pytest
from sqlmodel import Session, select

from app.api import reports as reports_api
from app.models import FeedbackFlag, Report, TeachingSession, User
from app.services import llm, scoring


@pytest.fixture
def teacher(engine):
    with Session(engine) as db:
        user = User(name="Bu Rina", email="rina@example.com")
        other = User(name="Pak Budi", email="budi@example.com")
        db.add(user)
        db.add(other)
        db.commit()
        lesson = TeachingSession(
            user_id=user.id, profile_id="matematika-fase-e", class_name="X-1", subject="Matematika", chapter="Fungsi kuadrat"
        )
        db.add(lesson)
        db.commit()
        return {"user": user.id, "other": other.id, "session": lesson.id}


def as_user(user_id):
    return {"X-User-Id": user_id}


def finish(client, teacher, user=None):
    return client.post(f"/api/sessions/{teacher['session']}/finish", headers=as_user(user or teacher["user"]))


def get_report(client, teacher, user=None):
    return client.get(f"/api/sessions/{teacher['session']}/report", headers=as_user(user or teacher["user"]))


# --- finish and poll ---


def test_finish_builds_and_stores_one_report(client, teacher, engine):
    r = finish(client, teacher)
    assert r.status_code == 202 and r.json() == {"report_status": "pending"}

    r = get_report(client, teacher)
    assert r.status_code == 200
    report = r.json()
    assert report["session_id"] == teacher["session"]
    with Session(engine) as db:
        stored = db.exec(select(Report)).all()
        assert len(stored) == 1 and stored[0].id == report["id"]
        assert stored[0].overall_score == report["overall"]["score"]
        assert db.get(TeachingSession, teacher["session"]).status == "ended"


def test_finishing_twice_keeps_the_first_report(client, teacher, engine):
    finish(client, teacher)
    first = get_report(client, teacher).json()
    finish(client, teacher)
    assert get_report(client, teacher).json() == first  # reopens identically, e.g. from History
    with Session(engine) as db:
        assert len(db.exec(select(Report)).all()) == 1


def test_no_report_before_finish(client, teacher):
    assert get_report(client, teacher).status_code == 404


def test_pending_while_being_made(client, teacher):
    reports_api._jobs[teacher["session"]] = "pending"
    r = get_report(client, teacher)
    assert r.status_code == 202 and r.json() == {"report_status": "pending"}


def test_failure_is_a_clear_error_and_finish_can_retry(client, teacher, monkeypatch):
    real = scoring.build_report

    def broken(db, session_id):
        raise llm.LLMError("every model busy")

    monkeypatch.setattr(scoring, "build_report", broken)
    finish(client, teacher)
    r = get_report(client, teacher)
    assert r.status_code == 500 and r.json()["detail"]

    monkeypatch.setattr(scoring, "build_report", real)
    finish(client, teacher)
    assert get_report(client, teacher).status_code == 200


# --- who may see what ---


def test_missing_or_unknown_user_is_401(client, teacher):
    assert client.get(f"/api/sessions/{teacher['session']}/report").status_code == 401
    assert get_report(client, teacher, user="not-a-user").status_code == 401


def test_another_teachers_session_is_not_found(client, teacher, engine):
    assert finish(client, teacher, user=teacher["other"]).status_code == 404
    finish(client, teacher)
    assert get_report(client, teacher, user=teacher["other"]).status_code == 404
    with Session(engine) as db:
        report_id = db.exec(select(Report)).one().id
    r = client.post(f"/api/reports/{report_id}/flags", json={"item_id": "x"}, headers=as_user(teacher["other"]))
    assert r.status_code == 404


# --- flags ---


def test_flagged_item_is_hidden_from_then_on(client, teacher, engine):
    finish(client, teacher)
    report = get_report(client, teacher).json()
    item = report["strengths"][0]
    url = f"/api/reports/{report['id']}/flags"

    assert client.post(url, json={"item_id": item["id"]}, headers=as_user(teacher["user"])).status_code == 204
    assert client.post(url, json={"item_id": item["id"]}, headers=as_user(teacher["user"])).status_code == 204

    shown = get_report(client, teacher).json()
    every_id = [i["id"] for i in shown["strengths"] + shown["ideas"]]
    every_id += [i["id"] for d in shown["dimensions"] for i in d["items"]]
    assert item["id"] not in every_id
    with Session(engine) as db:
        assert len(db.exec(select(FeedbackFlag)).all()) == 1  # a second click is not a second flag
        assert db.exec(select(Report)).one().data == report  # the stored report itself is unchanged


def test_flagging_an_unknown_item_is_404(client, teacher):
    finish(client, teacher)
    report = get_report(client, teacher).json()
    r = client.post(f"/api/reports/{report['id']}/flags", json={"item_id": "nope"}, headers=as_user(teacher["user"]))
    assert r.status_code == 404
