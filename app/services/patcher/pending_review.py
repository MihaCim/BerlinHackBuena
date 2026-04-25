from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from app.services.patcher.atomic import atomic_write_text

DEFAULT_TEMPLATE = (
    "---\n"
    "name: pending-review\n"
    "description: Open conflicts awaiting PM resolution.\n"
    "---\n\n"
    "## Open Conflicts\n\n"
    "<!-- agent-managed: one ### entry per conflict -->\n\n"
    "# Human Notes\n"
)

_BOUNDARY = "\n# Human Notes"


def append_entries(path: Path, entries: Iterable[str]) -> None:
    blocks = [block for block in entries if block]
    if not blocks:
        return
    text = path.read_text(encoding="utf-8") if path.exists() else DEFAULT_TEMPLATE
    boundary = text.find(_BOUNDARY)
    if boundary == -1:
        head = text.rstrip()
        suffix = "\n# Human Notes\n"
    else:
        head = text[:boundary].rstrip()
        suffix = text[boundary:]
    body = head + "\n" + "\n".join(blocks) + suffix
    atomic_write_text(path, body)
