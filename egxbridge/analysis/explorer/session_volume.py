"""Current-session volume metrics. Descriptive only — not a buy signal."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from egxbridge.analysis.common.data_stamp import parse_dt
from egxbridge.daily_bars import ohlcv_issue
from egxbridge.analysis.common.missing import (
    DATA_INSUFFICIENT,
    NOT_APPLICABLE,
    NOT_RELIABLE,
    SOURCE_UNAVAILABLE,
    from_optional,
    missing,
    observed,
)

CAIRO = ZoneInfo("Africa/Cairo")
MIN_SAME_TIME_SESSIONS = 5
SHOCK_MULTIPLE = 3.0


def timestamp_guard(
    timestamp: str | datetime | None,
    *,
    cutoff: str | datetime | None,
    skew_seconds: float = 120.0,
    max_age_seconds: float | None = None,
) -> dict[str, Any]:
    """Reject future (lookahead) and optionally stale bars. Never invent replacements."""
    dt = parse_dt(timestamp)
    cut = parse_dt(cutoff) or datetime.now(timezone.utc)
    if dt is None:
        return {"ok": False, "reason": "NOT_RELIABLE", "point_in_time_valid": False}
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if cut.tzinfo is None:
        cut = cut.replace(tzinfo=timezone.utc)
    if dt > cut + timedelta(seconds=max(0.0, float(skew_seconds))):
        return {"ok": False, "reason": "FUTURE", "point_in_time_valid": False}
    if max_age_seconds is not None:
        age = (cut - dt).total_seconds()
        if age > float(max_age_seconds):
            return {"ok": False, "reason": "STALE", "point_in_time_valid": False, "age_seconds": age}
    return {"ok": True, "reason": "OK", "point_in_time_valid": True}


def _f(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _cairo(ts: str | datetime | None) -> datetime | None:
    dt = parse_dt(ts)
    if dt is None:
        return None
    return dt.astimezone(CAIRO)


def _session_date(bar: dict[str, Any]) -> str | None:
    sess = bar.get("session_date")
    if sess:
        return str(sess)[:10]
    cairo = _cairo(bar.get("timestamp_cairo") or bar.get("timestamp") or bar.get("normalized_utc_timestamp"))
    return cairo.date().isoformat() if cairo else None


def _tod_minutes(ts: str | datetime | None) -> int | None:
    cairo = _cairo(ts)
    if cairo is None:
        return None
    return cairo.hour * 60 + cairo.minute


def serialize_ohlcv(
    candles: list[Any],
    *,
    cutoff: str | datetime | None = None,
    session_date: str | None = None,
    current_session_only: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Keep OHLCV including volume when the upstream bar had it. Do not drop volume=0."""
    cutoff = cutoff or datetime.now(timezone.utc)
    bars: list[dict[str, Any]] = []
    future_n = 0
    stale_n = 0
    invalid_n = 0
    invalid_ohlcv = 0
    for raw in candles or []:
        if hasattr(raw, "to_dict"):
            c = raw.to_dict()
        elif isinstance(raw, dict):
            c = raw
        else:
            c = {
                "timestamp": getattr(raw, "timestamp", None),
                "normalized_utc_timestamp": getattr(raw, "normalized_utc_timestamp", None),
                "normalized_cairo_timestamp": getattr(raw, "normalized_cairo_timestamp", None),
                "open": getattr(raw, "open", None),
                "high": getattr(raw, "high", None),
                "low": getattr(raw, "low", None),
                "close": getattr(raw, "close", None),
                "volume": getattr(raw, "volume", None),
                "session_date": getattr(raw, "session_date", None),
                "volume_semantics": getattr(raw, "volume_semantics", None),
            }
        ts = c.get("normalized_utc_timestamp") or c.get("timestamp")
        guard = timestamp_guard(ts, cutoff=cutoff)
        if not guard["ok"]:
            if guard["reason"] == "FUTURE":
                future_n += 1
            elif guard["reason"] == "STALE":
                stale_n += 1
            else:
                invalid_n += 1
            continue
        if ohlcv_issue(c):
            invalid_ohlcv += 1
            continue
        sess = c.get("session_date") or _session_date({"timestamp": ts, "timestamp_cairo": c.get("normalized_cairo_timestamp")})
        if current_session_only and session_date and sess and str(sess)[:10] != str(session_date)[:10]:
            continue
        vol = _f(c.get("volume"))
        bars.append({
            "timestamp": ts,
            "capture_timestamp": c.get("capture_timestamp"),
            "provider": c.get("provider"),
            "interval": c.get("interval"),
            "timestamp_semantics": c.get("timestamp_semantics"),
            "timestamp_cairo": c.get("normalized_cairo_timestamp"),
            "session_date": sess,
            "open": _f(c.get("open")),
            "high": _f(c.get("high")),
            "low": _f(c.get("low")),
            "close": _f(c.get("close")),
            "volume": vol,
            "volume_status": "AVAILABLE" if vol is not None else SOURCE_UNAVAILABLE,
            "volume_semantics": c.get("volume_semantics") or "BAR_VOLUME",
            "point_in_time_valid": True,
        })
    bars.sort(key=lambda b: str(b.get("timestamp") or ""))
    bars = list({b["timestamp"]: b for b in bars}.values())
    return bars, {
        "future_timestamp_records_rejected": future_n,
        "stale_records_rejected": stale_n,
        "invalid_timestamp_records_rejected": invalid_n,
        "invalid_ohlcv_records_rejected": invalid_ohlcv,
    }


