"""The shape of a finished report: `Report` in docs/api-contract.md, as Pydantic classes.

`scoring.build_report` validates against `ReportOut` before returning, so the
frontend always receives every field. The reports endpoint can use `ReportOut`
as its response_model instead of retyping the shape.
"""

from typing import Literal

from pydantic import BaseModel

Label = Literal["starting", "developing", "strong"]


class Item(BaseModel):
    id: str
    kind: Literal["worked", "noticed"]
    text: str
    quote: str | None = None  # the teacher's own words
    t_ms: int | None = None


class Idea(BaseModel):
    id: str
    text: str
    ready_to_use: str  # the example, story or question itself, in Bahasa Indonesia


class ParameterScore(BaseModel):
    key: str
    title: str
    score: float | None  # points earned, out of `max`
    max: int
    available: bool  # false when it could not be measured (no PDF, camera off, no student question)
    source: Literal["llm", "computed"]


class Dimension(BaseModel):
    key: str
    title: str
    score: int | None  # 0-100
    label: Label | None
    label_text: str | None
    weight: int  # share of the overall score
    available: bool
    locked: bool  # true when the tier does not include it
    unavailable_reason: str | None
    parameters: list[ParameterScore]
    items: list[Item]


class Overall(BaseModel):
    score: int | None  # 0-100; None when the recording was too short to assess
    label: Label | None
    label_text: str | None
    summary: str


class Metrics(BaseModel):
    words_per_minute: int
    pause_count: int
    questions_asked: int
    wait_time_avg_ms: int | None
    reading_share: float | None
    response_time_avg_ms: int | None
    filler_count: int
    time_per_slide: list[dict]


class Moment(BaseModel):
    t_ms: int
    kind: Literal["voice", "face", "both"]
    text: str


class AskedQuestion(BaseModel):
    event_id: str
    kind: str
    text: str
    asked_at_ms: int
    answer_quote: str | None
    response_time_ms: int | None


class ReportOut(BaseModel):
    id: str
    session_id: str
    created_at: str
    profile: dict  # { id, label }: the subject profile the lesson was read with
    overall: Overall
    strengths: list[Item]
    dimensions: list[Dimension]
    ideas: list[Idea]
    tip: str | None
    metrics: Metrics
    moments: list[Moment]
    questions: list[AskedQuestion]
