from __future__ import annotations

from pathlib import Path

from app.schemas.agents import (
    AgentCitation,
    AgentTrace,
    AgentTraceNode,
    ChatResponse,
    IntakeResponse,
    PatchResponse,
    Role,
    RollbackPreviewResponse,
    RollbackResponse,
    ToolCallRecord,
)
from app.services.context_guard import unified_diff
from app.services.agent_audit import AgentAuditStore
from app.services.agent_specialists import build_plan, detect_chat_intent, section_for_resource_kind
from app.services.agent_tools import AgentToolRegistry
from context_engine.ai import active_ai_label, answer_with_gemini


WRITE_ROLES: set[Role] = {"approver", "admin"}
DRY_RUN_ROLES: set[Role] = {"editor", "approver", "admin"}


class PropertyAgentSupervisor:
    def __init__(self, output_dir: Path) -> None:
        self.tools = AgentToolRegistry(output_dir)
        self.audit = AgentAuditStore(output_dir)

    def tool_names(self) -> list[str]:
        return self.tools.names()

    def chat(self, *, question: str, building_id: str | None, actor_role: Role, use_ai: bool = False) -> ChatResponse:
        route = self.tools.call("route_building", query=question, building_id=building_id)
        selected = str(route.output.get("building_id", building_id or ""))
        intent = detect_chat_intent(question)
        plan = build_plan(
            building_id=selected or "unrouted",
            intent=intent,
            mode="read_only",
            actor_role=actor_role,
            objective=question,
            tools=["route_building", "search_context"],
        )
        calls = [route]
        citations: list[AgentCitation] = []
        answer = route.summary
        search = None
        if route.status == "ok":
            search = self.tools.call("search_context", building_id=selected, query=question)
            calls.append(search)
            citations = [AgentCitation.model_validate(item) for item in search.output.get("citations", [])]
            answer = synthesize_answer(question, search, citations)
            ai_answer = answer_with_gemini(question, list(search.output.get("evidence", [])), use_ai=use_ai)
            if ai_answer and not ai_answer.startswith("AI answer failed safely:"):
                answer = ai_answer
                calls.append(ToolCallRecord(tool="model_synthesis", status="ok", summary=f"{active_ai_label()} synthesized the answer."))
            elif ai_answer:
                calls.append(ToolCallRecord(tool="model_synthesis", status="blocked", summary=f"{active_ai_label()} failed safely: {ai_answer}"))
        self.audit.append(
            building_id=selected or "unrouted",
            actor_role=actor_role,
            plan=plan,
            tool_calls=calls,
            result_status="ok" if all(call.status == "ok" for call in calls) else "blocked",
            result_summary=answer[:240],
        )
        return ChatResponse(
            answer=answer,
            building_id=selected or "unrouted",
            routed=bool(route.output.get("routed")),
            candidates=list(route.output.get("candidates", [])),
            citations=citations,
            plan=plan,
            tool_calls=calls,
            trace=trace_from(plan.agent, calls, citations),
        )

    def intake(
        self,
        *,
        content: str,
        resource_name: str,
        resource_kind: str,
        notes: str,
        building_id: str | None,
        apply: bool,
        actor_role: Role,
    ) -> IntakeResponse:
        permission = require_role(actor_role, WRITE_ROLES if apply else DRY_RUN_ROLES)
        route = self.tools.call("route_building", query=f"{resource_name}\n{content}", building_id=building_id)
        selected = str(route.output.get("building_id", building_id or "unrouted"))
        target = section_for_resource_kind(resource_kind)
        plan = build_plan(
            building_id=selected,
            intent="resource_intake",
            mode="write" if apply else "dry_run",
            actor_role=actor_role,
            objective=f"Validate and route resource {resource_name!r}.",
            tools=["route_building", "validate_resource", "dry_run_context_patch"] + (["write_context_patch"] if apply else []),
            target_section=target,
        )
        calls = [route]
        if permission is not None:
            calls.append(permission)
            return self._intake_response("rejected", permission.summary, selected, plan, calls)
        if route.status != "ok":
            return self._intake_response("rejected", route.summary, selected, plan, calls)
        validation = self.tools.call("validate_resource", resource_kind=resource_kind, content=content)
        calls.append(validation)
        if validation.status != "ok":
            self.audit.append(
                building_id=selected,
                actor_role=actor_role,
                plan=plan,
                tool_calls=calls,
                result_status="blocked",
                result_summary=validation.summary,
            )
            return self._intake_response("rejected", validation.summary, selected, plan, calls)
        summary = build_resource_summary(resource_name, resource_kind, content, notes)
        patch_tool = "write_context_patch" if apply else "dry_run_context_patch"
        patch = self.tools.call(patch_tool, building_id=selected, target_section=target, content=summary, reason=f"resource intake: {resource_name}")
        calls.append(patch)
        status = "written" if apply and patch.status == "ok" else "dry_run"
        if patch.status != "ok":
            status = "rejected"
        before = patch.output.get("before_context") if patch.status == "ok" and apply else None
        after = patch.output.get("candidate_context") if patch.status == "ok" and apply else None
        self.audit.append(
            building_id=selected,
            actor_role=actor_role,
            plan=plan,
            tool_calls=calls,
            result_status="ok" if patch.status == "ok" else patch.status,
            result_summary=patch.summary,
            before=before,
            after=after,
        )
        return IntakeResponse(
            status=status,  # type: ignore[arg-type]
            reason=patch.summary,
            building_id=selected,
            plan=plan,
            tool_calls=calls,
            trace=trace_from(plan.agent, calls, []),
            patch_preview=patch.output.get("patch_preview"),
        )

    def _intake_response(
        self,
        status: str,
        reason: str,
        building_id: str,
        plan,
        calls: list[ToolCallRecord],
    ) -> IntakeResponse:
        return IntakeResponse(
            status=status,  # type: ignore[arg-type]
            reason=reason,
            building_id=building_id,
            plan=plan,
            tool_calls=calls,
            trace=trace_from(plan.agent, calls, []),
        )

    def patch(
        self,
        *,
        target_section: str,
        content: str,
        reason: str,
        building_id: str | None,
        apply: bool,
        actor_role: Role,
    ) -> PatchResponse:
        permission = require_role(actor_role, WRITE_ROLES if apply else DRY_RUN_ROLES)
        route = self.tools.call("route_building", query=f"{target_section}\n{content}", building_id=building_id)
        selected = str(route.output.get("building_id", building_id or "unrouted"))
        plan = build_plan(
            building_id=selected,
            intent="context_writer",
            mode="write" if apply else "dry_run",
            actor_role=actor_role,
            objective=reason,
            tools=["route_building", "dry_run_context_patch"] + (["write_context_patch"] if apply else []),
            target_section=target_section,
        )
        calls = [route]
        if permission is not None:
            calls.append(permission)
            return PatchResponse(
                status="blocked",
                reason=permission.summary,
                building_id=selected,
                plan=plan,
                tool_calls=calls,
                trace=trace_from(plan.agent, calls, []),
                patch_preview="",
            )
        tool = "write_context_patch" if apply else "dry_run_context_patch"
        patch = self.tools.call(tool, building_id=selected, target_section=target_section, content=content, reason=reason)
        calls.append(patch)
        status = "written" if apply and patch.status == "ok" else "dry_run"
        if patch.status != "ok":
            status = "blocked"
        self.audit.append(
            building_id=selected,
            actor_role=actor_role,
            plan=plan,
            tool_calls=calls,
            result_status="ok" if patch.status == "ok" else patch.status,
            result_summary=patch.summary,
            before=patch.output.get("before_context") if apply and patch.status == "ok" else None,
            after=patch.output.get("candidate_context") if apply and patch.status == "ok" else None,
        )
        return PatchResponse(
            status=status,  # type: ignore[arg-type]
            reason=patch.summary,
            building_id=selected,
            plan=plan,
            tool_calls=calls,
            trace=trace_from(plan.agent, calls, []),
            patch_preview=str(patch.output.get("patch_preview", "")),
        )

    def rollback(self, *, building_id: str, event_id: str, actor_role: Role) -> RollbackResponse:
        calls = []
        permission = require_role(actor_role, {"admin"})
        if permission is not None:
            calls.append(permission)
            return RollbackResponse(
                status="blocked",
                reason=permission.summary,
                event_id=event_id,
                building_id=building_id,
                trace=trace_from("rollback_agent", calls, []),
            )
        event = self.audit.get(building_id, event_id)
        if event is None or not event.before_snapshot:
            calls.append(ToolCallRecord(tool="lookup_audit", status="blocked", summary="No rollback snapshot exists for this event."))
            return RollbackResponse(
                status="blocked",
                reason=calls[-1].summary,
                event_id=event_id,
                building_id=building_id,
                trace=trace_from("rollback_agent", calls, []),
            )
        rollback = self.tools.call("rollback_context", building_id=building_id, snapshot_path=event.before_snapshot)
        calls.append(rollback)
        return RollbackResponse(
            status="rolled_back" if rollback.status == "ok" else "blocked",
            reason=rollback.summary,
            event_id=event_id,
            building_id=building_id,
            trace=trace_from("rollback_agent", calls, []),
        )

    def rollback_preview(self, *, building_id: str, event_id: str, actor_role: Role) -> RollbackPreviewResponse:
        calls = []
        permission = require_role(actor_role, {"admin"})
        if permission is not None:
            calls.append(permission)
            return RollbackPreviewResponse(
                status="blocked",
                reason=permission.summary,
                event_id=event_id,
                building_id=building_id,
                patch_preview="",
                trace=trace_from("rollback_agent", calls, []),
            )
        event = self.audit.get(building_id, event_id)
        if event is None or not event.before_snapshot:
            calls.append(ToolCallRecord(tool="lookup_audit", status="blocked", summary="No rollback snapshot exists for this event."))
            return RollbackPreviewResponse(
                status="blocked",
                reason=calls[-1].summary,
                event_id=event_id,
                building_id=building_id,
                patch_preview="",
                trace=trace_from("rollback_agent", calls, []),
            )
        current = self.tools.memory.load(building_id) or ""
        before = Path(event.before_snapshot).read_text(encoding="utf-8")
        calls.append(ToolCallRecord(tool="rollback_preview", status="ok", summary="Rollback diff preview generated."))
        return RollbackPreviewResponse(
            status="preview",
            reason="Rollback preview generated. Review before applying.",
            event_id=event_id,
            building_id=building_id,
            patch_preview=unified_diff(current, before, f"{building_id}.current.md", f"{building_id}.rollback.md"),
            trace=trace_from("rollback_agent", calls, []),
        )

    def audit_log(self, building_id: str):
        return self.audit.list(building_id)