def _sum_volume(bars: list[dict[str, Any]]) -> float | None:
    if any(b.get("volume_semantics") not in {None, "BAR_VOLUME"} for b in bars):
        return None
    vals = [_f(b.get("volume")) for b in bars]
    present = [v for v in vals if v is not None]
    if not present or len(present) != len(vals):
        return None
    return float(sum(present))


def _window_volume(bars: list[dict[str, Any]], *, last_n: int, skip: int = 0) -> float | None:
    if not bars:
        return None
    chunk = bars[-(last_n + skip): len(bars) - skip if skip else None]
    if skip and len(bars) < last_n + skip:
        return None
    if len(chunk) < last_n:
        return None
    return _sum_volume(chunk[-last_n:])


def cumulative_at(bars: list[dict[str, Any]], hhmm_minutes: int) -> float | None:
    chosen = []
    for b in bars:
        tod = _tod_minutes(b.get("timestamp_cairo") or b.get("timestamp"))
        if tod is None or tod > hhmm_minutes:
            continue
        chosen.append(b)
    return _sum_volume(chosen)


def same_time_rvol(
    current_bars: list[dict[str, Any]],
    historical_by_session: dict[str, list[dict[str, Any]]],
    *,
    at: str | datetime | None = None,
    min_sessions: int = MIN_SAME_TIME_SESSIONS,
) -> dict[str, Any]:
    """Current cumulative volume at HH:MM / average historical cumulative volume at the same HH:MM."""
    now = _cairo(at) or datetime.now(CAIRO)
    hhmm = now.hour * 60 + now.minute
    current = cumulative_at(current_bars, hhmm)
    samples: list[float] = []
    shock: list[str] = []
    session_totals = []
    for sess, bars in (historical_by_session or {}).items():
        total = _sum_volume(bars)
        if total is not None:
            session_totals.append((str(sess), total))
    med = median([t for _, t in session_totals]) if session_totals else None
    ordinary: list[float] = []
    for sess, bars in (historical_by_session or {}).items():
        cum = cumulative_at(bars, hhmm)
        if cum is None:
            continue
        total = _sum_volume(bars)
        if med and total is not None and total > SHOCK_MULTIPLE * med:
            shock.append(str(sess))
            continue
        ordinary.append(cum)
        samples.append(cum)
    used = ordinary if ordinary else samples
    calc_ts = now.astimezone(timezone.utc).isoformat()
    if current is None:
        return {
            "value": None,
            "status": DATA_INSUFFICIENT,
            "sample_size": 0,
            "historical_sessions_used": 0,
            "calculation_timestamp": calc_ts,
            "confidence": NOT_RELIABLE,
            "note": "Current-session cumulative volume is unavailable.",
        }
    if len(used) < min_sessions:
        return {
            "value": None,
            "status": DATA_INSUFFICIENT,
            "sample_size": len(used),
            "historical_sessions_used": len(used),
            "calculation_timestamp": calc_ts,
            "confidence": NOT_RELIABLE,
            "intraday_rvol_same_time_20d": None,
            "shock_sessions_excluded": shock,
        }
    avg = sum(used) / len(used)
    med_v = median(used)
    if not avg:
        return {
            "value": None,
            "status": DATA_INSUFFICIENT,
            "sample_size": len(used),
            "historical_sessions_used": len(used),
            "calculation_timestamp": calc_ts,
            "confidence": NOT_RELIABLE,
        }
    rvol = round(current / avg, 4)
    return {
        "value": rvol,
        "status": "AVAILABLE",
        "intraday_rvol_same_time_20d": rvol,
        "sample_size": len(used),
        "historical_sessions_used": len(used),
        "calculation_timestamp": calc_ts,
        "confidence": "HIGH" if len(used) >= 15 else ("MEDIUM" if len(used) >= 10 else "LOW"),
        "ordinary_rolling_baseline": round(avg, 4),
        "pre_event_baseline_excluding_shock_sessions": round(sum(ordinary) / len(ordinary), 4) if ordinary else None,
        "same_time_avg_volume_20d": round(avg, 4),
        "same_time_median_volume_20d": round(float(med_v), 4) if med_v is not None else None,
        "shock_sessions_excluded": shock,
        "baseline_contamination_risk": "IDENTIFIED" if shock else "LOW",
        "hhmm_cairo": f"{now.hour:02d}:{now.minute:02d}",
        "current_cumulative_volume": current,
    }


