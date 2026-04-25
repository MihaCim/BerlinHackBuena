from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .utils import compact, read_json, read_text, write_json, write_text


SCHEMA_FILES = {
    "validation": "RESOURCE_VALIDATION_SCHEMA.md",
    "write": "CONTEXT_WRITE_SCHEMA.md",
    "process": "INGESTION_PROCESS_SCHEMA.md",
}

ALLOWED_KINDS = {"email", "text", "letter", "invoice", "bank", "other"}
TARGET_BY_KIND = {
    "email": "recent_communications",
    "letter": "meetings_decisions",
    "invoice": "invoices_payments",
    "bank": "financial_state",
    "text": "open_topics",
    "other": "open_topics",
}
SPAM_PHRASES = (
    "buy now",
    "limited time offer",
    "free money",
    "crypto giveaway",
    "work from home",
    "click here to claim",
    "viagra",
    "casino",
    "lottery winner",
)
ACCEPT_TERMS = (
    "property",
    "tenant",
    "owner",
    "invoice",
    "payment",
    "bank",
    "maintenance",
    "meeting",
    "heating",
    "water",
    "repair",
    "vendor",
    "eigentumer",
    "eigentuemer",
    "mieter",
    "rechnung",
    "zahlung",
    "instandhaltung",
    "versammlung",
    "heizung",
    "wasser",
    "schaden",
    "dienstleister",
    "weg",
)


def process_staged_intake(output_root: Path, property_id: str = "LIE-001", use_ai: bool = False) -> dict[str, Any]:
    schemas = load_agent_schemas()
    intake_dir = output_root / "intake"
    context_path = output_root / "properties" / property_id / "context.md"
    if not context_path.exists():
        return {"status": "blocked", "reason": "Run bootstrap first.", "processed": []}
    if not intake_dir.exists():
        return {"status": "ok", "reason": "No staged resources.", "processed": []}

    processed = []
    for record_path in sorted(intake_dir.glob("*.resource.json")):
        record = read_json(record_path)
        if record.get("status") not in ("staged_for_ingestion", "rejected"):
            continue
        if record.get("status") == "rejected" and not record.get("retry"):
            continue
        result = process_one_resource(record, record_path, context_path, schemas, use_ai=use_ai)
        processed.append(result)
    return {"status": "ok", "processed": processed}


def process_one_resource(
    record: dict[str, Any],
    record_path: Path,
    context_path: Path,
    schemas: dict[str, str],
    use_ai: bool = False,
) -> dict[str, Any]:
    raw_path = Path(record.get("raw_path", ""))
    content = read_text(raw_path) if raw_path.exists() else ""
    validation = validate_resource(record, content, schemas["validation"])
    now = datetime.now(timezone.utc).isoformat()
    if not validation["valid"]:
        updated = {
            **record,
            "status": "rejected",
            "processed_at": now,
            "validation": validation,
        }
        write_json(record_path, updated)
        return {"id": record.get("id"), "status": "rejected", "reason": validation["reason"]}

    target = route_resource(record, schemas["write"])
    block = build_agent_block(record, content, target, validation, schemas, now)
    context = read_text(context_path)
    updated_context = insert_agent_block(context, target, block, record.get("id", "INTAKE"))
    write_text(context_path, updated_context)
    updated_record = {
        **record,
        "status": "written_to_context",
        "processed_at": now,
        "target_section": target,
        "validation": validation,
        "agentic_schema_files": list(SCHEMA_FILES.values()),
    }
    write_json(record_path, updated_record)
    return {"id": record.get("id"), "status": "written_to_context", "target_section": target, "reason": validation["reason"]}


def load_agent_schemas(schema_root: Path | None = None) -> dict[str, str]:
    root = schema_root or Path.cwd() / "schemas"
    return {key: read_text(root / filename) for key, filename in SCHEMA_FILES.items()}


def validate_resource(record: dict[str, Any], content: str, schema_text: str) -> dict[str, Any]:
    kind = str(record.get("kind", "")).strip().lower()
    text = content.strip()
    lowered = text.lower()
    signals: list[str] = []
    if kind not in ALLOWED_KINDS:
        return decision(False, f"Unsupported resource kind: {kind or 'missing'}", 0.0, signals)
    if len(re.sub(r"\s+", "", text)) < 20:
        return decision(False, "Content is too short to safely ingest.", 0.0, signals)
    spam = [phrase for phrase in SPAM_PHRASES if phrase in lowered]
    if spam:
        return decision(False, f"Rejected as likely spam: {spam[0]}", 0.05, ["spam_phrase"])

    words = re.findall(r"[A-Za-z0-9_-]{3,}", lowered)
    urls = re.findall(r"https?://\S+|www\.\S+", lowered)
    non_empty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    url_lines = [line for line in non_empty_lines if re.fullmatch(r"https?://\S+|www\.\S+", line.lower())]
    if len(urls) > 3 and len(words) < 120:
        return decision(False, "Rejected because short content contains too many links.", 0.05, ["link_ratio"])
    if non_empty_lines and len(url_lines) / len(non_empty_lines) > 0.35:
        return decision(False, "Rejected because too many lines are only URLs.", 0.05, ["url_lines"])
    if repeated_content(non_empty_lines, words):
        return decision(False, "Rejected because content is mostly repeated text.", 0.1, ["repetition"])

    if any(term in lowered for term in ACCEPT_TERMS):
        signals.append("property_management_terms")
    if re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b|\b20\d{2}-\d{2}-\d{2}\b", text):
        signals.append("date")
    if re.search(r"\b\d+[,.]\d{2}\s?eur?\b|\b\d+[,.]\d{2}\b", lowered):
        signals.append("amount")
    if re.search(r"\b(subject|from|to|betreff|von|an):", lowered):
        signals.append("message_headers")
    if re.search(r"\b(inv|rg|rechnung)[-_ ]?\d+", lowered):
        signals.append("invoice_identifier")
    if not signals:
        return decision(False, "No property-management signal found in resource.", 0.25, [])

    confidence = min(0.95, 0.55 + 0.12 * len(set(signals)))
    return decision(True, f"Accepted by schema with signals: {', '.join(sorted(set(signals)))}.", confidence, sorted(set(signals)))


