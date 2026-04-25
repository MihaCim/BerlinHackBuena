from __future__ import annotations

from pathlib import Path

from app.services.normalize.eml import normalize_eml

REPO_ROOT = Path(__file__).resolve().parents[2]
EMAIL = REPO_ROOT / "data" / "emails" / "2024-01" / "20240101_101600_EMAIL-00001.eml"


def test_normalize_eml_decodes_quoted_printable_and_writes_frontmatter(tmp_path: Path) -> None:
    result = normalize_eml(EMAIL, tmp_path / "normalize")
    content = result.output_path.read_text(encoding="utf-8")

    assert result.output_path == tmp_path / "normalize/eml/2024-01/EMAIL-00001.md"
    assert result.sha256 in content
    assert 'parser: "python-email"' in content
    assert "parsed_at:" in content
    assert 'mime: "message/rfc822"' in content
    assert "| Subject | Rechnung RE-2024-4229 |" in content
    assert "Zahlung bitte innerhalb von 14 Tagen" in content


def test_normalize_eml_is_idempotent_on_sha256(tmp_path: Path) -> None:
    first = normalize_eml(EMAIL, tmp_path / "normalize")
    first_content = first.output_path.read_text(encoding="utf-8")
    second = normalize_eml(EMAIL, tmp_path / "normalize")

    assert first.idempotent is False
    assert second.idempotent is True
    assert second.output_path.read_text(encoding="utf-8") == first_content
