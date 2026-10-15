"""Uploaded material. See the Materials section of docs/api-contract.md."""

from pydantic import BaseModel


class MaterialOut(BaseModel):
    id: str
    filename: str | None  # the first PDF's name; null for a material without one
    page_count: int


class MaterialFileOut(BaseModel):
    id: str
    material_id: str
    kind: str  # pdf | image
    filename: str
    size_bytes: int
    first_page: int  # the item's pages are first_page .. first_page + page_count - 1 (send these to /slides)
    page_count: int
    status: str  # ready | reading | unreadable | failed
    status_text: str  # ready-to-display Bahasa Indonesia; empty when there is nothing to say


class Usage(BaseModel):
    files: int  # items and worked-example photos together
    bytes: int
    pdf_pages: int


class Limits(BaseModel):
    files: int
    bytes: int
    pdf_bytes: int
    image_bytes: int
    pdf_pages: int


class MaterialFilesOut(BaseModel):
    files: list[MaterialFileOut]
    used: Usage
    limits: Limits
