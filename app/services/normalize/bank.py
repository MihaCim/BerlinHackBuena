from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from app.services.normalize.common import (
    NormalizedDocument,
    canonical_json,
    month_from_value,
    normalized_path,
    parsed_timestamp,
    safe_document_id,
    sha256_text,
    table_escape,
    write_normalized_markdown,
)

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "id": ("id", "Kundenreferenz (End-to-End)"),
    "datum": ("datum", "Buchungstag"),
    "typ": ("typ", "Buchungstext"),
    "betrag": ("betrag", "Betrag"),
    "gegen_name": ("gegen_name", "Beguenstigter/Zahlungspflichtiger"),
    "verwendungszweck": ("verwendungszweck", "Verwendungszweck"),
    "referenz_id": ("referenz_id", "Mandatsreferenz"),
}


def normalize_bank_row(
    row: Mapping[str, object],
    normalize_dir: Path,
    *,
    source: str = "bank_index.csv",
) -> NormalizedDocument:
    canonical = {str(key): _string_value(value) for key, value in row.items()}
    tx_id = _required_alias(canonical, "id")
    datum = _required_alias(canonical, "datum")
    month = month_from_value(datum) or "unknown"
    sha = sha256_text(canonical_json(canonical))
    output_path = normalized_path(normalize_dir, "bank", month, safe_document_id(tx_id))
    body = _render_bank_markdown(tx_id, canonical)
    metadata = {
        "source": source,
        "sha256": sha,
        "parser": "csv-row",
        "parsed_at": parsed_timestamp(),
        "mime": "text/csv",
        "lang": "unknown",
    }
    return write_normalized_markdown(output_path=output_path, body=body, metadata=metadata)


def _render_bank_markdown(tx_id: str, row: Mapping[str, str]) -> str:
    ordered_keys = _ordered_keys(row)
    rows = "\n".join(f"| {table_escape(key)} | {table_escape(row[key])} |" for key in ordered_keys)
    return f"# Bank Transaction {tx_id}\n\n| Field | Value |\n|---|---|\n{rows}\n"


def _ordered_keys(row: Mapping[str, str]) -> list[str]:
    preferred = [
        "id",
        "datum",
        "typ",
        "betrag",
        "kategorie",
        "gegen_name",
        "verwendungszweck",
        "referenz_id",
        "error_types",
    ]
    keys = [key for key in preferred if key in row]
    keys.extend(key for key in row if key not in keys)
    return keys


def _required_alias(row: Mapping[str, str], field: str) -> str:
    for alias in _FIELD_ALIASES[field]:
        value = row.get(alias)
        if value:
            return value
    raise ValueError(f"bank row missing required field: {field}")


def _string_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)
