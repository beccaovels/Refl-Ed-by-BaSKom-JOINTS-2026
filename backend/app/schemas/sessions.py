"""Practice sessions, page turns and the closing question. See the Sessions section of docs/api-contract.md."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import TeachingSession


class SessionIn(BaseModel):
    profile_id: str = Field(min_length=1)
    class_name: str = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=1, max_length=100)
    chapter: str = Field(min_length=1, max_length=200)
    sub_chapter: str = Field(default="", max_length=200)
    material_id: str | None = None
    camera_on: bool = False
    demo_mode: bool = True

    @field_validator("class_name", "subject", "chapter", "sub_chapter", mode="before")
    @classmethod
    def strip(cls, value):
        return value.strip() if isinstance(value, str) else value


class SessionOut(BaseModel):
    id: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    profile_id: str
    class_name: str
    subject: str
    chapter: str
    sub_chapter: str
    material_id: str | None
    camera_on: bool
    demo_mode: bool

    @classmethod
    def of(cls, session: TeachingSession) -> "SessionOut":
        return cls.model_validate(session, from_attributes=True)


class SessionListItem(SessionOut):
    overall_score: float | None = None  # copied from the stored report; null until it exists
    overall_label: str | None = None


class EventOut(BaseModel):
    """A student event, as returned by app.services.questions. Extra fields from the service are passed on."""

    model_config = ConfigDict(extra="allow")

    id: str
    kind: str
    persona: dict | None = None
    text: str
    asked_at_ms: int
    refers_to_ms: int | None = None


class EndOut(BaseModel):
    event: EventOut


class SlideIn(BaseModel):
    page: int = Field(ge=1)
    t_ms: int = Field(ge=0)
