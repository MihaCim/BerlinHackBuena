from __future__ import annotations

from fastapi import APIRouter, Header

from app.core.config import get_settings
from app.schemas.agents import (
    AuditLogResponse,
    ChatRequest,
    ChatResponse,
    IntakeRequest,
    IntakeResponse,
    PatchRequest,
    PatchResponse,
    Role,
    RollbackRequest,
    RollbackPreviewResponse,
    RollbackResponse,
    ToolListResponse,
)
from app.services.agent_supervisor import PropertyAgentSupervisor

router = APIRouter()


def role_from_header(value: str) -> Role:
    return value if value in {"viewer", "editor", "approver", "admin"} else "viewer"  # type: ignore[return-value]


def supervisor() -> PropertyAgentSupervisor:
    return PropertyAgentSupervisor(get_settings().output_dir)


@router.get("/tools")
def list_agent_tools() -> ToolListResponse:
    return ToolListResponse(tools=supervisor().tool_names())


@router.post("/chat")
def chat_with_context(payload: ChatRequest, x_agent_role: str = Header(default="viewer")) -> ChatResponse:
    return supervisor().chat(
        question=payload.question,
        building_id=payload.building_id,
        actor_role=role_from_header(x_agent_role),
        use_ai=payload.use_ai,
    )


@router.post("/intake")
def intake_resource(payload: IntakeRequest, x_agent_role: str = Header(default="viewer")) -> IntakeResponse:
    return supervisor().intake(
        content=payload.content,
        resource_name=payload.resource_name,
        resource_kind=payload.resource_kind,
        notes=payload.notes,
        building_id=payload.building_id,
        apply=payload.apply,
        actor_role=role_from_header(x_agent_role),
    )


@router.post("/patch")
def patch_context(payload: PatchRequest, x_agent_role: str = Header(default="viewer")) -> PatchResponse:
    return supervisor().patch(
        target_section=payload.target_section,
        content=payload.content,
        reason=payload.reason,
        building_id=payload.building_id,
        apply=payload.apply,
        actor_role=role_from_header(x_agent_role),
    )


@router.post("/rollback")
def rollback_context(payload: RollbackRequest, x_agent_role: str = Header(default="viewer")) -> RollbackResponse:
    return supervisor().rollback(building_id=payload.building_id, event_id=payload.event_id, actor_role=role_from_header(x_agent_role))


@router.post("/rollback-preview")
def rollback_preview(payload: RollbackRequest, x_agent_role: str = Header(default="viewer")) -> RollbackPreviewResponse:
    return supervisor().rollback_preview(building_id=payload.building_id, event_id=payload.event_id, actor_role=role_from_header(x_agent_role))


@router.get("/audit/{building_id}")
def audit_log(building_id: str) -> AuditLogResponse:
    return AuditLogResponse(building_id=building_id, events=supervisor().audit_log(building_id))
