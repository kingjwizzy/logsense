from __future__ import annotations

from datetime import timezone

import pytest
from src.parsers.nginx import NginxParser

# Real Nginx combined log lines covering the main status code ranges
VALID_LINE = (
    '192.168.1.1 - - [01/May/2026:10:23:45 +0000] '
    '"GET /api/users HTTP/1.1" 200 1234 "-" "curl/7.68"'
)
VALID_LINE_404 = (
    '192.168.1.1 - - [01/May/2026:10:23:45 +0000] '
    '"GET /missing HTTP/1.1" 404 256 "-" "curl/7.68"'
)
VALID_LINE_500 = (
    '192.168.1.1 - - [01/May/2026:10:23:45 +0000] '
    '"POST /api/login HTTP/1.1" 500 512 "-" "curl/7.68"'
)
INVALID_LINE = "this is not a log line at all"


@pytest.fixture
def parser() -> NginxParser:
    """A fresh NginxParser instance injected into each test that requests it."""
    return NginxParser()


def test_parser_name(parser: NginxParser) -> None:
    """Parser identifies itself correctly via the name property."""
    assert parser.name == "nginx"


def test_valid_line_returns_entry(parser: NginxParser) -> None:
    """A valid Nginx line produces a LogEntry and never returns None."""
    result = parser.parse(VALID_LINE)
    assert result is not None


def test_parses_timestamp(parser: NginxParser) -> None:
    """Timestamp is parsed correctly and stored as UTC."""
    result = parser.parse(VALID_LINE)
    assert result is not None
    assert result.timestamp.year == 2026
    assert result.timestamp.month == 5
    assert result.timestamp.day == 1
    assert result.timestamp.hour == 10
    assert result.timestamp.tzinfo == timezone.utc


def test_parses_nginx_fields(parser: NginxParser) -> None:
    """All fields are correctly extracted from a valid Nginx line."""
    result = parser.parse(VALID_LINE)
    assert result is not None
    assert result.source_ip == "192.168.1.1"
    assert result.method == "GET"
    assert result.path == "/api/users"
    assert result.status_code == 200
    assert result.response_size == 1234
    assert result.parser_type == "nginx"


@pytest.mark.parametrize(
    ("line", "expected_level"),
    [
        (VALID_LINE, "INFO"),      # 2xx → INFO
        (VALID_LINE_404, "WARN"),  # 4xx → WARN
        (VALID_LINE_500, "ERROR"), # 5xx → ERROR
    ],
)
def test_maps_status_code_to_level(
    parser: NginxParser,
    line: str,
    expected_level: str,
) -> None:
    """HTTP status codes are correctly mapped to log levels."""
    result = parser.parse(line)
    assert result is not None
    assert result.level == expected_level


def test_invalid_line_returns_none(parser: NginxParser) -> None:
    """A line that doesn't match Nginx format returns None without crashing."""
    result = parser.parse(INVALID_LINE)
    assert result is None