from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader


IGNORED_NAMES = {"DATA_SUMMARY.md", ".DS_Store"}


@dataclass(frozen=True)
class Batch:
    batch_id: str
    source_path: Path
    content_date: str | None
    files: tuple[Path, ...]


class IngestionService:
    def __init__(self, data_dir: Path, db_path: Path):
        self.data_dir = data_dir
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def ingest_base(self, reprocess: bool = False) -> dict[str, object]:
        batches = self._base_batches()
        return self._ingest_batches(batches, reprocess=reprocess)

    def ingest_incremental_day(self, day: str, reprocess: bool = False) -> dict[str, object]:
        day_name = day if day.startswith("day-") else f"day-{int(day):02d}"
        day_dir = self.data_dir / "incremental" / day_name
        if not day_dir.exists():
            raise FileNotFoundError(f"Incremental day not found: {day_dir}")
        return self._ingest_batches((self._incremental_batch(day_dir),), reprocess=reprocess)

    def ingest_all_incremental(self, reprocess: bool = False) -> dict[str, object]:
        incremental_dir = self.data_dir / "incremental"
        if not incremental_dir.exists():
            return {"batches_total": 0, "batches_ingested": 0, "sources_ingested": 0, "skipped_batches": []}

        batches = tuple(
            self._incremental_batch(path)
            for path in sorted(incremental_dir.iterdir())
            if path.is_dir() and path.name.startswith("day-")
        )
        return self._ingest_batches(batches, reprocess=reprocess)

    def status(self) -> dict[str, object]:
        with self._connect() as con:
            batch_counts = con.execute(
                "select status, count(*) from ingestion_batches group by status"
            ).fetchall()
            source_counts = con.execute(
                "select source_type, count(*) from ingestion_sources group by source_type order by source_type"
            ).fetchall()
            recent_batches = con.execute(
                """
                select batch_id, status, source_count, processed_at
                from ingestion_batches
                order by processed_at desc
                limit 10
                """
            ).fetchall()

        return {
            "batch_counts": {row[0]: row[1] for row in batch_counts},
            "source_counts": {row[0]: row[1] for row in source_counts},
            "recent_batches": [dict(row) for row in recent_batches],
            "db_path": str(self.db_path),
        }

    def _ingest_batches(self, batches: Iterable[Batch], reprocess: bool) -> dict[str, object]:
        batches = tuple(batches)
        ingested = 0
        sources_ingested = 0
        skipped: list[str] = []
        errors: list[dict[str, str]] = []

        with self._connect() as con:
            for batch in batches:
                if not reprocess and self._batch_done(con, batch.batch_id):
                    skipped.append(batch.batch_id)
                    continue

                processed_at = now_iso()
                con.execute(
                    """
                    insert into ingestion_batches(batch_id, content_date, source_path, status, processed_at, source_count)
                    values (?, ?, ?, ?, ?, ?)
                    on conflict(batch_id) do update set
                        content_date=excluded.content_date,
                        source_path=excluded.source_path,
                        status=excluded.status,
                        processed_at=excluded.processed_at,
                        source_count=excluded.source_count
                    """,
                    (
                        batch.batch_id,
                        batch.content_date,
                        self._relative(batch.source_path),
                        "processing",
                        processed_at,
                        len(batch.files),
                    ),
                )

                batch_errors = []
                for source_path in batch.files:
                    try:
                        source = self._normalize_source(source_path)
                        self._upsert_source(con, batch.batch_id, source, processed_at)
                        sources_ingested += 1
                    except Exception as exc:  # Keep batch progress visible for imperfect source files.
                        batch_errors.append({"source_path": self._relative(source_path), "error": str(exc)})

                con.execute(
                    """
                    update ingestion_batches
                    set status = ?, processed_at = ?
                    where batch_id = ?
                    """,
                    ("failed" if batch_errors else "completed", now_iso(), batch.batch_id),
                )
                errors.extend(batch_errors)
                ingested += 1

        return {
            "batches_total": len(batches),
            "batches_ingested": ingested,
            "sources_ingested": sources_ingested,
            "skipped_batches": skipped,
            "errors": errors,
        }

    def _base_batches(self) -> tuple[Batch, ...]:
        batches: list[Batch] = []

        stammdaten_dir = self.data_dir / "stammdaten"
        if stammdaten_dir.exists():
            batches.append(Batch("base-stammdaten", stammdaten_dir, None, self._files_under(stammdaten_dir)))

        bank_dir = self.data_dir / "bank"
        if bank_dir.exists():
            batches.append(Batch("base-bank-2024-2025", bank_dir, None, self._files_under(bank_dir)))

        for section in ("rechnungen", "briefe", "emails"):
            section_dir = self.data_dir / section
            if not section_dir.exists():
                continue
            for month_dir in sorted(path for path in section_dir.iterdir() if path.is_dir()):
                batches.append(
                    Batch(
                        f"base-{section}-{month_dir.name}",
                        month_dir,
                        month_dir.name,
                        self._files_under(month_dir),
                    )
                )

        return tuple(batches)

    def _incremental_batch(self, day_dir: Path) -> Batch:
        manifest_path = day_dir / "incremental_manifest.json"
        content_date = None
        if manifest_path.exists():
            with manifest_path.open("r", encoding="utf-8") as f:
                content_date = json.load(f).get("content_date")
        return Batch(f"incremental-{day_dir.name}", day_dir, content_date, self._files_under(day_dir))

    def _files_under(self, directory: Path) -> tuple[Path, ...]:
        return tuple(
            sorted(
                path
                for path in directory.rglob("*")
                if path.is_file() and path.name not in IGNORED_NAMES
            )
        )

    def _normalize_source(self, path: Path) -> dict[str, Any]:
        suffix = path.suffix.lower()
        payload: dict[str, Any] = {
            "source_path": self._relative(path),
            "source_id": self._source_id(path),
            "source_type": self._source_type(path),
            "content_hash": file_hash(path),
            "size_bytes": path.stat().st_size,
        }

        if suffix == ".json":
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            payload["summary"] = summarize_json(data)
            payload["content"] = data
        elif suffix == ".csv":
            rows, fieldnames = read_csv_summary(path)
            payload["summary"] = {"rows": rows, "fieldnames": fieldnames}
        elif suffix == ".xml":
            payload["summary"] = read_xml_summary(path)
        elif suffix == ".eml":
            payload["content"] = read_email(path)
            payload["summary"] = {key: payload["content"].get(key) for key in ("subject", "from", "to", "date")}
        elif suffix == ".pdf":
            text, pages = extract_pdf_text(path)
            payload["content"] = {"text": text}
            payload["summary"] = {"pages": pages, "text_chars": len(text)}
        else:
            payload["summary"] = {"note": "stored metadata only"}

        return payload

    def _upsert_source(self, con: sqlite3.Connection, batch_id: str, source: dict[str, Any], processed_at: str) -> None:
        con.execute(
            """
            insert into ingestion_sources(
                source_id, batch_id, source_type, source_path, content_hash, status,
                target_context_ids, processed_at, payload_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(source_id) do update set
                batch_id=excluded.batch_id,
                source_type=excluded.source_type,
                source_path=excluded.source_path,
                content_hash=excluded.content_hash,
                status=excluded.status,
                target_context_ids=excluded.target_context_ids,
                processed_at=excluded.processed_at,
                payload_json=excluded.payload_json
            """,
            (
                source["source_id"],
                batch_id,
                source["source_type"],
                source["source_path"],
                source["content_hash"],
                "completed",
                "[]",
                processed_at,
                json.dumps(source, ensure_ascii=False),
            ),
        )

    def _source_id(self, path: Path) -> str:
        stable_id = re.search(r"(EMAIL-\d+|INV-(?:DUP-|FAKE-)?\d+|LTR-\d+|TX-\d+)", path.stem)
        if stable_id:
            return stable_id.group(1)
        return self._relative(path)

    def _source_type(self, path: Path) -> str:
        rel_parts = path.relative_to(self.data_dir).parts
        if "emails" in rel_parts or path.suffix.lower() == ".eml":
            return "email"
        if "rechnungen" in rel_parts:
            return "invoice"
        if "briefe" in rel_parts:
            return "letter"
        if "bank" in rel_parts:
            return "bank"
        if "stammdaten" in rel_parts:
            return "master_data"
        if path.name == "incremental_manifest.json":
            return "manifest"
        return path.suffix.lower().lstrip(".") or "unknown"

    def _batch_done(self, con: sqlite3.Connection, batch_id: str) -> bool:
        row = con.execute(
            "select status from ingestion_batches where batch_id = ?",
            (batch_id,),
        ).fetchone()
        return bool(row and row[0] == "completed")

    def _relative(self, path: Path) -> str:
        return str(path.relative_to(self.data_dir.parent))

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                create table if not exists ingestion_batches (
                    batch_id text primary key,
                    content_date text,
                    source_path text not null,
                    status text not null,
                    processed_at text not null,
                    source_count integer not null
                )
                """
            )
            con.execute(
                """
                create table if not exists ingestion_sources (
                    source_id text primary key,
                    batch_id text not null,
                    source_type text not null,
                    source_path text not null,
                    content_hash text not null,
                    status text not null,
                    target_context_ids text not null,
                    processed_at text not null,
                    payload_json text not null,
                    foreign key(batch_id) references ingestion_batches(batch_id)
                )
                """
            )


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize_json(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return {
            "type": "object",
            "keys": sorted(data.keys()),
            "counts": {key: len(value) for key, value in data.items() if isinstance(value, list)},
        }
    if isinstance(data, list):
        return {"type": "array", "rows": len(data)}
    return {"type": type(data).__name__}


def read_csv_summary(path: Path) -> tuple[int, list[str]]:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = sum(1 for _ in reader)
        return rows, list(reader.fieldnames or [])


def read_xml_summary(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    return {"root_tag": strip_namespace(root.tag), "children": len(list(root))}


def read_email(path: Path) -> dict[str, str | None]:
    with path.open("rb") as f:
        message = BytesParser(policy=policy.default).parse(f)

    body = message.get_body(preferencelist=("plain",))
    body_text = body.get_content() if body else ""
    return {
        "from": message.get("From"),
        "to": message.get("To"),
        "subject": message.get("Subject"),
        "date": message.get("Date"),
        "message_id": message.get("Message-ID"),
        "in_reply_to": message.get("In-Reply-To"),
        "references": message.get("References"),
        "body_text": body_text,
    }


def extract_pdf_text(path: Path) -> tuple[str, int]:
    reader = PdfReader(str(path))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return "\n\n".join(part for part in parts if part), len(reader.pages)


def strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
