from __future__ import annotations

from app.core.config import Settings
from app.schemas.webhook import IngestEvent
from app.services.handlers.email import EmailHandler


async def test_email_handler_accepts_payload_text(settings: Settings) -> None:
    result = await EmailHandler().handle(
        IngestEvent(
            event_id="EMAIL-TEST",
            event_type="email",
            property_id="LIE-001",
            payload={"text": "Heizung kalt in EH-001"},
        ),
        settings,
    )

    assert result.normalized_path.is_file()
    assert "Heizung kalt" in result.normalized_text
