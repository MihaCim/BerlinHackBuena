from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class IngestEvent(BaseModel):
    event_id: str
    event_type: str
    property_id: str = "LIE-001"
    source_path: Path | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    event_id: str
    status: str
    applied_ops: int = 0
    deferred_ops: int = 0
    commit_sha: str | None = None
    idempotent: bool = False
