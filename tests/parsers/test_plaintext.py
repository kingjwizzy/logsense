from __future__ import annotations

from datetime import timezone

import pytest
from src.parsers.plaintext import PlainTextParser

VALID_LINE = "2026-05-01 10:23:45 INFO Server started on port 8000"
VALID_LINE_WARN = "2026-05-01 10:23:45 WARNING Disk usage at 85%"
VALID_LINE_ERROR = "2026-05-01T10:23:45Z ERROR Database connection failed"
INVALID_LINE = "no timestamp here just some random text"


@pytest.fixture
def parser() -> PlainTextParser:
    return PlainTextParser()


def test_parser_name(parser: PlainTextParser) -> None:
    assert parser.name == "plaintext"


def test_valid_line_returns_entry(parser: PlainTextParser) -> None:
    result = parser.parse(VALID_LINE)
    assert result is not None


def test_parses_timestamp(parser: PlainTextParser) -> None:
    result = parser.parse(VALID_LINE)
    assert result is not None
    assert result.timestamp.year == 2026
    assert result.timestamp.month == 5
    assert result.timestamp.day == 1
    assert result.timestamp.hour == 10
    assert result.timestamp.minute == 23
    assert result.timestamp.second == 45
    assert result.timestamp.tzinfo == timezone.utc


def test_parses_plaintext_fields(parser: PlainTextParser) -> None:
    result = parser.parse(VALID_LINE)
    assert result is not None
    assert result.level == "INFO"
    assert result.message == "Server started on port 8000"
    assert result.parser_type == "plaintext"
    assert result.raw == VALID_LINE
    assert result.source_ip is None
    assert result.method is None
    assert result.path is None
    assert result.status_code is None
    assert result.response_size is None


@pytest.mark.parametrize(
    ("line", "expected_level", "expected_message"),
    [
        (VALID_LINE,       "INFO",  "Server started on port 8000"),
        (VALID_LINE_WARN,  "WARN",  "Disk usage at 85%"),
        (VALID_LINE_ERROR, "ERROR", "Database connection failed"),
    ],
)
def test_maps_plaintext_levels(
    parser: PlainTextParser,
    line: str,
    expected_level: str,
    expected_message: str,
) -> None:
    result = parser.parse(line)
    assert result is not None
    assert result.level == expected_level
    assert result.message == expected_message


def test_invalid_line_returns_none(parser: PlainTextParser) -> None:
    result = parser.parse(INVALID_LINE)
    assert result is None