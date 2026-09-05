from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any
from zoneinfo import ZoneInfo
import time as time_mod

from .freshness import (
    CAIRO_TZ,
    EGX_WEEKEND_WEEKDAYS,
    EGX_SESSION_OPEN,
    EGX_SESSION_CLOSE,
    egx_session_open_at,
    parse_timestamp,
    classify_freshness,
    FreshnessThresholds,
)


# Volume semantics
BAR_VOLUME = "BAR_VOLUME"
SESSION_CUMULATIVE_VOLUME = "SESSION_CUMULATIVE_VOLUME"
DAILY_FINAL_VOLUME = "DAILY_FINAL_VOLUME"
UNKNOWN_VOLUME = "UNKNOWN_VOLUME"

# Timestamp semantics
QUOTE_OBSERVATION = "QUOTE_OBSERVATION"
BAR_OPEN = "BAR_OPEN"
BAR_CLOSE = "BAR_CLOSE"
DAILY_BAR = "DAILY_BAR"
SESSION_CLOSE = "SESSION_CLOSE"
TS_UNKNOWN = "UNKNOWN"

# Price observation types
LIVE_QUOTE = "LIVE_QUOTE"
DELAYED_QUOTE = "DELAYED_QUOTE"
CANDLE_CLOSE = "CANDLE_CLOSE"
DAILY_CLOSE = "DAILY_CLOSE"
PRICE_UNKNOWN = "UNKNOWN"


@dataclass
class TimestampBundle:
    provider_raw_timestamp: str | None
    provider_timezone_if_known: str | None
    normalized_utc_timestamp: str | None
    normalized_cairo_timestamp: str | None
    timestamp_semantics: str
    naive_treated_as_utc: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def host_local_tz() -> ZoneInfo | timezone:
    """Timezone used by datetime.fromtimestamp() on this host (tvDatafeed behavior)."""
    try:
        return datetime.now().astimezone().tzinfo or timezone.utc
    except Exception:
        return timezone.utc


