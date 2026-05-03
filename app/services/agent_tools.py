from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.schemas.agents import AgentCitation, ToolCallRecord
from app.services.building_memory import BuildingMemoryService
from app.services.context_guard import sanitize_agent_markdown, unified_diff, validate_human_authority

PROPERTY_TERMS = {
    "property",
    "building",
    "tenant",
    "owner",
    "invoice",
    "payment",
    "maintenance",
    "meeting",
    "heating",
    "water",
    "repair",
    "vendor",
    "weg",
    "eigentümer",
    "eigentuemer",
    "mieter",
    "rechnung",
    "zahlung",
    "instandhaltung",
    "versammlung",
}

SPAM_TERMS = {"buy now", "casino", "lottery winner", "crypto giveaway", "viagra", "click here to claim"}


class AgentToolRegistry:
    def __init__(self, output_dir: Path) -> None:
        self.memory = BuildingMemoryService(output_dir)
        self.tools: dict[str, Callable[..., ToolCallRecord]] = {
            "list_buildings": self.list_buildings,
            "read_context": self.read_context,
            "route_building": self.route_building,
            "search_context": self.search_context,
            "validate_resource": self.validate_resource,
            "dry_run_context_patch": self.dry_run_context_patch,
            "write_context_patch": self.write_context_patch,
            "rollback_context": self.rollback_context,
        }

    def names(self) -> list[str]:
        return sorted(self.tools)

    def call(self, name: str, **kwargs: Any) -> ToolCallRecord:
        tool = self.tools.get(name)
        if tool is None:
            return ToolCallRecord(tool=name, status="blocked", summary="Tool is not registered.")
        try:
            return tool(**kwargs)
        except Exception as exc:  # pragma: no cover
            return ToolCallRecord(tool=name, status="error", summary=str(exc))

    def list_buildings(self) -> ToolCallRecord:
        buildings = self.memory.list_buildings()
        return ToolCallRecord(
            tool="list_buildings",
            status="ok",
            summary=f"Found {len(buildings)} building context file(s).",
            output={"buildings": buildings},
        )

    def read_context(self, *, building_id: str) -> ToolCallRecord:
        context = self.memory.load(building_id)
        if context is None:
            return ToolCallRecord(tool="read_context", status="blocked", summary=f"Context file not found for {building_id}.")
        return ToolCallRecord(
            tool="read_context",
            status="ok",
            summary=f"Loaded {len(context)} characters.",
            output={"context": context, "building_id": building_id},
        )

    def route_building(self, *, query: str, building_id: str | None = None) -> ToolCallRecord:
        buildings = self.memory.list_buildings()
        if building_id and building_id != "auto":
            if building_id in buildings:
                return ToolCallRecord(
                    tool="route_building",
                    status="ok",
                    summary=f"Using requested building {building_id}.",
                    output={"building_id": building_id, "candidates": buildings, "routed": False},
                )
            return ToolCallRecord(
                tool="route_building",
                status="blocked",
                summary=f"Requested building {building_id} was not found.",
                output={"candidates": buildings},
            )
        scored = []
        for candidate in buildings:
            context = self.memory.load(candidate) or ""
            scored.append((route_score(query, f"{candidate}\n{context}"), candidate))
        scored.sort(reverse=True)
        if not scored:
            return ToolCallRecord(tool="route_building", status="blocked", summary="No building contexts are available.")
        selected = scored[0][1]
        return ToolCallRecord(
            tool="route_building",
            status="ok",
            summary=f"Auto-routed to {selected}.",
            output={"building_id": selected, "candidates": [item[1] for item in scored[:5]], "routed": True},
        )

    def search_context(self, *, building_id: str, query: str) -> ToolCallRecord:
        read = self.read_context(building_id=building_id)
        if read.status != "ok":
            return ToolCallRecord(tool="search_context", status=read.status, summary=read.summary)
        context = str(read.output["context"])
        evidence = []
        for title, body in split_sections(context):
            score = score_text(query, f"{title}\n{body}") + section_intent_boost(query, title)
            if score:
                evidence.append((score, title, trim(body)))
        evidence.sort(reverse=True, key=lambda item: item[0])
        citations = [
            AgentCitation(building_id=building_id, title=title, quote=first_quote(body), rank=index + 1).model_dump()
            for index, (_, title, body) in enumerate(evidence[:5])
        ]
        return ToolCallRecord(
            tool="search_context",
            status="ok",
            summary=f"Retrieved {len(citations)} cited evidence section(s).",
            output={"evidence": [{"title": item[1], "body": item[2]} for item in evidence[:5]], "citations": citations},
        )

    def validate_resource(self, *, resource_kind: str, content: str) -> ToolCallRecord:
        lowered = content.lower()
        if len(content.strip()) < 20:
            return ToolCallRecord(tool="validate_resource", status="blocked", summary="Rejected because content is too short.")
        if any(term in lowered for term in SPAM_TERMS):
            return ToolCallRecord(tool="validate_resource", status="blocked", summary="Rejected because content looks like spam.")
        signals = sorted(term for term in PROPERTY_TERMS if term in lowered)
        if not signals:
            return ToolCallRecord(tool="validate_resource", status="blocked", summary="Rejected because no property-management signal was found.")
        return ToolCallRecord(
            tool="validate_resource",
            status="ok",
            summary=f"Accepted {resource_kind} with signals: {', '.join(signals[:5])}.",
            output={"signals": signals, "confidence": min(0.96, 0.58 + len(signals) * 0.07)},
        )

    def dry_run_context_patch(self, *, building_id: str, target_section: str, content: str, reason: str) -> ToolCallRecord:
        read = self.read_context(building_id=building_id)
        if read.status != "ok":
            return ToolCallRecord(tool="dry_run_context_patch", status=read.status, summary=read.summary)
        before = str(read.output["context"])
        after = build_context_update(before, target_section, content, reason)
        guard = validate_human_authority(before, after)
        return ToolCallRecord(
            tool="dry_run_context_patch",
            status="ok" if guard.ok else "blocked",
            summary=guard.reason,
            output={
                "patch_preview": unified_diff(before, after, f"{building_id}.md", f"{building_id}.agent.md"),
                "candidate_context": after,
                "before_context": before,
            },
        )

    def write_context_patch(self, *, building_id: str, target_section: str, content: str, reason: str) -> ToolCallRecord:
        dry = self.dry_run_context_patch(building_id=building_id, target_section=target_section, content=content, reason=reason)
        if dry.status != "ok":
            return ToolCallRecord(tool="write_context_patch", status=dry.status, summary=dry.summary, output=dry.output)
        self.memory.write(building_id, str(dry.output["candidate_context"]))
        return ToolCallRecord(
            tool="write_context_patch",
            status="ok",
            summary="Context patch written after dry-run guard checks.",
            output=dry.output,
        )

    def rollback_context(self, *, building_id: str, snapshot_path: str) -> ToolCallRecord:
        path = Path(snapshot_path)
        if not path.exists():
            return ToolCallRecord(tool="rollback_context", status="blocked", summary="Rollback snapshot is missing.")
        self.memory.write(building_id, path.read_text(encoding="utf-8"))
        return ToolCallRecord(tool="rollback_context", status="ok", summary=f"Restored {building_id} from audited snapshot.")


