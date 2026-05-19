from __future__ import annotations

import sqlite3
from pathlib import Path


# SQL to create the logs table.
# IF NOT EXISTS makes this safe to run on every startup.
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

# Indexes on the columns we filter and sort by most often.
# Without these, every query does a full table scan.
_CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_logs_timestamp   ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_level       ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_source_ip   ON logs(source_ip);
CREATE INDEX IF NOT EXISTS idx_logs_status_code ON logs(status_code);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Open a SQLite connection to db_path.

    Creates parent directories if they don't exist.
    Sets row_factory so rows behave like dicts (row["level"] not row[1]).
    Enables WAL mode for better concurrent read performance.

    Args:
        db_path: File path e.g. 'data/logsense.db', or ':memory:' for tests.

    Returns:
        An open sqlite3.Connection ready to use.
    """
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # WAL mode allows concurrent reads during writes - better for API + CLI use
    conn.execute("PRAGMA journal_mode=WAL;")

    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """
    Create the logs table and indexes if they don't already exist.

    Safe to call on every startup — all statements use IF NOT EXISTS.

    Args:
        conn: An open SQLite connection, typically from get_connection().
    """
    # Run table creation and indexes in one script
    conn.executescript(_CREATE_TABLE + _CREATE_INDEXES)
    conn.commit()