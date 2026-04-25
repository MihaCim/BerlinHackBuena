from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import Depends

from app.core.config import REPO_ROOT, Settings, get_settings
from app.schemas.webhook import IngestEvent
from app.services.classify import Classification, classify_document
from app.services.conflict import scan_patch_plan_conflicts
from app.services.extract import extract_patch_plan
from app.services.handlers import get_event_handler
from app.services.llm.client import LLMClient, get_llm_client
from app.services.locate import locate_sections
from app.services.patcher.apply import PatchApplyResult, apply_patch_plan
from app.services.patcher.atomic import atomic_write_text
from app.services.reindex import reindex_property
from app.services.resolve import resolve_context
from app.storage.stammdaten import StammdatenStore, open_stammdaten
from app.storage.wiki_chunks import open_wiki_chunks

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class SupervisorResult:
    event_id: str
    status: str
    classification: Classification | None
    patch: PatchApplyResult | None


class Supervisor:
    def __init__(self, *, settings: Settings, llm: LLMClient) -> None:
        self._settings = settings
        self._llm = llm

    async def handle(self, event: IngestEvent) -> SupervisorResult:
        handler = get_event_handler(event.event_type)
        normalized = await handler.handle(event, self._settings)

        classification = await classify_document(
            normalized_text=normalized.normalized_text,
            llm=self._llm,
            settings=self._settings,
        )
        if not classification.signal:
            log.info(
                "ingest_short_circuit",
                event_id=event.event_id,
                event_type=event.event_type,
                category=classification.category,
            )
            return SupervisorResult(event.event_id, "no_signal", classification, None)

        stammdaten = _open_stammdaten(self._settings, property_id=event.property_id)
        resolution = resolve_context(
            normalized_text=normalized.normalized_text,
            stammdaten=stammdaten,
            property_id=event.property_id,
        )
        wiki_chunks_db = _wiki_chunks_db_path(self._settings)
        if (self._settings.wiki_dir / event.property_id).is_dir():
            reindex_property(
                wiki_dir=self._settings.wiki_dir,
                property_id=event.property_id,
                db_path=wiki_chunks_db,
            )
        wiki_chunks = open_wiki_chunks(wiki_chunks_db)
        sections = locate_sections(
            wiki_chunks=wiki_chunks,
            property_id=event.property_id,
            entity_ids=resolution.entity_ids,
            query_text=normalized.normalized_text,
        )
        plan = await extract_patch_plan(
            event_id=event.event_id,
            event_type=event.event_type,
            property_id=event.property_id,
            normalized_text=normalized.normalized_text,
            resolution=resolution,
            sections=sections,
            llm=self._llm,
            settings=self._settings,
        )
        plan, conflict_issues = scan_patch_plan_conflicts(plan, wiki_dir=self._settings.wiki_dir)
        if conflict_issues:
            log.info(
                "ingest_conflicts_deferred",
                event_id=event.event_id,
                deferred=len(conflict_issues),
            )

        patch = apply_patch_plan(
            plan.model_dump(exclude_none=True),
            wiki_dir=self._settings.wiki_dir,
            vocabulary_path=REPO_ROOT / "schema" / "VOCABULARY.md",
            wiki_chunks_db_path=wiki_chunks_db,
        )
        return SupervisorResult(event.event_id, "applied", classification, patch)

    def record_failed_event(self, event: IngestEvent, reason: str) -> None:
        property_root = self._settings.wiki_dir / event.property_id
        property_root.mkdir(parents=True, exist_ok=True)
        path = property_root / "_hermes_feedback.jsonl"
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        record = {
            "kind": "ingest",
            "event_id": event.event_id,
            "property_id": event.property_id,
            "event_type": event.event_type,
            "retrieval_success": False,
            "error": reason,
        }
        atomic_write_text(path, existing + json.dumps(record, ensure_ascii=False) + "\n")


def _open_stammdaten(settings: Settings, *, property_id: str) -> StammdatenStore:
    db_path = settings.output_dir / "stammdaten.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = open_stammdaten(db_path)
    if store.find_entity_by_id(property_id) is None:
        source = settings.data_dir / "stammdaten" / "stammdaten.json"
        if source.is_file():
            store.load_from_json(source)
    return store


def _wiki_chunks_db_path(settings: Settings) -> Path:
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    return settings.output_dir / "wiki_chunks.duckdb"


def get_supervisor(
    settings: Annotated[Settings, Depends(get_settings)],
    llm: Annotated[LLMClient, Depends(get_llm_client)],
) -> Supervisor:
    return Supervisor(settings=settings, llm=llm)
