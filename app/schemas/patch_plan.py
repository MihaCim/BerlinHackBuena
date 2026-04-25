from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PatchOp(BaseModel):
    model_config = ConfigDict(extra="allow")

    op: str
    file: str | None = None
    section: str | None = None
    key: str | None = None
    text: str | None = None
    row: str | list[Any] | None = None
    header: list[Any] | None = None
    updates: dict[str, Any] | None = None
    counters: dict[str, int] | None = None
    max_rows: int | None = None
    ref_counts: dict[str, int] | None = None


class ReviewItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    review_type: str
    title: str
    description: str = ""
    source_ids: list[str] = Field(default_factory=list)
    severity: str = "medium"


class PatchPlan(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    property_id: str
    summary: str = "patch"
    event_type: str = "unknown"
    source_ids: list[str] = Field(default_factory=list)
    ops: list[PatchOp] = Field(default_factory=list)
    review_items: list[ReviewItem] = Field(default_factory=list)
    complexity_score: int = 0
    skill_candidate: bool = False
