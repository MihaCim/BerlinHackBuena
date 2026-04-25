from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from app.services.patcher.atomic import atomic_write_text

_FRONTMATTER_SHA_RE = re.compile(r'^sha256:\s*"?(?P<sha>[0-9a-f]{64})"?\s*$', re.MULTILINE)
_FILENAME_DATE_RE = re.compile(r"^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})")
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_.-]+")

_GERMAN_MARKERS = (
    " sehr geehrte",
    " rechnung",
    " betrag",
    " zahlung",
    " bitte ",
    " mit freundlichen gruessen",
    " mahnung",
)
_ENGLISH_MARKERS = (
    " dear ",
    " invoice",
    " payment",
    " please ",
    " best regards",
    " quote",
)


@dataclass(frozen=True)
class NormalizedDocument:
    output_path: Path
    sha256: str
    parser: str
    idempotent: bool
    metadata: dict[str, str]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def parsed_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def detect_lang(text: str) -> str:
    lowered = f" {text.lower()} "
    german_hits = sum(1 for marker in _GERMAN_MARKERS if marker in lowered)
    english_hits = sum(1 for marker in _ENGLISH_MARKERS if marker in lowered)
    if german_hits > english_hits:
        return "de"
    if english_hits > german_hits:
        return "en"
    return "unknown"


def document_id_from_name(source_path: Path, *prefixes: str) -> str:
    if prefixes:
        prefix_group = "|".join(re.escape(prefix) for prefix in prefixes)
        match = re.search(rf"(?P<id>(?:{prefix_group})(?:-[A-Z]+)?-\d+)", source_path.stem, re.I)
        if match is not None:
            return match.group("id").upper()
    return safe_document_id(source_path.stem)


def safe_document_id(value: str) -> str:
    cleaned = _SAFE_ID_RE.sub("_", value.strip())
    return cleaned.strip("._") or "document"


def month_from_source(source_path: Path, fallback: str | date | datetime | None = None) -> str:
    match = _FILENAME_DATE_RE.match(source_path.name)
    if match is not None:
        return f"{match.group('year')}-{match.group('month')}"
    parsed = month_from_value(fallback)
    if parsed is not None:
        return parsed
    return "unknown"


def month_from_value(value: str | date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime | date):
        return f"{value:%Y-%m}"
    iso_match = re.match(r"^(?P<year>\d{4})-(?P<month>\d{2})-\d{2}", value)
    if iso_match is not None:
        return f"{iso_match.group('year')}-{iso_match.group('month')}"
    german_match = re.match(r"^\d{2}\.(?P<month>\d{2})\.(?P<year>\d{4})$", value)
    if german_match is not None:
        return f"{german_match.group('year')}-{german_match.group('month')}"
    return None


def normalized_path(normalize_dir: Path, kind: str, month: str, document_id: str) -> Path:
    return normalize_dir / kind / month / f"{safe_document_id(document_id)}.md"


def table_escape(value: object) -> str:
    return str(value).replace("\n", "<br>").replace("|", r"\|")


def write_normalized_markdown(
    *,
    output_path: Path,
    body: str,
    metadata: dict[str, str],
) -> NormalizedDocument:
    sha = metadata["sha256"]
    parser = metadata["parser"]
    if output_path.exists() and _existing_sha(output_path) == sha:
        return NormalizedDocument(output_path, sha, parser, True, metadata)
    content = f"{_render_frontmatter(metadata)}{body.rstrip()}\n"
    atomic_write_text(output_path, content)
    return NormalizedDocument(output_path, sha, parser, False, metadata)


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def _existing_sha(path: Path) -> str | None:
    match = _FRONTMATTER_SHA_RE.search(path.read_text(encoding="utf-8"))
    if match is None:
        return None
    return match.group("sha")


def _render_frontmatter(metadata: dict[str, str]) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)
