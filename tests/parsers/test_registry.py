from __future__ import annotations

import pytest
from src.parsers.apache import ApacheParser
from src.parsers.json_log import JsonLogParser
from src.parsers.nginx import NginxParser
from src.parsers.plaintext import PlainTextParser
from src.parsers.registry import available_formats, detect_format, get_parser


# ── get_parser() ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("fmt", "expected_type"),
    [
        ("apache",    ApacheParser),
        ("nginx",     NginxParser),
        ("plaintext", PlainTextParser),
        ("json",      JsonLogParser),
    ],
)
def test_get_parser_returns_correct_type(fmt: str, expected_type: type) -> None:
    assert isinstance(get_parser(fmt), expected_type)


def test_get_parser_raises_on_unknown_format() -> None:
    with pytest.raises(ValueError, match="Unknown format"):
        get_parser("does_not_exist")


# ── detect_format() ───────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("path", "expected_format"),
    [
        ("access.log",  "plaintext"),  # .log → plaintext
        ("notes.txt",   "plaintext"),  # .txt → plaintext
        ("events.json", "json"),       # .json → json
        ("data.xyz",    "plaintext"),  # unrecognised → plaintext fallback
    ],
)
def test_detect_format(path: str, expected_format: str) -> None:
    assert detect_format(path) == expected_format


# ── available_formats() ───────────────────────────────────────────────────────

def test_available_formats_contains_all_parsers() -> None:
    formats = available_formats()
    assert set(formats) >= {"apache", "nginx", "plaintext", "json"}