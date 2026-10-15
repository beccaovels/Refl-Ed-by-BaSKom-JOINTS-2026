"""Login. See the Users section of docs/api-contract.md."""

from pydantic import BaseModel, Field, field_validator

EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class LoginIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=254, pattern=EMAIL)

    @field_validator("name", "email", mode="before")
    @classmethod
    def strip(cls, value):
        return value.strip() if isinstance(value, str) else value


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    tier: str
