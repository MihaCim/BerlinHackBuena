from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from httpx import AsyncClient

from tests.conftest import write_property_index

_INITIAL = (
    "---\nname: property-lie-001\ndescription: test\n---\n\n"
    "## Open Issues\n\n"
    "- 🔴 **EH-014:** Heizung [^EMAIL-1]\n\n"
    "# Human Notes\n\n"
    "Original PM note.\n"
)


@pytest.fixture
def lie_index(wiki_dir: Path) -> Path:
    path = write_property_index(wiki_dir, "LIE-001", _INITIAL)
    subprocess.run(["git", "init", "-q"], cwd=wiki_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=wiki_dir, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=wiki_dir, check=True)
    subprocess.run(["git", "add", "-A"], cwd=wiki_dir, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=wiki_dir, check=True)
    return path


async def test_get_human_notes_returns_body_below_boundary(
    client: AsyncClient, lie_index: Path
) -> None:
    r = await client.get("/api/v1/wiki/human-notes", params={"path": "LIE-001/index.md"})
    assert r.status_code == 200
    body = r.json()
    assert body["path"] == "LIE-001/index.md"
    assert body["body"] == "Original PM note."


async def test_put_human_notes_replaces_only_below_boundary(
    client: AsyncClient, wiki_dir: Path, lie_index: Path
) -> None:
    r = await client.put(
        "/api/v1/wiki/human-notes",
        params={"path": "LIE-001/index.md"},
        headers={"x-pm-user": "alice"},
        json={"body": "New note line 1\n\nLine 2"},
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["bytes_written"] > 0
    assert payload["commit_sha"]

    content = lie_index.read_text(encoding="utf-8")
    assert "## Open Issues" in content
    assert "EH-014" in content
    assert "Original PM note." not in content
    assert content.endswith("# Human Notes\n\nNew note line 1\n\nLine 2\n")


async def test_put_human_notes_rejects_double_boundary(
    client: AsyncClient, lie_index: Path
) -> None:
    r = await client.put(
        "/api/v1/wiki/human-notes",
        params={"path": "LIE-001/index.md"},
        headers={"x-pm-user": "alice"},
        json={"body": "Some text\n# Human Notes\nSneaky"},
    )
    assert r.status_code == 400


async def test_put_human_notes_requires_pm_user_header(
    client: AsyncClient, lie_index: Path
) -> None:
    r = await client.put(
        "/api/v1/wiki/human-notes",
        params={"path": "LIE-001/index.md"},
        json={"body": "x"},
    )
    assert r.status_code == 422


async def test_put_human_notes_path_traversal_rejected(
    client: AsyncClient, lie_index: Path
) -> None:
    r = await client.put(
        "/api/v1/wiki/human-notes",
        params={"path": "../etc/passwd"},
        headers={"x-pm-user": "alice"},
        json={"body": "x"},
    )
    assert r.status_code == 400


async def test_put_human_notes_idempotent_when_body_unchanged(
    client: AsyncClient, wiki_dir: Path, lie_index: Path
) -> None:
    r1 = await client.put(
        "/api/v1/wiki/human-notes",
        params={"path": "LIE-001/index.md"},
        headers={"x-pm-user": "alice"},
        json={"body": "Original PM note."},
    )
    assert r1.status_code == 200
    assert r1.json()["bytes_written"] == 0


async def test_put_human_notes_404_for_missing_file(
    client: AsyncClient, lie_index: Path
) -> None:
    r = await client.put(
        "/api/v1/wiki/human-notes",
        params={"path": "LIE-001/does-not-exist.md"},
        headers={"x-pm-user": "alice"},
        json={"body": "x"},
    )
    assert r.status_code == 400
