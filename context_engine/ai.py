from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def gemini_configured() -> bool:
    return bool(_academic_key() or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def get_agentic_advice(data: dict[str, Any], use_ai: bool = False) -> str:
    """Return a short Gemini-generated executive note when configured.

    The product is intentionally deterministic by default. Gemini is used as
    an agentic reviewer over already-extracted structured facts, not as the
    source of truth.
    """
    if not use_ai or not gemini_configured():
        return ""
    prompt = (
        "You are reviewing a German property-management context compiler output. "
        "Write 3 concise bullets naming what an AI agent should pay attention to. "
        "Do not invent facts. Use only these metrics and topic titles.\n\n"
        f"Metrics: {data.get('metrics')}\n"
        f"Recent topics: {[topic.get('title') for topic in data.get('topics', [])[-8:]]}\n"
        f"Anomalies: {[item.get('summary') for item in data.get('anomalies', [])[:8]]}\n"
    )
    answer, error = chat_completion([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=320)
    if answer:
        return answer
    return f"AI advisory step failed safely: {error}"


def answer_with_gemini(question: str, evidence: list[dict[str, str]], use_ai: bool = False) -> str:
    if not use_ai or not gemini_configured():
        return ""
    evidence_text = "\n\n".join(
        f"SECTION: {item['title']}\n{item['body']}" for item in evidence[:4]
    )
    prompt = (
        "Answer the user's property-management question in natural language. "
        "Use only the evidence below. Be concise, practical, and cite source IDs when they are visible. "
        "If the evidence is insufficient, say what is missing instead of guessing.\n\n"
        f"Question: {question}\n\n"
        f"Evidence:\n{evidence_text}"
    )
    answer, error = chat_completion([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=650)
    if answer:
        return answer
    return f"AI answer failed safely: {error}"


def chat_completion(messages: list[dict[str, str]], temperature: float = 0.1, max_tokens: int = 500) -> tuple[str, str]:
    provider = os.getenv("AI_PROVIDER", "").strip().lower()
    if provider == "gemini" or (not _academic_key() and (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))):
        return _gemini_completion(messages, temperature, max_tokens)
    return _academic_cloud_completion(messages, temperature, max_tokens)


def _academic_cloud_completion(
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> tuple[str, str]:
    key = _academic_key()
    if not key:
        return "", "Academic Cloud key is missing. Set `ACADEMIC_CLOUD_API_KEY` in `.env`."
    base_url = os.getenv("ACADEMIC_CLOUD_BASE_URL", "https://chat-ai.academiccloud.de/v1").rstrip("/")
    model_name = os.getenv("ACADEMIC_CLOUD_MODEL", os.getenv("AI_MODEL", "llama-3.3-70b-instruct"))
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if content:
            return content, ""
        reasoning = (((data.get("choices") or [{}])[0].get("message") or {}).get("reasoning") or "").strip()
        if reasoning:
            return "", f"`{model_name}` returned reasoning but no final answer. Try `ACADEMIC_CLOUD_MODEL=llama-3.3-70b-instruct`."
        return "", f"`{model_name}` returned no answer content."
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return "", _friendly_academic_error(exc.code, detail, model_name)
    except Exception as exc:
        return "", str(exc)


def _gemini_completion(messages: list[dict[str, str]], temperature: float, max_tokens: int) -> tuple[str, str]:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except Exception:
        return "", "Gemini selected, but `langchain-google-genai` is not installed."

    model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    model = ChatGoogleGenerativeAI(model=model_name, temperature=temperature, max_output_tokens=max_tokens)
    try:
        response = model.invoke(messages)
        return str(getattr(response, "content", response)).strip(), ""
    except Exception as exc:
        return "", _friendly_gemini_error(exc, model_name)


def _academic_key() -> str:
    return (
        os.getenv("ACADEMIC_CLOUD_API_KEY")
        or os.getenv("CHAT_AI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()


def _friendly_academic_error(status_code: int, detail: str, model_name: str) -> str:
    if status_code in (401, 403):
        return "Academic Cloud rejected the API key or account permissions. Check `ACADEMIC_CLOUD_API_KEY`."
    if status_code == 404:
        return f"Academic Cloud model or endpoint was not found for `{model_name}`. Check `ACADEMIC_CLOUD_MODEL`."
    if status_code == 429:
        return "Academic Cloud returned rate limit or quota exhaustion. Try again later or choose a smaller model."
    return f"Academic Cloud returned HTTP {status_code}: {detail[:300]}"


def _friendly_gemini_error(exc: Exception, model_name: str) -> str:
    message = str(exc)
    if "RESOURCE_EXHAUSTED" in message or "429" in message:
        return (
            f"Gemini returned quota/resource exhaustion for `{model_name}`. "
            "Check the Google AI Studio quota/billing state for this key, or use a different key/project."
        )
    if "NOT_FOUND" in message or "404" in message:
        return (
            f"Gemini model `{model_name}` was not found for this API/key. "
            "Set `GEMINI_MODEL=gemini-flash-latest` in `.env`, or use a model listed for your Google project."
        )
    if "API_KEY" in message or "permission" in message.lower() or "403" in message:
        return "Gemini rejected the key or permissions. Check `GEMINI_API_KEY` in `.env` and the project access."
    return message
