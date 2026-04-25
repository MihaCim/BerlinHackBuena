from __future__ import annotations

import asyncio
from functools import partial

import anyio

from app.core.config import Settings
from app.schemas.webhook import IngestEvent
from app.services.handlers.base import HandlerResult, PayloadMarkdownHandler
from app.services.normalize.bank import normalize_bank_row


class BankHandler(PayloadMarkdownHandler):
    kind = "bank"

    async def handle(self, event: IngestEvent, settings: Settings) -> HandlerResult:
        row = event.payload.get("row")
        if not isinstance(row, dict):
            return await super().handle(event, settings)
        document = await asyncio.to_thread(
            partial(
                normalize_bank_row,
                row,
                settings.normalize_dir,
                source=str(event.source_path or "webhook"),
            )
        )
        text = await anyio.Path(document.output_path).read_text(encoding="utf-8")
        return HandlerResult(
            normalized_path=document.output_path,
            normalized_text=text,
            source_id=event.event_id,
            event_type=event.event_type,
        )
