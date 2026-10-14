"""The reply to one audio piece. See the Audio section of docs/api-contract.md."""

from pydantic import BaseModel

from app.schemas.sessions import EventOut


class SegmentOut(BaseModel):
    seq: int
    start_ms: int
    end_ms: int
    text: str


class AudioReply(BaseModel):
    seq: int
    segment: SegmentOut | None  # null when the piece had no speech
    event: EventOut | None  # null most of the time
