from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import anyio

from app.core.config import Settings
from app.schemas.webhook import IngestEvent
from app.services.normalize.common import parsed_timestamp, safe_document_id, sha256_text
from app.services.patcher.atomic import atomic_write_text


@dataclass(frozen=True)
class HandlerResult:
    normalized_path: Path
    normalized_text: str
    source_id: str
    event_type: str
    extras: dict[str, Any] = field(default_factory=dict)


class EventHandler(Protocol):
    async def handle(self, event: IngestEvent, settings: Settings) -> HandlerResult:
        """Normalize one event into markdown for the supervisor."""


class PayloadMarkdownHandler:
    kind = "document"

    async def handle(self, event: IngestEvent, settings: Settings) -> HandlerResult:
        text = await _event_text(event)
        source_id = safe_document_id(event.event_id)
        month = str(event.payload.get("month") or "unknown")
        output_path = settings.normalize_dir / self.kind / month / f"{source_id}.md"
        metadata = {
            "source": str(event.source_path or event.event_id),
            "sha256": sha256_text(text),
            "parser": f"payload-{self.kind}",
            "parsed_at": parsed_timestamp(),
            "mime": "text/plain",
            "lang": "unknown",
        }
        body = (
            f"# {self.kind.title()} {source_id}\n\n"
            "| Field | Value |\n"
            "|---|---|\n"
            f"| event_id | {event.event_id} |\n"
            f"| event_type | {event.event_type} |\n\n"
            "## Body\n\n"
            f"{text.strip()}\n"
        )
        content = _frontmatter(metadata) + body
        atomic_write_text(output_path, content)
        return HandlerResult(
            normalized_path=output_path,
            normalized_text=content,
            source_id=source_id,
            event_type=event.event_type,
        )


async def _event_text(event: IngestEvent) -> str:
    if "normalized_text" in event.payload:
        return str(event.payload["normalized_text"])
    if "text" in event.payload:
        return str(event.payload["text"])
    if event.source_path is not None and event.source_path.is_file():
        return await anyio.Path(event.source_path).read_text(encoding="utf-8")
    return json.dumps(event.payload, ensure_ascii=False, sort_keys=True, default=str)


def _frontmatter(metadata: dict[str, str]) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)
