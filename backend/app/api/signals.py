"""Delivery signal bins from the browser: ten seconds each, numbers only. Video never reaches the backend."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.auth import current_user, own_session
from app.core.db import get_session
from app.models import SignalBin, User
from app.schemas.signals import SignalsIn

router = APIRouter(tags=["signals"])


@router.post("/sessions/{session_id}/signals", status_code=204)
def receive_signals(
    session_id: str, body: SignalsIn, user: User = Depends(current_user), db: Session = Depends(get_session)
):
    """Saves the bins. A bin whose t_start_ms is already stored for this session is ignored.

    Accepted after the session has ended too: the last bin can arrive just after "Selesai mengajar".
    """
    own_session(db, session_id, user)
    stored = set(db.exec(select(SignalBin.t_start_ms).where(SignalBin.session_id == session_id)))
    new = {}
    for b in body.bins:
        if b.t_start_ms not in stored:
            new.setdefault(b.t_start_ms, b)  # a repeat inside one batch keeps the first
    rows = [SignalBin(session_id=session_id, **b.model_dump()) for b in new.values()]
    db.add_all(rows)
    try:
        db.commit()
    except IntegrityError:  # another request stored some of them a moment ago: save the rest one by one
        db.rollback()
        for b in new.values():
            db.add(SignalBin(session_id=session_id, **b.model_dump()))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
    return Response(status_code=204)
