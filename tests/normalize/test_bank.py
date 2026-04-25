from __future__ import annotations

import csv
from pathlib import Path

from app.services.normalize.bank import normalize_bank_row

REPO_ROOT = Path(__file__).resolve().parents[2]
BANK_INDEX = REPO_ROOT / "data" / "bank" / "bank_index.csv"


def test_normalize_bank_row_writes_one_markdown_file_per_transaction(tmp_path: Path) -> None:
    with BANK_INDEX.open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    result = normalize_bank_row(row, tmp_path / "normalize")
    content = result.output_path.read_text(encoding="utf-8")

    assert result.output_path == tmp_path / "normalize/bank/2024-01/TX-00001.md"
    assert result.sha256 in content
    assert 'parser: "csv-row"' in content
    assert "# Bank Transaction TX-00001" in content
    assert "| betrag | 1256.00 |" in content
    assert "| verwendungszweck | Miete 01/2024 EH-045 |" in content


def test_normalize_bank_row_is_idempotent_on_sha256(tmp_path: Path) -> None:
    with BANK_INDEX.open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    first = normalize_bank_row(row, tmp_path / "normalize")
    second = normalize_bank_row(row, tmp_path / "normalize")

    assert first.idempotent is False
    assert second.idempotent is True
