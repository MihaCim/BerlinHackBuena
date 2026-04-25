from __future__ import annotations

import pytest

from app.core.config import Settings
from app.schemas.webhook import IngestEvent
from app.services.handlers.chat import ChatHandler
from app.services.handlers.document import DocumentHandler
from app.services.handlers.erp import ErpHandler
from app.services.handlers.letter import LetterHandler
from app.services.handlers.lint import LintHandler
from app.services.handlers.manual import ManualHandler
from app.services.handlers.schedule import ScheduleHandler
from app.services.handlers.voicenote import VoiceNoteHandler


@pytest.mark.parametrize(
    ("event_type", "handler"),
    [
        ("letter", LetterHandler()),
        ("chat", ChatHandler()),
        ("voicenote", VoiceNoteHandler()),
        ("erp", ErpHandler()),
        ("document", DocumentHandler()),
        ("manual", ManualHandler()),
        ("schedule", ScheduleHandler()),
        ("lint", LintHandler()),
    ],
)
async def test_remaining_handlers_smoke(event_type: str, handler, settings: Settings) -> None:
    result = await handler.handle(
        IngestEvent(
            event_id=f"{event_type.upper()}-001",
            event_type=event_type,
            property_id="LIE-001",
            payload={"text": "smoke"},
        ),
        settings,
    )

    assert result.normalized_path.is_file()