def require_role(actor_role: Role, allowed: set[Role]) -> ToolCallRecord | None:
    if actor_role in allowed:
        return None
    return ToolCallRecord(
        tool="permission_gate",
        status="blocked",
        summary=f"Role {actor_role!r} cannot perform this action. Required: {', '.join(sorted(allowed))}.",
    )


def synthesize_answer(question: str, search: ToolCallRecord, citations: list[AgentCitation]) -> str:
    if search.status != "ok":
        return search.summary
    evidence = search.output.get("evidence", [])
    if not evidence:
        return "I could not find enough evidence in the building context to answer that."
    first = evidence[0]
    body_lines = [line.strip(" |-") for line in str(first["body"]).splitlines() if line.strip()]
    bullets = "\n".join(f"- {line}" for line in body_lines[:6])
    cited = "\n".join(f"[{citation.rank}] {citation.title}: {citation.quote}" for citation in citations[:3])
    return f"From `{first['title']}`, the strongest context I found for \"{question}\" is:\n\n{bullets}\n\nCitations:\n{cited}"


def build_resource_summary(resource_name: str, resource_kind: str, content: str, notes: str) -> str:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    selected = "\n".join(f"- {line[:220]}" for line in lines[:6]) or "- No readable text after validation."
    note = f"\n- Intake note: {notes}" if notes.strip() else ""
    return f"- Resource: {resource_name}\n- Kind: {resource_kind}{note}\n\nAccepted evidence:\n{selected}"


def trace_from(agent_name: str, calls: list[ToolCallRecord], citations: list[AgentCitation]) -> AgentTrace:
    nodes = [
        AgentTraceNode(id="agent", label=agent_name, status="info", detail="Selected specialist agent."),
    ]
    for index, call in enumerate(calls, start=1):
        nodes.append(
            AgentTraceNode(
                id=f"tool-{index}",
                label=call.tool,
                status=call.status if call.status in {"ok", "blocked", "error"} else "info",
                detail=call.summary,
                tool=call.tool,
            )
        )
    if citations:
        nodes.append(
            AgentTraceNode(
                id="citations",
                label="citations",
                status="ok",
                detail=f"{len(citations)} source citation(s) attached.",
            )
        )
    return AgentTrace(nodes=nodes)
