"""Subject profiles for Setup. See the Profiles section of docs/api-contract.md."""

from pydantic import BaseModel


class ProfileOut(BaseModel):
    id: str
    subject: str
    grade: int
    phase: str
    label: str
