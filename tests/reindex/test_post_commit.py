from __future__ import annotations

from pathlib import Path

from app.services.reindex import reindex_files
from app.storage.wiki_chunks import open_wiki_chunks


def test_reindex_touched_file_extracts_sections_and_entity_refs(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    root = wiki_dir / "LIE-001"
    root.mkdir(parents=True)
    (root / "index.md").write_text(
        "---\nname: test\ndescription: test\n---\n\n"
        "## Open Issues\n\n"
        "- 🔴 **EH-014:** Heizung defekt bei MIE-014\n\n"
        "## Recent Events\n\n"
        "| Date | Entity | Text |\n"
        "|---|---|---|\n"
        "| 2026-01-01 | HAUS-12 | Meldung |\n\n"
        "# Human Notes\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "wiki_chunks.duckdb"

    count = reindex_files(
        wiki_dir=wiki_dir,
        property_id="LIE-001",
        files=["index.md"],
        db_path=db_path,
    )

    store = open_wiki_chunks(db_path)
    rows = store.find_by_entity("LIE-001", "EH-014")
    assert count == 2
    assert rows[0]["file"] == "index.md"
    assert rows[0]["section"] == "Open Issues"
    assert rows[0]["entity_refs"] == ["EH-014", "MIE-014"]
