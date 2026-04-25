from __future__ import annotations

from pathlib import Path

from app.schemas.patch_plan import PatchPlan
from app.services.conflict import scan_patch_plan_conflicts


def test_red_to_green_status_flip_is_deferred(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    root.mkdir()
    (root / "index.md").write_text(
        "---\nname: test\ndescription: test\n---\n\n"
        "## Open Issues\n\n"
        "- 🔴 **EH-014:** Heizung defekt\n\n"
        "# Human Notes\n",
        encoding="utf-8",
    )
    plan = PatchPlan.model_validate(
        {
            "event_id": "EVT-1",
            "property_id": "LIE-001",
            "ops": [
                {
                    "op": "upsert_bullet",
                    "file": "index.md",
                    "section": "Open Issues",
                    "key": "EH-014",
                    "text": "- 🟢 **EH-014:** Heizung erledigt",
                }
            ],
        }
    )

    filtered, issues = scan_patch_plan_conflicts(plan, wiki_dir=tmp_path)

    assert filtered.ops == []
    assert issues[0].reason == "status flip requires human approval"
