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
    page: int | None = None  # set when the quote is from the teacher's writing: the page of that worked example


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


class Exchange(BaseModel):
    """One exchange with an AI student: a question they asked, or their answer to the teacher's question."""

    event_id: str
    kind: str  # regular | misconception | capstone | answer
    persona: dict | None
    text: str  # what the student said
    asked_at_ms: int
    level: int | None  # depth of a student's question: 1 clarify, 2 why/how, 3 what-if
    teacher_question: str | None  # kind `answer`: the teacher's question the student answered
    answer_quote: str | None  # what the teacher said next
    response_time_ms: int | None
    satisfied: bool | None  # whether the student showed the answer landed
    follow_up: str | None  # the student's one follow-up, when the first answer did not settle it


class ExampleOut(BaseModel):
    """A photo of the teacher's own working. Only a confirmed example that was shown counts in the score."""

    example_id: str
    page: int
    shown_at_ms: int | None  # when it was first on stage; None if it never was
    shown_ms: int  # how long it was on stage in total
    confirmed: bool  # the teacher said "this is what I wrote", or edited it
    reading: dict | None  # { question, steps: [{ n, text, unclear }], final_answer, answer_unclear }
    check: dict | None  # { answer, our_answer, steps: [{ n, status, note }], summary }; None until confirmed
    items: list[Item]  # at most one worked and one noticed, worked first


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
    questions: list[Exchange]
    examples: list[ExampleOut]  # the teacher's handwritten worked examples, in page order
