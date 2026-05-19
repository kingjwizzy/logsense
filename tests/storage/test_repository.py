# tests/storage/test_repository.py
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from src.parsers.base import LogEntry
from src.storage.database import get_connection, init_db
from src.storage.repository import LogRepository


def make_entry(
    message: str = "Test message",
    level: str = "INFO",
    parser_type: str = "plaintext",
    source_ip: str = None,
    status_code: int = None,
    method: str = None,
    path: str = None,
) -> LogEntry:
    """
    Helper that builds a minimal LogEntry for tests.
    Only override the fields your test cares about.
    """
    return LogEntry(
        timestamp=datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
        level=level,
        message=message,
        parser_type=parser_type,
        raw=f"raw {message}",
        source_ip=source_ip,
        status_code=status_code,
        method=method,
        path=path,
    )


@pytest.fixture
def repo() -> LogRepository:
    """
    Fresh in-memory repository for each test.
    No files created on disk, no cleanup needed.
    """
    conn = get_connection(":memory:")
    init_db(conn)
    return LogRepository(conn)

# ── save() ────────────────────────────────────────────────────────────────────

def test_save_returns_entry_with_id(repo: LogRepository) -> None:
    entry = make_entry()
    saved = repo.save(entry)
    assert saved.id is not None
    assert saved.id > 0


def test_save_persists_entry(repo: LogRepository) -> None:
    entry = make_entry(message="Hello database")
    saved = repo.save(entry)
    fetched = repo.get_by_id(saved.id)
    assert fetched is not None
    assert fetched.message == "Hello database"


# ── save_many() ───────────────────────────────────────────────────────────────

def test_save_many_returns_count(repo: LogRepository) -> None:
    entries = [make_entry(message=f"entry {i}") for i in range(5)]
    count = repo.save_many(entries)
    assert count == 5


def test_save_many_persists_all(repo: LogRepository) -> None:
    entries = [make_entry(message=f"entry {i}") for i in range(3)]
    repo.save_many(entries)
    results = repo.find()
    assert len(results) == 3


# ── find() ────────────────────────────────────────────────────────────────────

def test_find_returns_all_when_no_filters(repo: LogRepository) -> None:
    repo.save_many([make_entry() for _ in range(4)])
    results = repo.find()
    assert len(results) == 4


def test_find_filters_by_level(repo: LogRepository) -> None:
    repo.save(make_entry(level="ERROR"))
    repo.save(make_entry(level="INFO"))
    repo.save(make_entry(level="ERROR"))
    results = repo.find(level="ERROR")
    assert len(results) == 2
    assert all(r.level == "ERROR" for r in results)


def test_find_filters_by_source_ip(repo: LogRepository) -> None:
    repo.save(make_entry(source_ip="192.168.1.1"))
    repo.save(make_entry(source_ip="10.0.0.1"))
    results = repo.find(source_ip="192.168.1.1")
    assert len(results) == 1
    assert results[0].source_ip == "192.168.1.1"


def test_find_respects_limit(repo: LogRepository) -> None:
    repo.save_many([make_entry() for _ in range(10)])
    results = repo.find(limit=3)
    assert len(results) == 3


def test_find_respects_offset(repo: LogRepository) -> None:
    repo.save_many([make_entry(message=f"entry {i}") for i in range(5)])
    page1 = repo.find(limit=2, offset=0)
    page2 = repo.find(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    # Pages should contain different entries
    assert page1[0].message != page2[0].message


# ── get_by_id() ───────────────────────────────────────────────────────────────

def test_get_by_id_returns_entry(repo: LogRepository) -> None:
    saved = repo.save(make_entry(message="find me"))
    fetched = repo.get_by_id(saved.id)
    assert fetched is not None
    assert fetched.message == "find me"


def test_get_by_id_returns_none_for_missing(repo: LogRepository) -> None:
    result = repo.get_by_id(99999)
    assert result is None


# ── delete_by_id() ────────────────────────────────────────────────────────────

def test_delete_by_id_removes_entry(repo: LogRepository) -> None:
    saved = repo.save(make_entry())
    deleted = repo.delete_by_id(saved.id)
    assert deleted is True
    assert repo.get_by_id(saved.id) is None


def test_delete_by_id_returns_false_for_missing(repo: LogRepository) -> None:
    result = repo.delete_by_id(99999)
    assert result is False


# ── count() ───────────────────────────────────────────────────────────────────

def test_count_returns_total(repo: LogRepository) -> None:
    repo.save_many([make_entry() for _ in range(6)])
    assert repo.count() == 6


def test_count_filters_by_level(repo: LogRepository) -> None:
    repo.save(make_entry(level="ERROR"))
    repo.save(make_entry(level="ERROR"))
    repo.save(make_entry(level="INFO"))
    assert repo.count(level="ERROR") == 2