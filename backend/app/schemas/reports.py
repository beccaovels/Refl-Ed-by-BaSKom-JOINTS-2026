"""Request and response shapes for the report endpoints. Field names follow docs/api-contract.md.

The Report itself is returned as the stored JSON, unchanged apart from flagged items,
so it has no class here; the scoring service owns its shape.
"""

from typing import Literal

from pydantic import BaseModel


class ReportPending(BaseModel):
    report_status: Literal["pending"] = "pending"


class FlagIn(BaseModel):
    item_id: str
