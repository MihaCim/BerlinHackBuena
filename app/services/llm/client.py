from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Annotated, Protocol

import httpx
from fastapi import Depends

from app.core.config import REPO_ROOT, Settings, get_settings


class LLMClient(Protocol):
    async def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        """Return raw model text for a single prompt."""


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


class AnthropicClient:
    """Minimal Anthropic Messages API client used behind the LLMClient protocol."""

    def __init__(
        self,
        *,
        api_key: str,
        timeout: float = 60.0,
        base_url: str = "https://api.anthropic.com/v1/messages",
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._base_url = base_url

    async def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": 4096,
            "system": [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": [{"role": "user", "content": user_prompt}],
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self._base_url, headers=headers, json=payload)
            response.raise_for_status()
        data = response.json()
        return "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if isinstance(block, Mapping) and block.get("type") == "text"
        )


class FakeLLMClient:
    """Offline LLM test double keyed by (model, prompt_hash(user_prompt))."""

    def __init__(self, responses: Mapping[object, str] | None = None) -> None:
        self.responses = dict(responses or {})
        self.calls: list[dict[str, str]] = []

    def add_response(self, *, model: str, user_prompt: str, response: str) -> None:
        self.responses[(model, prompt_hash(user_prompt))] = response

    async def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(
            {
                "model": model,
                "system_hash": prompt_hash(system_prompt),
                "prompt_hash": prompt_hash(user_prompt),
                "user_prompt": user_prompt,
            }
        )
        keys = (
            (model, prompt_hash(user_prompt)),
            (model, user_prompt),
            prompt_hash(user_prompt),
            model,
            "*",
        )
        for key in keys:
            if key in self.responses:
                return self.responses[key]
        return (
            '{"event_id":"","property_id":"LIE-001","summary":"fake empty plan",'
            '"ops":[],"review_items":[]}'
        )


def _system_prompt() -> str:
    return (REPO_ROOT / "schema" / "CLAUDE.md").read_text(encoding="utf-8")


def get_llm_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> LLMClient:
    if settings.anthropic_api_key is None:
        return FakeLLMClient()
    return AnthropicClient(api_key=settings.anthropic_api_key)
