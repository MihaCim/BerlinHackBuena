from __future__ import annotations

from pathlib import Path
from typing import Any

from .ai import answer_with_gemini
from .qa import retrieve_evidence, synthesize_answer
from .utils import read_text


CHAT_SCHEMA = "CHAT_AGENT_SCHEMA.md"


def answer_with_chat_agent(context_path: Path, question: str, use_ai: bool = False) -> dict[str, Any]:
    schema = load_chat_schema()
    clean_question = question.strip()
    if not clean_question:
        return {
            "answer": "Ask me a property question and I will search the compiled context.",
            "agent": build_agent_meta("empty_question", [], schema, "deterministic"),
        }

    context = read_text(context_path)
    evidence = retrieve_evidence(context, clean_question)
    intent = detect_intent(clean_question)
    if not evidence:
        return {
            "answer": "I could not find enough context to answer that from the compiled property file.",
            "agent": build_agent_meta(intent, [], schema, "no_evidence"),
        }

    ai_answer = answer_with_gemini(clean_question, evidence, use_ai=use_ai)
    if ai_answer and not ai_answer.startswith("AI answer failed safely:"):
        return {
            "answer": ai_answer,
            "agent": build_agent_meta(intent, evidence, schema, "model_synthesis"),
        }

    fallback = synthesize_answer(clean_question, evidence)
    if ai_answer:
        fallback = f"{fallback}\n\nNote: {ai_answer}"
    return {
        "answer": fallback,
        "agent": build_agent_meta(intent, evidence, schema, "deterministic_synthesis"),
    }


def load_chat_schema(schema_root: Path | None = None) -> str:
    root = schema_root or Path.cwd() / "schemas"
    return read_text(root / CHAT_SCHEMA)


def detect_intent(question: str) -> str:
    lowered = question.lower()
    if any(word in lowered for word in ("risk", "anomal", "review", "unresolved", "financial", "unpaid", "payment", "invoice")):
        return "financial_risk"
    if any(word in lowered for word in ("owner", "owns", "unit", "we ", "eh-", "eig")):
        return "owner_lookup"
    if any(word in lowered for word in ("provider", "vendor", "contractor", "service", "dienstleister")):
        return "service_provider_lookup"
    if any(word in lowered for word in ("topic", "open", "issue", "maintenance", "heating", "water", "damage")):
        return "operational_topic"
    return "general_context"


def build_agent_meta(intent: str, evidence: list[dict[str, str]], schema: str, mode: str) -> dict[str, Any]:
    return {
        "name": "context_chat_agent",
        "schema": CHAT_SCHEMA,
        "schema_loaded": bool(schema.strip()),
        "intent": intent,
        "mode": mode,
        "evidence_titles": [item["title"] for item in evidence],
        "steps": [
            "validate_question",
            "load_context",
            "retrieve_evidence",
            "plan_answer",
            "synthesize_response",
        ],
    }
