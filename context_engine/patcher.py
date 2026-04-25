from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any

from .utils import read_text, write_json, write_text


PATCHABLE_SECTIONS = [
    "agent_brief",
    "service_providers",
    "financial_state",
    "open_topics",
    "meetings_decisions",
    "recent_communications",
    "invoices_payments",
    "risks_review",
    "timeline",
    "source_register",
]


def apply_context_patch(current_path: Path, proposed: str, patch_log_path: Path, changed_sections: list[str] | None = None) -> dict[str, Any]:
    if not current_path.exists():
        write_text(current_path, proposed)
        patch_log = {
            "mode": "create",
            "patches_applied": ["full_file"],
            "lines_changed": len(proposed.splitlines()),
            "human_notes_preserved": True,
        }
        write_json(patch_log_path, patch_log)
        return patch_log

    current = read_text(current_path)
    proposed = preserve_human_notes(current, proposed)
    sections = changed_sections or PATCHABLE_SECTIONS
    patched = replace_frontmatter(current, proposed)
    applied = ["frontmatter"]
    review_items = []

    for section in sections:
        result = replace_section(patched, proposed, section)
        if result is None:
            review_items.append({"section": section, "reason": "Missing section anchor in current or proposed context."})
            continue
        if result != patched:
            applied.append(f"SECTION:{section}")
            patched = result

    if patched == current and proposed != current:
        review_items.append({"section": "fallback", "reason": "No patchable section changed; proposed context differs outside patch scope."})

    diff = list(difflib.unified_diff(current.splitlines(), patched.splitlines(), fromfile="before/context.md", tofile="after/context.md", lineterm=""))
    write_text(current_path, patched)
    patch_log = {
        "mode": "patch",
        "patches_applied": applied,
        "review_items": review_items,
        "lines_changed": len(diff),
        "human_notes_preserved": extract_human_notes(current) == extract_human_notes(patched),
        "diff_preview": diff[:200],
    }
    write_json(patch_log_path, patch_log)
    return patch_log


def preserve_human_notes(current: str, proposed: str) -> str:
    current_notes = extract_human_notes(current)
    if not current_notes:
        return proposed
    return re.sub(r"<!-- HUMAN_NOTES_START -->.*?<!-- HUMAN_NOTES_END -->", current_notes, proposed, flags=re.S)


def extract_human_notes(text: str) -> str:
    match = re.search(r"<!-- HUMAN_NOTES_START -->.*?<!-- HUMAN_NOTES_END -->", text, flags=re.S)
    return match.group(0) if match else ""


def replace_frontmatter(current: str, proposed: str) -> str:
    current_match = re.match(r"---\n.*?\n---", current, flags=re.S)
    proposed_match = re.match(r"---\n.*?\n---", proposed, flags=re.S)
    if not current_match or not proposed_match:
        return current
    return proposed_match.group(0) + current[current_match.end() :]


def replace_section(current: str, proposed: str, section: str) -> str | None:
    pattern = rf"<!-- SECTION:{re.escape(section)} START -->.*?<!-- SECTION:{re.escape(section)} END -->"
    proposed_match = re.search(pattern, proposed, flags=re.S)
    current_match = re.search(pattern, current, flags=re.S)
    if not proposed_match or not current_match:
        return None
    return current[: current_match.start()] + proposed_match.group(0) + current[current_match.end() :]

