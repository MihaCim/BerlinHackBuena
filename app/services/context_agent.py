from __future__ import annotations

from pathlib import Path
from typing import Any

import anyio
from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import FilesystemBackend

from app.services.university_chat_model import UniversityChatModel


class ContextAgentService:
    def __init__(
        self,
        workspace_root: Path,
        model: str,
        tub_api_key: str | None,
        tub_api_base: str,
        tub_chat_endpoint: str,
        tub_custom_instructions: str,
        tub_hide_custom_instructions: bool,
    ) -> None:
        self.workspace_root = workspace_root
        self.model = model
        self.tub_api_key = tub_api_key
        self.tub_api_base = tub_api_base
        self.tub_chat_endpoint = tub_chat_endpoint
        self.tub_custom_instructions = tub_custom_instructions
        self.tub_hide_custom_instructions = tub_hide_custom_instructions
        self.prompt_path = workspace_root / "schema" / "DEEP_AGENT.md"

    async def status(self) -> dict[str, object]:
        return {
            "model": self.model,
            "provider": "tub-chatbot",
            "prompt_path": str(self.prompt_path),
            "tub_configured": bool(self.tub_api_key),
            "subagents_enabled": False,
            "read_roots": ["/schema/**", "/normalize/**", "/output/**", "/template_index.md"],
            "write_roots": ["/output/**"],
        }

    async def build_base_context(self) -> dict[str, object]:
        return await anyio.to_thread.run_sync(self._build_base_context_sync)

    def _build_base_context_sync(self) -> dict[str, object]:
        agent = self._create_agent()
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Build the initial Buena context from base normalized sources. "
                            "Read schema/DEEP_AGENT.md first, then schema/CLAUDE.md, "
                            "schema/WIKI_SCHEMA.md, schema/extractors/00_shared_rules.md, "
                            "and normalize/base/stammdaten/stammdaten.md. Create "
                            "output/LIE-001/building.md and required sidecar files only."
                        ),
                    }
                ]
            }
        )
        return {"status": "completed", "result": compact_agent_result(result)}

    def _create_agent(self) -> Any:
        return create_deep_agent(
            model=self._create_model(),
            system_prompt=self.prompt_path.read_text(encoding="utf-8"),
            backend=FilesystemBackend(root_dir=self.workspace_root, virtual_mode=True),
            permissions=filesystem_permissions(),
            subagents=[],
            name="buena-context-agent",
        )

    def _create_model(self) -> UniversityChatModel:
        if not self.tub_api_key:
            raise ValueError("TUB_API_KEY is missing.")
        return UniversityChatModel(
            api_key=self.tub_api_key,
            api_base=self.tub_api_base,
            endpoint=self.tub_chat_endpoint,
            model_name=self.model,
            custom_instructions=self.tub_custom_instructions,
            hide_custom_instructions=self.tub_hide_custom_instructions,
        )


def filesystem_permissions() -> list[FilesystemPermission]:
    return [
        FilesystemPermission(
            operations=["read", "write"],
            paths=[
                "/.env",
                "/.env.*",
                "/.git/**",
                "/.venv/**",
                "/.opencode/**",
                "/codex_mem/**",
                "/data/**",
            ],
            mode="deny",
        ),
        FilesystemPermission(
            operations=["write"],
            paths=[
                "/schema/**",
                "/normalize/**",
                "/app/**",
                "/tests/**",
                "/scripts/**",
                "/pyproject.toml",
                "/uv.lock",
                "/README.md",
                "/AGENTS.md",
                "/CLAUDE.md",
            ],
            mode="deny",
        ),
    ]


def compact_agent_result(result: Any) -> dict[str, object]:
    messages = result.get("messages", []) if isinstance(result, dict) else []
    last_message = messages[-1] if messages else None
    content = getattr(last_message, "content", None)
    return {
        "message_count": len(messages),
        "final_message": content if isinstance(content, str) else str(content)[:4000],
    }
