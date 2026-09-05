"""EGX session-phase labels from a Cairo clock. Not live execution capability."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

CAIRO = ZoneInfo("Africa/Cairo")

# Documented EGX cash-market bands (Africa/Cairo). Configurable, not an exchange feed.
PRE_OPEN_END = (10, 0)
CONTINUOUS_END = (14, 20)
CLOSING_AUCTION_END = (14, 30)
TRADING_AT_LAST_END = (14, 45)


def parse_dt(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def now_utc_cairo(at: datetime | None = None) -> dict[str, str]:
    dt = at or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    utc = dt.astimezone(timezone.utc)
    cairo = dt.astimezone(CAIRO)
    return {
        "analysis_timestamp_utc": utc.isoformat(),
        "analysis_timestamp_cairo": cairo.isoformat(),
    }


def classify_session_phase(at: datetime | str | None = None) -> str:
    """Map a timestamp onto EGX session bands. Weekends → POST_CLOSE."""
    dt = parse_dt(at) if not isinstance(at, datetime) else at
    if dt is None:
        dt = datetime.now(timezone.utc)
    cairo = dt.astimezone(CAIRO)
    if cairo.weekday() in (4, 5):  # Friday and Saturday; Sunday is an EGX session day.
        return "POST_CLOSE"
    hm = (cairo.hour, cairo.minute)
    if hm < PRE_OPEN_END:
        return "PRE_OPEN"
    if hm < CONTINUOUS_END:
        return "CONTINUOUS_TRADING"
    if hm < CLOSING_AUCTION_END:
        return "CLOSING_AUCTION"
    if hm < TRADING_AT_LAST_END:
        return "TRADING_AT_LAST"
    return "POST_CLOSE"


def session_context(at: datetime | None = None) -> dict[str, Any]:
    stamps = now_utc_cairo(at)
    phase = classify_session_phase(stamps["analysis_timestamp_utc"])
    return {
        **stamps,
        "session_phase": phase,
        "target_next_working_day": "UNKNOWN",
        "target_session_status": "UNKNOWN",
        "note": "No official EGX calendar locally; do not guess holidays. Session phase is a clock-band label, not live execution.",
        "egx_bands_cairo": {
            "PRE_OPEN": "until 10:00",
            "CONTINUOUS_TRADING": "10:00–14:20",
            "CLOSING_AUCTION": "14:20–14:30",
            "TRADING_AT_LAST": "14:30–14:45",
            "POST_CLOSE": "after 14:45 or weekend",
        },
    }
