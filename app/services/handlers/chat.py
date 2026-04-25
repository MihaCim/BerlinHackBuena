from __future__ import annotations

from app.services.handlers.base import PayloadMarkdownHandler


class ChatHandler(PayloadMarkdownHandler):
    kind = "chat"
