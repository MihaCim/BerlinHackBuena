from __future__ import annotations

from dataclasses import dataclass
from email.utils import parseaddr

from app.core.config import REPO_ROOT, Settings
from app.services.llm.client import LLMClient
from app.services.llm.json import parse_json_object

_MIN_TABLE_CELLS = 2


@dataclass(frozen=True)
class Classification:
    signal: bool
    category: str
    priority: str
    confidence: float


def classify_prompt(*, normalized_text: str) -> str:
    excerpt = normalized_text[:500]
    sender = _markdown_field(normalized_text, "From")
    subject = _markdown_field(normalized_text, "Subject")
    if sender:
        _, email = parseaddr(sender)
        sender = email or sender
    return (
        "Classify this normalized property-management source. Return only JSON with "
        "keys: signal (boolean), category (string), priority (low|medium|high), "
        "confidence (0..1).\n\n"
        f"Sender: {sender}\n"
        f"Subject: {subject}\n"
        f"Excerpt:\n{excerpt}"
    )


async def classify_document(
    *,
    normalized_text: str,
    llm: LLMClient,
    settings: Settings,
) -> Classification:
    response = await llm.complete(
        model=settings.fast_model,
        system_prompt=_classification_system_prompt(),
        user_prompt=classify_prompt(normalized_text=normalized_text),
    )
    payload = parse_json_object(response)
    return Classification(
        signal=bool(payload.get("signal", False)),
        category=str(payload.get("category", "noise")),
        priority=str(payload.get("priority", "low")),
        confidence=float(payload.get("confidence", 0.0)),
    )


def _classification_system_prompt() -> str:
    path = REPO_ROOT / "schema" / "CLAUDE.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "You classify property-management input into signal/noise."


def _markdown_field(text: str, field: str) -> str:
    needle = f"| {field} |"
    for line in text.splitlines():
        if not line.startswith(needle):
            continue
        cells = [cell.strip().replace(r"\|", "|") for cell in line.strip().strip("|").split("|")]
        if len(cells) >= _MIN_TABLE_CELLS:
            return cells[1]
    return ""
