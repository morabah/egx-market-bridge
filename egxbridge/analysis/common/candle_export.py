"""Handoff candle enrichment — preserve/repair timestamp semantics without inventing data."""
from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from egxbridge.semantics import (
    normalize_timestamp,
    session_date_cairo,
    BAR_OPEN,
    DAILY_BAR,
    BAR_VOLUME,
    DAILY_FINAL_VOLUME,
    UNKNOWN_VOLUME,
    CANDLE_CLOSE,
    DAILY_CLOSE,
    TS_UNKNOWN,
    PRICE_UNKNOWN,
)


NORMALIZED = "NORMALIZED"
RAW_ONLY = "RAW_ONLY"
LEGACY_UNNORMALIZED = "LEGACY_UNNORMALIZED"
UNKNOWN = "UNKNOWN"

SEMANTIC_FIELDS = (
    "provider_raw_timestamp",
    "provider_timezone_if_known",
    "normalized_utc_timestamp",
    "normalized_cairo_timestamp",
    "timestamp_semantics",
    "session_date",
    "effective_session_date",
    "volume_semantics",
    "volume_interval",
    "price_observation_type",
    "latest_completed_session",
    "freshness_class",
    "timestamp_normalization_status",
    "timestamp_utc",  # canonical alias for normalized_utc_timestamp
)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    s = str(ts).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _looks_like_legacy_tv_utc(row: dict[str, Any]) -> bool:
    """TV naive Cairo wall clock wrongly stored as +00:00 (e.g. 14:25+00:00)."""
    if (row.get("provider") or "").lower() != "tradingview":
        return False
    if row.get("normalized_utc_timestamp") and row.get("provider_timezone_if_known"):
        # Already has proper bundle
        return False
    dt = _parse_iso(row.get("timestamp"))
    if dt is None or dt.tzinfo is None:
        return False
    # UTC offset zero but hour in EGX cash session wall-clock band (Cairo ~10:00–15:00)
    if dt.utcoffset() != timezone.utc.utcoffset(dt):
        # not UTC
        off = dt.utcoffset()
        if off is not None and off.total_seconds() != 0:
            return False
    hour = dt.hour
    return 9 <= hour <= 15


def enrich_candle_row(row: dict[str, Any]) -> dict[str, Any]:
    """Return export row with full semantic fields. Never silently treat legacy as UTC."""
    out = dict(row)
    provider = (out.get("provider") or "").lower()
    interval = out.get("interval") or ""

    # Prefer already-normalized fields (from DB extras or raw collect)
    if out.get("normalized_utc_timestamp") and out.get("normalized_cairo_timestamp"):
        out["timestamp_normalization_status"] = NORMALIZED
        out["timestamp_utc"] = out["normalized_utc_timestamp"]
        # Canonical timestamp is always normalized UTC — never leave legacy mislabel as `timestamp`
        legacy = out.get("timestamp")
        if legacy and legacy != out["normalized_utc_timestamp"]:
            out.setdefault("legacy_unnormalized_timestamp", legacy)
        out["timestamp"] = out["normalized_utc_timestamp"]
        if not out.get("session_date"):
            out["session_date"] = session_date_cairo(out.get("normalized_cairo_timestamp"))
        if not out.get("effective_session_date"):
            out["effective_session_date"] = out.get("session_date")
        if not out.get("volume_semantics"):
            out["volume_semantics"] = DAILY_FINAL_VOLUME if interval == "1d" else BAR_VOLUME
        if not out.get("volume_interval"):
            out["volume_interval"] = interval or None
        if not out.get("price_observation_type"):
            out["price_observation_type"] = DAILY_CLOSE if interval == "1d" else CANDLE_CLOSE
        if not out.get("timestamp_semantics"):
            out["timestamp_semantics"] = DAILY_BAR if interval == "1d" else BAR_OPEN
        return out

    # Legacy TradingView: +00:00 label on Cairo wall clock
    if _looks_like_legacy_tv_utc(out):
        dt = _parse_iso(out.get("timestamp"))
        naive = dt.replace(tzinfo=None) if dt else None
        bundle = normalize_timestamp(
            naive,
            provider_timezone_if_known="Africa/Cairo",
            timestamp_semantics=BAR_OPEN if interval != "1d" else DAILY_BAR,
        )
        out["provider_raw_timestamp"] = out.get("provider_raw_timestamp") or (
            naive.isoformat(sep=" ") if naive else out.get("timestamp")
        )
        out["provider_timezone_if_known"] = "Africa/Cairo"
        out["normalized_utc_timestamp"] = bundle.normalized_utc_timestamp
        out["normalized_cairo_timestamp"] = bundle.normalized_cairo_timestamp
        out["timestamp_semantics"] = bundle.timestamp_semantics
        out["session_date"] = session_date_cairo(bundle.normalized_cairo_timestamp)
        out["effective_session_date"] = out["session_date"]
        out["volume_semantics"] = out.get("volume_semantics") or (
            DAILY_FINAL_VOLUME if interval == "1d" else BAR_VOLUME
        )
        out["volume_interval"] = interval or None
        out["price_observation_type"] = DAILY_CLOSE if interval == "1d" else CANDLE_CLOSE
        out["timestamp_normalization_status"] = NORMALIZED
        out["legacy_repair"] = "LEGACY_TV_UTC_LABEL_REINTERPRETED_AS_CAIRO"
        out["timestamp_utc"] = out["normalized_utc_timestamp"]
        # Do not keep ambiguous legacy timestamp as canonical
        out["legacy_unnormalized_timestamp"] = out.get("timestamp")
        out["timestamp"] = out["normalized_utc_timestamp"]
        return out

    # Yahoo / others with only timestamp column — try parse if already aware
    dt = _parse_iso(out.get("timestamp"))
    if dt is not None and dt.tzinfo is not None:
        tz_known = "Africa/Cairo" if provider == "yahoo" else None
        bundle = normalize_timestamp(
            dt,
            provider_timezone_if_known=tz_known,
            timestamp_semantics=DAILY_BAR if interval == "1d" else BAR_OPEN,
        )
        out["provider_raw_timestamp"] = out.get("provider_raw_timestamp") or out.get("timestamp")
        out["provider_timezone_if_known"] = bundle.provider_timezone_if_known
        out["normalized_utc_timestamp"] = bundle.normalized_utc_timestamp
        out["normalized_cairo_timestamp"] = bundle.normalized_cairo_timestamp
        out["timestamp_semantics"] = bundle.timestamp_semantics
        out["session_date"] = session_date_cairo(bundle.normalized_cairo_timestamp)
        out["effective_session_date"] = out["session_date"]
        out["volume_semantics"] = out.get("volume_semantics") or (
            DAILY_FINAL_VOLUME if interval == "1d" else (BAR_VOLUME if interval else UNKNOWN_VOLUME)
        )
        out["volume_interval"] = interval or None
        out["price_observation_type"] = DAILY_CLOSE if interval == "1d" else CANDLE_CLOSE
        out["timestamp_normalization_status"] = NORMALIZED
        out["timestamp_utc"] = out["normalized_utc_timestamp"]
        out["timestamp"] = out["normalized_utc_timestamp"]
        return out

    # Cannot normalize safely — do not treat as UTC
    out["timestamp_normalization_status"] = LEGACY_UNNORMALIZED if out.get("timestamp") else UNKNOWN
    out["normalized_utc_timestamp"] = None
    out["normalized_cairo_timestamp"] = None
    out["timestamp_utc"] = None
    out["volume_semantics"] = out.get("volume_semantics") or UNKNOWN_VOLUME
    out["timestamp_semantics"] = out.get("timestamp_semantics") or TS_UNKNOWN
    out["price_observation_type"] = out.get("price_observation_type") or PRICE_UNKNOWN
    return out


