from __future__ import annotations

import re
import quopri
import hashlib
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from .utils import compact, normalize_iban, parse_float, read_csv, read_json, read_text, rel, safe_date


INVOICE_RE = re.compile(r"(?P<date>\d{8})_DL-(?P<vendor>\d{3})_INV-(?P<inv>\d{5})\.pdf$", re.I)
INVOICE_DUP_RE = re.compile(r"(?P<date>\d{8})_DL-(?P<vendor>\d{3})_INV-DUP-(?P<inv>\d{5})\.pdf$", re.I)
LETTER_RE = re.compile(r"(?P<date>\d{8})_(?P<kind>[a-z_]+)_LTR-(?P<num>\d{4})\.pdf$", re.I)
ENTITY_RE = re.compile(r"\b(?:EH|EIG|MIE|DL|INV|LTR)-\d{3,5}\b", re.I)


def load_master(source_root: Path) -> dict[str, Any]:
    master = read_json(source_root / "stammdaten" / "stammdaten.json")
    for owner in master.get("eigentuemer", []):
        owner["iban_normalized"] = normalize_iban(owner.get("iban"))
        owner["display_name"] = display_party(owner)
    for tenant in master.get("mieter", []):
        tenant["iban_normalized"] = normalize_iban(tenant.get("iban"))
        tenant["display_name"] = display_party(tenant)
    for provider in master.get("dienstleister", []):
        provider["iban_normalized"] = normalize_iban(provider.get("iban"))
        provider["display_name"] = provider.get("firma") or display_party(provider)
    return master


def display_party(row: dict[str, Any]) -> str:
    if row.get("firma"):
        return str(row["firma"])
    name = " ".join(str(row.get(key) or "").strip() for key in ("vorname", "nachname")).strip()
    return name or str(row.get("id") or "")


