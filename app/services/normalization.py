from __future__ import annotations

import csv
import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any

import anyio
from pypdf import PdfReader

IGNORED_NAMES = {"DATA_SUMMARY.md", ".DS_Store"}


@dataclass(frozen=True)
class NormalizationBatch:
    batch_id: str
    source_path: Path
    target_root: Path
    files: tuple[Path, ...]


class NormalizationService:
    def __init__(self, data_dir: Path, normalize_dir: Path) -> None:
        self.data_dir = data_dir
        self.normalize_dir = normalize_dir

    async def normalize_base(self, overwrite: bool = True) -> dict[str, object]:
        return await anyio.to_thread.run_sync(self._normalize_base_sync, overwrite)

    async def normalize_incremental_day(
        self, day: str, overwrite: bool = True
    ) -> dict[str, object]:
        return await anyio.to_thread.run_sync(self._normalize_incremental_day_sync, day, overwrite)

    async def normalize_all_incremental(self, overwrite: bool = True) -> dict[str, object]:
        return await anyio.to_thread.run_sync(self._normalize_all_incremental_sync, overwrite)

    async def status(self) -> dict[str, object]:
        return await anyio.to_thread.run_sync(self._status_sync)

    def _normalize_base_sync(self, overwrite: bool = True) -> dict[str, object]:
        batches = []
        for section in ("stammdaten", "bank", "rechnungen", "briefe", "emails"):
            section_dir = self.data_dir / section
            if section_dir.exists():
                batches.append(
                    NormalizationBatch(
                        batch_id=f"base-{section}",
                        source_path=section_dir,
                        target_root=self.normalize_dir / "base" / section,
                        files=self._files_under(section_dir),
                    )
                )
        return self._normalize_batches(batches, overwrite=overwrite)

    def _normalize_incremental_day_sync(
        self, day: str, overwrite: bool = True
    ) -> dict[str, object]:
        day_name = day if day.startswith("day-") else f"day-{int(day):02d}"
        day_dir = self.data_dir / "incremental" / day_name
        if not day_dir.exists():
            raise FileNotFoundError(f"Incremental day not found: {day_dir}")

        batch = NormalizationBatch(
            batch_id=f"incremental-{day_name}",
            source_path=day_dir,
            target_root=self.normalize_dir / "incremental" / day_name,
            files=self._files_under(day_dir),
        )
        return self._normalize_batches((batch,), overwrite=overwrite)

    def _normalize_all_incremental_sync(self, overwrite: bool = True) -> dict[str, object]:
        incremental_dir = self.data_dir / "incremental"
        if not incremental_dir.exists():
            return self._empty_result()

        batches = tuple(
            NormalizationBatch(
                batch_id=f"incremental-{path.name}",
                source_path=path,
                target_root=self.normalize_dir / "incremental" / path.name,
                files=self._files_under(path),
            )
            for path in sorted(incremental_dir.iterdir())
            if path.is_dir() and path.name.startswith("day-")
        )
        return self._normalize_batches(batches, overwrite=overwrite)

    def _normalize_batches(
        self, batches: Iterable[NormalizationBatch], overwrite: bool
    ) -> dict[str, object]:
        batches = tuple(batches)
        files_written = 0
        files_skipped = 0
        errors: list[dict[str, str]] = []

        for batch in batches:
            for source_path in batch.files:
                target_path = self._target_path(batch, source_path)
                if target_path.exists() and not overwrite:
                    files_skipped += 1
                    continue

                try:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(
                        normalize_source_to_markdown(self.data_dir, source_path),
                        encoding="utf-8",
                    )
                    files_written += 1
                except Exception as exc:  # Keep imperfect source files visible to the agent.
                    errors.append(
                        {
                            "source_path": relative_to_parent(self.data_dir, source_path),
                            "error": str(exc),
                        }
                    )

        return {
            "batches_total": len(batches),
            "files_written": files_written,
            "files_skipped": files_skipped,
            "errors": errors,
            "normalize_dir": str(self.normalize_dir),
        }

    def _status_sync(self) -> dict[str, object]:
        files = tuple(self.normalize_dir.rglob("*.md")) if self.normalize_dir.exists() else ()
        by_root: dict[str, int] = {}
        for path in files:
            rel = path.relative_to(self.normalize_dir)
            root = rel.parts[0] if rel.parts else "unknown"
            by_root[root] = by_root.get(root, 0) + 1

        return {
            "files_total": len(files),
            "files_by_root": by_root,
            "normalize_dir": str(self.normalize_dir),
        }

    def _files_under(self, directory: Path) -> tuple[Path, ...]:
        return tuple(
            sorted(
                path
                for path in directory.rglob("*")
                if path.is_file() and path.name not in IGNORED_NAMES
            )
        )

    def _target_path(self, batch: NormalizationBatch, source_path: Path) -> Path:
        relative_path = source_path.relative_to(batch.source_path)
        return batch.target_root / relative_path.with_suffix(".md")

    def _empty_result(self) -> dict[str, object]:
        return {
            "batches_total": 0,
            "files_written": 0,
            "files_skipped": 0,
            "errors": [],
            "normalize_dir": str(self.normalize_dir),
        }


