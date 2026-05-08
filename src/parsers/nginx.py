from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from .apache import _infer_level, _parse_time
from .base import LogEntry, Parser


# Nginx default combined log format
# Similar to Apache but size is always a number and referer/UA are always present
_NGINX_RE = re.compile(
    r'(?P<ip>\S+)'            # client IP
    r' - \S+'                 # - remote_user, always "-", ignored
    r' \[(?P<time>[^\]]+)\]'  # [timestamp] - everything inside brackets
    r' "(?P<request>[^"]*)"'  # full request string e.g. "GET /path HTTP/1.1"
    r' (?P<status>\d{3})'     # status code - exactly 3 digits
    r' (?P<size>\d+)'         # response size - Nginx always logs a number, never "-"
    r'(?:\s.*)?$'             # referer and user agent - present but not useful to us
)


def _parse_request(request: str) -> tuple[Optional[str], Optional[str]]:
    """
    Split 'GET /path HTTP/1.1' into (method, path).
    
    Nginx captures the entire request as one string unlike Apache which
    captures method and path separately. Returns (None, None) if malformed.
    """
    parts = request.split(" ", 2)
    if len(parts) >= 2:
        return parts[0].upper(), parts[1]
    return None, None


class NginxParser(Parser):
    """Parser for Nginx default combined access log format."""

    @property
    def name(self) -> str:
        return "nginx"

    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse one Nginx access log line. Returns None if the line doesn't match."""
        line = line.rstrip("\n\r")

        match = _NGINX_RE.match(line)
        if not match:
            return None

        # Reuse Apache's time parser - both formats use identical timestamp structure
        timestamp = _parse_time(match.group("time"))
        if timestamp is None:
            return None

        status = int(match.group("status"))
        
        # Split the single request string into method and path
        method, path = _parse_request(match.group("request"))

        return LogEntry(
            timestamp=timestamp,
            level=_infer_level(status),  # Derived from status code, same as Apache
            source_ip=match.group("ip"),
            method=method,
            path=path,
            status_code=status,
            response_size=int(match.group("size")),
            # Fall back to raw request string if method parsing failed
            message=f"{method} {path} {status}" if method else match.group("request"),
            parser_type=self.name,
            raw=line,
        )