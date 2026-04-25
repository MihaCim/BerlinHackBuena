from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import anyio
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.patcher.atomic import atomic_write_text
from app.services.patcher.git import commit_all, head_sha
from app.services.patcher.ops import HUMAN_NOTES_HEADING, PatchOperationError

MAX_BYTES = 32_768


class HumanNotesError(ValueError):
    """Raised when human-notes content fails validation or the file lacks a boundary."""


@dataclass(frozen=True)
class HumanNotesWriteResult:
    rel_path: str
    bytes_written: int
    commit_sha: str | None


def split_at_boundary(content: str) -> tuple[str, str]:
    if content.startswith(HUMAN_NOTES_HEADING):
        return "", content
    marker = f"\n{HUMAN_NOTES_HEADING}"
    idx = content.find(marker)
    if idx == -1:
        raise PatchOperationError("missing # Human Notes boundary")
    return content[: idx + 1], content[idx + 1 :]


def replace_human_notes(content: str, body: str) -> str:
    above, _ = split_at_boundary(content)
    body_normalized = _normalize_body(body)
    if body_normalized:
        return f"{above}{HUMAN_NOTES_HEADING}\n\n{body_normalized}"
    return f"{above}{HUMAN_NOTES_HEADING}\n"


def _normalize_body(body: str) -> str:
    stripped = body.replace("\r\n", "\n").strip()
    if not stripped:
        return ""
    return stripped + "\n"


def validate_body(body: str) -> None:
    encoded = body.encode("utf-8")
    if len(encoded) > MAX_BYTES:
        raise HumanNotesError(f"human notes exceed {MAX_BYTES} bytes")
    if HUMAN_NOTES_HEADING in body:
        raise HumanNotesError("human notes body must not contain another '# Human Notes' heading")


class HumanNotesService:
    def __init__(self, *, wiki_dir: Path) -> None:
        self._wiki_dir = wiki_dir

    def _resolve_safe(self, rel_path: str) -> Path:
        if not rel_path or rel_path.startswith("/") or ".." in Path(rel_path).parts:
            raise HumanNotesError("invalid path")
        if not rel_path.endswith(".md"):
            raise HumanNotesError("path must reference a markdown file")
        full = (self._wiki_dir / rel_path).resolve()
        root = self._wiki_dir.resolve()
        if root not in full.parents:
            raise HumanNotesError("path escapes wiki_dir")
        return full

    async def read(self, rel_path: str) -> str | None:
        full = self._resolve_safe(rel_path)
        if not await anyio.Path(full).is_file():
            return None
        content = await anyio.Path(full).read_text(encoding="utf-8")
        try:
            _, below = split_at_boundary(content)
        except PatchOperationError:
            return None
        body = below[len(HUMAN_NOTES_HEADING) :].lstrip("\n").rstrip()
        return body

    async def write(self, rel_path: str, *, body: str, pm_user: str) -> HumanNotesWriteResult:
        validate_body(body)
        full = self._resolve_safe(rel_path)
        if not await anyio.Path(full).is_file():
            raise HumanNotesError("file not found")
        existing = await anyio.Path(full).read_text(encoding="utf-8")
        try:
            updated = replace_human_notes(existing, body)
        except PatchOperationError as exc:
            raise HumanNotesError(str(exc)) from exc
        if updated == existing:
            return HumanNotesWriteResult(
                rel_path=rel_path,
                bytes_written=0,
                commit_sha=head_sha(self._wiki_dir),
            )
        atomic_write_text(full, updated)
        diff = commit_all(
            self._wiki_dir,
            message=f"human-notes({rel_path}): {pm_user}",
        )
        return HumanNotesWriteResult(
            rel_path=rel_path,
            bytes_written=len(updated.encode("utf-8")),
            commit_sha=diff,
        )


def get_human_notes_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HumanNotesService:
    return HumanNotesService(wiki_dir=settings.wiki_dir)
