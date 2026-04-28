from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch


def write_buildings(output_dir: Path) -> None:
    (output_dir / "HAUS-12.md").write_text(
        "\n".join(
            [
                "# HAUS-12",
                "",
                "## owners",
                "| Unit | Owner |",
                "| --- | --- |",
                "| WE 01 | Osman Jacob |",
                "",
                "## financials",
                "- Invoice RG-100 remains unpaid and needs review.",
                "",
                "## open_topics",
                "<user id=\"u1\">Human note: never overwrite this roof leak context.</user>",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / "HAUS-99.md").write_text(
        "# HAUS-99\n\n## maintenance\n- Elevator maintenance is complete.\n",
        encoding="utf-8",
    )


def test_chat_auto_routes_and_returns_citations_and_visual_trace(client: TestClient, output_dir: Path) -> None:
    write_buildings(output_dir)
    response = client.post("/api/v1/agents/chat", json={"question": "Who owns WE 01?"})
    assert response.status_code == 200
    body = response.json()
    assert body["building_id"] == "HAUS-12"
    assert body["routed"] is True
    assert "Osman Jacob" in body["answer"]
    assert body["citations"][0]["title"] == "owners"
    assert [node["label"] for node in body["trace"]["nodes"]] == [
        "owner_lookup_agent",
        "route_building",
        "search_context",
        "citations",
    ]


def test_chat_uses_model_synthesis_when_requested(client: TestClient, output_dir: Path, monkeypatch: MonkeyPatch) -> None:
    write_buildings(output_dir)
    monkeypatch.setattr(
        "app.services.agent_supervisor.answer_with_gemini",
        lambda question, evidence, use_ai=False: "Model synthesized answer." if use_ai else "",
    )
    response = client.post("/api/v1/agents/chat", json={"question": "Who owns WE 01?", "use_ai": True})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Model synthesized answer."
    assert "model_synthesis" in [node["label"] for node in body["trace"]["nodes"]]


def test_write_requires_approver_role(client: TestClient, output_dir: Path) -> None:
    write_buildings(output_dir)
    response = client.post(
        "/api/v1/agents/patch",
        json={
            "building_id": "HAUS-12",
            "target_section": "open_topics",
            "content": "Heating contractor visit scheduled.",
            "reason": "maintenance update",
            "apply": True,
        },
        headers={"X-Agent-Role": "editor"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert "cannot perform" in response.json()["reason"]


def test_write_then_rollback_as_admin_preserves_user_blocks(client: TestClient, output_dir: Path) -> None:
    write_buildings(output_dir)
    write_response = client.post(
        "/api/v1/agents/patch",
        json={
            "building_id": "HAUS-12",
            "target_section": "open_topics",
            "content": "Heating contractor visit scheduled.",
            "reason": "maintenance update",
            "apply": True,
        },
        headers={"X-Agent-Role": "approver"},
    )
    assert write_response.status_code == 200
    assert write_response.json()["status"] == "written"
    changed = (output_dir / "HAUS-12.md").read_text(encoding="utf-8")
    assert "Heating contractor visit scheduled." in changed
    assert "<user id=\"u1\">Human note: never overwrite this roof leak context.</user>" in changed

    audit = client.get("/api/v1/agents/audit/HAUS-12").json()["events"]
    event_id = audit[-1]["event_id"]
    preview = client.post(
        "/api/v1/agents/rollback-preview",
        json={"building_id": "HAUS-12", "event_id": event_id},
        headers={"X-Agent-Role": "admin"},
    )
    assert preview.status_code == 200
    assert preview.json()["status"] == "preview"
    assert "Heating contractor visit scheduled." in preview.json()["patch_preview"]

    rollback = client.post(
        "/api/v1/agents/rollback",
        json={"building_id": "HAUS-12", "event_id": event_id},
        headers={"X-Agent-Role": "admin"},
    )
    assert rollback.status_code == 200
    assert rollback.json()["status"] == "rolled_back"
    restored = (output_dir / "HAUS-12.md").read_text(encoding="utf-8")
    assert "Heating contractor visit scheduled." not in restored
    assert "<user id=\"u1\">Human note: never overwrite this roof leak context.</user>" in restored


def test_rollback_requires_admin(client: TestClient, output_dir: Path) -> None:
    write_buildings(output_dir)
    response = client.post(
        "/api/v1/agents/rollback",
        json={"building_id": "HAUS-12", "event_id": "AUD-missing"},
        headers={"X-Agent-Role": "approver"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"


def test_valid_intake_can_auto_route_and_dry_run(client: TestClient, output_dir: Path) -> None:
    write_buildings(output_dir)
    response = client.post(
        "/api/v1/agents/intake",
        json={
            "resource_name": "owner-email.txt",
            "resource_kind": "email",
            "content": "Owner asks about WE 01 payment and property maintenance.",
            "apply": False,
        },
        headers={"X-Agent-Role": "editor"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "dry_run"
    assert body["building_id"] == "HAUS-12"
    assert "patch_preview" in body and body["patch_preview"]
