"""Pass-1 cheap universe screen + missing-ticker recovery.

A prior Explorer shortlist is a priority queue, not the universe.
Scoring weights are not modified here.
"""
from __future__ import annotations

from typing import Any

from egxbridge.analysis.common.missing import SOURCE_UNAVAILABLE, from_optional, missing
from egxbridge.analysis.common.models import utc_now
from egxbridge.analysis.explorer.session_volume import timestamp_guard
from egxbridge.analysis.common.data_stamp import parse_dt, CAIRO
from egxbridge.semantics import session_date_cairo
from egxbridge.symbols import canonicalize_any


def _f(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def cheap_snapshot(
    ticker: str,
    *,
    metrics: dict[str, Any] | None = None,
    quote: dict[str, Any] | None = None,
    retrieval_timestamp: str | None = None,
    cutoff: str | None = None,
) -> dict[str, Any]:
    """Cheapest current fields for one equity. Explicit missing, never silent."""
    m = dict(metrics or {})
    q = dict(quote or {})
    retrieved = retrieval_timestamp or utc_now()
    last = _f(q.get("last") or q.get("close") or m.get("last_close") or m.get("latest_close"))
    daily_last = _f(m.get("last_close") or m.get("latest_close"))
    prev = _f(q.get("prev_close") or m.get("prev_close") or m.get("previous_close"))
    src_ts = q.get("provider_timestamp") or q.get("normalized_utc_timestamp") or m.get("latest_session")
    source_session = session_date_cairo(src_ts) or str(src_ts or "")[:10]
    daily_session = m.get("latest_session")
    # The latest daily close is a previous-close reference only on a later session.
    if q and daily_last and daily_session and source_session > daily_session:
        prev = daily_last
    chg = _f(q.get("change_pct"))
    if chg is None and last is not None and prev:
        chg = round((last / prev - 1) * 100, 4)
    if chg is None and not q:
        chg = _f(m.get("daily_return_pct"))
    guard = timestamp_guard(src_ts, cutoff=cutoff or retrieved) if src_ts else {"ok": True, "point_in_time_valid": src_ts is not None, "reason": "OK"}
    delay = None
    from egxbridge.analysis.common.data_stamp import delay_seconds
    if src_ts:
        delay = delay_seconds(retrieved, src_ts)
    current_session = source_session == parse_dt(cutoff or retrieved).astimezone(CAIRO).date().isoformat()
    evidence_kind = q.get("evidence_kind") or ("QUOTE" if q else "DAILY_CLOSE")
    current_evidence = current_session and bool(guard.get("ok")) and (
        (evidence_kind == "DAILY_CLOSE" and m.get("daily_bars_lagging") is False)
        or (evidence_kind != "DAILY_CLOSE" and delay is not None and delay <= 1800)
    )
    # Recompute distance-to-20d-high from a live last vs the daily 20d high.
    # Does not change CSS/QB scoring — recovery flags only.
    dist = _f(m.get("dist_from_20d_high_pct"))
    if last is not None and daily_last and dist is not None:
        denom = 1.0 + (dist / 100.0)
        if denom:
            high_20 = daily_last / denom
            if high_20:
                dist = round((last / high_20 - 1.0) * 100, 4)
    breakout = m.get("breakout_20d")
    if last is not None and dist is not None and dist >= 0:
        breakout = True
    return {
        "ticker": str(ticker).upper(),
        "canonical_ticker": canonicalize_any(ticker),
        "last_price": from_optional(last),
        "pct_change": from_optional(chg),
        "session_high": from_optional(_f(q.get("session_high"))),
        "session_low": from_optional(_f(q.get("session_low"))),
        "session_volume": from_optional(_f(q.get("volume")) if q.get("volume_semantics") == "SESSION_CUMULATIVE_VOLUME" else None),
        "bar_high": from_optional(_f(q.get("bar_high"))),
        "bar_low": from_optional(_f(q.get("bar_low"))),
        "bar_volume": from_optional(_f(q.get("bar_volume"))),
        "bar_interval": q.get("interval"),
        "evidence_kind": evidence_kind,
        "source_session": source_session or None,
        "current_session": current_session,
        "current_mover_evidence": current_evidence,
        "daily_session": daily_session,
        "prev_close": prev,
        "daily_bars_lagging": m.get("daily_bars_lagging"),
        "traded_value": missing(SOURCE_UNAVAILABLE, note="Not inferred from last*volume."),
        "halt_limit_state": from_optional(q.get("halt_state") or m.get("halt_limit_state"), empty_status="NOT_APPLICABLE"),
        "latest_timestamp": from_optional(src_ts, empty_status="DATA_INSUFFICIENT"),
        "source": q.get("provider") or m.get("daily_provider") or "yahoo+scanner",
        "source_timestamp": src_ts,
        "retrieval_timestamp": retrieved,
        "exchange_timestamp_if_available": q.get("provider_timestamp"),
        "data_delay_seconds": delay,
        "is_delayed": True,
        "point_in_time_valid": bool(guard.get("point_in_time_valid")) if src_ts else False,
        "status": "NOT_RELIABLE" if src_ts and not guard.get("ok") else ("AVAILABLE" if current_evidence and last is not None else "HISTORICAL" if last is not None else "DATA_INSUFFICIENT"),
        "rvol_20": _f(m.get("rvol_20")) if daily_session == source_session else None,
        "dist_from_20d_high_pct": dist,
        "breakout_20d": breakout,
        "daily_return_pct": _f(m.get("daily_return_pct")),
        "last_close": _f(m.get("last_close") or last),
    }


def activity_triggers(snap: dict[str, Any]) -> list[str]:
    """Generic unusual-activity flags. Not RMDA/OFH specific."""
    flags: list[str] = []
    chg = _f((snap.get("pct_change") or {}).get("value") if isinstance(snap.get("pct_change"), dict) else snap.get("pct_change"))
    if chg is None:
        chg = snap.get("daily_return_pct")
    rvol = snap.get("rvol_20")
    dist = snap.get("dist_from_20d_high_pct")
    if chg is not None and abs(chg) >= 2.0:
        flags.append("UNUSUAL_SESSION_MOVE")
    if rvol is not None and rvol >= 1.5:
        flags.append("HIGH_RVOL")
    if snap.get("breakout_20d") is True:
        flags.append("NEAR_BREAKOUT")
    if dist is not None and dist >= -1.0 and (chg or 0) > 0:
        flags.append("THROUGH_NEAR_RESISTANCE")
    if chg is not None and chg >= 1.0 and dist is not None and dist >= -2.0:
        flags.append("FRESH_ACTIVATION")
    return flags


def overlay_session_quotes(
    snapshots: dict[str, dict[str, Any]] | None,
    quotes_by_ticker: dict[str, dict[str, Any]] | None,
    *,
    retrieval_timestamp: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Merge current-session quotes into cheap snapshots. Does not change scores."""
    out = dict(snapshots or {})
    retrieved = retrieval_timestamp or utc_now()
    for raw_t, quote in (quotes_by_ticker or {}).items():
        t = str(raw_t or "").upper()
        if not t or not isinstance(quote, dict):
            continue
        prev = out.get(t) or {}
        metrics = {
            "last_close": prev.get("last_close"),
            "prev_close": prev.get("prev_close"),
            "latest_session": prev.get("daily_session"),
            "daily_bars_lagging": prev.get("daily_bars_lagging"),
            "daily_return_pct": prev.get("daily_return_pct"),
            "rvol_20": prev.get("rvol_20"),
            "dist_from_20d_high_pct": prev.get("dist_from_20d_high_pct"),
            "breakout_20d": prev.get("breakout_20d"),
            "session_high": prev.get("session_high") if not isinstance(prev.get("session_high"), dict) else None,
            "session_low": prev.get("session_low") if not isinstance(prev.get("session_low"), dict) else None,
            "volume": prev.get("session_volume") if not isinstance(prev.get("session_volume"), dict) else None,
        }
        out[t] = cheap_snapshot(
            t,
            metrics=metrics,
            quote=quote,
            retrieval_timestamp=retrieved,
        )
    return out


def session_quotes_from_db(db, tickers: list[str], *, today: str | None = None, cutoff: str | None = None) -> dict[str, dict[str, Any]]:
    """Cheap current-session pass from stored quotes / 5m bars. No scoring."""
    from zoneinfo import ZoneInfo

    if db is None:
        return {}
    cutoff = cutoff or utc_now()
    today = today or parse_dt(cutoff).astimezone(ZoneInfo("Africa/Cairo")).date().isoformat()
    out: dict[str, dict[str, Any]] = {}
    for raw in tickers or []:
        t = str(raw or "").upper()
        if not t:
            continue
        last = None
        src_ts = None
        vol = None
        high = None
        low = None
        provider = "db_session_cache"
        bars = []
        interval = None
        for iv in ("5m", "1m"):
            try:
                raw_bars = db.fetch_candles(t, iv, limit=400) or []
            except Exception:
                raw_bars = []
            bars = [b for b in raw_bars if (b.get("session_date") or session_date_cairo(b.get("normalized_utc_timestamp") or b.get("timestamp"))) == today and timestamp_guard(b.get("normalized_utc_timestamp") or b.get("timestamp"), cutoff=cutoff)["ok"]]
            if bars:
                interval = iv
                bars.sort(key=lambda b: b.get("normalized_utc_timestamp") or b.get("timestamp"), reverse=True)
                break
        for b in bars:
            ts = b.get("normalized_utc_timestamp") or b.get("timestamp")
            sess = str(b.get("session_date") or session_date_cairo(ts) or "")[:10]
            if sess != today:
                continue
            last = _f(b.get("close"))
            src_ts = ts
            vol = _f(b.get("volume"))
            high = _f(b.get("high"))
            low = _f(b.get("low"))
            provider = b.get("provider") or provider
            break
        if last is None:
            try:
                quotes = db.fetch_latest_quotes(t) or []
            except Exception:
                quotes = []
            for q in quotes:
                ts = q.get("provider_timestamp") or q.get("normalized_utc_timestamp")
                if session_date_cairo(ts) != today or not timestamp_guard(ts, cutoff=cutoff)["ok"]:
                    continue
                last = _f(q.get("last") or q.get("close") or q.get("price"))
                src_ts = ts
                provider = q.get("provider") or provider
                break
        if last is None:
            continue
        out[t] = {
            "last": last,
            "close": last,
            "bar_volume": vol,
            "bar_high": high,
            "bar_low": low,
            "interval": interval,
            "evidence_kind": "BAR" if interval else "QUOTE",
            "provider": provider,
            "provider_timestamp": src_ts,
        }
    return out


def merge_recovery_into_enrich(enrich_tickers: list[str], recovery_log: list[dict[str, Any]]) -> list[str]:
    out = list(dict.fromkeys(str(t).upper() for t in (enrich_tickers or []) if t))
    for rec in recovery_log or []:
        t = str(rec.get("ticker") or "").upper()
        if t and rec.get("recovered") and t not in out:
            out.append(t)
    return out


def recover_missing_tickers(
    scored: list[dict[str, Any]],
    *,
    shortlist_tickers: set[str],
    snapshots: dict[str, dict[str, Any]] | None = None,
    limit: int = 10,
    retrieval_timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """Inject scanner-eligible names that look active but were not in the prior shortlist."""
    short = {str(t).upper() for t in (shortlist_tickers or set())}
    snaps = snapshots or {}
    retrieved = retrieval_timestamp or utc_now()
    ranked: list[tuple[int, dict[str, Any]]] = []
    for row in scored or []:
        ticker = str(row.get("ticker") or "").upper()
        if not ticker or ticker in short:
            continue
        metrics = row.get("metrics") or row
        snap = snaps.get(ticker) or cheap_snapshot(ticker, metrics=metrics, retrieval_timestamp=retrieved)
        if not snap.get("current_mover_evidence") or snap.get("status") != "AVAILABLE":
            continue
        flags = activity_triggers(snap)
        if not flags:
            continue
        ident = canonicalize_any(ticker)
        ranked.append((len(flags), {
            "ticker": ticker,
            "canonical_ticker": ident,
            "alias_observed": ticker,
            "first_source": "scanner_metrics+session_snapshot",
            "first_source_timestamp": snap.get("source_timestamp") or retrieved,
            "reason_missing": "ABSENT_FROM_PREMARKET_SHORTLIST",
            "recovered": True,
            "recovery_timestamp": retrieved,
            "downstream_state": "CURRENT_MOVER / RECOVERED",
            "notes": ",".join(flags),
            "recovery_flags": flags,
        }))
    ranked.sort(key=lambda x: (-x[0], x[1]["ticker"]))
    out = []
    for _, rec in ranked[: max(0, int(limit))]:
        out.append(rec)
    return out
