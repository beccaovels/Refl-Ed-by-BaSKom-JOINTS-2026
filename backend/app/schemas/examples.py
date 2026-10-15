"""Handwritten worked examples ("Papan tulis"). See the Handwritten worked examples section of docs/api-contract.md."""

from pydantic import BaseModel, ConfigDict, Field


class ExampleOut(BaseModel):
    id: str
    material_id: str
    page: int
    status: str  # reading | unconfirmed | confirmed | unreadable | failed
    status_text: str
    reading: dict | None = None
    check: dict | None = None  # null until the teacher has confirmed


class ConfirmIn(BaseModel):
    """`{}` means "yes, this is what I wrote". A field that is sent replaces that part."""

    model_config = ConfigDict(extra="forbid")

    question: str | None = Field(default=None, max_length=2000)
    steps: list[str] | None = Field(default=None, max_length=30)
    final_answer: str | None = Field(default=None, max_length=500)
