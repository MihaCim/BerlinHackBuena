from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["viewer", "editor", "approver", "admin"]
AgentMode = Literal["read_only", "dry_run", "write", "rollback"]
AgentIntent = Literal[
    "financial_anomaly",
    "owner_lookup",
    "maintenance_topic",
    "service_provider",
    "context_writer",
    "resource_intake",
    "general_context",
]


class AgentCitation(BaseModel):
    building_id: str
    title: str
    quote: str
    rank: int


class AgentTraceNode(BaseModel):
    id: str
    label: str
    status: Literal["ok", "blocked", "error", "info"]
    detail: str
    tool: str | None = None


class AgentTrace(BaseModel):
    nodes: list[AgentTraceNode]


class AgentActionPlan(BaseModel):
    agent: str
    intent: AgentIntent
    mode: AgentMode
    building_id: str
    objective: str
    actor_role: Role
    tools: list[str]
    target_section: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    safety_checks: list[str]
    rollback: str


class ToolCallRecord(BaseModel):
    tool: str
    status: Literal["ok", "blocked", "error"]
    summary: str
    output: dict[str, Any] = Field(default_factory=dict)


class AgentAuditEvent(BaseModel):
    event_id: str
    created_at: str
    building_id: str
    actor_role: Role
    agent: str
    intent: AgentIntent
    mode: AgentMode
    objective: str
    plan: AgentActionPlan
    tool_calls: list[ToolCallRecord]
    result_status: Literal["ok", "blocked", "error"]
    result_summary: str
    before_snapshot: str | None = None
    after_snapshot: str | None = None


class ChatRequest(BaseModel):
    question: str
    building_id: str | None = None
    use_ai: bool = False


class ChatResponse(BaseModel):
    answer: str
    building_id: str
    routed: bool
    candidates: list[str]
    citations: list[AgentCitation]
    plan: AgentActionPlan
    tool_calls: list[ToolCallRecord]
    trace: AgentTrace


class IntakeRequest(BaseModel):
    content: str
    resource_name: str = "resource.txt"
    resource_kind: str = "text"
    notes: str = ""
    building_id: str | None = None
    apply: bool = False


class IntakeResponse(BaseModel):
    status: Literal["accepted", "rejected", "written", "dry_run"]
    reason: str
    building_id: str
    citations: list[AgentCitation] = Field(default_factory=list)
    plan: AgentActionPlan
    tool_calls: list[ToolCallRecord]
    trace: AgentTrace
    patch_preview: str | None = None


class PatchRequest(BaseModel):
    target_section: str
    content: str
    reason: str = "agent proposed update"
    building_id: str | None = None
    apply: bool = False


class PatchResponse(BaseModel):
    status: Literal["dry_run", "written", "blocked"]
    reason: str
    building_id: str
    plan: AgentActionPlan
    tool_calls: list[ToolCallRecord]
    trace: AgentTrace
    patch_preview: str


class RollbackRequest(BaseModel):
    building_id: str
    event_id: str


class RollbackResponse(BaseModel):
    status: Literal["rolled_back", "blocked"]
    reason: str
    event_id: str
    building_id: str
    trace: AgentTrace


class RollbackPreviewResponse(BaseModel):
    status: Literal["preview", "blocked"]
    reason: str
    event_id: str
    building_id: str
    patch_preview: str
    trace: AgentTrace


class ToolListResponse(BaseModel):
    tools: list[str]


class AuditLogResponse(BaseModel):
    building_id: str
    events: list[AgentAuditEvent]
