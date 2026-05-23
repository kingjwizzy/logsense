# src/storage/repository.py
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from src.parsers.base import LogEntry


class RepositoryError(Exception):
    """Raised when a database operation fails unexpectedly."""


class LogRepository:
    """
    All database operations for log entries.

    The only class in the project that writes SQL.
    Everything else works through this interface.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        """
        Args:
            conn: An open SQLite connection from get_connection().
                  Injected so tests can pass in an in-memory connection.
        """
        self._conn = conn

    def save(self, entry: LogEntry) -> LogEntry:
        """
        Insert one LogEntry into the database.

        Args:
            entry: A parsed LogEntry to persist.

        Returns:
            The same entry with its id field populated.

        Raises:
            RepositoryError: If the database operation fails.
        """
        try:
            cursor = self._conn.execute(
                """
                INSERT INTO logs (
                    timestamp, level, source_ip, method, path,
                    status_code, response_size, message, parser_type, raw
                ) VALUES (
                    :timestamp, :level, :source_ip, :method, :path,
                    :status_code, :response_size, :message, :parser_type, :raw
                )
                """,
                {
                    "timestamp":     entry.timestamp.isoformat(),
                    "level":         entry.level,
                    "source_ip":     entry.source_ip,
                    "method":        entry.method,
                    "path":          entry.path,
                    "status_code":   entry.status_code,
                    "response_size": entry.response_size,
                    "message":       entry.message,
                    "parser_type":   entry.parser_type,
                    "raw":           entry.raw,
                },
            )
            self._conn.commit()
            entry.id = cursor.lastrowid
            return entry
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to save entry: {e}") from e

    def save_many(self, entries: list[LogEntry]) -> int:
        """
        Insert a list of LogEntry objects in a single transaction.

        Faster than calling save() in a loop because one commit
        covers all inserts instead of one commit per insert.

        Args:
            entries: List of parsed LogEntry objects to persist.

        Returns:
            Number of entries successfully saved.
        """
        params = [
            {
                "timestamp":     e.timestamp.isoformat(),
                "level":         e.level,
                "source_ip":     e.source_ip,
                "method":        e.method,
                "path":          e.path,
                "status_code":   e.status_code,
                "response_size": e.response_size,
                "message":       e.message,
                "parser_type":   e.parser_type,
                "raw":           e.raw,
            }
            for e in entries
        ]
        self._conn.executemany(
            """
            INSERT INTO logs (
                timestamp, level, source_ip, method, path,
                status_code, response_size, message, parser_type, raw
            ) VALUES (
                :timestamp, :level, :source_ip, :method, :path,
                :status_code, :response_size, :message, :parser_type, :raw
            )
            """,
            params,
        )
        self._conn.commit()
        return len(entries)

    def find(
        self,
        level: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        source_ip: Optional[str] = None,
        status_code: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LogEntry]:
        """
        Query log entries with optional filters.

        All filters are optional and combinable.
        Results are ordered newest first.

        Args:
            level:       Filter by log level e.g. 'ERROR'
            since:       Only entries at or after this datetime
            until:       Only entries at or before this datetime
            source_ip:   Filter by exact IP address
            status_code: Filter by HTTP status code
            limit:       Max entries to return (default 100)
            offset:      Skip this many entries for pagination

        Returns:
            List of matching LogEntry objects, newest first.

        Raises:
            RepositoryError: If the database operation fails.
        """
        query = "SELECT * FROM logs WHERE 1=1"
        params: dict = {}

        if level:
            query += " AND level = :level"
            params["level"] = level.upper()

        if since:
            query += " AND timestamp >= :since"
            params["since"] = since.isoformat()

        if until:
            query += " AND timestamp <= :until"
            params["until"] = until.isoformat()

        if source_ip:
            query += " AND source_ip = :source_ip"
            params["source_ip"] = source_ip

        if status_code:
            query += " AND status_code = :status_code"
            params["status_code"] = status_code

        query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        try:
            rows = self._conn.execute(query, params).fetchall()
            return [self._row_to_entry(row) for row in rows]
        except sqlite3.Error as e:
            raise RepositoryError(f"Failed to query entries: {e}") from e

    def get_by_id(self, entry_id: int) -> Optional[LogEntry]:
        """
        Fetch a single log entry by its database ID.

        Args:
            entry_id: The auto-assigned integer ID of the entry.

        Returns:
            The matching LogEntry, or None if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM logs WHERE id = :id",
            {"id": entry_id},
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def delete_by_id(self, entry_id: int) -> bool:
        """
        Delete a single log entry by its database ID.

        Args:
            entry_id: The ID of the entry to delete.

        Returns:
            True if a row was deleted, False if the ID didn't exist.
        """
        cursor = self._conn.execute(
            "DELETE FROM logs WHERE id = :id",
            {"id": entry_id},
        )
        self._conn.commit()
        # rowcount tells us how many rows were affected
        return cursor.rowcount > 0

    def count(
        self,
        level: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> int:
        """
        Count entries matching optional filters.

        Useful for the API to report totals without fetching all rows.

        Args:
            level: Filter by log level
            since: Only entries at or after this datetime
            until: Only entries at or before this datetime

        Returns:
            Integer count of matching entries.
        """
        query = "SELECT COUNT(*) FROM logs WHERE 1=1"
        params: dict = {}

        if level:
            query += " AND level = :level"
            params["level"] = level.upper()

        if since:
            query += " AND timestamp >= :since"
            params["since"] = since.isoformat()

        if until:
            query += " AND timestamp <= :until"
            params["until"] = until.isoformat()

        row = self._conn.execute(query, params).fetchone()
        return row[0] if row else 0

    def _row_to_entry(self, row: sqlite3.Row) -> LogEntry:
        """
        Convert a raw SQLite row into a LogEntry object.

        Private method — only used internally by find() and get_by_id().
        sqlite3.Row lets us access columns by name e.g. row['level'].

        Args:
            row: A sqlite3.Row returned from a SELECT query.

        Returns:
            A fully populated LogEntry.
        """
        return LogEntry(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            level=row["level"],
            source_ip=row["source_ip"],
            method=row["method"],
            path=row["path"],
            status_code=row["status_code"],
            response_size=row["response_size"],
            message=row["message"],
            parser_type=row["parser_type"],
            raw=row["raw"],
        )