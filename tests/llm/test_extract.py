from __future__ import annotations

from app.schemas.patch_plan import PatchPlan
from app.services.extract import canonicalize_patch_plan


def test_extract_canonicalizes_patch_plan_ops() -> None:
    plan = canonicalize_patch_plan(
        {
            "summary": "heating",
            "ops": [
                {
                    "op": "upsert_bullet",
                    "file": "wiki/LIE-001/index.md",
                    "section": "Open Issues",
                    "key": "EH-014",
                    "content": "- 🔴 **EH-014:** Heizung defekt [^EMAIL-1]",
                },
                {
                    "op": "upsert_footnote",
                    "file": "wiki/LIE-001/index.md",
                    "key": "EMAIL-1",
                    "value": "normalize/eml/EMAIL-1.md",
                },
            ],
        },
        event_id="EMAIL-1",
        property_id="LIE-001",
        event_type="email",
    )

    assert isinstance(plan, PatchPlan)
    assert plan.ops[0].file == "index.md"
    assert plan.ops[0].text == "- 🔴 **EH-014:** Heizung defekt [^EMAIL-1]"
    assert plan.ops[1].text == "normalize/eml/EMAIL-1.md"
