from __future__ import annotations

from datetime import timezone

import pytest
from src.parsers.json_log import JsonLogParser

# structlog/generic style - one JSON object per line
VALID_LINE = '{"timestamp": "2026-05-01T10:23:45Z", "level": "info", "message": "Server started"}'
VALID_LINE_ERROR = '{"timestamp": "2026-05-01T10:23:45Z", "level": "error", "message": "DB failed"}'

# Pino style - integer level, millisecond epoch timestamp, "msg" field
VALID_LINE_PINO = '{"time": 1746093825000, "level": 30, "msg": "Request received"}'

# Invalid inputs
INVALID_LINE = "this is not json at all"
INVALID_NO_TIMESTAMP = '{"level": "info", "message": "no timestamp here"}'


@pytest.fixture
def parser() -> JsonLogParser:
    return JsonLogParser()


def test_parser_name(parser: JsonLogParser) -> None:
    assert parser.name == "json"


def test_valid_line_returns_entry(parser: JsonLogParser) -> None:
    result = parser.parse(VALID_LINE)
    assert result is not None


def test_parses_timestamp(parser: JsonLogParser) -> None:
    result = parser.parse(VALID_LINE)
    assert result is not None
    assert result.timestamp.year == 2026
    assert result.timestamp.month == 5
    assert result.timestamp.day == 1
    assert result.timestamp.hour == 10
    assert result.timestamp.minute == 23
    assert result.timestamp.second == 45
    assert result.timestamp.tzinfo == timezone.utc


def test_parses_json_fields(parser: JsonLogParser) -> None:
    result = parser.parse(VALID_LINE)
    assert result is not None
    assert result.level == "INFO"
    assert result.message == "Server started"
    assert result.parser_type == "json"
    assert result.raw == VALID_LINE
    assert result.source_ip is None
    assert result.method is None
    assert result.path is None
    assert result.status_code is None
    assert result.response_size is None


@pytest.mark.parametrize(
    ("line", "expected_level"),
    [
        (VALID_LINE, "INFO"),        # string "info" → INFO
        (VALID_LINE_ERROR, "ERROR"), # string "error" → ERROR
        (VALID_LINE_PINO, "INFO"),   # Pino integer 30 → INFO
    ],
)
def test_level_normalisation(
    parser: JsonLogParser,
    line: str,
    expected_level: str,
) -> None:
    result = parser.parse(line)
    assert result is not None
    assert result.level == expected_level


def test_pino_msg_field_becomes_message(parser: JsonLogParser) -> None:
    # Pino uses "msg" instead of "message" - verify we handle both
    result = parser.parse(VALID_LINE_PINO)
    assert result is not None
    assert result.message == "Request received"


def test_pino_epoch_timestamp(parser: JsonLogParser) -> None:
    # Pino logs time as milliseconds since epoch - verify correct conversion
    result = parser.parse(VALID_LINE_PINO)
    assert result is not None
    assert result.timestamp.tzinfo == timezone.utc
    assert result.timestamp.year == 2025


def test_missing_timestamp_returns_none(parser: JsonLogParser) -> None:
    result = parser.parse(INVALID_NO_TIMESTAMP)
    assert result is None


def test_invalid_json_returns_none(parser: JsonLogParser) -> None:
    result = parser.parse(INVALID_LINE)
    assert result is None