def load_bank_rows(source_root: Path, delta_dirs: list[Path] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base = source_root / "bank" / "bank_index.csv"
    if base.exists():
        rows.extend(_normalize_bank_rows(read_csv(base), base, source_root))
    for delta_dir in delta_dirs or []:
        path = delta_dir / "bank" / "bank_index.csv"
        if path.exists():
            rows.extend(_normalize_bank_rows(read_csv(path), path, source_root))
    return rows


def load_delta_bank_rows(source_root: Path, delta_dir: Path) -> list[dict[str, Any]]:
    path = delta_dir / "bank" / "bank_index.csv"
    return _normalize_bank_rows(read_csv(path), path, source_root) if path.exists() else []


def _normalize_bank_rows(rows: list[dict[str, str]], path: Path, root: Path) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        normalized.append(
            {
                "id": row.get("id", ""),
                "date": safe_date(row.get("datum")),
                "direction": row.get("typ", ""),
                "amount": parse_float(row.get("betrag")),
                "category": row.get("kategorie", ""),
                "counterparty": row.get("gegen_name", ""),
                "purpose": row.get("verwendungszweck", ""),
                "reference_id": row.get("referenz_id", ""),
                "error_types": row.get("error_types", ""),
                "source_id": f"S:bank:{row.get('id', '')}",
                "source_path": rel(path, root),
            }
        )
    return normalized


def load_invoice_rows(source_root: Path, delta_dirs: list[Path] | None = None) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    duplicates: Counter[str] = Counter()
    for path in sorted((source_root / "rechnungen").glob("**/*.pdf")):
        invoice = invoice_from_pdf_path(path, source_root)
        if invoice:
            duplicates[invoice["id"]] += 1
            if invoice["id"] not in by_id:
                by_id[invoice["id"]] = invoice
            elif "duplicate_file" not in by_id[invoice["id"]]["error_types"]:
                by_id[invoice["id"]]["error_types"].append("duplicate_file")
    for delta_dir in delta_dirs or []:
        index = delta_dir / "rechnungen_index.csv"
        if index.exists():
            for row in read_csv(index):
                invoice_id = row.get("id", "")
                by_id[invoice_id] = {
                    "id": invoice_id,
                    "invoice_number": row.get("rechnungsnr", ""),
                    "date": safe_date(row.get("datum")),
                    "vendor_id": row.get("dienstleister_id", ""),
                    "vendor_name": row.get("dienstleister_firma", ""),
                    "recipient": row.get("empfaenger", ""),
                    "net": parse_float(row.get("netto")),
                    "vat": parse_float(row.get("mwst")),
                    "gross": parse_float(row.get("brutto")),
                    "iban": normalize_iban(row.get("iban")),
                    "error_types": [e for e in (row.get("error_types", "") or "").split("|") if e],
                    "filename": row.get("filename", ""),
                    "source_id": f"S:invoice:{invoice_id}",
                    "source_path": rel(index, source_root),
                }
    for invoice_id, count in duplicates.items():
        if count > 1 and invoice_id in by_id:
            by_id[invoice_id].setdefault("error_types", []).append("duplicate_file")
    return sorted(by_id.values(), key=lambda x: (x.get("date", ""), x.get("id", "")))


def load_delta_invoice_rows(source_root: Path, delta_dir: Path) -> list[dict[str, Any]]:
    index = delta_dir / "rechnungen_index.csv"
    invoices: list[dict[str, Any]] = []
    if not index.exists():
        return invoices
    for row in read_csv(index):
        invoice_id = row.get("id", "")
        invoices.append(
            {
                "id": invoice_id,
                "invoice_number": row.get("rechnungsnr", ""),
                "date": safe_date(row.get("datum")),
                "vendor_id": row.get("dienstleister_id", ""),
                "vendor_name": row.get("dienstleister_firma", ""),
                "recipient": row.get("empfaenger", ""),
                "net": parse_float(row.get("netto")),
                "vat": parse_float(row.get("mwst")),
                "gross": parse_float(row.get("brutto")),
                "iban": normalize_iban(row.get("iban")),
                "error_types": [e for e in (row.get("error_types", "") or "").split("|") if e],
                "filename": row.get("filename", ""),
                "source_id": f"S:invoice:{invoice_id}",
                "source_path": rel(index, source_root),
            }
        )
    return invoices


def invoice_from_pdf_path(path: Path, root: Path) -> dict[str, Any] | None:
    match = INVOICE_RE.search(path.name)
    duplicate_match = INVOICE_DUP_RE.search(path.name)
    if not match and not duplicate_match:
        return None
    match = match or duplicate_match
    assert match is not None
    invoice_id = f"INV-{match.group('inv')}"
    vendor_id = f"DL-{match.group('vendor')}"
    return {
        "id": invoice_id,
        "invoice_number": "",
        "date": safe_date(match.group("date")),
        "vendor_id": vendor_id,
        "vendor_name": "",
        "recipient": "",
        "net": 0.0,
        "vat": 0.0,
        "gross": 0.0,
        "iban": "",
        "error_types": ["duplicate_filename"] if duplicate_match else [],
        "filename": path.name,
        "source_id": f"S:invoice:{invoice_id}",
        "source_path": rel(path, root),
    }


def load_letters(source_root: Path) -> list[dict[str, Any]]:
    letters = []
    for path in sorted((source_root / "briefe").glob("**/*.pdf")):
        match = LETTER_RE.search(path.name)
        if not match:
            continue
        letter_id = f"LTR-{match.group('num')}"
        letters.append(
            {
                "id": letter_id,
                "date": safe_date(match.group("date")),
                "kind": match.group("kind").lower(),
                "filename": path.name,
                "source_id": f"S:letter:{letter_id}",
                "source_path": rel(path, source_root),
            }
        )
    return letters


def load_emails(source_root: Path, delta_dirs: list[Path] | None = None) -> list[dict[str, Any]]:
    indexed: dict[str, dict[str, str]] = {}
    search_roots = [source_root / "emails"]
    for delta_dir in delta_dirs or []:
        idx = delta_dir / "emails_index.csv"
        if idx.exists():
            for row in read_csv(idx):
                indexed[row.get("filename", "")] = row
        search_roots.append(delta_dir / "emails")

    emails = []
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for path in sorted(search_root.glob("**/*.eml")):
            parsed = parse_eml(path)
            index_row = indexed.get(path.name, {})
            email_id = index_row.get("id") or email_id_from_filename(path.name)
            category = index_row.get("category") or classify_email(parsed["subject"], parsed["body"])
            body = parsed["body"]
            emails.append(
                {
                    "id": email_id,
                    "datetime": index_row.get("datetime") or parsed["date"],
                    "thread_id": index_row.get("thread_id") or "",
                    "direction": index_row.get("direction") or infer_direction(parsed["from"]),
                    "from_email": index_row.get("from_email") or parsed["from"],
                    "to_email": index_row.get("to_email") or parsed["to"],
                    "subject": index_row.get("subject") or parsed["subject"],
                    "category": category,
                    "language": index_row.get("sprache") or "de",
                    "error_types": index_row.get("error_types") or "",
                    "body": body,
                    "summary": compact(body, 220),
                    "entities": sorted(set(match.upper() for match in ENTITY_RE.findall(body + " " + parsed["subject"]))),
                    "score": score_email(category, parsed["subject"], body),
                    "source_id": f"S:email:{email_id}",
                    "source_path": rel(path, source_root),
                }
            )
    return sorted(emails, key=lambda e: e.get("datetime", ""))


def load_delta_emails(source_root: Path, delta_dir: Path) -> list[dict[str, Any]]:
    indexed: dict[str, dict[str, str]] = {}
    idx = delta_dir / "emails_index.csv"
    if idx.exists():
        for row in read_csv(idx):
            indexed[row.get("filename", "")] = row
    emails = []
    search_root = delta_dir / "emails"
    if not search_root.exists():
        return emails
    for path in sorted(search_root.glob("**/*.eml")):
        parsed = parse_eml(path)
        index_row = indexed.get(path.name, {})
        email_id = index_row.get("id") or email_id_from_filename(path.name)
        category = index_row.get("category") or classify_email(parsed["subject"], parsed["body"])
        body = parsed["body"]
        emails.append(
            {
                "id": email_id,
                "datetime": index_row.get("datetime") or parsed["date"],
                "thread_id": index_row.get("thread_id") or "",
                "direction": index_row.get("direction") or infer_direction(parsed["from"]),
                "from_email": index_row.get("from_email") or parsed["from"],
                "to_email": index_row.get("to_email") or parsed["to"],
                "subject": index_row.get("subject") or parsed["subject"],
                "category": category,
                "language": index_row.get("sprache") or "de",
                "error_types": index_row.get("error_types") or "",
                "body": body,
                "summary": compact(body, 220),
                "entities": sorted(set(match.upper() for match in ENTITY_RE.findall(body + " " + parsed["subject"]))),
                "score": score_email(category, parsed["subject"], body),
                "source_id": f"S:email:{email_id}",
                "source_path": rel(path, source_root),
            }
        )
    return sorted(emails, key=lambda e: e.get("datetime", ""))


def parse_eml(path: Path) -> dict[str, str]:
    # The hackathon EML files are simple plain-text RFC 822 messages. A small
    # parser is much faster than constructing full email.message trees for
    # thousands of files, and still handles folded headers plus quoted-printable
    # bodies used in the dataset.
    raw_bytes = path.read_bytes()
    header_bytes, _, body_bytes = raw_bytes.partition(b"\n\n")
    header_text = header_bytes.decode("utf-8", errors="replace")
    body = body_bytes.decode("utf-8", errors="replace")
    headers = parse_headers(header_text)
    if headers.get("Content-Transfer-Encoding", "").lower() == "quoted-printable":
        body = quopri.decodestring(body.encode("utf-8", errors="ignore")).decode("utf-8", errors="replace")
    return {
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": decode_header_value(headers.get("Subject", "")),
        "date": headers.get("Date", ""),
        "body": body or "",
    }


def parse_headers(header_text: str) -> dict[str, str]:
    unfolded: list[str] = []
    for line in header_text.splitlines():
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += " " + line.strip()
        else:
            unfolded.append(line.rstrip())
    headers: dict[str, str] = {}
    for line in unfolded:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers


def decode_header_value(value: str) -> str:
    if "=?" not in value:
        return value
    try:
        from email.header import decode_header, make_header

        return str(make_header(decode_header(value)))
    except Exception:
        return value


def email_id_from_filename(name: str) -> str:
    match = re.search(r"(EMAIL-\d+)", name, re.I)
    return match.group(1).upper() if match else Path(name).stem


def infer_direction(sender: str) -> str:
    return "outgoing" if "huber-partner-verwaltung" in sender.lower() else "incoming"


def classify_email(subject: str, body: str = "") -> str:
    text = f"{subject} {body}".lower()
    rules = [
        ("rechtlich", ["einspruch", "beschluss", "kuendigung", "kündigung", "mahnung", "recht", "frist"]),
        ("mieter/kaution", ["kaution"]),
        ("rechnung", ["rechnung", "invoice", "abrechnung"]),
        ("schaden", ["leck", "wasserschaden", "heizung", "aufzug", "schimmel", "defekt"]),
        ("eigentuemer", ["eigentuemer", "eigentümer", "sonderumlage", "etv"]),
        ("noise", ["newsletter", "werbung", "angebot"]),
    ]
    for category, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return category
    return "allgemein"


def score_email(category: str, subject: str, body: str) -> float:
    text = f"{category} {subject} {body}".lower()
    score = 0.35
    if any(word in text for word in ("recht", "einspruch", "kuendigung", "kündigung", "frist", "mahnung")):
        score += 0.35
    if any(word in text for word in ("rechnung", "kaution", "zahlung", "sonderumlage", "hausgeld")):
        score += 0.2
    if any(word in text for word in ("heizung", "wasser", "leck", "aufzug", "schimmel", "notfall")):
        score += 0.25
    if "noise" in category:
        score -= 0.3
    return max(0.0, min(1.0, round(score, 2)))


def build_delta_dirs(source_root: Path, target_delta: Path | None = None, include_all: bool = False) -> list[Path]:
    incremental = source_root / "incremental"
    if not incremental.exists():
        return []
    dirs = sorted(path for path in incremental.glob("day-*") if path.is_dir())
    if include_all:
        return dirs
    if target_delta is None:
        return []
    target = target_delta.resolve()
    selected = []
    for path in dirs:
        selected.append(path)
        if path.resolve() == target:
            break
    return selected


@lru_cache(maxsize=4)
def _base_master(source_root: str) -> dict[str, Any]:
    return load_master(Path(source_root))


@lru_cache(maxsize=4)
def _base_bank_rows(source_root: str) -> tuple[dict[str, Any], ...]:
    return tuple(load_bank_rows(Path(source_root), []))


@lru_cache(maxsize=4)
def _base_invoice_rows(source_root: str) -> tuple[dict[str, Any], ...]:
    return tuple(load_invoice_rows(Path(source_root), []))


@lru_cache(maxsize=4)
def _base_emails(source_root: str) -> tuple[dict[str, Any], ...]:
    return tuple(load_emails(Path(source_root), []))


@lru_cache(maxsize=4)
def _base_letters(source_root: str) -> tuple[dict[str, Any], ...]:
    return tuple(load_letters(Path(source_root)))


def build_context_data(source_root: Path, delta_path: Path | None = None, include_all_deltas: bool = False) -> dict[str, Any]:
    source_root = source_root.resolve()
    source_key = str(source_root)
    delta_dirs = build_delta_dirs(source_root, delta_path, include_all_deltas)
    master = _base_master(source_key)
    bank_rows = list(_base_bank_rows(source_key))
    invoices_by_id = {invoice["id"]: dict(invoice) for invoice in _base_invoice_rows(source_key)}
    emails = list(_base_emails(source_key))
    letters = list(_base_letters(source_key))
    for delta_dir in delta_dirs:
        bank_rows.extend(load_delta_bank_rows(source_root, delta_dir))
        for invoice in load_delta_invoice_rows(source_root, delta_dir):
            invoices_by_id[invoice["id"]] = invoice
        emails.extend(load_delta_emails(source_root, delta_dir))
    invoices = sorted(invoices_by_id.values(), key=lambda x: (x.get("date", ""), x.get("id", "")))
    matches = reconcile_invoices(invoices, bank_rows)
    anomalies = collect_anomalies(bank_rows, invoices, emails, matches)
    topics = build_topics(emails)
    return {
        "source_root": str(source_root),
        "watermark": delta_dirs[-1].name if delta_dirs else "bootstrap",
        "master": master,
        "bank_rows": bank_rows,
        "invoices": invoices,
        "emails": emails,
        "letters": letters,
        "invoice_matches": matches,
        "anomalies": anomalies,
        "topics": topics,
        "metrics": {
            "bank_transactions": len(bank_rows),
            "invoices": len(invoices),
            "emails": len(emails),
            "letters": len(letters),
            "delta_days_included": len(delta_dirs),
            "topics": len(topics),
            "anomalies": len(anomalies),
        },
    }


def reconcile_invoices(invoices: list[dict[str, Any]], bank_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    bank_by_ref = defaultdict(list)
    for row in bank_rows:
        if row.get("reference_id"):
            bank_by_ref[row["reference_id"]].append(row)
        match = re.search(r"INV-\d{5}", row.get("purpose", ""))
        if match:
            bank_by_ref[match.group(0)].append(row)
    matches: dict[str, dict[str, Any]] = {}
    for invoice in invoices:
        invoice_id = invoice["id"]
        candidates = bank_by_ref.get(invoice_id, [])
        if not candidates and invoice.get("gross"):
            candidates = [
                row
                for row in bank_rows
                if row.get("direction") == "DEBIT" and abs(row.get("amount", 0.0) - invoice.get("gross", 0.0)) < 0.01
            ][:3]
        if candidates:
            best = candidates[0]
            matches[invoice_id] = {
                "status": "matched",
                "transaction_id": best.get("id"),
                "score": 0.95 if best.get("reference_id") == invoice_id else 0.72,
                "source_ids": [invoice.get("source_id"), best.get("source_id")],
            }
        else:
            matches[invoice_id] = {"status": "unmatched", "transaction_id": "", "score": 0.0, "source_ids": [invoice.get("source_id")]}
    return matches


def collect_anomalies(
    bank_rows: list[dict[str, Any]],
    invoices: list[dict[str, Any]],
    emails: list[dict[str, Any]],
    matches: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    anomalies = []
    for row in bank_rows:
        if row.get("error_types"):
            anomalies.append(
                {
                    "id": f"ANOM-{row['id']}",
                    "kind": "bank",
                    "severity": "medium",
                    "summary": f"Bank transaction {row['id']} has flags: {row['error_types']}",
                    "source_ids": [row["source_id"]],
                }
            )
    for invoice in invoices:
        errors = invoice.get("error_types") or []
        match = matches.get(invoice["id"], {})
        if errors or match.get("status") == "unmatched":
            severity = "high" if errors else "medium"
            reason = ", ".join(errors) if errors else "no matching bank transaction"
            anomalies.append(
                {
                    "id": f"ANOM-{invoice['id']}",
                    "kind": "invoice",
                    "severity": severity,
                    "summary": f"Invoice {invoice['id']} needs review: {reason}.",
                    "source_ids": [invoice["source_id"]],
                }
            )
    for email in emails:
        if email.get("score", 0) >= 0.8:
            anomalies.append(
                {
                    "id": f"REVIEW-{email['id']}",
                    "kind": "communication",
                    "severity": "high" if "recht" in email.get("category", "") else "medium",
                    "summary": f"High-signal email: {email['subject']}",
                    "source_ids": [email["source_id"]],
                }
            )
    return anomalies


def build_topics(emails: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for email in emails:
        if email.get("score", 0) >= 0.6:
            key = email.get("thread_id") or re.sub(r"^(re|aw):\s*", "", email.get("subject", "").lower())
            grouped[key].append(email)
    topics = []
    for key, items in sorted(grouped.items()):
        latest = sorted(items, key=lambda x: x.get("datetime", ""))[-1]
        topic_id = "TOPIC-" + hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()[:8].upper()
        topics.append(
            {
                "id": topic_id,
                "key": key,
                "title": latest.get("subject", "Untitled topic"),
                "status": "open",
                "priority": "high" if any(item.get("score", 0) >= 0.8 for item in items) else "medium",
                "latest": latest.get("datetime", ""),
                "summary": latest.get("summary", ""),
                "source_ids": [item["source_id"] for item in items[-3:]],
                "entities": sorted({entity for item in items for entity in item.get("entities", [])}),
            }
        )
    return topics[-30:]
