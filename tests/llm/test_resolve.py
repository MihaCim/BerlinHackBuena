from __future__ import annotations

from pathlib import Path

from app.services.resolve import resolve_context
from app.storage.stammdaten import open_stammdaten

STAMMDATEN = Path(__file__).parents[2] / "data/stammdaten/stammdaten.json"


def test_resolve_sender_email_and_mentioned_id(tmp_path: Path) -> None:
    store = open_stammdaten(tmp_path / "stammdaten.duckdb")
    store.load_from_json(STAMMDATEN)

    result = resolve_context(
        normalized_text=(
            "| From | Julius Nette <julius.nette@outlook.com> |\n\n"
            "## Body\n\nBitte prüfen Sie die Heizung in EH-014."
        ),
        stammdaten=store,
        property_id="LIE-001",
    )

    assert "MIE-001" in result.entity_ids
    assert "EH-014" in result.mentioned_ids
    assert result.unresolved_ids == []


def test_resolve_unknown_iban_returns_no_entity(tmp_path: Path) -> None:
    store = open_stammdaten(tmp_path / "stammdaten.duckdb")
    store.load_from_json(STAMMDATEN)

    result = resolve_context(
        normalized_text="IBAN: DE00111111111111111111",
        stammdaten=store,
        property_id="LIE-001",
    )

    assert result.entities == []
