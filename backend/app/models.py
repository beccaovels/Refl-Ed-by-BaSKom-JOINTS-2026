"""Database tables. Mirrors the Database section of docs/plan.md."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def new_id() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=new_id, primary_key=True)
    name: str
    email: str = Field(index=True, unique=True)
    tier: str = "free"  # free | institutional


class Material(SQLModel, table=True):
    __tablename__ = "materials"
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    filename: str
    path: str
    page_count: int = 0


class MaterialChunk(SQLModel, table=True):
    __tablename__ = "material_chunks"
    id: str = Field(default_factory=new_id, primary_key=True)
    material_id: str = Field(foreign_key="materials.id", index=True)
    page: int
    order: int
    text: str
    embedding: list[float] = Field(default_factory=list, sa_column=Column(JSON))


class TeachingSession(SQLModel, table=True):
    __tablename__ = "sessions"
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    profile_id: str
    class_name: str
    subject: str
    chapter: str
    sub_chapter: str = ""
    material_id: Optional[str] = Field(default=None, foreign_key="materials.id")
    status: str = "active"  # active | ended | partial
    started_at: datetime = Field(default_factory=now)
    ended_at: Optional[datetime] = None
    camera_on: bool = False
    demo_mode: bool = True


class SlideEvent(SQLModel, table=True):
    __tablename__ = "slide_events"
    id: str = Field(default_factory=new_id, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    page: int
    t_ms: int


class TranscriptSegment(SQLModel, table=True):
    __tablename__ = "transcript_segments"
    # a resent audio chunk hits this constraint and is ignored
    __table_args__ = (UniqueConstraint("session_id", "seq"),)
    id: str = Field(default_factory=new_id, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    seq: int
    start_ms: int
    end_ms: int
    text: str


class AudioChunk(SQLModel, table=True):
    """One processed audio piece and what its reply carried. Not the audio itself, which is never stored.

    A silent piece has no transcript row, so this is what lets a resent piece get its first reply back.
    """

    __tablename__ = "audio_chunks"
    __table_args__ = (UniqueConstraint("session_id", "seq"),)
    id: str = Field(default_factory=new_id, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    seq: int
    segment_id: Optional[str] = Field(default=None, foreign_key="transcript_segments.id")
    event_id: Optional[str] = Field(default=None, foreign_key="questions.id")


class Question(SQLModel, table=True):
    __tablename__ = "questions"
    id: str = Field(default_factory=new_id, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    kind: str  # regular | misconception | capstone | nudge
    persona: Optional[str] = None
    text: str
    asked_at_ms: int
    answered_at_ms: Optional[int] = None
    refers_to_ms: Optional[int] = None


class SignalBin(SQLModel, table=True):
    __tablename__ = "signal_bins"
    __table_args__ = (UniqueConstraint("session_id", "t_start_ms"),)
    id: str = Field(default_factory=new_id, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    t_start_ms: int
    measured: bool = True  # false: too dark or face not found; left out of scoring
    facing_pct: Optional[float] = None
    posture_ok_pct: Optional[float] = None
    gesture_rate: Optional[float] = None
    expressiveness: Optional[float] = None
    face_visible_pct: Optional[float] = None
    volume: Optional[float] = None
    pitch_variation: Optional[float] = None


class Report(SQLModel, table=True):
    __tablename__ = "reports"
    id: str = Field(default_factory=new_id, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", unique=True)
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))  # the whole report, as first generated
    overall_score: Optional[float] = None
    created_at: datetime = Field(default_factory=now)


class FeedbackFlag(SQLModel, table=True):
    __tablename__ = "feedback_flags"
    id: str = Field(default_factory=new_id, primary_key=True)
    report_id: str = Field(foreign_key="reports.id", index=True)
    item_id: str
    created_at: datetime = Field(default_factory=now)


class ScheduleEntry(SQLModel, table=True):
    __tablename__ = "schedule"
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    planned_at: datetime
    subject: str
    chapter: str
    session_id: Optional[str] = Field(default=None, foreign_key="sessions.id")
