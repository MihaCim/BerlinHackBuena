from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Any

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import FilesystemBackend

from app.services.openrouter_chat_model import OpenRouterChatModel

BASE_BATCH_ORDER = {
    "stammdaten": 0,
    "bank": 1,
    "rechnungen": 2,
    "briefe": 3,
    "emails": 4,
}


@dataclass(frozen=True)
class ContextAgentBatch:
    batch_id: str
    path: Path
    source_kind: str
    extractor_paths: tuple[str, ...]
    file_count: int


class ContextAgentService:
    def __init__(
        self,
        workspace_root: Path,
        model: str,
        sub_model: str,
        openrouter_api_key: str | None,
        openrouter_api_base: str,
    ) -> None:
        self.workspace_root = workspace_root
        self.model = model
        self.sub_model = sub_model
        self.openrouter_api_key = openrouter_api_key
        self.openrouter_api_base = openrouter_api_base
        self.prompt_path = workspace_root / "schema" / "DEEP_AGENT.md"

    async def status(self) -> dict[str, object]:
        base_batches = self._base_batches()
        return {
            "model": self.model,
            "sub_model": self.sub_model,
            "provider": "openrouter",
            "prompt_path": str(self.prompt_path),
            "openrouter_configured": bool(self.openrouter_api_key),
            "subagents_enabled": False,
            "read_roots": ["/schema/**", "/normalize/**", "/output/**", "/template_index.md"],
            "write_roots": ["/output/**"],
            "base_batches_total": len(base_batches),
            "base_batches": [batch_summary(batch, self.workspace_root) for batch in base_batches],
        }

    async def build_base_context(self) -> dict[str, object]:
        return await asyncio.to_thread(self._build_base_context_sync)

    async def enrich_base_context(self, max_batches: int | None = None) -> dict[str, object]:
        return await asyncio.to_thread(self._enrich_base_context_sync, max_batches)

    async def enrich_base_batch(self, batch_id: str) -> dict[str, object]:
        return await asyncio.to_thread(self._enrich_base_batch_sync, batch_id)

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

    def _enrich_base_context_sync(self, max_batches: int | None) -> dict[str, object]:
        batches = self._base_batches()
        selected = batches[:max_batches] if max_batches is not None else batches
        results = [self._run_base_batch(batch) for batch in selected]
        return {
            "status": "completed",
            "batches_total": len(batches),
            "batches_processed": len(results),
            "results": results,
        }

    def _enrich_base_batch_sync(self, batch_id: str) -> dict[str, object]:
        for batch in self._base_batches():
            if batch.batch_id == batch_id:
                return self._run_base_batch(batch)
        raise ValueError(f"Unknown base batch: {batch_id}")

    def _run_base_batch(self, batch: ContextAgentBatch) -> dict[str, object]:
        agent = self._create_agent()
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": self._base_batch_prompt(batch),
                    }
                ]
            }
        )
        return {
            "batch": batch_summary(batch, self.workspace_root),
            "result": compact_agent_result(result),
        }

    def _base_batches(self) -> list[ContextAgentBatch]:
        base_dir = self.workspace_root / "normalize" / "base"
        if not base_dir.exists():
            return []

        batches: list[ContextAgentBatch] = []
        for section in sorted(base_dir.iterdir(), key=batch_sort_key):
            if not section.is_dir():
                continue
            if section.name in {"stammdaten", "bank"}:
                batches.append(self._batch_for_path(section, section.name))
                continue
            for month_dir in sorted(path for path in section.iterdir() if path.is_dir()):
                batches.append(self._batch_for_path(month_dir, section.name))
        return batches

    def _batch_for_path(self, path: Path, source_kind: str) -> ContextAgentBatch:
        batch_root = self.workspace_root / "normalize" / "base"
        batch_id = "base-" + "-".join(path.relative_to(batch_root).parts)
        return ContextAgentBatch(
            batch_id=batch_id,
            path=path,
            source_kind=source_kind,
            extractor_paths=extractors_for(source_kind),
            file_count=sum(1 for item in path.rglob("*.md") if item.is_file()),
        )

    def _base_batch_prompt(self, batch: ContextAgentBatch) -> str:
        rel_path = batch.path.relative_to(self.workspace_root)
        extractor_list = ", ".join(batch.extractor_paths)
        return dedent(
            f"""
            Process normalized base batch `{rel_path}` into the Buena living context.

            Mandatory reads before changing output:
            - `schema/DEEP_AGENT.md`
            - `schema/CLAUDE.md`
            - `schema/WIKI_SCHEMA.md`
            - `schema/extractors/00_shared_rules.md`
            - `{extractor_list}`
            - `output/LIE-001/building.md`
            - `output/LIE-001/_state.json`
            - `output/LIE-001/06_skills.md` if it exists

            Batch metadata:
            - batch_id: `{batch.batch_id}`
            - source_kind: `{batch.source_kind}`
            - normalized_files: {batch.file_count}

            Work requirements:
            1. Visit every `.md` file under `{rel_path}`.
            2. Do not summarize from file names only.
            3. Classify each source as risk, financial, task, context, reference, or noise.
            4. Patch only durable, source-backed facts.
            5. Ignore greetings, boilerplate, and routine rent rows unless they affect status.
            6. Resolve entities from `output/` and `normalize/base/stammdaten/stammdaten.md`.
            7. Never invent unresolved IDs.
            8. Organize facts by property, HAUS, EH, EIG, MIE, DL, finance, timeline, skills.
            9. Create or patch management, building issue, physical, unit, person, provider,
               finance, invoice, skill, timeline, pending-review, and log files as needed.
            10. Detect conflicts and write low-confidence items to `_pending_review.md`.
            11. Preserve every `# Human Notes` section. Never write below it.
            12. Use source footnotes (`EMAIL-*`, `INV-*`, `LTR-*`, `TX-*`).
            13. Treat `06_skills.md` as self-updating operating memory.
            14. Add skills only for reusable property-management procedures.

            Completion response must include counts: files visited, sources patched,
            sources skipped, conflicts added, skills added, and files changed.
            """
        ).strip()

    def _create_agent(self) -> Any:
        return create_deep_agent(
            model=self._create_model(),
            system_prompt=self.prompt_path.read_text(encoding="utf-8"),
            backend=FilesystemBackend(root_dir=self.workspace_root, virtual_mode=True),
            permissions=filesystem_permissions(),
            subagents=[],
            name="buena-context-agent",
        )

    def _create_model(self) -> OpenRouterChatModel:
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is missing.")
        return OpenRouterChatModel(
            api_key=self.openrouter_api_key,
            api_base=self.openrouter_api_base,
            model_name=self.model,
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


def batch_sort_key(path: Path) -> tuple[int, str]:
    return (BASE_BATCH_ORDER.get(path.name, 99), path.name)


def extractors_for(source_kind: str) -> tuple[str, ...]:
    common = ("schema/extractors/10_coordinator.md",)
    match source_kind:
        case "stammdaten":
            return ("schema/extractors/02_stammdaten.md", *common)
        case "bank":
            return (
                "schema/extractors/07_bank_index.md",
                "schema/extractors/08_kontoauszug.md",
                *common,
            )
        case "rechnungen":
            return ("schema/extractors/06_invoice_pdf.md", *common)
        case "briefe":
            return ("schema/extractors/09_letter.md", *common)
        case "emails":
            return ("schema/extractors/04_eml.md", *common)
        case _:
            return common


def batch_summary(batch: ContextAgentBatch, workspace_root: Path) -> dict[str, object]:
    return {
        "batch_id": batch.batch_id,
        "path": str(batch.path.relative_to(workspace_root)),
        "source_kind": batch.source_kind,
        "file_count": batch.file_count,
        "extractor_paths": list(batch.extractor_paths),
    }


def compact_agent_result(result: Any) -> dict[str, object]:
    messages = result.get("messages", []) if isinstance(result, dict) else []
    last_message = messages[-1] if messages else None
    content = getattr(last_message, "content", None)
    return {
        "message_count": len(messages),
        "final_message": content if isinstance(content, str) else str(content)[:4000],
    }
