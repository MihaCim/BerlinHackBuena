from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .utils import read_text


SCHEMA_ROOT = Path(__file__).resolve().parents[1] / "schemas"


@lru_cache(maxsize=16)
def load_schema(filename: str) -> str:
    return read_text(SCHEMA_ROOT / filename)


def table_rows(schema_text: str, heading: str) -> list[dict[str, str]]:
    lines = schema_text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip().lower() == f"## {heading}".lower():
            start = index + 1
            break
    if start is None:
        return []
    table: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("## ") and table:
            break
        if stripped.startswith("|"):
            table.append(stripped)
        elif table:
            break
    if len(table) < 3:
        return []
    headers = [cell.strip() for cell in table[0].strip("|").split("|")]
    rows = []
    for raw in table[2:]:
        cells = [cell.strip().strip("`") for cell in raw.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def regex_blocks(schema_text: str, heading: str) -> list[str]:
    section = section_text(schema_text, heading)
    return re.findall(r"```regex\n(.*?)\n```", section, flags=re.S)


def section_text(schema_text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)"
    match = re.search(pattern, schema_text, flags=re.S | re.M)
    return match.group("body") if match else ""


@lru_cache(maxsize=1)
def parser_contract() -> dict[str, Any]:
    schema = load_schema("PARSER_SCHEMA.md")
    families = {row["family"]: row for row in table_rows(schema, "Source Families")}
    classification = [
        {
            "category": row["category"],
            "keywords": split_csv(row["keywords"]),
        }
        for row in table_rows(schema, "Email Classification Rules")
    ]
    score_rules = [
        {
            "label": row["label"],
            "keywords": split_csv(row["keywords"]),
            "boost": float(row["boost"]),
        }
        for row in table_rows(schema, "Email Score Rules")
    ]
    entity_patterns = re.findall(r"```regex\n(.*?)\n```", section_text(schema, "Entity Pattern"), flags=re.S)
    return {
        "schema_file": "PARSER_SCHEMA.md",
        "families": families,
        "classification": classification,
        "score_rules": score_rules,
        "entity_pattern": entity_patterns[0] if entity_patterns else r"\b(?:EH|EIG|MIE|DL|INV|LTR)-\d{3,5}\b",
    }


@lru_cache(maxsize=1)
def render_contract() -> dict[str, Any]:
    schema = load_schema("RENDER_SCHEMA.md")
    sections = sorted(table_rows(schema, "Render Sections"), key=lambda row: int(row["order"]))
    return {"schema_file": "RENDER_SCHEMA.md", "sections": sections}


@lru_cache(maxsize=1)
def patch_contract() -> dict[str, Any]:
    schema = load_schema("PATCH_SCHEMA.md")
    sections = sorted(table_rows(schema, "Patchable Sections"), key=lambda row: int(row["order"]))
    return {
        "schema_file": "PATCH_SCHEMA.md",
        "patchable_sections": [row["anchor"] for row in sections],
        "locked_patterns": regex_blocks(schema, "Locked Block Patterns"),
        "human_notes_pattern": (regex_blocks(schema, "Human Notes Pattern") or [r"<!-- HUMAN_NOTES_START -->.*?<!-- HUMAN_NOTES_END -->"])[0],
    }


def split_csv(value: str) -> list[str]:
    return [part.strip().lower() for part in value.split(",") if part.strip()]
