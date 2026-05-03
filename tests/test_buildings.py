from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_get_building_404_when_missing(client: TestClient) -> None:
    r = client.get("/api/v1/buildings/HAUS-12")
    assert r.status_code == 404


def test_get_building_returns_markdown(client: TestClient, output_dir: Path) -> None:
    (output_dir / "HAUS-12.md").write_text("# HAUS-12\nHello.\n", encoding="utf-8")
    r = client.get("/api/v1/buildings/HAUS-12")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert "HAUS-12" in r.text


def test_get_building_rejects_bad_id(client: TestClient) -> None:
    r = client.get("/api/v1/buildings/..%2Fetc%2Fpasswd")
    assert r.status_code in {404, 422}
