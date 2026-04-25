from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .utils import write_json


def persist_outputs(output_dir: Path, data: dict[str, Any], patch_log: dict[str, Any] | None = None) -> None:
    property_dir = output_dir / "properties" / "LIE-001"
    property_dir.mkdir(parents=True, exist_ok=True)
    write_json(property_dir / "context.meta.json", build_meta(data, patch_log))
    write_provenance(property_dir / "provenance.sqlite", data)


def build_meta(data: dict[str, Any], patch_log: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "property_id": data["master"]["liegenschaft"].get("id"),
        "watermark": data.get("watermark"),
        "metrics": data.get("metrics"),
        "patch_log": patch_log or {},
        "langgraph": data.get("langgraph", {}),
    }


def write_provenance(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sources (source_id TEXT PRIMARY KEY, source_type TEXT, source_path TEXT, title TEXT)"
        )
        conn.execute("CREATE TABLE IF NOT EXISTS metrics (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("DELETE FROM sources")
        conn.execute("DELETE FROM metrics")
        for row in data.get("bank_rows", []):
            conn.execute(
                "INSERT OR REPLACE INTO sources VALUES (?, ?, ?, ?)",
                (row.get("source_id"), "bank", row.get("source_path"), row.get("purpose")),
            )
        for row in data.get("invoices", []):
            conn.execute(
                "INSERT OR REPLACE INTO sources VALUES (?, ?, ?, ?)",
                (row.get("source_id"), "invoice", row.get("source_path"), row.get("filename")),
            )
        for row in data.get("emails", []):
            conn.execute(
                "INSERT OR REPLACE INTO sources VALUES (?, ?, ?, ?)",
                (row.get("source_id"), "email", row.get("source_path"), row.get("subject")),
            )
        for row in data.get("letters", []):
            conn.execute(
                "INSERT OR REPLACE INTO sources VALUES (?, ?, ?, ?)",
                (row.get("source_id"), "letter", row.get("source_path"), row.get("filename")),
            )
        for key, value in data.get("metrics", {}).items():
            conn.execute("INSERT OR REPLACE INTO metrics VALUES (?, ?)", (key, str(value)))
        conn.commit()
    finally:
        conn.close()