def normalize_source_to_markdown(data_dir: Path, path: Path) -> str:
    metadata = source_metadata(data_dir, path)
    body = source_body_markdown(path)
    return f"{metadata}\n\n{body}\n"


def source_metadata(data_dir: Path, path: Path) -> str:
    metadata = {
        "source_id": source_id(path),
        "source_type": source_type(data_dir, path),
        "source_path": relative_to_parent(data_dir, path),
        "content_hash": file_hash(path),
        "size_bytes": path.stat().st_size,
        "normalized_at": datetime.now(UTC).isoformat(),
    }
    lines = ["---"]
    lines.extend(
        f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items()
    )
    lines.append("---")
    return "\n".join(lines)


def source_body_markdown(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".eml":
        return email_to_markdown(path)
    if suffix == ".pdf":
        return pdf_to_markdown(path)
    if suffix == ".csv":
        return csv_to_markdown(path)
    if suffix == ".json":
        return json_to_markdown(path)
    if suffix == ".xml":
        return text_file_to_markdown(path, language="xml")
    return text_file_to_markdown(path, language="text")


def email_to_markdown(path: Path) -> str:
    with path.open("rb") as f:
        message = BytesParser(policy=policy.default).parse(f)

    body = message.get_body(preferencelist=("plain",))
    body_text = body.get_content() if body else ""
    headers = {
        "From": message.get("From"),
        "To": message.get("To"),
        "Subject": message.get("Subject"),
        "Date": message.get("Date"),
        "Message-ID": message.get("Message-ID"),
        "In-Reply-To": message.get("In-Reply-To"),
        "References": message.get("References"),
    }

    lines = [f"# {source_id(path)}", "", "## Email Headers", ""]
    lines.extend(f"- **{key}:** {value or ''}" for key, value in headers.items())
    lines.extend(["", "## Body", "", body_text.strip()])
    return "\n".join(lines)


def pdf_to_markdown(path: Path) -> str:
    reader = PdfReader(str(path))
    parts = [(page.extract_text() or "") for page in reader.pages]
    text = "\n\n".join(part for part in parts if part).strip()
    return f"# {source_id(path)}\n\n## PDF Text\n\n{text}\n"


def csv_to_markdown(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)

    fieldnames = list(reader.fieldnames or [])
    lines = [f"# {path.stem}", "", f"Rows: {len(rows)}", ""]
    if not fieldnames:
        return "\n".join(lines)

    lines.append("| " + " | ".join(escape_table_cell(name) for name in fieldnames) + " |")
    lines.append("| " + " | ".join("---" for _ in fieldnames) + " |")
    for row in rows:
        lines.append(
            "| "
            + " | ".join(escape_table_cell(row.get(fieldname, "")) for fieldname in fieldnames)
            + " |"
        )
    return "\n".join(lines)


def json_to_markdown(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return f"# {path.stem}\n\n```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```"


def text_file_to_markdown(path: Path, language: str) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    return f"# {path.stem}\n\n```{language}\n{text}\n```"


def source_id(path: Path) -> str:
    stable_id = re.search(r"(EMAIL-\d+|INV-(?:DUP-|FAKE-)?\d+|LTR-\d+|TX-\d+)", path.stem)
    if stable_id:
        return stable_id.group(1)
    return path.stem


def source_type(data_dir: Path, path: Path) -> str:
    rel_parts = path.relative_to(data_dir).parts
    if path.name == "incremental_manifest.json":
        return "manifest"

    section_types = {
        "emails": "email",
        "rechnungen": "invoice",
        "briefe": "letter",
        "bank": "bank",
        "stammdaten": "master_data",
    }
    for section, normalized_type in section_types.items():
        if section in rel_parts:
            return normalized_type
    return path.suffix.lower().lstrip(".") or "unknown"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_to_parent(data_dir: Path, path: Path) -> str:
    return str(path.relative_to(data_dir.parent))


def escape_table_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")
