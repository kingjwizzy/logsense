from __future__ import annotations 

import re 
from datetime import datetime, timezone
from typing import Optional

from .base import LogEntry,Parser

# Multiple timestamp patterns ordered most-specific first
# Try each one in order and stop at the first match
_TS_PATTERNS: list[tuple[re.Pattern, str]] = [
    # ISO 8601 with Z e.g. 2026-05-01T10:23:45Z
    (re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z"), "%Y-%m-%dT%H:%M:%S"),
    # ISO 8601 no T e.g. 2026-05-01 10:23:45
    (re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"), "%Y-%m-%d %H:%M:%S"),
    # Slash date e.g. 2026/05/01 10:23:45
    (re.compile(r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})"), "%Y/%m/%d %H:%M:%S"),
    # Syslog style e.g. May  1 10:23:45
    (re.compile(r"([A-Za-z]{3}\s+\d{1,2} \d{2}:\d{2}:\d{2})"), "%b %d %H:%M:%S"),
]

# Matches level words wherever they appear in the line
_LEVEL_RE = re.compile(
    r"\b(DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|CRITICAL|FATAL)\b",
    re.IGNORECASE  # Match regardless of case e.g. "info", "INFO", "Info"
)

# Maps non-standard level words to our canonical set
_LEVEL_MAP = {
    "NOTICE": "INFO",
    "WARNING": "WARN",
    "CRITICAL": "ERROR",
    "FATAL": "ERROR",
}


def _extract_timestamp(line: str) -> tuple[Optional[datetime], int]:
    """
    Find and parse a timestamp anywhere in the line.
    
    Returns (datetime, end_index) where end_index is the position
    in the line immediately after the timestamp match. The caller
    uses end_index to know where the remainder of the line starts.
    Returns (None, 0) if no pattern matched.
    """
    for pattern, fmt in _TS_PATTERNS:
        match = pattern.search(line)
        if match:
            try:
                dt = datetime.strptime(match.group(1), fmt)
                # Treat all parsed times as UTC
                return dt.replace(tzinfo=timezone.utc), match.end()
            except ValueError:
                # Pattern matched but time was invalid e.g. month 13 - try next
                continue
    return None, 0

def _extract_level(text: str) -> tuple[str, str]:
    """
    Find and extract a level word from text.

    Returns (level, remainder) where remainder is the text with
    the level word removed - what's left becomes the message.
    Returns ("UNKNOWN", original_text) if no level word found.
    """
    match = _LEVEL_RE.search(text)
    if not match:
        # No recognisable level word - label it UNKNOWN and use full text as message
        return "UNKNOWN", text.strip()

    # Pull out the matched word and normalise it via the map
    raw_level = match.group(1).upper()
    level = _LEVEL_MAP.get(raw_level, raw_level)

    # Remove the level word from the text to leave just the message
    remainder = (text[:match.start()] + text[match.end():]).strip()
    return level, remainder



class PlainTextParser(Parser):
    """
    Parser for plain text logs with a recognisable timestamp and optional level.
    
    Deliberately broad to handle the variety of real application logs.
    Requires at least a parseable timestamp - lines without one are skipped.
    """

    @property
    def name(self) -> str:
        return "plaintext"

    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse one plain text log line. Returns None if no timestamp found."""
        line = line.rstrip("\n\r")
        if not line.strip():
            # Skip blank lines silently
            return None

        # Step 1 - find the timestamp and where it ends in the line
        timestamp, ts_end = _extract_timestamp(line)
        if timestamp is None:
            # No recognisable timestamp - we can't make a valid entry
            return None

        # Step 2 - everything after the timestamp is the remainder
        remainder = line[ts_end:].strip(" :-|[]")

        # Step 3 - find and extract the level from the remainder
        level, message = _extract_level(remainder)

        # Step 4 - clean up the message or fall back to the full line
        message = message.strip(" :-|") or line

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            parser_type=self.name,
            raw=line,
        )
    
    