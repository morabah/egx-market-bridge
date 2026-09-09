"""Explicit missing-data envelopes — never silently omit or fabricate zeros."""
from __future__ import annotations

from typing import Any

AVAILABLE = "AVAILABLE"
DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
SOURCE_MISSING = "SOURCE_MISSING"
NOT_RELIABLE = "NOT_RELIABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"


def observed(value: Any, **extra: Any) -> dict[str, Any]:
    return {"value": value, "status": AVAILABLE, **extra}


def missing(status: str, *, value: Any = None, note: str | None = None, **extra: Any) -> dict[str, Any]:
    row = {"value": value, "status": status, **extra}
    if note:
        row["note"] = note
    return row


def from_optional(value: Any, *, empty_status: str = DATA_INSUFFICIENT, zero_is_valid: bool = True, **extra: Any) -> dict[str, Any]:
    if value is None:
        return missing(empty_status, **extra)
    if not zero_is_valid and value == 0:
        return missing(empty_status, value=None, **extra)
    return observed(value, **extra)
