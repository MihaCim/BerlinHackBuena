from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "agent_buildings"
    directory.mkdir()
    return directory


@pytest.fixture
def settings(output_dir: Path, monkeypatch: MonkeyPatch) -> Settings:
    monkeypatch.setenv("APP_OUTPUT_DIR", str(output_dir))
    get_settings.cache_clear()
    return Settings(output_dir=output_dir)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: settings
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()
