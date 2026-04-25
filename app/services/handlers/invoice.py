from __future__ import annotations

import asyncio

import anyio

from app.core.config import Settings
from app.schemas.webhook import IngestEvent
from app.services.handlers.base import HandlerResult, PayloadMarkdownHandler
from app.services.normalize.pdf import normalize_invoice_pdf


class InvoiceHandler(PayloadMarkdownHandler):
    kind = "invoice"

    async def handle(self, event: IngestEvent, settings: Settings) -> HandlerResult:
        if event.source_path is None or not event.source_path.is_file():
            return await super().handle(event, settings)
        document = await asyncio.to_thread(
            normalize_invoice_pdf,
            event.source_path,
            settings.normalize_dir,
        )
        text = await anyio.Path(document.output_path).read_text(encoding="utf-8")
        return HandlerResult(
            normalized_path=document.output_path,
            normalized_text=text,
            source_id=event.event_id,
            event_type=event.event_type,
        )
