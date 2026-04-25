from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.schemas.webhook import IngestEvent
from app.services.llm.client import FakeLLMClient
from app.services.supervisor import Supervisor
from app.storage.wiki_chunks import open_wiki_chunks
from app.tools.bootstrap_wiki import bootstrap

STAMMDATEN = Path(__file__).parents[2] / "data/stammdaten/stammdaten.json"


async def test_supervisor_runs_signal_to_apply_and_reindex(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    root = bootstrap(STAMMDATEN, wiki_dir)
    settings = Settings(
        wiki_dir=wiki_dir,
        normalize_dir=tmp_path / "normalize",
        output_dir=tmp_path / "output",
        data_dir=Path(__file__).parents[2] / "data",
    )
    llm = FakeLLMClient(
        {
            settings.fast_model: (
                '{"signal": true, "category": "manual/leak", "priority": "high", "confidence": 0.9}'
            ),
            settings.smart_model: (
                '{"summary":"manual leak","ops":['
                '{"op":"upsert_bullet","file":"index.md","section":"Open Issues",'
                '"key":"EH-001","text":"- 🔴 **EH-001:** Leak reported [^EVT-1]"},'
                '{"op":"upsert_footnote","file":"index.md","key":"EVT-1",'
                '"text":"normalize/manual/unknown/EVT-1.md"}]}'
            ),
        }
    )

    result = await Supervisor(settings=settings, llm=llm).handle(
        IngestEvent(
            event_id="EVT-1",
            event_type="manual",
            property_id="LIE-001",
            payload={"text": "Leak reported in EH-001"},
        )
    )

    store = open_wiki_chunks(settings.output_dir / "wiki_chunks.duckdb")
    rows = store.find_by_entity("LIE-001", "EH-001")
    assert result.patch is not None
    assert result.patch.applied_ops == 2
    assert "Leak reported" in (root / "index.md").read_text(encoding="utf-8")
    assert any(row["section"] == "Open Issues" for row in rows)
