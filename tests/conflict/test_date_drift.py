from __future__ import annotations

from pathlib import Path

from app.schemas.patch_plan import PatchPlan
from app.services.conflict import scan_patch_plan_conflicts


def test_date_drift_deferred_to_pending_review(tmp_path: Path) -> None:
    root = _write_index(tmp_path, "- 🔴 **EH-014:** Heizung defekt seit 2026-01-01\n")
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
                    "text": "- 🔴 **EH-014:** Heizung defekt seit 2026-01-07",
                }
            ],
        }
    )

    filtered, issues = scan_patch_plan_conflicts(plan, wiki_dir=tmp_path)

    assert filtered.ops == []
    assert issues[0].reason == "date drift exceeds 3 days"
    assert "EH-014" in (root / "_pending_review.md").read_text(encoding="utf-8")


def _write_index(tmp_path: Path, open_issues: str) -> Path:
    root = tmp_path / "LIE-001"
    root.mkdir()
    (root / "index.md").write_text(
        "---\nname: test\ndescription: test\n---\n\n"
        "## Open Issues\n\n"
        f"{open_issues}\n"
        "## Provenance\n\n"
        "# Human Notes\n",
        encoding="utf-8",
    )
    return root
