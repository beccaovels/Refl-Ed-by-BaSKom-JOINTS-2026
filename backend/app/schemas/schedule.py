"""Planned practice sessions. See the Schedule section of docs/api-contract.md."""

from datetime import datetime

from pydantic import BaseModel


class ScheduleOut(BaseModel):
    id: str
    datetime: datetime
    subject: str
    chapter: str
    session_id: str | None