def decision(valid: bool, reason: str, confidence: float, signals: list[str]) -> dict[str, Any]:
    return {"valid": valid, "reason": reason, "confidence": round(confidence, 2), "signals": signals}


def repeated_content(lines: list[str], words: list[str]) -> bool:
    if len(lines) >= 4 and len(set(lines)) <= max(1, len(lines) // 3):
        return True
    if len(words) >= 30 and len(set(words)) <= max(4, len(words) // 8):
        return True
    return False


def route_resource(record: dict[str, Any], schema_text: str) -> str:
    kind = str(record.get("kind", "other")).strip().lower()
    return TARGET_BY_KIND.get(kind, "open_topics")


def build_agent_block(
    record: dict[str, Any],
    content: str,
    target: str,
    validation: dict[str, Any],
    schemas: dict[str, str],
    created_at: str,
) -> str:
    resource_id = sanitize_attr(str(record.get("id") or "INTAKE"))
    kind = sanitize_attr(str(record.get("kind") or "other"))
    name = sanitize_markdown(str(record.get("name") or resource_id))
    notes = sanitize_markdown(str(record.get("notes") or "none"))
    summary = summarize_content(content)
    return "\n".join(
        [
            f'<!-- AGENT_INTAKE_START id="{resource_id}" kind="{kind}" target="{target}" created_at="{created_at}" schema="INGESTION_PROCESS_SCHEMA.md" -->',
            f"### Intake: {name}",
            "",
            "- Status: validated and written by intake agent.",
            f"- Reason: {sanitize_markdown(validation['reason'])}",
            f"- Confidence: {validation['confidence']}",
            f"- Source: staged resource `{resource_id}`.",
            f"- Notes: {notes}.",
            "",
            summary,
            "<!-- AGENT_INTAKE_END -->",
        ]
    )


def summarize_content(content: str) -> str:
    lines = [line.strip("- \t") for line in content.splitlines() if line.strip()]
    selected = [compact(line, 180) for line in lines[:5]]
    if not selected:
        return "No readable text was available after validation."
    return "Accepted evidence summary:\n\n" + "\n".join(f"- {sanitize_markdown(line)}" for line in selected)


def insert_agent_block(context: str, target: str, block: str, resource_id: str) -> str:
    target_section = target if section_exists(context, target) else "open_topics"
    pattern = rf"(<!-- SECTION:{re.escape(target_section)} START -->\n## .+?\n)(?P<body>.*?)(<!-- SECTION:{re.escape(target_section)} END -->)"
    match = re.search(pattern, context, flags=re.S)
    if not match:
        return context.rstrip() + "\n\n" + block + "\n"
    section = match.group(0)
    section = remove_existing_agent_block(section, resource_id)
    insert_at = find_section_insert_index(section)
    replacement = section[:insert_at] + "\n" + block + "\n\n" + section[insert_at:].lstrip("\n")
    return context[: match.start()] + replacement + context[match.end() :]


def section_exists(context: str, target: str) -> bool:
    return f"<!-- SECTION:{target} START -->" in context and f"<!-- SECTION:{target} END -->" in context


def remove_existing_agent_block(section: str, resource_id: str) -> str:
    safe_id = re.escape(str(resource_id))
    pattern = rf"\n?<!-- AGENT_INTAKE_START id=\"{safe_id}\".*?<!-- AGENT_INTAKE_END -->\n?"
    return re.sub(pattern, "\n", section, flags=re.S)


def find_section_insert_index(section: str) -> int:
    heading = re.search(r"<!-- SECTION:[^>]+ START -->\n## .+?\n", section)
    if not heading:
        return 0
    index = heading.end()
    if section[index : index + 1] == "\n":
        index += 1
    return index


def sanitize_markdown(value: str) -> str:
    return value.replace("<!--", "< !--").replace("-->", "-- >").replace("</user>", "</ user>").strip()


def sanitize_attr(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.@-]+", "-", value).strip("-")[:120] or "resource"
