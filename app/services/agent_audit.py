from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.schemas.agents import AgentActionPlan, AgentAuditEvent, Role, ToolCallRecord


class AgentAuditStore:
    def __init__(self, output_dir: Path) -> None:
        self.root = output_dir / "agent_audit"
        self.snapshots = output_dir / "agent_snapshots"
        self.root.mkdir(parents=True, exist_ok=True)
        self.snapshots.mkdir(parents=True, exist_ok=True)

    def path(self, building_id: str) -> Path:
        return self.root / f"{building_id}.jsonl"

    def snapshot_path(self, building_id: str, event_id: str, label: str) -> Path:
        directory = self.snapshots / building_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{event_id}.{label}.md"

    def append(
        self,
        *,
        building_id: str,
        actor_role: Role,
        plan: AgentActionPlan,
        tool_calls: list[ToolCallRecord],
        result_status: str,
        result_summary: str,
        before: str | None = None,
        after: str | None = None,
    ) -> AgentAuditEvent:
        event_id = f"AUD-{uuid4().hex[:12]}"
        before_snapshot = None
        after_snapshot = None
        if before is not None:
            before_path = self.snapshot_path(building_id, event_id, "before")
            before_path.write_text(before, encoding="utf-8")
            before_snapshot = str(before_path)
        if after is not None:
            after_path = self.snapshot_path(building_id, event_id, "after")
            after_path.write_text(after, encoding="utf-8")
            after_snapshot = str(after_path)
        event = AgentAuditEvent(
            event_id=event_id,
            created_at=datetime.now(UTC).isoformat(),
            building_id=building_id,
            actor_role=actor_role,
            agent=plan.agent,
            intent=plan.intent,
            mode=plan.mode,
            objective=plan.objective,
            plan=plan,
            tool_calls=tool_calls,
            result_status=result_status,  # type: ignore[arg-type]
            result_summary=result_summary,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
        with self.path(building_id).open("a", encoding="utf-8") as file:
            file.write(event.model_dump_json() + "\n")
        return event

    def list(self, building_id: str) -> list[AgentAuditEvent]:
        path = self.path(building_id)
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(AgentAuditEvent.model_validate(json.loads(line)))
        return events

    def get(self, building_id: str, event_id: str) -> AgentAuditEvent | None:
        for event in self.list(building_id):
            if event.event_id == event_id:
                return event
        return None
