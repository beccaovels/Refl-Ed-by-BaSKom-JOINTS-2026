"""Uploaded material. See the Materials section of docs/api-contract.md."""

from pydantic import BaseModel


class MaterialOut(BaseModel):
    id: str
    filename: str
    page_count: int
