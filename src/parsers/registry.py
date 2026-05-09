from __future__ import annotations

from pathlib import Path
from typing import Optional

from .apache import ApacheParser
from .base import Parser
from .json_log import JsonLogParser
from .nginx import NginxParser
from .plaintext import PlainTextParser

# Single instances - parsers are stateless so one instance per format is enough
_PARSERS: dict[str, Parser] = {
    "apache":    ApacheParser(),
    "nginx":     NginxParser(),
    "plaintext": PlainTextParser(),
    "json":      JsonLogParser(),
}

# Map file extensions to parser names
# A file ending in .json uses the json parser etc.
_EXTENSION_MAP: dict[str, str] = {
    ".log":  "plaintext",
    ".txt":  "plaintext",
    ".json": "json",
}


def get_parser(fmt: str) -> Parser:
    """
    Return the parser for a given format name.
    
    Args:
        fmt: One of 'apache', 'nginx', 'plaintext', 'json'
    
    Raises:
        ValueError if the format name is not recognised.
    """
    parser = _PARSERS.get(fmt)
    if parser is None:
        raise ValueError(f"Unknown format '{fmt}'. choices: {list(_PARSERS)}")
    return parser


def detect_format(path: str) -> str:
    """
    Guess the parser format from a file extension.
    
    Falls back to 'plaintext' when the extension is unrecognised
    since plain text is the most broadly compatible parser.
    """
    ext = Path(path).suffix.lower()
    return _EXTENSION_MAP.get(ext, "plaintext")


def available_formats() -> list[str]:
    """Return all registered format names."""
    return list(_PARSERS)


