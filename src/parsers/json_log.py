from __future__ import annotations

import json
from datetime import datetime , timezone
from typing import Any,Optional

from .base import LogEntry,Parser


# Pino and Bunyan use integer levels instead of strings
# This maps their numbers to our canonical level names
_PINO_LEVELS: dict[int, str] = {
    10: "DEBUG",  # trace
    20: "DEBUG",
    30: "INFO",
    40: "WARN",
    50: "ERROR",
    60: "ERROR",  # fatal
}


def _extract_message(obj: dict) -> str:
    """
    Find the best message field in a JSON log object.
    
    Different libraries use different field names for the message:
    - Pino/Bunyan use 'msg'
    - structlog uses 'event'
    - others use 'message'
    Falls back to the entire JSON object as a string if nothing found.
    """
    for key in ("msg", "event", "message", "text"):
        val = obj.get(key)
        if isinstance(val, str) and val:
            return val
    return json.dumps(obj)


def _extract_level(obj: dict) -> str:
    """
    Find and normalise the level from a JSON log object.
    
    Handles both string levels ('info', 'ERROR') and
    Pino/Bunyan integer levels (30 = INFO, 50 = ERROR).
    """
    raw = obj.get("level") or obj.get("severity")
    if raw is None:
        return "UNKNOWN"
    # Pino and Bunyan use integers
    if isinstance(raw, int):
        return _PINO_LEVELS.get(raw, "UNKNOWN")
    # String level - normalise to uppercase
    normalised = str(raw).upper().strip()
    mapping = {"WARNING": "WARN", "CRITICAL": "ERROR", "FATAL": "ERROR"}
    return mapping.get(normalised, normalised)


def _extract_timestamp(obj: dict) -> Optional[datetime]:
    """
    Find and parse a timestamp from a JSON log object.
    
    Tries common field names in order of preference.
    Handles both ISO 8601 strings and millisecond epoch integers (Pino default).
    """
    for key in ("timestamp", "time", "@timestamp", "date"):
        val = obj.get(key)
        if val is None:
            continue
        # Pino logs time as milliseconds since epoch e.g. 1714556625000
        if isinstance(val, (int, float)):
            try:
                return datetime.fromtimestamp(val / 1000, tz=timezone.utc)
            except (OSError, ValueError):
                continue
        # String timestamp - try common ISO 8601 formats
        if isinstance(val, str):
            for fmt in (
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
            ):
                try:
                    dt = datetime.strptime(val, fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
    return None


class JsonLogParser(Parser):
    """
    Parser for structured JSON logs.
    
    Supports structlog (Python), Pino (Node.js), Bunyan (Node.js),
    and any logger that outputs one JSON object per line with a
    recognisable timestamp field.
    """

    @property
    def name(self) -> str:
        return "json"

    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse one JSON log line. Returns None if not valid JSON or no timestamp."""
        line = line.rstrip("\n\r").strip()

        # Quick check before attempting full JSON parse - saves time on non-JSON lines
        if not line or not line.startswith("{"):
            return None

        try:
            obj: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError:
            # Invalid JSON - skip silently, never crash
            return None

        if not isinstance(obj, dict):
            # Valid JSON but not an object e.g. a bare array or string - skip
            return None

        # Timestamp is required - without it we can't place the event in time
        timestamp = _extract_timestamp(obj)
        if timestamp is None:
            return None

        return LogEntry(
            timestamp=timestamp,
            level=_extract_level(obj),
            source_ip=obj.get("ip") or obj.get("remote_ip"),
            method=(obj.get("method") or "").upper() or None,
            path=obj.get("path") or obj.get("url"),
            status_code=obj.get("status") or obj.get("status_code"),
            response_size=obj.get("response_size") or obj.get("bytes"),
            message=_extract_message(obj),
            parser_type=self.name,
            raw=line,
        )