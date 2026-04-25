from __future__ import annotations

from pydantic import BaseModel, Field


class HumanNotesReadResponse(BaseModel):
    path: str
    body: str


class HumanNotesWriteRequest(BaseModel):
    body: str = Field(..., max_length=131_072)


class HumanNotesWriteResponse(BaseModel):
    path: str
    bytes_written: int
    commit_sha: str | None
