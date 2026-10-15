"""The report after a lesson: generated once in the background, stored whole, reopened unchanged.

GET  /sessions/{id}/report   200 Report | 202 pending | 500 failed
POST /reports/{id}/flags     "Ini tidak akurat": hides one item from then on

Generation is started by POST /sessions/{id}/finish in api/sessions.py, through start_report().
"""

import copy
import logging
from threading import Lock

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.auth import current_user, own_session
from app.core.db import get_session
from app.models import FeedbackFlag, Report, TeachingSession, User
from app.schemas.reports import FlagIn, ReportPending
from app.services import scoring

log = logging.getLogger(__name__)
router = APIRouter(tags=["reports"])

# session_id -> "pending" | "failed". Kept in memory: after a restart a pending job is gone,
# and calling /finish again simply starts it over. A stored report always wins over this.
_jobs: dict[str, str] = {}
_jobs_lock = Lock()


def start_report(db: Session, session_id: str, background: BackgroundTasks) -> None:
    """Queue report generation unless the report exists or is already being made."""
    if _stored(db, session_id) is not None:
        return
    with _jobs_lock:
        if _jobs.get(session_id) == "pending":
            return
        _jobs[session_id] = "pending"
    # the request's own db session closes with the request, so the job opens one on the same engine
    background.add_task(_build, session_id, db.get_bind())


def _build(session_id: str, engine: Engine) -> None:
    try:
        with Session(engine) as db:
            data = scoring.build_report(db, session_id)
            db.add(
                Report(
                    id=data["id"],  # the id the frontend sees in the report is the one /flags is called with
                    session_id=session_id,
                    data=data,
                    overall_score=(data.get("overall") or {}).get("score"),
                )
            )
            try:
                db.commit()
            except IntegrityError:
                db.rollback()  # a report for this session was already saved; keep the first one
        with _jobs_lock:
            _jobs.pop(session_id, None)
    except Exception:
        log.exception("Report generation failed for session %s", session_id)
        with _jobs_lock:
            _jobs[session_id] = "failed"


def _stored(db: Session, session_id: str) -> Report | None:
    return db.exec(select(Report).where(Report.session_id == session_id)).first()


@router.get(
    "/sessions/{session_id}/report",
    responses={202: {"model": ReportPending}, 404: {}, 500: {}},
)
def get_report(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_session)):
    own_session(db, session_id, user)
    report = _stored(db, session_id)
    if report is not None:
        flagged = set(db.exec(select(FeedbackFlag.item_id).where(FeedbackFlag.report_id == report.id)))
        return _without(report.data, flagged)
    state = _jobs.get(session_id)
    if state == "pending":
        return JSONResponse(status_code=202, content=ReportPending().model_dump())
    if state == "failed":
        raise HTTPException(status_code=500, detail="Laporan belum berhasil dibuat. Silakan coba lagi.")
    raise HTTPException(status_code=404, detail="Laporan untuk sesi ini belum dibuat.")


@router.post("/reports/{report_id}/flags", status_code=204)
def flag_item(report_id: str, body: FlagIn, user: User = Depends(current_user), db: Session = Depends(get_session)):
    report = db.get(Report, report_id)
    session = db.get(TeachingSession, report.session_id) if report else None
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan.")
    if body.item_id not in _item_ids(report.data):
        raise HTTPException(status_code=404, detail="Bagian laporan tidak ditemukan.")
    already = db.exec(
        select(FeedbackFlag).where(FeedbackFlag.report_id == report_id, FeedbackFlag.item_id == body.item_id)
    ).first()
    if already is None:
        db.add(FeedbackFlag(report_id=report_id, item_id=body.item_id))
        db.commit()
    return Response(status_code=204)


def _item_lists(data: dict) -> list[list]:
    """Every list of flaggable items in a report: strengths, each card's items, ideas, each worked example's items."""
    lists = [data.get("strengths") or [], data.get("ideas") or []]
    lists += [d.get("items") or [] for d in data.get("dimensions") or []]
    lists += [e.get("items") or [] for e in data.get("examples") or []]
    return lists


def _item_ids(data: dict) -> set[str]:
    return {item["id"] for items in _item_lists(data) for item in items if isinstance(item, dict) and "id" in item}


def _without(data: dict, flagged: set[str]) -> dict:
    """The stored report with flagged items removed. The stored JSON itself is never changed."""
    if not flagged:
        return data
    shown = copy.deepcopy(data)
    for items in _item_lists(shown):
        items[:] = [item for item in items if not (isinstance(item, dict) and item.get("id") in flagged)]
    return shown
