# src/api/deps.py
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from src.storage.database import get_connection, init_db
from src.storage.repository import LogRepository


def get_db_path() -> str:
    """
    Return the database path from environment or use the default.

    Separated into its own function so tests can override it easily
    by overriding this dependency.
    """
    import os
    return os.getenv("DATABASE_PATH", "data/logsense.db")


def get_repository(db_path: str = Depends(get_db_path)) -> LogRepository:
    """
    FastAPI dependency that provides a ready LogRepository.

    FastAPI calls this automatically for any route that declares
    repo: LogRepository = Depends(get_repository) as a parameter.

    Args:
        db_path: Injected by FastAPI from get_db_path().

    Returns:
        A LogRepository connected to the configured database.
    """
    conn = get_connection(db_path)
    init_db(conn)
    return LogRepository(conn)