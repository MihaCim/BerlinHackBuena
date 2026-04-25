from __future__ import annotations

import re
from datetime import UTC, datetime
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path

from app.services.normalize.common import (
    NormalizedDocument,
    detect_lang,
    document_id_from_name,
    month_from_source,
    normalized_path,
    parsed_timestamp,
    sha256_bytes,
    table_escape,
    write_normalized_markdown,
)


def normalize_eml(source_path: Path, normalize_dir: Path) -> NormalizedDocument:
    raw = source_path.read_bytes()
    sha = sha256_bytes(raw)
    message = BytesParser(policy=policy.default).parsebytes(raw)
    body = _plain_body(message)
    subject = _header(message, "subject")
    document_id = document_id_from_name(source_path, "EMAIL")
    message_date = _message_date(message)
    output_path = normalized_path(
        normalize_dir,
        "eml",
        month_from_source(source_path, message_date),
        document_id,
    )

    metadata = {
        "source": str(source_path),
        "sha256": sha,
        "parser": "python-email",
        "parsed_at": parsed_timestamp(),
        "mime": "message/rfc822",
        "lang": detect_lang(f"{subject}\n{body}"),
    }
    markdown = _render_email_markdown(
        document_id=document_id,
        subject=subject,
        sender=_header(message, "from"),
        recipients=_header(message, "to"),
        date_header=_header(message, "date"),
        message_id=_header(message, "message-id"),
        body=body,
    )
    return write_normalized_markdown(output_path=output_path, body=markdown, metadata=metadata)


def _plain_body(message: Message) -> str:
    if isinstance(message, EmailMessage):
        plain = message.get_body(preferencelist=("plain",))
        if plain is not None:
            return _clean_body(str(plain.get_content()))
        html = message.get_body(preferencelist=("html",))
        if html is not None:
            return _clean_body(_html_to_text(str(html.get_content())))

    if message.is_multipart():
        parts = []
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_disposition() == "attachment":
                continue
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                if isinstance(payload, bytes):
                    parts.append(payload.decode(charset, errors="replace"))
                elif isinstance(payload, str):
                    parts.append(payload)
        return _clean_body("\n\n".join(parts))

    payload = message.get_payload(decode=True)
    if isinstance(payload, bytes):
        charset = message.get_content_charset() or "utf-8"
        return _clean_body(payload.decode(charset, errors="replace"))
    return _clean_body(str(message.get_payload()))


def _header(message: Message, name: str) -> str:
    value = message.get(name, "")
    return str(value).strip()


def _message_date(message: Message) -> datetime | None:
    raw = _header(message, "date")
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _render_email_markdown(
    *,
    document_id: str,
    subject: str,
    sender: str,
    recipients: str,
    date_header: str,
    message_id: str,
    body: str,
) -> str:
    rows = [
        ("ID", document_id),
        ("Subject", subject),
        ("From", sender),
        ("To", recipients),
        ("Date", date_header),
        ("Message-ID", message_id),
    ]
    table = "\n".join(f"| {field} | {table_escape(value)} |" for field, value in rows)
    return (
        f"# Email {document_id}\n\n"
        "| Field | Value |\n"
        "|---|---|\n"
        f"{table}\n\n"
        "## Body\n\n"
        f"{body.strip()}\n"
    )


def _clean_body(body: str) -> str:
    return body.replace("\r\n", "\n").replace("\r", "\n").strip()


def _html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    text = re.sub(r"(?s)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)</p\s*>", "\n\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    return text
