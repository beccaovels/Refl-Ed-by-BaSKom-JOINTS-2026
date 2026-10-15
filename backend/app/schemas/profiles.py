"""Subject profiles for Setup. See the Profiles section of docs/api-contract.md."""

from pydantic import BaseModel


class ChapterOut(BaseModel):
    name: str
    subchapters: list[str]


class ProfileOut(BaseModel):
    id: str
    subject: str
    grade: int
    phase: str
    label: str
    chapters: list[ChapterOut]