def score_text(query: str, text: str) -> int:
    terms = {term.lower() for term in re.findall(r"[A-Za-z0-9_-]{3,}", query)}
    haystack = text.lower()
    return sum(1 for term in terms if term in haystack)


def route_score(query: str, text: str) -> int:
    score = score_text(query, text)
    lowered = query.lower()
    haystack = text.lower()
    if any(term in lowered for term in ("owner", "owns", "we ", "unit", "eig")) and any(
        term in haystack for term in ("## owners", "| owner", "we 01", "unit")
    ):
        score += 8
    if any(term in lowered for term in ("maintenance", "heating", "repair", "water", "damage")) and any(
        term in haystack for term in ("maintenance", "heating", "repair", "open_topics")
    ):
        score += 8
    if any(term in lowered for term in ("invoice", "payment", "financial", "unpaid")) and any(
        term in haystack for term in ("financial", "invoice", "payment", "unpaid")
    ):
        score += 8
    return score


def section_intent_boost(query: str, title: str) -> int:
    lowered = query.lower()
    title_lower = title.lower()
    boosts = [
        (("owner", "owns", "unit", "we ", "eh-", "eig"), ("owner", "unit"), 6),
        (("invoice", "payment", "unpaid", "financial", "risk", "anomal"), ("financial", "invoice", "payment"), 6),
        (("maintenance", "repair", "heating", "water", "damage", "topic"), ("topic", "maintenance", "repair"), 6),
        (("provider", "vendor", "contractor", "service"), ("provider", "vendor", "contractor", "service"), 6),
    ]
    for query_terms, title_terms, score in boosts:
        if any(term in lowered for term in query_terms) and any(term in title_lower for term in title_terms):
            return score
    return 0


def split_sections(markdown: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^##\s+(?P<title>.+?)\n", markdown, flags=re.MULTILINE))
    if not matches:
        return [("Document", markdown)]
    sections = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections.append((match.group("title").strip(), markdown[start:end].strip()))
    return sections


def trim(value: str, max_lines: int = 18) -> str:
    lines = [line.rstrip() for line in value.splitlines() if line.strip()]
    return "\n".join(lines[:max_lines] + (["..."] if len(lines) > max_lines else []))


def first_quote(value: str) -> str:
    for line in value.splitlines():
        clean = line.strip(" |-")
        if clean and not set(clean) <= {"-", ":"}:
            return clean[:220]
    return trim(value, 1)[:220]


def build_context_update(before: str, target_section: str, content: str, reason: str) -> str:
    safe_content = sanitize_agent_markdown(content)
    safe_reason = sanitize_agent_markdown(reason)
    stamp = datetime.now(UTC).isoformat()
    block = "\n".join(
        [
            f'<!-- AGENT_CONTEXT_START target="{target_section}" created_at="{stamp}" -->',
            f"### Agent update: {safe_reason}",
            "",
            safe_content,
            "<!-- AGENT_CONTEXT_END -->",
        ]
    )
    heading = re.search(rf"^##\s+{re.escape(target_section)}\s*$", before, flags=re.MULTILINE | re.IGNORECASE)
    if heading is None:
        return before.rstrip() + f"\n\n## {target_section}\n\n{block}\n"
    return before[: heading.end()] + "\n\n" + block + before[heading.end() :]
