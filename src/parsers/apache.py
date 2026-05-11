from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from .base import LogEntry, Parser

# Matches a full Apache Combined Log Format line
# Each (?P<name>...) is a named capture group we retrieve after matching
_APACHE_RE = re.compile(
    r'(?P<ip>\S+)'            # client IP e.g. 192.168.1.1
    r' \S+ \S+'               # ident + auth user, always "-", ignored
    r' \[(?P<time>[^\]]+)\]'  # timestamp inside brackets
    r' "(?P<method>\S+)'      # HTTP method e.g. GET
    r' (?P<path>\S+)'         # request path e.g. /api/users
    r' \S+"'                  # protocol e.g. HTTP/1.1
    r' (?P<status>\d{3})'     # status code, exactly 3 digits
    r' (?P<size>\S+)'         # response size, can be "-" when zero
)

# Apache timestamp format: 01/May/2026:10:23:45
_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S"


def _parse_time(time_str: str) -> Optional[datetime]:
    """
    Convert an Apache timestamp string to a UTC datetime.

    Apache format: '01/May/2026:10:23:45 +0000'
    We strip the timezone offset before parsing since strptime
    doesn't handle the Apache +0000 format directly.
    """
    parts = time_str.rsplit(" ", 1)
    if len(parts) != 2:
        return None
    try:
        dt = datetime.strptime(parts[0], _TIME_FORMAT)
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _infer_level(status: int) -> str:
    """Derive a log level from an HTTP status code."""
    if status >= 500:
        return "ERROR"
    if status >= 400:
        return "WARN"
    return "INFO"


class ApacheParser(Parser):
    """Parser for Apache Combined Log Format."""

    @property
    def name(self) -> str:
        return "apache"

    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse one Apache log line. Returns None if the line doesn't match."""
        line = line.rstrip("\n\r")

        match = _APACHE_RE.match(line)
        if not match:
            return None

        timestamp = _parse_time(match.group("time"))
        if timestamp is None:
            return None

        status = int(match.group("status"))
        method = match.group("method").upper()
        path = match.group("path")

        # Apache logs "-" for response size when zero bytes were sent
        size_raw = match.group("size")
        response_size = int(size_raw) if size_raw.isdigit() else None

        return LogEntry(
            timestamp=timestamp,
            level=_infer_level(status),
            source_ip=match.group("ip"),
            method=method,
            path=path,
            status_code=status,
            response_size=response_size,
            message=f"{method} {path} {status}",
            parser_type=self.name,
            raw=line,
        )
    
    