def participation_state(rvol: float | None) -> str:
    if rvol is None:
        return NOT_RELIABLE
    if rvol >= 3.0:
        return "VERY_HIGH"
    if rvol >= 1.8:
        return "HIGH"
    if rvol >= 0.8:
        return "NORMAL"
    return "LOW"


def volume_price_state(*, price_change_pct: float | None, volume_expanding: bool | None) -> str:
    if price_change_pct is None or volume_expanding is None:
        return NOT_RELIABLE
    up = price_change_pct > 0.15
    down = price_change_pct < -0.15
    if up and volume_expanding:
        return "PRICE_UP_VOLUME_EXPANDING"
    if up and not volume_expanding:
        return "PRICE_UP_VOLUME_FADING"
    if down and volume_expanding:
        return "PRICE_DOWN_VOLUME_EXPANDING"
    if abs(price_change_pct) <= 0.15 and volume_expanding:
        return "PRICE_FLAT_VOLUME_EXPANDING"
    return "MIXED"


def session_volume_metrics(
    *,
    bars_1m: list[dict[str, Any]] | None = None,
    bars_5m: list[dict[str, Any]] | None = None,
    bars_15m: list[dict[str, Any]] | None = None,
    previous_full_session_volume: float | None = None,
    historical_1m_by_session: dict[str, list[dict[str, Any]]] | None = None,
    at: str | datetime | None = None,
    prev_close: float | None = None,
    last_price: float | None = None,
    dist_from_20d_high_pct: float | None = None,
) -> dict[str, Any]:
    reference = _cairo(at) or datetime.now(CAIRO)
    session = reference.date().isoformat()
    def current_bars(rows):
        unique = {b.get("timestamp"): b for b in rows or []
                  if _session_date(b) == session and timestamp_guard(b.get("timestamp"), cutoff=reference)["ok"]}
        return [unique[t] for t in sorted(unique)]
    b1 = current_bars(bars_1m)
    b5 = current_bars(bars_5m)
    b15 = current_bars(bars_15m)
    session_vol = _sum_volume(b1) if b1 else _sum_volume(b5)
    last_px = last_price if last_price is not None else (b1[-1].get("close") if b1 else (b5[-1].get("close") if b5 else None))
    high = max((_f(b.get("high")) or _f(b.get("close")) or 0) for b in (b1 or b5 or [None]) if b) if (b1 or b5) else None
    low = min((_f(b.get("low")) or _f(b.get("close")) or 0) for b in (b1 or b5 or [None]) if b) if (b1 or b5) else None
    px_chg = None
    if last_px is not None and prev_close:
        px_chg = round((float(last_px) / float(prev_close) - 1) * 100, 4)
    last_5 = _window_volume(b5, last_n=1) if b5 else _window_volume(b1, last_n=5)
    prev_5 = _window_volume(b5, last_n=1, skip=1) if b5 else _window_volume(b1, last_n=5, skip=5)
    last_15 = _window_volume(b15, last_n=1) if b15 else _window_volume(b1, last_n=15)
    prev_15 = _window_volume(b15, last_n=1, skip=1) if b15 else _window_volume(b1, last_n=15, skip=15)
    last_30 = _window_volume(b1, last_n=30)
    prev_30 = _window_volume(b1, last_n=30, skip=30)

    def _accel(cur: float | None, prev: float | None) -> dict[str, Any]:
        if cur is None or prev is None:
            return missing(DATA_INSUFFICIENT)
        if prev == 0:
            return missing(DATA_INSUFFICIENT, note="Previous window volume is zero.")
        return observed(round(cur / prev, 4))

    same = same_time_rvol(b1 or b5, historical_1m_by_session or {}, at=at)
    rvol_val = same.get("value")
    expanding = None
    if last_5 is not None and prev_5 is not None:
        expanding = last_5 > prev_5
    vs_full = missing(DATA_INSUFFICIENT)
    if session_vol is not None and previous_full_session_volume:
        vs_full = observed(round(session_vol / previous_full_session_volume, 4), note="Partial session vs previous FULL session — not same-time RVOL.")
    vs_same = missing(DATA_INSUFFICIENT)
    if session_vol is not None and same.get("current_cumulative_volume") is not None and same.get("ordinary_rolling_baseline"):
        vs_same = observed(round(same["current_cumulative_volume"] / same["ordinary_rolling_baseline"], 4))

    clv = None
    if last_px is not None and high and low and high != low:
        clv = round((float(last_px) - float(low)) / (float(high) - float(low)), 4)

    return {
        "session_date": session,
        "observed_bar_count": len(b1 or b5),
        "observed_from": (b1 or b5)[0].get("timestamp") if (b1 or b5) else None,
        "observed_through": (b1 or b5)[-1].get("timestamp") if (b1 or b5) else None,
        "coverage_note": "Sum of available bars in this session; full-session coverage is unverified. Unknown or missing volume is not summed.",
        "session_volume_so_far": from_optional(session_vol, empty_status=DATA_INSUFFICIENT, zero_is_valid=True),
        "session_traded_value_so_far": missing(
            SOURCE_UNAVAILABLE,
            note="Traded value requires price*qty tape or value field; not inferred from candles.",
        ),
        "session_transaction_count": missing(
            SOURCE_UNAVAILABLE,
            note="Transaction count is not available from OHLCV bars. Do not treat as zero.",
        ),
        "same_time_avg_volume_20d": from_optional(same.get("same_time_avg_volume_20d"), empty_status=DATA_INSUFFICIENT),
        "same_time_median_volume_20d": from_optional(same.get("same_time_median_volume_20d"), empty_status=DATA_INSUFFICIENT),
        "intraday_rvol_20d": missing(
            DATA_INSUFFICIENT if rvol_val is None else "NOT_APPLICABLE",
            note="Use intraday_rvol_same_time_20d. Full-day RVOL is not a substitute for early-session confirmation.",
        ),
        "intraday_rvol_same_time_20d": same,
        "volume_vs_previous_session_same_time": vs_same,
        "volume_vs_previous_full_session": vs_full,
        "volume_acceleration_5m": _accel(last_5, prev_5),
        "volume_acceleration_15m": _accel(last_15, prev_15),
        "volume_acceleration_30m": _accel(last_30, prev_30),
        "last_5m_volume": from_optional(last_5),
        "previous_5m_volume": from_optional(prev_5),
        "last_15m_volume": from_optional(last_15),
        "previous_15m_volume": from_optional(prev_15),
        "pre_event_volume_baseline": from_optional(same.get("pre_event_baseline_excluding_shock_sessions")),
        "pre_event_value_baseline": missing(SOURCE_UNAVAILABLE),
        "baseline_contamination_risk": same.get("baseline_contamination_risk") or "UNKNOWN",
        "ordinary_rolling_baseline": from_optional(same.get("ordinary_rolling_baseline")),
        "pre_event_baseline_excluding_shock_sessions": from_optional(same.get("pre_event_baseline_excluding_shock_sessions")),
        "price_change_pct": from_optional(px_chg),
        "close_location": from_optional(clv),
        "distance_to_resistance": from_optional(dist_from_20d_high_pct),
        "distance_to_qb_upper_edge": missing(NOT_APPLICABLE, note="QB edges are not exported from this volume module (scoring frozen)."),
        "session_volume_percentile": missing(DATA_INSUFFICIENT, note="Requires a historical same-time distribution."),
        "participation_state": participation_state(rvol_val),
        "volume_price_state": volume_price_state(price_change_pct=px_chg, volume_expanding=expanding),
        "volume_is_participation_evidence_only": True,
        "not_a_buy_signal": True,
    }


