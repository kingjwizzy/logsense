from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from abc import ABC, abstractmethod


@dataclass
class LogEntry:
    """A single parsed log record. The shared data shape across all layers."""

    # --- Always present ---
    timestamp: datetime          # UTC strongly preferred
    level: str                   # Normalised in __post_init__ to INFO/WARN/ERROR/DEBUG/UNKNOWN
    message: str                 # Human readable event description
    parser_type: str             # Which parser produced this: apache|nginx|plaintext|json
    raw: str                     # Original unmodified line, kept for debugging

    # --- Present only in web server logs ---
    source_ip: Optional[str] = None
    method: Optional[str] = None        # GET, POST, PUT etc.
    path: Optional[str] = None          # e.g. /api/users
    status_code: Optional[int] = None   # e.g. 200, 404, 500
    response_size: Optional[int] = None # Response body size in bytes

    # --- Set by the database after persistence ---
    id: Optional[int] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Normalise level on creation so the rest of the system never sees raw values."""
        level = self.level.upper().strip()
        if level == "WARNING":
            level = "WARN"
        valid = {"INFO", "WARN", "ERROR", "DEBUG", "UNKNOWN"}
        self.level = level if level in valid else "UNKNOWN"


class Parser(ABC):
    """
    Blueprint that every log format parser must follow.

    New formats are added by subclassing Parser and implementing
    both abstract members. The rest of the system never imports
    a specific parser directly - it works through this interface.
    """

    @abstractmethod
    def parse(self, line: str) -> Optional[LogEntry]:
        """
        Parse one raw log line.

        Returns a LogEntry on success, or None if the line
        does not match this format. Never raises an exception.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short format identifier e.g. 'apache', 'nginx'."""