def host_local_tz_name() -> str:
    tz = host_local_tz()
    key = getattr(tz, "key", None)
    if key:
        return str(key)
    # Fallback offset label
    now = datetime.now(tz)
    off = now.utcoffset() or timedelta(0)
    hours = int(off.total_seconds() // 3600)
    return f"UTC{hours:+d}"


def normalize_timestamp(
    raw: Any,
    *,
    provider_timezone_if_known: str | None = None,
    timestamp_semantics: str = TS_UNKNOWN,
    allow_naive_as_utc: bool = False,
) -> TimestampBundle:
    """Normalize provider timestamps without blindly attaching UTC to naive values.

    - Aware datetimes: convert to UTC + Cairo.
    - Naive datetimes: require provider_timezone_if_known (IANA or 'local');
      otherwise leave normalized_utc as None (do not invent UTC).
    """
    raw_s = None if raw is None or raw == "" else str(raw)
    if raw is None or raw == "":
        return TimestampBundle(None, provider_timezone_if_known, None, None, timestamp_semantics)

    dt: datetime | None = None
    if isinstance(raw, datetime):
        dt = raw
    else:
        s = str(raw).strip()
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt = datetime.fromisoformat(s)
        except Exception:
            # epoch?
            try:
                if s.replace(".", "", 1).isdigit():
                    n = float(s)
                    if n > 10_000_000_000:
                        n /= 1000.0
                    dt = datetime.fromtimestamp(n, tz=timezone.utc)
                    provider_timezone_if_known = provider_timezone_if_known or "UTC"
            except Exception:
                dt = None

    if dt is None:
        return TimestampBundle(raw_s, provider_timezone_if_known, None, None, timestamp_semantics)

    naive_as_utc = False
    if dt.tzinfo is None:
        tz_name = provider_timezone_if_known
        if tz_name in (None, "", "UNKNOWN"):
            if allow_naive_as_utc:
                dt = dt.replace(tzinfo=timezone.utc)
                naive_as_utc = True
                provider_timezone_if_known = "UTC(assumed)"
            else:
                return TimestampBundle(
                    raw_s,
                    None,
                    None,
                    None,
                    timestamp_semantics,
                    naive_treated_as_utc=False,
                )
        elif tz_name == "local":
            dt = dt.replace(tzinfo=host_local_tz())
            provider_timezone_if_known = host_local_tz_name()
        else:
            dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    else:
        if not provider_timezone_if_known:
            provider_timezone_if_known = getattr(dt.tzinfo, "key", None) or str(dt.tzinfo)

    utc_dt = dt.astimezone(timezone.utc)
    cairo_dt = dt.astimezone(CAIRO_TZ)
    return TimestampBundle(
        provider_raw_timestamp=raw_s,
        provider_timezone_if_known=provider_timezone_if_known,
        normalized_utc_timestamp=utc_dt.isoformat(),
        normalized_cairo_timestamp=cairo_dt.isoformat(),
        timestamp_semantics=timestamp_semantics,
        naive_treated_as_utc=naive_as_utc,
    )


def session_date_cairo(ts_utc_or_cairo: Any) -> str | None:
    """Calendar session date in Africa/Cairo for an observation."""
    if ts_utc_or_cairo is None:
        return None
    if isinstance(ts_utc_or_cairo, str) and "T" in ts_utc_or_cairo:
        try:
            s = ts_utc_or_cairo
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                return None
            return dt.astimezone(CAIRO_TZ).date().isoformat()
        except Exception:
            return None
    pt = parse_timestamp(ts_utc_or_cairo)
    if pt is None:
        return None
    return pt.astimezone(CAIRO_TZ).date().isoformat()


def previous_egx_session_date(as_of: datetime | None = None) -> str:
    """Most recent completed EGX session date (Cairo) strictly before `as_of` if during session
    still in progress... Actually: latest *completed* session.

    If currently in session, latest completed is previous trading day.
    If outside session, latest completed is the last Sun–Thu session day <= today
    (if after close today, today; if before open today, previous trading day).
    """
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local = now.astimezone(CAIRO_TZ)
    d = local.date()
    t = local.time()

    def is_trading_day(day) -> bool:
        return day.weekday() not in EGX_WEEKEND_WEEKDAYS

    # If weekend or before open → walk back to last trading day
    # If during session → previous trading day is last *completed*
    # If after close on trading day → today is last completed
    if is_trading_day(d) and t > EGX_SESSION_CLOSE:
        return d.isoformat()
    # else walk back
    cur = d
    for _ in range(10):
        cur = cur - timedelta(days=1)
        if is_trading_day(cur):
            # If we walked back from a trading day before open, that's previous
            # If from during session, previous trading day
            return cur.isoformat()
    return d.isoformat()


def is_latest_completed_session(session_date: str | None, as_of: datetime | None = None) -> bool:
    if not session_date:
        return False
    return session_date == previous_egx_session_date(as_of)


def volumes_comparable(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Only comparable when same semantic type and same session/interval context."""
    sa = a.get("volume_semantics") or UNKNOWN_VOLUME
    sb = b.get("volume_semantics") or UNKNOWN_VOLUME
    if sa == UNKNOWN_VOLUME or sb == UNKNOWN_VOLUME or sa != sb:
        return False
    sess_a = effective_session_date_of(a) or a.get("session_date") or ""
    sess_b = effective_session_date_of(b) or b.get("session_date") or ""
    if sa == BAR_VOLUME:
        return (a.get("interval") or "") == (b.get("interval") or "") and sess_a == sess_b and bool(sess_a)
    # SESSION_CUMULATIVE / DAILY_FINAL: same session_date required
    return sess_a == sess_b and bool(sess_a)


def is_daily_session_label(observation: dict[str, Any]) -> bool:
    """True when timestamps are session labels, not real observation wall-clock times."""
    return (
        observation.get("timestamp_semantics") == DAILY_BAR
        or observation.get("price_observation_type") == DAILY_CLOSE
        or observation.get("volume_semantics") == DAILY_FINAL_VOLUME
    )


def effective_session_date_of(observation: dict[str, Any]) -> str | None:
    return observation.get("effective_session_date") or observation.get("session_date")


def classify_freshness_aware(
    normalized_utc_timestamp: Any,
    capture_timestamp: Any | None = None,
    thresholds: FreshnessThresholds | None = None,
) -> tuple[str, float | None]:
    """Freshness using normalized UTC only (never naive-as-UTC unless already normalized)."""
    if not normalized_utc_timestamp:
        return "UNKNOWN", None
    return classify_freshness(normalized_utc_timestamp, capture_timestamp, thresholds)
