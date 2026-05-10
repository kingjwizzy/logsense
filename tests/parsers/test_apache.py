from __future__ import annotations

import pytest
from src.parsers.apache import ApacheParser

# Real Apache Combined log lines used as test inputs
# Defined at module level so every test function can use them without repetition
VALID_LINE = (
    '192.168.1.1 - frank [01/May/2026:10:23:45 +0000] '
    '"GET /api/users HTTP/1.1" 200 1234'
)
VALID_LINE_500 = (
    '192.168.1.1 - - [01/May/2026:10:23:45 +0000] '
    '"POST /api/login HTTP/1.1" 500 512'
)
INVALID_LINE = "this is not a log line at all"


@pytest.fixture
def parser() -> ApacheParser:
    """A fresh ApacheParser instance injected into each test that requests it."""
    return ApacheParser()


def test_parser_name(parser: ApacheParser) -> None:
    """Parser identifies itself correctly via the name property."""
    assert parser.name == "apache"


def test_valid_line_returns_entry(parser: ApacheParser) -> None:
    """A valid Apache line produces a LogEntry and never returns None."""
    result = parser.parse(VALID_LINE)
    assert result is not None


def test_parses_apache_fields(parser: ApacheParser) -> None:
    """All fields are correctly extracted from a valid Apache line."""
    result = parser.parse(VALID_LINE)
    assert result is not None
    assert result.source_ip == "192.168.1.1"
    assert result.method == "GET"
    assert result.path == "/api/users"
    assert result.status_code == 200
    assert result.response_size == 1234
    assert result.parser_type == "apache"


@pytest.mark.parametrize(
    ("line", "expected_level"),
    [
        (VALID_LINE, "INFO"),        # 200 response should map to INFO
        (VALID_LINE_500, "ERROR"),   # 500 response should map to ERROR
    ],
)
def test_maps_status_code_to_level(
    parser: ApacheParser,
    line: str,
    expected_level: str,
) -> None:
    """HTTP status codes are correctly mapped to log levels."""
    result = parser.parse(line)
    assert result is not None
    assert result.level == expected_level


def test_invalid_line_returns_none(parser: ApacheParser) -> None:
    """A line that doesn't match Apache format returns None without crashing."""
    result = parser.parse(INVALID_LINE)
    assert result is None