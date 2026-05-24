# src/api/models.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LogEntryResponse(BaseModel):
    """
    API response shape for a single log entry.

    Pydantic validates and serialises LogEntry dataclass objects
    into this shape before they leave the API as JSON.
    """
    id: int
    timestamp: datetime
    level: str
    message: str
    parser_type: str
    source_ip: Optional[str] = None    # null for non-web-server logs
    method: Optional[str] = None       # HTTP verb e.g. GET, POST
    path: Optional[str] = None         # URL path e.g. /api/users
    status_code: Optional[int] = None  # HTTP status e.g. 200, 404, 500
    response_size: Optional[int] = None

    class Config:
        # Allows Pydantic to read from object attributes (e.g. entry.level)
        # not just from dictionaries. Required to convert LogEntry → JSON.
        from_attributes = True


class IngestRequest(BaseModel):
    """Request body for POST /logs."""

    # Required - the raw log text to parse
    text: str = Field(..., description="Raw log text to parse and store.")

    # Optional - if omitted, format is auto-detected from content
    format: Optional[str] = Field(
        default=None,
        description="Log format: apache, nginx, plaintext, json. Auto-detected if omitted."
    )


class IngestResponse(BaseModel):
    """Response body for POST /logs — summary of what was stored."""
    stored: int   # number of entries successfully parsed and saved
    skipped: int  # number of lines that couldn't be parsed


class ErrorDetail(BaseModel):
    """
    The inner error object containing machine and human readable info.

    code    — machine readable e.g. 'not_found', 'validation_error'
    message — human readable explanation
    details — optional extra context e.g. which field failed validation
    """
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    """
    Standard error envelope returned on all error responses.

    Matches the SRS contract:
    { "error": { "code": "...", "message": "..." } }
    """
    error: ErrorDetail