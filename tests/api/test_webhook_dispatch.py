from __future__ import annotations

from app.services.handlers import get_event_handler
from app.services.handlers.bank import BankHandler
from app.services.handlers.email import EmailHandler
from app.services.handlers.invoice import InvoiceHandler


def test_webhook_event_types_route_to_handlers() -> None:
    assert isinstance(get_event_handler("email"), EmailHandler)
    assert isinstance(get_event_handler("invoice"), InvoiceHandler)
    assert isinstance(get_event_handler("bank"), BankHandler)
