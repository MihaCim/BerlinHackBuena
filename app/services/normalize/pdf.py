from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pypdf import PdfReader

from app.services.normalize.common import (
    NormalizedDocument,
    detect_lang,
    document_id_from_name,
    month_from_source,
    normalized_path,
    parsed_timestamp,
    sha256_bytes,
    table_escape,
    write_normalized_markdown,
)

_MONEY_RE = re.compile(r"\d+(?:[.\s]\d{3})*(?:,\d{2}|\.\d{2})\s*EUR")
_TOTAL_LABELS = ("Summe netto", "MwSt", "Gesamtbetrag")


def normalize_pdf(
    source_path: Path,
    normalize_dir: Path,
    document_type: Literal["invoice", "letter"],
) -> NormalizedDocument:
    raw = source_path.read_bytes()
    sha = sha256_bytes(raw)
    text = _extract_text(source_path)
    document_id = document_id_from_name(
        source_path,
        "INV" if document_type == "invoice" else "LTR",
    )
    output_path = normalized_path(
        normalize_dir,
        document_type,
        month_from_source(source_path),
        document_id,
    )
    metadata = {
        "source": str(source_path),
        "sha256": sha,
        "parser": "pypdf",
        "parsed_at": parsed_timestamp(),
        "mime": "application/pdf",
        "lang": detect_lang(text),
    }
    if document_type == "invoice":
        markdown = _render_invoice(document_id, text)
    else:
        markdown = _render_letter(document_id, text)
    return write_normalized_markdown(output_path=output_path, body=markdown, metadata=metadata)


def normalize_invoice_pdf(source_path: Path, normalize_dir: Path) -> NormalizedDocument:
    return normalize_pdf(source_path, normalize_dir, "invoice")


def normalize_letter_pdf(source_path: Path, normalize_dir: Path) -> NormalizedDocument:
    return normalize_pdf(source_path, normalize_dir, "letter")


def _extract_text(source_path: Path) -> str:
    reader = PdfReader(str(source_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _render_invoice(document_id: str, text: str) -> str:
    lines = _non_empty_lines(text)
    line_items = _line_items(lines)
    totals = _totals(lines)
    return (
        f"# Invoice {document_id}\n\n"
        "## Line Items\n\n"
        "| Position | Menge | Einzelpreis | Betrag |\n"
        "|---|---|---|---|\n"
        f"{_render_rows(line_items, 4)}\n\n"
        "## Totals\n\n"
        "| Type | Amount |\n"
        "|---|---|\n"
        f"{_render_rows(totals, 2)}\n\n"
        "## Text\n\n"
        f"{text.strip()}\n"
    )


def _render_letter(document_id: str, text: str) -> str:
    return f"# Letter {document_id}\n\n## Text\n\n{text.strip()}\n"


def _non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _line_items(lines: list[str]) -> list[tuple[str, ...]]:
    try:
        position_idx = lines.index("Position")
    except ValueError:
        return []

    header_end = position_idx
    for idx in range(position_idx + 1, min(position_idx + 8, len(lines))):
        if lines[idx] == "Betrag":
            header_end = idx
            break

    items: list[tuple[str, ...]] = []
    idx = header_end + 1
    while idx + 3 < len(lines):
        if _is_total_or_footer(lines[idx]):
            break
        candidate = (lines[idx], lines[idx + 1], lines[idx + 2], lines[idx + 3])
        if _MONEY_RE.fullmatch(candidate[2]) and _MONEY_RE.fullmatch(candidate[3]):
            items.append(candidate)
            idx += 4
            continue
        idx += 1
    return items


def _totals(lines: list[str]) -> list[tuple[str, ...]]:
    totals: list[tuple[str, ...]] = []
    for idx, line in enumerate(lines):
        label = _total_label(line)
        if label is None:
            continue
        amount = _amount_in_line(line)
        if amount is None and idx + 1 < len(lines):
            amount = _amount_in_line(lines[idx + 1])
        if amount is not None:
            totals.append((line, amount))
    return totals


def _is_total_or_footer(line: str) -> bool:
    return _total_label(line) is not None or line.startswith(("Bankverbindung", "Steuernr."))


def _total_label(line: str) -> str | None:
    for label in _TOTAL_LABELS:
        if line.startswith(label):
            return label
    return None


def _amount_in_line(line: str) -> str | None:
    match = _MONEY_RE.search(line)
    if match is None:
        return None
    return match.group(0)


def _render_rows(rows: Sequence[Sequence[str]], width: int) -> str:
    if not rows:
        return "| " + " | ".join([""] * width) + " |"
    return "\n".join("| " + " | ".join(table_escape(cell) for cell in row) + " |" for row in rows)
