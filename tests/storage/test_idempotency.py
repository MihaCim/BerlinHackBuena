from __future__ import annotations

from pathlib import Path

from app.storage.idempotency import open_idempotency


def test_claim_first_time_returns_true(tmp_path: Path) -> None:
    store = open_idempotency(tmp_path / "idem.duckdb")
    assert store.claim("evt-1") is True


def test_claim_second_time_returns_false(tmp_path: Path) -> None:
    store = open_idempotency(tmp_path / "idem.duckdb")
    assert store.claim("evt-1") is True
    assert store.claim("evt-1") is False


def test_status_lifecycle(tmp_path: Path) -> None:
    store = open_idempotency(tmp_path / "idem.duckdb")
    assert store.status("evt-2") is None
    store.claim("evt-2")
    assert store.status("evt-2") == "pending"
    store.mark_done("evt-2")
    assert store.status("evt-2") == "done"


def test_mark_failed(tmp_path: Path) -> None:
    store = open_idempotency(tmp_path / "idem.duckdb")
    store.claim("evt-3")
    store.mark_failed("evt-3")
    assert store.status("evt-3") == "failed"


def test_failed_event_can_be_reclaimed(tmp_path: Path) -> None:
    store = open_idempotency(tmp_path / "idem.duckdb")
    assert store.claim("evt-4") is True
    store.mark_failed("evt-4")
    assert store.claim("evt-4") is True
    assert store.status("evt-4") == "pending"


def test_done_event_cannot_be_reclaimed(tmp_path: Path) -> None:
    store = open_idempotency(tmp_path / "idem.duckdb")
    store.claim("evt-5")
    store.mark_done("evt-5")
    assert store.claim("evt-5") is False
