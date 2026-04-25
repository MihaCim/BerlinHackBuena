from __future__ import annotations

from pathlib import Path

from app.services.normalize.pdf import normalize_letter_pdf

REPO_ROOT = Path(__file__).resolve().parents[2]
LETTER = REPO_ROOT / "data" / "briefe" / "2024-04" / "20240420_mahnung_LTR-0035.pdf"


def test_normalize_letter_pdf_writes_markdown_prose(tmp_path: Path) -> None:
    result = normalize_letter_pdf(LETTER, tmp_path / "normalize")
    content = result.output_path.read_text(encoding="utf-8")

    assert result.output_path == tmp_path / "normalize/letter/2024-04/LTR-0035.md"
    assert result.sha256 in content
    assert 'mime: "application/pdf"' in content
    assert "# Letter LTR-0035" in content
    assert "Zahlungserinnerung (2. Mahnung)" in content
    assert "Bitte ueberweisen Sie den offenen Betrag" in content
