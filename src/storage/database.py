# src/storage/database.py
"""SQLite connection factory and schema bootstrap.

Responsible for two things only:
- Opening a connection with the right settings (row_factory, WAL mode).
- Creating the logs table and indexes idempotently on first run.

No SQL that belongs to business logic lives here — that's repository.py's job.
"""

import sqlite3
from pathlib import Path


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT NOT NULL,
    level         TEXT NOT NULL,
    source_ip     TEXT,
    method        TEXT,
    path          TEXT,
    status_code   INTEGER,
    response_size INTEGER,
    message       TEXT NOT NULL,
    parser_type   TEXT NOT NULL,
    raw           TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_logs_timestamp   ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_level       ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_source_ip   ON logs(source_ip);
CREATE INDEX IF NOT EXISTS idx_logs_status_code ON logs(status_code);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection to db_path.

    Creates parent directories if they don't exist.
    Sets row_factory so rows behave like dicts.
    Enables WAL mode for better concurrent read performance.

    Args:
        db_path: File path, or ':memory:' for an in-memory database.

    Returns:
        An open sqlite3.Connection.
    """
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create the logs table and indexes if they don't already exist.

    Safe to call on every startup — all statements use IF NOT EXISTS.

    Args:
        conn: An open SQLite connection, typically from get_connection().
    """
    conn.executescript(_CREATE_TABLE + _CREATE_INDEXES)
    conn.commit()