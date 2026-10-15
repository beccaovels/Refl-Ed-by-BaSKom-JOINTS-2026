"""Schedule: a read-only list of the teacher's planned practice sessions. No calendar, no reminders."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.auth import current_user
from app.core.db import get_session
from app.models import ScheduleEntry, User
from app.schemas.schedule import ScheduleOut

router = APIRouter(tags=["schedule"])


@router.get("/schedule", response_model=list[ScheduleOut])
def list_schedule(user: User = Depends(current_user), db: Session = Depends(get_session)):
    entries = db.exec(
        select(ScheduleEntry).where(ScheduleEntry.user_id == user.id).order_by(ScheduleEntry.planned_at)
    ).all()
    return [
        ScheduleOut(id=e.id, datetime=e.planned_at, subject=e.subject, chapter=e.chapter, session_id=e.session_id)
        for e in entries
    ]