def unavailable_book() -> dict[str, Any]:
    return {
        "depth_status": SOURCE_UNAVAILABLE,
        "best_bid": missing(SOURCE_UNAVAILABLE),
        "best_bid_qty": missing(SOURCE_UNAVAILABLE),
        "best_ask": missing(SOURCE_UNAVAILABLE),
        "best_ask_qty": missing(SOURCE_UNAVAILABLE),
        "spread_abs": missing(SOURCE_UNAVAILABLE),
        "spread_pct": missing(SOURCE_UNAVAILABLE),
        "total_bid_depth": missing(SOURCE_UNAVAILABLE),
        "total_ask_depth": missing(SOURCE_UNAVAILABLE),
        "bid_ask_depth_ratio": missing(SOURCE_UNAVAILABLE),
        "depth_levels": [],
        "supply_wall_levels": [],
        "demand_wall_levels": [],
        "note": "Anonymous delayed candles have no order book. Do not infer accumulation from missing depth.",
    }


def unavailable_tape() -> dict[str, Any]:
    return {
        "tape_status": SOURCE_UNAVAILABLE,
        "trades": [],
        "transactions_last_1m": missing(SOURCE_UNAVAILABLE),
        "transactions_last_5m": missing(SOURCE_UNAVAILABLE),
        "transactions_last_15m": missing(SOURCE_UNAVAILABLE),
        "shares_last_1m": missing(SOURCE_UNAVAILABLE),
        "shares_last_5m": missing(SOURCE_UNAVAILABLE),
        "shares_last_15m": missing(SOURCE_UNAVAILABLE),
        "value_last_1m": missing(SOURCE_UNAVAILABLE),
        "value_last_5m": missing(SOURCE_UNAVAILABLE),
        "value_last_15m": missing(SOURCE_UNAVAILABLE),
        "aggressor_classification": missing(SOURCE_UNAVAILABLE, note="Do not infer buy/sell aggressor."),
        "note": "Individual transactions are not available from the current delayed candle feed.",
    }


def group_bars_by_session(bars: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for b in bars or []:
        sess = _session_date(b)
        if not sess:
            continue
        out.setdefault(sess, []).append(b)
    for sess in out:
        out[sess].sort(key=lambda x: str(x.get("timestamp") or ""))
    return out
