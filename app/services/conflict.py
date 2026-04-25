from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.schemas.patch_plan import PatchPlan
from app.services.patcher.atomic import atomic_write_text

_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_MONEY_RE = re.compile(r"(?:€\s*)?(-?\d+(?:[.\s]\d{3})*(?:,\d{2}|\.\d{2}))\s*(?:€|EUR)?")
_BULLET_STATUS_RE = re.compile(r"^\s*-\s*(?P<status>[🔴🟡🟢])")


@dataclass(frozen=True)
class ConflictIssue:
    file: str
    section: str
    key: str
    reason: str
    existing: str
    incoming: str


def scan_patch_plan_conflicts(
    plan: PatchPlan,
    *,
    wiki_dir: Path,
    date_drift_days: int = 3,
    amount_delta_ratio: Decimal = Decimal("0.10"),
) -> tuple[PatchPlan, list[ConflictIssue]]:
    kept_ops: list[dict[str, Any]] = []
    issues: list[ConflictIssue] = []
    property_root = wiki_dir / plan.property_id

    for op in plan.ops:
        op_data = op.model_dump(exclude_none=True)
        issue = _conflict_for_op(
            op_data,
            property_root=property_root,
            date_drift_days=date_drift_days,
            amount_delta_ratio=amount_delta_ratio,
        )
        if issue is None:
            kept_ops.append(op_data)
        else:
            issues.append(issue)

    if issues:
        append_conflicts(property_root, issues)

    data = plan.model_dump()
    data["ops"] = kept_ops
    return PatchPlan.model_validate(data), issues


def append_conflicts(property_root: Path, issues: list[ConflictIssue]) -> None:
    if not issues:
        return
    path = property_root / "_pending_review.md"
    text = path.read_text(encoding="utf-8") if path.exists() else _default_pending_review()
    marker = "\n# Human Notes"
    boundary = text.find(marker)
    suffix = text[boundary:] if boundary != -1 else "\n# Human Notes\n"
    body = text[:boundary].rstrip() if boundary != -1 else text.rstrip()
    entries = []
    for issue in issues:
        entries.append(
            "\n".join(
                [
                    "",
                    f"### conflict: {issue.key}",
                    f"- file: `{issue.file}`",
                    f"- section: `{issue.section}`",
                    f"- reason: {issue.reason}",
                    f"- existing: `{issue.existing}`",
                    f"- incoming: `{issue.incoming}`",
                    "",
                ]
            )
        )
    atomic_write_text(path, body + "\n" + "\n".join(entries) + suffix)


def _conflict_for_op(
    op: dict[str, Any],
    *,
    property_root: Path,
    date_drift_days: int,
    amount_delta_ratio: Decimal,
) -> ConflictIssue | None:
    if op.get("op") not in {"upsert_bullet", "upsert_row"}:
        return None
    file = str(op.get("file", ""))
    section = str(op.get("section", ""))
    key = str(op.get("key", ""))
    if not file or not section or not key:
        return None
    path = property_root / file
    if not path.is_file():
        return None
    existing = _existing_keyed_line(path.read_text(encoding="utf-8"), section=section, key=key)
    if existing is None:
        return None
    incoming = _incoming_line(op)
    reason = _conflict_reason(
        existing,
        incoming,
        date_drift_days=date_drift_days,
        amount_delta_ratio=amount_delta_ratio,
    )
    if reason is None:
        return None
    return ConflictIssue(
        file=file,
        section=section,
        key=key,
        reason=reason,
        existing=existing,
        incoming=incoming,
    )


def _existing_keyed_line(content: str, *, section: str, key: str) -> str | None:
    body = _section_body(content, section)
    if body is None:
        return None
    bullet_key = re.compile(rf"\*\*{re.escape(key)}:\*\*")
    for line in body.splitlines():
        if line.lstrip().startswith("- ") and bullet_key.search(line):
            return line.strip()
        if line.lstrip().startswith("|") and _row_key(line) == key:
            return line.strip()
    return None


def _section_body(content: str, section: str) -> str | None:
    managed = content.split("\n# Human Notes", 1)[0]
    match = re.search(rf"^## {re.escape(section)}\s*$", managed, flags=re.MULTILINE)
    if match is None:
        return None
    next_match = re.search(r"^## .*$", managed[match.end() :], flags=re.MULTILINE)
    end = len(managed) if next_match is None else match.end() + next_match.start()
    return managed[match.end() : end]


def _row_key(line: str) -> str | None:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if not cells or set(cells[0]) <= {"-"}:
        return None
    return cells[0]


def _incoming_line(op: dict[str, Any]) -> str:
    if op.get("op") == "upsert_bullet":
        text = str(op.get("text") or op.get("content") or "")
        if text.lstrip().startswith("- "):
            return text.strip()
        key = str(op.get("key", ""))
        return f"- **{key}:** {text.strip()}"
    row = op.get("row") or op.get("content") or ""
    if isinstance(row, list):
        return "| " + " | ".join(str(cell).strip() for cell in row) + " |"
    return str(row).strip()


def _conflict_reason(
    existing: str,
    incoming: str,
    *,
    date_drift_days: int,
    amount_delta_ratio: Decimal,
) -> str | None:
    old_status = _status(existing)
    new_status = _status(incoming)
    if old_status == "🔴" and new_status == "🟢":
        return "status flip requires human approval"

    old_date = _first_date(existing)
    new_date = _first_date(incoming)
    if (
        old_date is not None
        and new_date is not None
        and abs((new_date - old_date).days) > date_drift_days
    ):
        return f"date drift exceeds {date_drift_days} days"

    old_amount = _first_amount(existing)
    new_amount = _first_amount(incoming)
    if old_amount is not None and new_amount is not None and old_amount != 0:
        delta = abs(new_amount - old_amount) / abs(old_amount)
        if delta > amount_delta_ratio:
            return f"amount delta exceeds {amount_delta_ratio:.0%}"
    return None


def _status(line: str) -> str | None:
    match = _BULLET_STATUS_RE.match(line)
    return match.group("status") if match is not None else None


def _first_date(line: str) -> date | None:
    match = _DATE_RE.search(line)
    if match is None:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _first_amount(line: str) -> Decimal | None:
    for match in _MONEY_RE.finditer(line):
        raw = match.group(1).replace(" ", "")
        if raw.count(",") == 1:
            raw = raw.replace(".", "").replace(",", ".")
        try:
            return Decimal(raw)
        except InvalidOperation:
            continue
    return None


def _default_pending_review() -> str:
    return (
        "---\n"
        "name: pending-review\n"
        "description: Open conflicts awaiting PM resolution.\n"
        "---\n\n"
        "## Open Conflicts\n\n"
        "<!-- agent-managed: one ### entry per conflict -->\n\n"
        "# Human Notes\n"
    )
