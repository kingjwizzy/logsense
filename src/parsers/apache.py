from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from .base import LogEntry,Parser


# Regex pattern describing the shape of an Apache Combined Log line
# Each (?P<name>...) captures a named piece we want to extract
_APACHE_RE = re.compile(
    r'(?P<ip>\S+)'            # client IP
    r' \S+ \S+'               # ident and auth user - always "-", ignored
    r' \[(?P<time>[^\]]+)\]'  # [timestamp] - capture everything inside brackets
    r' "(?P<method>\S+)'      # "METHOD
    r' (?P<path>\S+)'         # /path
    r' \S+"'                  # HTTP/1.1"
    r' (?P<status>\d{3})'     # status code - exactly 3 digits
    r' (?P<size>\S+)'         # response size - can be "-" when zero
)

# Format string matching Apache's timestamp e.g. 01/May/2026:10:23:45
_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S"


def _parse_time(time_str: str) -> Optional[datetime]:
    """Convert Apache timestamp string to a UTC datetime. Returns None if unparseable."""
    # Apache time looks like: 01/May/2026:10:23:45 +0000
    # We split off the timezone offset before parsing the main part
    parts = time_str.rsplit(" ", 1)
    if len(parts) != 2:
        return None
    try:
        dt = datetime.strptime(parts[0], _TIME_FORMAT)
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _infer_level(status: int) -> str:
    """Map HTTP status code to a log level."""
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
        
        # Try to match the line against our pattern
        match = _APACHE_RE.match(line)
        if not match:
            return None

        # Parse the timestamp - if we can't, skip the line
        timestamp = _parse_time(match.group("time"))
        if timestamp is None:
            return None

        status = int(match.group("status"))
        method = match.group("method").upper()
        path = match.group("path")
        
        # Size can be "-" when Apache logs zero bytes
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