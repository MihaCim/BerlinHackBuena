from __future__ import annotations

from app.core.config import Settings
from app.schemas.webhook import IngestEvent
from app.services.handlers.invoice import InvoiceHandler


async def test_invoice_handler_smoke_payload(settings: Settings) -> None:
    result = await InvoiceHandler().handle(
        IngestEvent(
            event_id="INV-TEST",
            event_type="invoice",
            property_id="LIE-001",
            payload={"text": "Rechnung INV-TEST Betrag 120.00 EUR"},
        ),
        settings,
    )

    assert result.normalized_path.is_file()
    assert "INV-TEST" in result.normalized_text
