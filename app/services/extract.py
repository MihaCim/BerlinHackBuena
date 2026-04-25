from __future__ import annotations

import json
from typing import Any

from app.core.config import REPO_ROOT, Settings
from app.schemas.patch_plan import PatchPlan
from app.services.llm.client import LLMClient
from app.services.llm.json import parse_json_object
from app.services.locate import LocatedSection
from app.services.patcher.paths import normalize_property_file
from app.services.resolve import ResolutionResult


def extract_prompt(
    *,
    event_id: str,
    event_type: str,
    property_id: str,
    normalized_text: str,
    resolution: ResolutionResult,
    sections: list[LocatedSection],
) -> str:
    located = [
        {
            "file": section.file,
            "section": section.section,
            "entity_refs": section.entity_refs,
            "body": section.body,
        }
        for section in sections
    ]
    payload = {
        "event_id": event_id,
        "event_type": event_type,
        "property_id": property_id,
        "resolved_entity_ids": resolution.entity_ids,
        "source_ids": resolution.source_ids,
        "unresolved_ids": resolution.unresolved_ids,
        "located_sections": located,
        "normalized_document": normalized_text,
    }
    return (
        "Produce one PatchPlan JSON object for this normalized source. "
        "Use only the provided located sections and schema vocabulary. "
        "Return JSON only, no markdown.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, default=str)}"
    )


async def extract_patch_plan(
    *,
    event_id: str,
    event_type: str,
    property_id: str,
    normalized_text: str,
    resolution: ResolutionResult,
    sections: list[LocatedSection],
    llm: LLMClient,
    settings: Settings,
) -> PatchPlan:
    response = await llm.complete(
        model=settings.smart_model,
        system_prompt=_extract_system_prompt(),
        user_prompt=extract_prompt(
            event_id=event_id,
            event_type=event_type,
            property_id=property_id,
            normalized_text=normalized_text,
            resolution=resolution,
            sections=sections,
        ),
    )
    payload = parse_json_object(response)
    return canonicalize_patch_plan(
        payload,
        event_id=event_id,
        property_id=property_id,
        event_type=event_type,
        source_ids=resolution.source_ids,
    )


def canonicalize_patch_plan(
    payload: dict[str, Any],
    *,
    event_id: str,
    property_id: str,
    event_type: str,
    source_ids: list[str] | None = None,
) -> PatchPlan:
    data = dict(payload)
    data["event_id"] = event_id
    data["property_id"] = property_id
    data["event_type"] = event_type
    if source_ids and not data.get("source_ids"):
        data["source_ids"] = source_ids
    data["ops"] = [_canonical_op(op, property_id=property_id) for op in data.get("ops", [])]
    return PatchPlan.model_validate(data)


def _canonical_op(raw: object, *, property_id: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("patch op must be an object")
    op = dict(raw)
    op_name = str(op.get("op", ""))
    if "file" in op and op["file"] is not None:
        op["file"] = _normalize_file(str(op["file"]), property_id=property_id)

    if op_name == "upsert_bullet" and "text" not in op and "content" in op:
        op["text"] = op["content"]
    if op_name in {"upsert_row", "prepend_row"} and "row" not in op and "content" in op:
        op["row"] = op["content"]
    if op_name == "upsert_footnote" and "text" not in op and "value" in op:
        op["text"] = op["value"]
    if op_name == "update_state" and "updates" not in op and "field" in op:
        op["updates"] = {str(op["field"]): op.get("value")}
    return op


def _normalize_file(path: str, *, property_id: str) -> str:
    return normalize_property_file(path, property_id=property_id)


def _extract_system_prompt() -> str:
    parts = []
    for relative in (
        "schema/CLAUDE.md",
        "schema/VOCABULARY.md",
        "schema/extractors/00_shared_rules.md",
    ):
        path = REPO_ROOT / relative
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(parts) or "You produce PatchPlan JSON for a markdown wiki patcher."
