from __future__ import annotations

from pathlib import Path

from app.schemas.patch_plan import PatchPlan
from app.services.conflict import scan_patch_plan_conflicts


def test_amount_delta_over_ten_percent_is_deferred(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    root.mkdir()
    (root / "index.md").write_text(
        "---\nname: test\ndescription: test\n---\n\n"
        "## Recent Invoices\n\n"
        "| ID | Amount |\n"
        "|---|---|\n"
        "| INV-001 | 100.00 EUR |\n\n"
        "# Human Notes\n",
        encoding="utf-8",
    )
    plan = PatchPlan.model_validate(
        {
            "event_id": "EVT-1",
            "property_id": "LIE-001",
            "ops": [
                {
                    "op": "upsert_row",
                    "file": "index.md",
                    "section": "Recent Invoices",
                    "key": "INV-001",
                    "row": ["INV-001", "125.00 EUR"],
                }
            ],
        }
    )

    filtered, issues = scan_patch_plan_conflicts(plan, wiki_dir=tmp_path)

    assert filtered.ops == []
    assert issues[0].reason == "amount delta exceeds 10%"
