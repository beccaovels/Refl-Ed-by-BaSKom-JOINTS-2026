"""Practice sessions. See the Sessions section of docs/api-contract.md."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlmodel import Session, select

from app.api.reports import start_report
from app.core.auth import current_user, own_session
from app.core.db import get_session
from app.models import Material, Question, Report, SlideEvent, TeachingSession, User, now
from app.schemas.reports import ReportPending
from app.schemas.sessions import EndOut, SessionIn, SessionListItem, SessionOut, SlideIn
from app.services import profiles, questions

router = APIRouter(tags=["sessions"])


@router.post("/sessions", response_model=SessionOut)
def create_session(body: SessionIn, user: User = Depends(current_user), db: Session = Depends(get_session)):
    if profiles.get(body.profile_id) is None:
        raise HTTPException(status_code=422, detail="Profil mata pelajaran tidak dikenal.")
    if body.material_id is not None:
        material = db.get(Material, body.material_id)
        if material is None or material.user_id != user.id:
            raise HTTPException(status_code=404, detail="Materi tidak ditemukan.")
    session = TeachingSession(user_id=user.id, **body.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionOut.of(session)


@router.get("/sessions", response_model=list[SessionListItem])
def list_sessions(user: User = Depends(current_user), db: Session = Depends(get_session)):
    """The teacher's sessions, newest first, with the score from the stored report when there is one."""
    rows = db.exec(
        select(TeachingSession, Report)
        .join(Report, Report.session_id == TeachingSession.id, isouter=True)
        .where(TeachingSession.user_id == user.id)
        .order_by(TeachingSession.started_at.desc())
    ).all()
    return [
        SessionListItem(
            **SessionOut.of(session).model_dump(),
            overall_score=report.overall_score if report else None,
            overall_label=((report.data or {}).get("overall") or {}).get("label") if report else None,
        )
        for session, report in rows
    ]


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session_detail(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_session)):
    return SessionOut.of(own_session(db, session_id, user))


@router.post("/sessions/{session_id}/slides", status_code=204)
def slide_turn(session_id: str, body: SlideIn, user: User = Depends(current_user), db: Session = Depends(get_session)):
    """One page turn. A turn already stored (same page, same time) is ignored, so a retry is safe."""
    session = own_session(db, session_id, user)
    _require_active(session)
    if session.material_id:
        material = db.get(Material, session.material_id)
        if material and body.page > material.page_count:
            raise HTTPException(status_code=422, detail="Nomor halaman melebihi jumlah halaman materi.")
    seen = db.exec(
        select(SlideEvent).where(
            SlideEvent.session_id == session_id, SlideEvent.page == body.page, SlideEvent.t_ms == body.t_ms
        )
    ).first()
    if seen is None:
        db.add(SlideEvent(session_id=session_id, page=body.page, t_ms=body.t_ms))
        db.commit()
    return Response(status_code=204)


@router.post("/sessions/{session_id}/end", response_model=EndOut)
def end(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_session)):
    """"Selesai mengajar": the one closing question. Pressing it again returns the same question.

    The session stays active so the teacher's answer is still transcribed; /finish closes it.
    """
    session = own_session(db, session_id, user)
    _require_active(session)
    asked = db.exec(select(Question).where(Question.session_id == session_id, Question.kind == "capstone")).first()
    event = questions.to_event(asked) if asked else questions.capstone(db, session_id)
    return EndOut(event=event)


@router.post("/sessions/{session_id}/finish", status_code=202, response_model=ReportPending)
def finish(
    session_id: str,
    background: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
):
    """After the capstone answer: close the session and start making the report. Safe to call again."""
    session = own_session(db, session_id, user)
    if session.status == "active":
        session.status = "ended"
        session.ended_at = now()
        db.add(session)
        db.commit()
    start_report(db, session_id, background)
    return ReportPending()


def _require_active(session: TeachingSession) -> None:
    if session.status != "active":
        raise HTTPException(status_code=409, detail="Sesi ini sudah selesai.")
