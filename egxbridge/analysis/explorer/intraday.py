"""TradingView intraday enrichment for Explorer shortlist only."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from egxbridge.analysis.common.models import utc_now
from egxbridge.analysis.explorer.session_volume import (
    group_bars_by_session,
    serialize_ohlcv,
    session_volume_metrics,
    timestamp_guard,
    unavailable_book,
    unavailable_tape,
)
from egxbridge.analysis.common.data_stamp import delay_seconds
from egxbridge.daily_bars import ohlcv_issue
from egxbridge.analysis.explorer.intraday_fetch import (
    EMPTY_RESPONSE,
    PARSE_ERROR,
    PROVIDER_ERROR,
    NOT_REQUESTED,
    SKIPPED,
    RATE_LIMITED,
    STALE_ONLY,
    SUCCESS,
    SYMBOL_NOT_FOUND,
    TIMEOUT,
    UNKNOWN_FAILURE,
    build_yahoo_fallback,
    empty_ticker_diagnostics,
    fetch_interval_with_retry,
    load_stale_bars,
    provider_symbol_for,
    sanitize_error_message,
    summarize_fetch_diagnostics,
)
from egxbridge.freshness import classify_freshness
from egxbridge.semantics import previous_egx_session_date, session_date_cairo


INTRADAY_INTERVALS = ("1m", "5m", "15m")
# Prefer intervals that usually return during EGX continuous trading.
LIVE_REFRESH_INTERVALS = ("5m", "1m", "15m")

_CIRCUIT_OPEN_AFTER = 3


def _classify_tv_failure(exc: BaseException) -> str:
    """Backward-compatible alias used by older tests/callers."""
    from egxbridge.analysis.explorer.intraday_fetch import classify_fetch_error
    return classify_fetch_error(exc)


def _candle_field(candle: Any, key: str):
    if candle is None:
        return None
    if isinstance(candle, dict):
        return candle.get(key)
    return getattr(candle, key, None)


def _candle_to_row(candle: Any) -> dict[str, Any]:
    if hasattr(candle, "to_dict"):
        return candle.to_dict()
    return dict(candle)


def resolve_intraday_tickers(
    payload: dict[str, Any] | None,
    *,
    limit: int = 15,
) -> list[str]:
    """Pick tickers for a live intraday refresh even if Explorer skipped TV earlier."""
    payload = payload or {}
    queried = [
        str(t).upper()
        for t in (payload.get("intraday_queried_tickers") or [])
        if t
    ]
    recovered = [
        str(t).upper()
        for t in (payload.get("recovered_tickers") or [])
        if t
    ]
    cap = max(1, int(limit) + len(recovered))
    if queried:
        return list(dict.fromkeys(recovered + queried))[:cap]

    candidates = list(payload.get("candidates") or [])
    selected = [
        str(c.get("ticker")).upper()
        for c in candidates
        if c.get("ticker") and (
            c.get("intraday_selection_reason")
            or c.get("intraday_available")
            or c.get("recovery_state")
        )
    ]
    if selected:
        return list(dict.fromkeys(recovered + selected))[:cap]

    ranked = sorted(
        [c for c in candidates if c.get("ticker")],
        key=lambda c: (
            c.get("calibrated_rank") is None,
            c.get("calibrated_rank") if c.get("calibrated_rank") is not None else 10**9,
        ),
    )
    ranked_tickers = [str(c.get("ticker")).upper() for c in ranked]
    return list(dict.fromkeys(recovered + ranked_tickers))[:cap]


def _volume_semantics(candles: list[Any]) -> str | None:
    if not candles:
        return None
    return _candle_field(candles[-1], "volume_semantics")


def _source_name(candles: list[Any], default: str) -> str:
    if not candles:
        return default
    return str(_candle_field(candles[-1], "provider") or default)


def _fill_interval_from_candles(
    rec: dict[str, Any],
    candles: list[Any],
    *,
    used_source: str,
    today_cairo: str,
    cutoff: str,
    keep_ohlcv: bool,
    store_candles: bool,
    db,
    ohlcv: dict[str, list[dict[str, Any]]],
    interval_source: dict[str, str],
) -> tuple[Any, int, int]:
    """Apply live bars to one interval row. Returns (last_candle, future_rejected, stale_rejected)."""
    iv = rec["interval"]
    series, stats = serialize_ohlcv(candles, cutoff=cutoff, current_session_only=False)
    future_rejected = int(stats.get("future_timestamp_records_rejected") or 0)
    stale_rejected = int(stats.get("stale_records_rejected") or 0)
    rec["bars_received"] = len(candles)
    rec["bars"] = rec["ohlcv_bars"] = len(series)
    rec["rejected_bars"] = len(candles) - len(series)
    if not series:
        rec.update(available=False, intraday_fetch_state=PARSE_ERROR, failure_reason="NO_VALID_BARS")
        return None, future_rejected, stale_rejected
    rec["available"] = True
    rec["provider"] = used_source
    rec["intraday_fetch_state"] = SUCCESS
    rec["failure_reason"] = None
    valid_timestamps = {b["timestamp"] for b in series}
    accepted = list({(_candle_field(c, "normalized_utc_timestamp") or _candle_field(c, "timestamp")): c for c in candles
                     if (_candle_field(c, "normalized_utc_timestamp") or _candle_field(c, "timestamp")) in valid_timestamps
                     and not ohlcv_issue(_candle_to_row(c))}.values())
    last = next(c for c in accepted if (_candle_field(c, "normalized_utc_timestamp") or _candle_field(c, "timestamp")) == series[-1]["timestamp"])
    rec["latest_timestamp_utc"] = _candle_field(last, "normalized_utc_timestamp") or _candle_field(last, "timestamp")
    rec["latest_timestamp_cairo"] = _candle_field(last, "normalized_cairo_timestamp")
    rec["timestamp_semantics"] = _candle_field(last, "timestamp_semantics")
    rec["volume_semantics"] = _candle_field(last, "volume_semantics")
    rec["provider_mode"] = _candle_field(last, "provider_mode") or rec.get("provider_mode")
    rec["latest_close"] = _candle_field(last, "close")
    sess = _candle_field(last, "session_date") or session_date_cairo(
        rec["latest_timestamp_cairo"] or rec["latest_timestamp_utc"]
    )
    rec["session_date"] = sess
    rec["current_session"] = sess == today_cairo
    rec["data_state"] = "CURRENT_SESSION" if rec["current_session"] else "HISTORICAL"
    ts = rec["latest_timestamp_utc"]
    if ts:
        rec["freshness"], _ = classify_freshness(ts)
    if keep_ohlcv:
        ohlcv[iv] = series
        interval_source[iv] = used_source
        future_rejected = int(stats.get("future_timestamp_records_rejected") or 0)
        stale_rejected = int(stats.get("stale_records_rejected") or 0)
        rec["ohlcv_bars"] = len(series)
        rec["volume_present"] = any(b.get("volume") is not None for b in series)
    if store_candles and db is not None:
        for c in accepted:
            row = _candle_to_row(c)
            row.setdefault("provider", used_source)
            row.setdefault("interval", iv)
            try:
                db.upsert_candle(row)
            except Exception:
                pass
    return last, future_rejected, stale_rejected


def enrich_shortlist_intraday(
    tickers: list[str],
    *,
    tv=None,
    intervals: tuple[str, ...] = INTRADAY_INTERVALS,
    n_bars: int = 80,
    fetch_candles: Callable | None = None,
    db=None,
    store_candles: bool = False,
    retries: int = 1,
    cutoff: str | None = None,
    keep_ohlcv: bool = True,
    live_fetch: bool = True,
    fallback_fetch: Callable | None = None,
    allow_yahoo_fallback: bool = True,
    base_delay: float = 0.8,
    **_extra: Any,
) -> dict[str, Any]:
    """Query the live provider for selected tickers. Never silently drop a ticker."""
    queried = list(dict.fromkeys(t.upper() for t in tickers if t))
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    by_ticker: dict[str, dict[str, Any]] = {}
    fetched_at = utc_now()
    cutoff = cutoff or fetched_at
    from egxbridge.analysis.common.data_stamp import parse_dt
    today_cairo = parse_dt(cutoff).astimezone(ZoneInfo("Africa/Cairo")).date().isoformat()
    expected_session = previous_egx_session_date(parse_dt(cutoff))
    future_rejected = 0
    stale_rejected = 0
    retry_budget_used = 0

    tv_ready = True
    if fetch_candles is None:
        if tv is None or getattr(tv, "_tv", None) is None or not getattr(tv, "enabled", True):
            tv_ready = False

    if fetch_candles is not None and fallback_fetch is None:
        allow_yahoo_fallback = False
    if not live_fetch:
        allow_yahoo_fallback = False

    yahoo_fn = fallback_fetch
    yahoo_built = False

    def _primary(symbol: str, interval: str):
        if fetch_candles is not None:
            return fetch_candles(symbol, interval, n_bars)
        if tv is None:
            raise RuntimeError("intraday provider unavailable")
        return tv.get_candles(symbol, interval, n_bars=n_bars)

    def _fallback(symbol: str, interval: str):
        nonlocal yahoo_fn, yahoo_built
        if yahoo_fn is None and allow_yahoo_fallback and not yahoo_built:
            yahoo_built = True
            yahoo_fn = build_yahoo_fallback()
        if yahoo_fn is None:
            return None
        return yahoo_fn(symbol, interval, n_bars)

    def _history_1m(symbol: str) -> dict[str, list[dict[str, Any]]]:
        if db is None:
            return {}
        try:
            raw = db.fetch_candles(symbol, "1m", limit=4000)
        except Exception:
            return {}
        bars, _stats = serialize_ohlcv(list(reversed(raw)), cutoff=cutoff, current_session_only=False)
        grouped = group_bars_by_session(bars)
        grouped.pop(today_cairo, None)
        return grouped

    circuit_reason: str | None = None
    consecutive_provider_faults = 0

    for t in queried:
        diag = empty_ticker_diagnostics(t, provider_symbol=provider_symbol_for(t))
        interval_rows = []
        ohlcv: dict[str, list[dict[str, Any]]] = {}
        interval_source: dict[str, str] = {}
        any_live = False
        best_candle = None
        best_rank = None
        interval_rank = {iv: i for i, iv in enumerate(("1m", "5m", "15m", "30m", "1h"))}
        ticker_attempts = 0
        first_attempt = None
        last_attempt = None
        last_error_class = None
        last_error_msg = None
        live_state_votes: list[str] = []
        fallback_used = False
        fallback_source = None

        skip_live = not live_fetch
        skip_primary = skip_live or bool(circuit_reason) or (not tv_ready and fetch_candles is None)
        if circuit_reason and live_fetch:
            last_error_class = circuit_reason
            last_error_msg = sanitize_error_message(f"provider circuit open ({circuit_reason})")
            live_state_votes.append(circuit_reason)
        elif skip_primary and not live_fetch:
            live_state_votes.append(NOT_REQUESTED)
        elif skip_primary and not tv_ready and fetch_candles is None:
            live_state_votes.append(PROVIDER_ERROR)

        for iv in intervals:
            rec = {
                "ticker": t,
                "interval": iv,
                "available": False,
                "bars": 0,
                "latest_timestamp_utc": None,
                "latest_timestamp_cairo": None,
                "latest_close": None,
                "session_date": None,
                "current_session": False,
                "timestamp_semantics": None,
                "volume_semantics": None,
                "provider_mode": getattr(tv, "mode", None) if tv is not None else None,
                "freshness": None,
                "failure_reason": None,
                "provider": "tradingview",
                "intraday_fetch_state": None,
                "cache_status": None,
                "provider_attempts": [],
            }
            candles: list[Any] = []
            used_source = "tradingview"

            if skip_primary:
                rec["failure_reason"] = None if skip_live else circuit_reason or PROVIDER_ERROR
                rec["intraday_fetch_state"] = NOT_REQUESTED if skip_live else SKIPPED if circuit_reason else PROVIDER_ERROR
                rec["error_class"] = "LIVE_FETCH_SKIPPED" if not circuit_reason else circuit_reason
            else:
                result = fetch_interval_with_retry(
                    lambda iv=iv, t=t: _primary(t, iv),
                    retries=retries,
                    base_delay=base_delay,
                )
                rec["provider_attempts"].append({"provider": "tradingview", **{k: v for k, v in result.items() if k != "candles"}})
                ticker_attempts += int(result.get("attempt_count") or 0)
                retry_budget_used += max(0, int(result.get("attempt_count") or 1) - 1)
                first_attempt = first_attempt or result.get("first_attempt_timestamp")
                last_attempt = result.get("last_attempt_timestamp") or last_attempt
                candles = list(result.get("candles") or [])
                rec["intraday_fetch_state"] = result.get("state")
                if result.get("state") != SUCCESS:
                    last_error_class = result.get("error_class") or result.get("state")
                    last_error_msg = result.get("error_message_sanitized")
                    live_state_votes.append(str(result.get("state") or UNKNOWN_FAILURE))
                if result.get("state") == SUCCESS:
                    used_source = _source_name(candles, "tradingview")
                else:
                    rec["failure_reason"] = result.get("state")

            if candles:
                last, fut, stl = _fill_interval_from_candles(
                    rec, candles, used_source=used_source, today_cairo=today_cairo,
                    cutoff=cutoff, keep_ohlcv=keep_ohlcv, store_candles=store_candles, db=db,
                    ohlcv=ohlcv, interval_source=interval_source,
                )
                future_rejected += fut
                stale_rejected += stl
                any_live = any_live or last is not None
                if last is None:
                    live_state_votes.append(PARSE_ERROR)
                    failures.append({**rec, "reason": rec["failure_reason"]})
                rank = interval_rank.get(iv, 99)
                score = (rec.get("session_date") or "", rec.get("latest_timestamp_utc") or "", -rank)
                if last is not None and (best_candle is None or best_rank is None or score > best_rank):
                    best_candle = last
                    best_rank = score
            else:
                rec["failure_reason"] = rec.get("failure_reason") or rec.get("intraday_fetch_state") or EMPTY_RESPONSE
                rec["available"] = False
                if not skip_primary:
                    failures.append({**rec, "reason": rec["failure_reason"]})

            interval_rows.append(rec)
            rows.append(rec)

        # Second pass: Yahoo (or injected fallback) only if the primary source failed every interval.
        if not any_live and allow_yahoo_fallback and not skip_live:
            for rec in interval_rows:
                iv = rec["interval"]
                fb = fetch_interval_with_retry(
                    lambda iv=iv, t=t: _fallback(t, iv) or [],
                    retries=min(1, retries),
                    base_delay=base_delay,
                )
                rec["provider_attempts"].append({"provider": "yahoo", **{k: v for k, v in fb.items() if k != "candles"}})
                ticker_attempts += int(fb.get("attempt_count") or 0)
                retry_budget_used += max(0, int(fb.get("attempt_count") or 1) - 1)
                last_attempt = fb.get("last_attempt_timestamp") or last_attempt
                first_attempt = first_attempt or fb.get("first_attempt_timestamp")
                candles = list(fb.get("candles") or [])
                if fb.get("state") != SUCCESS or not candles:
                    if fb.get("error_message_sanitized"):
                        last_error_msg = last_error_msg or fb.get("error_message_sanitized")
                    continue
                used_source = _source_name(candles, "yahoo")
                last, fut, stl = _fill_interval_from_candles(
                    rec, candles, used_source=used_source, today_cairo=today_cairo,
                    cutoff=cutoff, keep_ohlcv=keep_ohlcv, store_candles=store_candles, db=db,
                    ohlcv=ohlcv, interval_source=interval_source,
                )
                rec["fallback_used"] = True
                rec["fallback_source"] = used_source
                future_rejected += fut
                stale_rejected += stl
                if last is None:
                    continue
                any_live = True
                fallback_used = True
                fallback_source = used_source
                rank = interval_rank.get(iv, 99)
                score = (rec.get("session_date") or "", rec.get("latest_timestamp_utc") or "", -rank)
                if best_candle is None or best_rank is None or score > best_rank:
                    best_candle = last
                    best_rank = score

        # If the live fetch produced nothing, keep last-good bars as STALE_CACHE.
        stale_used = False
        stale_age = None
        stale_source_ts = None
        if not any_live:
            for iv in intervals:
                cached = load_stale_bars(db, t, iv, cutoff=cutoff)
                if not cached:
                    continue
                stale_used = True
                series = cached["series"]
                if keep_ohlcv and iv not in ohlcv:
                    ohlcv[iv] = series
                    interval_source[iv] = str(cached.get("provider") or "cache")
                rec_match = next((r for r in interval_rows if r.get("interval") == iv), None)
                last = cached.get("last") or {}
                if rec_match is not None:
                    rec_match["available"] = True
                    rec_match["bars"] = len(series)
                    rec_match["cache_status"] = "STALE_CACHE"
                    rec_match["status"] = "STALE_CACHE"
                    rec_match["intraday_fetch_state"] = NOT_REQUESTED if skip_live else SKIPPED if circuit_reason and not ticker_attempts else STALE_ONLY
                    rec_match["latest_timestamp_utc"] = last.get("timestamp")
                    rec_match["latest_timestamp_cairo"] = last.get("timestamp_cairo")
                    rec_match["latest_close"] = last.get("close")
                    rec_match["session_date"] = last.get("session_date")
                    rec_match["current_session"] = last.get("session_date") == today_cairo
                    rec_match["volume_semantics"] = last.get("volume_semantics")
                    rec_match["age_seconds"] = cached.get("age_seconds")
                    rec_match["point_in_time_valid"] = cached.get("point_in_time_valid")
                    rec_match["provider"] = cached.get("provider") or rec_match.get("provider")
                score = (last.get("session_date") or "", last.get("timestamp") or "", -interval_rank.get(iv, 99))
                if best_candle is None or best_rank is None or score > best_rank:
                    best_candle = {
                        "close": last.get("close"),
                        "normalized_utc_timestamp": last.get("timestamp"),
                        "normalized_cairo_timestamp": last.get("timestamp_cairo"),
                        "session_date": last.get("session_date"),
                        "timestamp": last.get("timestamp"),
                    }
                    best_rank = score
                    stale_age = cached.get("age_seconds")
                    stale_source_ts = cached.get("source_timestamp")

        fetch_state = SUCCESS if any_live else (STALE_ONLY if stale_used else (live_state_votes[0] if live_state_votes else (PROVIDER_ERROR if skip_live else EMPTY_RESPONSE)))
        if not any_live:
            if skip_live:
                fetch_state = NOT_REQUESTED
            elif circuit_reason and not ticker_attempts:
                fetch_state = SKIPPED
            elif not live_state_votes and not stale_used:
                fetch_state = EMPTY_RESPONSE
            elif live_state_votes:
                # Prefer the most severe observed reason.
                for cand in (RATE_LIMITED, TIMEOUT, SYMBOL_NOT_FOUND, PARSE_ERROR, PROVIDER_ERROR, EMPTY_RESPONSE, UNKNOWN_FAILURE):
                    if cand in live_state_votes:
                        fetch_state = cand
                        break
                if stale_used:
                    fetch_state = STALE_ONLY

        fault = next((state for state in (RATE_LIMITED, TIMEOUT) if state in live_state_votes), None)
        if any_live:
            consecutive_provider_faults = 0
        elif fault:
            consecutive_provider_faults += 1
            if consecutive_provider_faults >= _CIRCUIT_OPEN_AFTER and circuit_reason is None:
                circuit_reason = fault
        else:
            consecutive_provider_faults = 0

        last_price = _candle_field(best_candle, "close") if best_candle else None
        last_ts = (
            (_candle_field(best_candle, "normalized_utc_timestamp") or _candle_field(best_candle, "timestamp"))
            if best_candle else None
        )
        last_cairo = _candle_field(best_candle, "normalized_cairo_timestamp") if best_candle else None
        last_sess = _candle_field(best_candle, "session_date") if best_candle else None
        if not last_sess and last_cairo:
            last_sess = session_date_cairo(last_cairo)
        finished_at = utc_now()
        delay = delay_seconds(finished_at, last_ts) if last_ts else stale_age
        prev_full = None
        if db is not None:
            try:
                daily = db.fetch_candles(t, "1d", limit=5)
                if daily:
                    prev_full = daily[0].get("volume")
            except Exception:
                prev_full = None

        metric_ohlcv = dict(ohlcv)
        sources = set(interval_source.values())
        if len(sources) > 1 and "tradingview" in sources:
            metric_ohlcv = {k: v for k, v in ohlcv.items() if interval_source.get(k) == "tradingview"}

        vol_metrics = session_volume_metrics(
            bars_1m=metric_ohlcv.get("1m") or [],
            bars_5m=metric_ohlcv.get("5m") or [],
            bars_15m=metric_ohlcv.get("15m") or [],
            previous_full_session_volume=prev_full,
            historical_1m_by_session=_history_1m(t),
            at=cutoff,
            last_price=last_price,
        )

        bars_1m = next((r.get("bars") or 0 for r in interval_rows if r.get("interval") == "1m"), 0)
        bars_5m = next((r.get("bars") or 0 for r in interval_rows if r.get("interval") == "5m"), 0)
        bars_15m = next((r.get("bars") or 0 for r in interval_rows if r.get("interval") == "15m"), 0)
        diag.update({
            "intraday_fetch_state": fetch_state,
            "provider_symbol": provider_symbol_for(t, source=fallback_source or "tradingview") if fallback_used else provider_symbol_for(t),
            "attempt_count": ticker_attempts,
            "first_attempt_timestamp": first_attempt,
            "last_attempt_timestamp": last_attempt,
            "error_class": None if fetch_state in {SUCCESS, NOT_REQUESTED} else (last_error_class or fetch_state),
            "error_message_sanitized": None if fetch_state == SUCCESS else last_error_msg,
            "bars_returned_1m": int(bars_1m or 0),
            "bars_returned_5m": int(bars_5m or 0),
            "bars_returned_15m": int(bars_15m or 0),
            "latest_bar_timestamp": last_ts or stale_source_ts,
            "cache_status": "STALE_CACHE" if stale_used and not any_live else ("AVAILABLE" if any_live else None),
            "age_seconds": delay if stale_used and not any_live else None,
            "fallback_used": fallback_used,
            "fallback_source": fallback_source,
        })
        status = "AVAILABLE" if any_live else ("STALE_CACHE" if stale_used else "SOURCE_UNAVAILABLE")
        by_ticker[t] = {
            "ticker": t,
            "intraday_available": any_live,
            "intervals": interval_rows,
            "ohlcv": ohlcv if keep_ohlcv else {},
            "queried_at": fetched_at,
            "last_price": last_price,
            "current_session_price": last_price if (any_live and last_sess == today_cairo) else None,
            "session_date": last_sess,
            "current_session": bool(any_live and last_sess == today_cairo),
            "normalized_utc_timestamp": last_ts,
            "normalized_cairo_timestamp": last_cairo,
            "expected_completed_session": expected_session,
            "provider": fallback_source or ("cache" if stale_used and not any_live else "tradingview"),
            "source": fallback_source or ("cache" if stale_used and not any_live else "tradingview"),
            "source_timestamp": last_ts or stale_source_ts,
            "retrieval_timestamp": finished_at,
            "fetch_started_at": first_attempt,
            "fetch_finished_at": finished_at if ticker_attempts else None,
            "data_state": "CURRENT_SESSION" if any_live and last_sess == today_cairo else "HISTORICAL" if last_ts else "MISSING",
            "exchange_timestamp_if_available": last_cairo,
            "data_delay_seconds": delay,
            "data_delay_seconds_or_minutes": delay,
            "is_delayed": True,
            "point_in_time_valid": bool(last_ts) and (not stale_used or bool(timestamp_guard(last_ts, cutoff=cutoff).get("point_in_time_valid"))),
            "status": status,
            "cache_status": diag["cache_status"],
            "age_seconds": diag["age_seconds"],
            "session_volume": vol_metrics,
            "depth": unavailable_book(),
            "trades": unavailable_tape(),
            **diag,
        }

    diagnostics = summarize_fetch_diagnostics(
        {t: by_ticker[t] for t in queried},
        retries=retry_budget_used,
    )
    today_n = sum(1 for v in by_ticker.values() if v.get("current_session") and v.get("intraday_fetch_state") == SUCCESS)
    ohlcv_n = sum(
        1 for v in by_ticker.values()
        if any((v.get("ohlcv") or {}).values())
    )
    return {
        "queried_tickers": queried,
        "rows": rows,
        "failures": failures,
        "by_ticker": by_ticker,
        "intraday_enriched": sum(1 for v in by_ticker.values() if v.get("intraday_fetch_state") == SUCCESS),
        "today_session_enriched": today_n,
        "intraday_ohlcv_count": ohlcv_n,
        "stale_cache_count": sum(1 for v in by_ticker.values() if v.get("status") == "STALE_CACHE"),
        "today_session": today_cairo,
        "fetch_started_at": fetched_at,
        "fetched_at": utc_now() if live_fetch else None,
        "live_fetch_requested": live_fetch,
        "future_timestamp_records_rejected": future_rejected,
        "stale_records_rejected": stale_rejected,
        "lookahead_guard_pass": future_rejected == 0,
        "intraday_fetch_diagnostics": diagnostics,
        "note": "Intraday enrichment must not redefine Funnel Fair Value or quality scores",
    }