def _rank_row(x: dict[str, Any]) -> tuple:
    return (
        1 if x.get("timestamp_normalization_status") == NORMALIZED else 0,
        1 if x.get("normalized_utc_timestamp") else 0,
        0 if x.get("legacy_repair") else 1,
        1 if x.get("provider_raw_timestamp") else 0,
    )


def enrich_candles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched = [enrich_candle_row(r) for r in rows]
    # Dedupe by provider/interval/normalized_utc (prefer native NORMALIZED over repaired)
    best: dict[tuple, dict] = {}
    for r in enriched:
        canon = r.get("normalized_utc_timestamp")
        if not canon:
            # Keep unrepaired legacy rows under their raw key so they remain visible but timing-excluded
            key = (r.get("provider"), r.get("interval"), "LEGACY", r.get("timestamp"))
        else:
            key = (r.get("provider"), r.get("interval"), canon)
        prev = best.get(key)
        if prev is None or _rank_row(r) >= _rank_row(prev):
            best[key] = r
    out = list(best.values())
    out.sort(key=lambda r: r.get("normalized_utc_timestamp") or r.get("timestamp") or "")
    return out


def timing_safe_candles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Exclude LEGACY_UNNORMALIZED / unknown from freshness & explorer timing."""
    return [
        r for r in enrich_candles(rows)
        if r.get("timestamp_normalization_status") == NORMALIZED and r.get("normalized_utc_timestamp")
    ]


def provenance_record(row: dict[str, Any]) -> dict[str, Any]:
    e = enrich_candle_row(row) if "timestamp_normalization_status" not in row else row
    return {
        "provider": e.get("provider"),
        "interval": e.get("interval"),
        "capture_timestamp": e.get("capture_timestamp"),
        "provider_raw_timestamp": e.get("provider_raw_timestamp"),
        "provider_timezone_if_known": e.get("provider_timezone_if_known"),
        "normalized_utc_timestamp": e.get("normalized_utc_timestamp"),
        "normalized_cairo_timestamp": e.get("normalized_cairo_timestamp"),
        "timestamp_semantics": e.get("timestamp_semantics"),
        "timestamp_normalization_status": e.get("timestamp_normalization_status"),
        "session_date": e.get("session_date"),
        "volume_semantics": e.get("volume_semantics"),
        "legacy_repair": e.get("legacy_repair"),
    }
