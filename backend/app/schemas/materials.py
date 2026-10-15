"""Uploaded material. See the Materials section of docs/api-contract.md."""

from pydantic import BaseModel


class MaterialOut(BaseModel):
    id: str
    filename: str | None  # null for a material that holds only photos
    page_count: int
