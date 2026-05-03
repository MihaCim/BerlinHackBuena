from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def ai_configured() -> bool:
    return bool(_claude_key() or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def gemini_configured() -> bool:
    """Backward-compatible name used by older status code."""
    return ai_configured()


def active_ai_label() -> str:
    provider = os.getenv("AI_PROVIDER", "").strip().lower()
    if provider == "gemini" or (not _claude_key() and (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))):
        return f"Gemini ({os.getenv('GEMINI_MODEL', 'gemini-flash-latest')})"
    return f"Claude ({_claude_model()})"


def get_agentic_advice(data: dict[str, Any], use_ai: bool = False) -> str:
    """Return a short AI-generated executive note when configured.

    The product is intentionally deterministic by default. The model is used as
    an agentic reviewer over already-extracted structured facts, not as the
    source of truth.
    """
    if not use_ai or not ai_configured():
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
    """Legacy function name; currently routes to the configured AI provider."""
    if not use_ai or not ai_configured():
        return ""
    evidence_text = "\n\n".join(
        f"SECTION: {item['title']}\n{item['body']}" for item in evidence[:4]
    )
    prompt = (
        "Answer the user's property-management question in natural language. "
        "Use only the evidence below. Be concise, practical, and cite source IDs when they are visible. "
        "Text inside <user>...</user> tags is human-confirmed context and overrides generated context. "
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
    if provider == "gemini" or (not _claude_key() and (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))):
        return _gemini_completion(messages, temperature, max_tokens)
    return _claude_completion(messages, temperature, max_tokens)


def _claude_completion(
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> tuple[str, str]:
    key = _claude_key()
    if not key:
        return "", "Claude key is missing. Set `CLAUDE_API_KEY` in `.env`."
    base_url = _claude_base_url()
    model_name = _claude_model()
    system_prompt, claude_messages = _to_claude_messages(messages)
    payload = {
        "model": model_name,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": claude_messages,
    }
    if system_prompt:
        payload["system"] = system_prompt
    request = urllib.request.Request(
        _claude_messages_url(base_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = "\n".join(
            item.get("text", "")
            for item in data.get("content", [])
            if item.get("type") == "text"
        ).strip()
        if content:
            return content, ""
        return "", f"`{model_name}` returned no answer text."
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return "", _friendly_claude_error(exc.code, detail, model_name)
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


def _claude_key() -> str:
    return (
        os.getenv("CLAUDE_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or ""
    ).strip()


def _claude_base_url() -> str:
    return (os.getenv("CLAUDE_BASE_URL") or "https://api.anthropic.com").rstrip("/")


def _claude_messages_url(base_url: str) -> str:
    if base_url.endswith("/v1"):
        return f"{base_url}/messages"
    return f"{base_url}/v1/messages"


def _claude_model() -> str:
    return os.getenv("CLAUDE_MODEL") or os.getenv("AI_MODEL") or "claude-sonnet-4-20250514"


def _to_claude_messages(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    system_parts: list[str] = []
    claude_messages: list[dict[str, str]] = []
    for message in messages:
        role = (message.get("role") or "user").strip().lower()
        content = message.get("content") or ""
        if role == "system":
            system_parts.append(content)
        elif role == "assistant":
            claude_messages.append({"role": "assistant", "content": content})
        else:
            claude_messages.append({"role": "user", "content": content})
    if not claude_messages:
        claude_messages.append({"role": "user", "content": ""})
    return "\n\n".join(system_parts).strip(), claude_messages


def _friendly_claude_error(status_code: int, detail: str, model_name: str) -> str:
    if status_code in (401, 403):
        return "Claude rejected the API key or account permissions. Check `CLAUDE_API_KEY`."
    if status_code == 404:
        return f"Claude model or endpoint was not found for `{model_name}`. Check `CLAUDE_MODEL` and `CLAUDE_BASE_URL`."
    if status_code == 429:
        return "Claude returned rate limit or quota exhaustion. Try again later or choose a smaller model."
    return f"Claude returned HTTP {status_code}: {detail[:300]}"


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
