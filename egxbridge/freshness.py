from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, time as dtime
from typing import Any
from zoneinfo import ZoneInfo


CAIRO_TZ = ZoneInfo("Africa/Cairo")

# EGX regular session (Sun–Thu). Window is inclusive of typical open/close buffer.
# Official cash session is commonly ~10:00–14:30 Cairo; we use 10:00–14:45.
EGX_SESSION_OPEN = dtime(10, 0)
EGX_SESSION_CLOSE = dtime(14, 45)
# Egypt weekend: Friday + Saturday
EGX_WEEKEND_WEEKDAYS = {4, 5}  # Fri=4, Sat=5


@dataclass
class FreshnessThresholds:
    live_seconds: float = 15
    fresh_seconds: float = 120
    delayed_seconds: float = 20 * 60  # 20 minutes
    # above delayed => STALE_EXPECTED or STALE_UNEXPECTED


DEFAULT_THRESHOLDS = FreshnessThresholds()


def parse_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    s = str(value).strip()
    if not s:
        return None
    # epoch seconds / ms
    try:
        if s.isdigit() or (s.replace(".", "", 1).isdigit() and s.count(".") <= 1):
            n = float(s)
            if n > 10_000_000_000:
                n = n / 1000.0
            return datetime.fromtimestamp(n, tz=timezone.utc)
    except Exception:
        pass
    # ISO-ish
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def egx_session_open_at(when: datetime | None = None) -> bool:
    """True if EGX cash session is expected open at `when` (UTC or aware).

    Does not include an official holiday calendar — weekends and off-hours only.
    Unknown holidays may therefore be classified STALE_UNEXPECTED during weekdays.
    """
    ct = when or datetime.now(timezone.utc)
    if ct.tzinfo is None:
        ct = ct.replace(tzinfo=timezone.utc)
    local = ct.astimezone(CAIRO_TZ)
    if local.weekday() in EGX_WEEKEND_WEEKDAYS:
        return False
    t = local.time()
    return EGX_SESSION_OPEN <= t <= EGX_SESSION_CLOSE


def classify_freshness(
    provider_timestamp: Any,
    capture_timestamp: Any | None = None,
    thresholds: FreshnessThresholds | None = None,
) -> tuple[str, float | None]:
    """Return (class, freshness_seconds).

    Classes: LIVE, FRESH, DELAYED, STALE_EXPECTED, STALE_UNEXPECTED, UNKNOWN.

    STALE_EXPECTED = market closed / weekend (and simple off-hours).
    STALE_UNEXPECTED = session should be open but observation is stale.
    Never labels data REALTIME; LIVE only from age <= live_seconds.
    """
    th = thresholds or DEFAULT_THRESHOLDS
    pt = parse_timestamp(provider_timestamp)
    if pt is None:
        return "UNKNOWN", None
    ct = parse_timestamp(capture_timestamp) or datetime.now(timezone.utc)
    age = (ct - pt).total_seconds()
    if age < 0:
        age = 0.0
    if age <= th.live_seconds:
        return "LIVE", age
    if age <= th.fresh_seconds:
        return "FRESH", age
    if age <= th.delayed_seconds:
        return "DELAYED", age
    # Stale: distinguish expected (closed) vs unexpected (should be open)
    if egx_session_open_at(ct):
        return "STALE_UNEXPECTED", age
    return "STALE_EXPECTED", age
