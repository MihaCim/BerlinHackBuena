from __future__ import annotations

from app.schemas.agents import AgentActionPlan, AgentIntent, AgentMode, Role

SPECIALIST_BY_INTENT: dict[AgentIntent, str] = {
    "financial_anomaly": "financial_anomaly_agent",
    "owner_lookup": "owner_lookup_agent",
    "maintenance_topic": "maintenance_topic_agent",
    "service_provider": "service_provider_agent",
    "context_writer": "context_writer_agent",
    "resource_intake": "resource_intake_agent",
    "general_context": "general_context_agent",
}

TARGET_SECTION_BY_KIND = {
    "email": "communications",
    "letter": "meetings_and_decisions",
    "invoice": "financials",
    "bank": "financials",
    "text": "open_topics",
    "other": "open_topics",
}


def detect_chat_intent(question: str) -> AgentIntent:
    lowered = question.lower()
    if any(term in lowered for term in ("risk", "anomal", "unpaid", "payment", "invoice", "financial")):
        return "financial_anomaly"
    if any(term in lowered for term in ("owner", "owns", "unit", "we ", "eh-", "eig")):
        return "owner_lookup"
    if any(term in lowered for term in ("maintenance", "repair", "heating", "water", "damage", "topic", "open")):
        return "maintenance_topic"
    if any(term in lowered for term in ("provider", "vendor", "contractor", "service", "dienstleister")):
        return "service_provider"
    return "general_context"


def section_for_resource_kind(kind: str) -> str:
    return TARGET_SECTION_BY_KIND.get(kind.strip().lower(), "open_topics")


def build_plan(
    *,
    building_id: str,
    intent: AgentIntent,
    mode: AgentMode,
    actor_role: Role,
    objective: str,
    tools: list[str],
    target_section: str | None = None,
    confidence: float = 0.74,
) -> AgentActionPlan:
    return AgentActionPlan(
        agent=SPECIALIST_BY_INTENT[intent],
        intent=intent,
        mode=mode,
        building_id=building_id,
        objective=objective,
        actor_role=actor_role,
        tools=tools,
        target_section=target_section,
        confidence=confidence,
        safety_checks=[
            "only registered tools may run",
            "building id is path constrained",
            "protected <user> blocks are immutable",
            "writes require dry-run preview first",
            "all actions append audit events",
            "write and rollback actions require elevated roles",
        ],
        rollback="Use /api/v1/agents/rollback with an audited write event id.",
    )
