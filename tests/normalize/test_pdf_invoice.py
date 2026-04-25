from __future__ import annotations

from pathlib import Path

from app.services.normalize.pdf import normalize_invoice_pdf

REPO_ROOT = Path(__file__).resolve().parents[2]
INVOICE = REPO_ROOT / "data" / "rechnungen" / "2024-01" / "20240106_DL-010_INV-00001.pdf"


def test_normalize_invoice_pdf_extracts_line_items_and_totals(tmp_path: Path) -> None:
    result = normalize_invoice_pdf(INVOICE, tmp_path / "normalize")
    content = result.output_path.read_text(encoding="utf-8")

    assert result.output_path == tmp_path / "normalize/invoice/2024-01/INV-00001.md"
    assert result.sha256 in content
    assert 'parser: "pypdf"' in content
    assert "| Grundgebuehr | 1 pauschal | 210,00 EUR | 210,00 EUR |" in content
    assert "| Summe netto | 210,00 EUR |" in content
    assert "| MwSt. 19% | 39,90 EUR |" in content
    assert "| Gesamtbetrag | 249,90 EUR |" in content


def test_normalize_invoice_pdf_is_idempotent_on_sha256(tmp_path: Path) -> None:
    first = normalize_invoice_pdf(INVOICE, tmp_path / "normalize")
    second = normalize_invoice_pdf(INVOICE, tmp_path / "normalize")

    assert first.idempotent is False
    assert second.idempotent is True
