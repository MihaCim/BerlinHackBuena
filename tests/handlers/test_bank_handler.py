from __future__ import annotations

from app.core.config import Settings
from app.schemas.webhook import IngestEvent
from app.services.handlers.bank import BankHandler


async def test_bank_handler_normalizes_row(settings: Settings) -> None:
    result = await BankHandler().handle(
        IngestEvent(
            event_id="TX-001",
            event_type="bank",
            property_id="LIE-001",
            payload={
                "row": {
                    "id": "TX-001",
                    "datum": "2026-01-02",
                    "typ": "Ueberweisung",
                    "betrag": "120.00",
                }
            },
        ),
        settings,
    )

    assert result.normalized_path.is_file()
    assert "| betrag | 120.00 |" in result.normalized_text
