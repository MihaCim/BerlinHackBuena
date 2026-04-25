from __future__ import annotations

from app.services.handlers.bank import BankHandler
from app.services.handlers.base import EventHandler
from app.services.handlers.chat import ChatHandler
from app.services.handlers.document import DocumentHandler
from app.services.handlers.email import EmailHandler
from app.services.handlers.erp import ErpHandler
from app.services.handlers.invoice import InvoiceHandler
from app.services.handlers.letter import LetterHandler
from app.services.handlers.lint import LintHandler
from app.services.handlers.manual import ManualHandler
from app.services.handlers.schedule import ScheduleHandler
from app.services.handlers.voicenote import VoiceNoteHandler

_HANDLERS: dict[str, EventHandler] = {
    "email": EmailHandler(),
    "eml": EmailHandler(),
    "letter": LetterHandler(),
    "invoice": InvoiceHandler(),
    "bank": BankHandler(),
    "chat": ChatHandler(),
    "slack": ChatHandler(),
    "whatsapp": ChatHandler(),
    "voicenote": VoiceNoteHandler(),
    "erp": ErpHandler(),
    "document": DocumentHandler(),
    "manual": ManualHandler(),
    "schedule": ScheduleHandler(),
    "lint": LintHandler(),
}


def get_event_handler(event_type: str) -> EventHandler:
    return _HANDLERS.get(event_type.lower(), DocumentHandler())


__all__ = ["EventHandler", "get_event_handler"]
