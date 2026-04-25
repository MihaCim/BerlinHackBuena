from __future__ import annotations

import pytest

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


def test_extract_keeps_server_owned_ids() -> None:
    plan = canonicalize_patch_plan(
        {
            "event_id": "EVT-INJECTED",
            "property_id": "LIE-999",
            "event_type": "manual",
            "ops": [],
        },
        event_id="EMAIL-1",
        property_id="LIE-001",
        event_type="email",
    )

    assert plan.event_id == "EMAIL-1"
    assert plan.property_id == "LIE-001"
    assert plan.event_type == "email"


def test_extract_rejects_escaping_patch_paths() -> None:
    with pytest.raises(ValueError, match="inside the property"):
        canonicalize_patch_plan(
            {
                "summary": "escape",
                "ops": [
                    {
                        "op": "upsert_bullet",
                        "file": "../outside.md",
                        "section": "Open Issues",
                        "key": "EH-014",
                        "content": "bad",
                    }
                ],
            },
            event_id="EMAIL-1",
            property_id="LIE-001",
            event_type="email",
        )
