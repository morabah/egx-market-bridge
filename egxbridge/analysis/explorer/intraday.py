"""TradingView intraday enrichment for Explorer shortlist only."""
from __future__ import annotations

from typing import Any, Callable

from egxbridge.analysis.common.models import utc_now
from egxbridge.freshness import classify_freshness
from egxbridge.providers.base import ProviderError


INTRADAY_INTERVALS = ("1m", "5m", "15m", "30m", "1h")


def _classify_tv_failure(exc: BaseException) -> str:
    msg = str(exc).lower()
    http = getattr(exc, "http_status", None)
    if http == 429 or "429" in msg or "rate" in msg:
        return "RATE_LIMITED"
    if "timeout" in msg:
        return "TIMEOUT"
    if "no tv" in msg or "no data" in msg or "no candles" in msg:
        return "NO_DATA"
    if "disabled" in msg or "missing" in msg or "unavailable" in msg:
        return "PROVIDER_ERROR"
    return "PROVIDER_ERROR"


def enrich_shortlist_intraday(
    tickers: list[str],
    *,
    tv=None,
    intervals: tuple[str, ...] = INTRADAY_INTERVALS,
    n_bars: int = 80,
    fetch_candles: Callable | None = None,
) -> dict[str, Any]:
    """Query TradingView only for the shortlist. Missing interval ≠ candidate failure."""
    queried = list(dict.fromkeys(t.upper() for t in tickers if t))
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    by_ticker: dict[str, dict[str, Any]] = {}

    tv_ready = True
    if fetch_candles is None:
        if tv is None or getattr(tv, "_tv", None) is None or not getattr(tv, "enabled", True):
            tv_ready = False

    def _fetch(symbol: str, interval: str):
        if fetch_candles is not None:
            return fetch_candles(symbol, interval, n_bars)
        return tv.get_candles(symbol, interval, n_bars=n_bars)

    for t in queried:
        interval_rows = []
        any_ok = False
        for iv in intervals:
            rec = {
                "ticker": t,
                "interval": iv,
                "available": False,
                "bars": 0,
                "latest_timestamp_utc": None,
                "latest_timestamp_cairo": None,
                "timestamp_semantics": None,
                "volume_semantics": None,
                "provider_mode": getattr(tv, "mode", None) if tv is not None else None,
                "freshness": None,
                "failure_reason": None,
                "provider": "tradingview",
            }
            if not tv_ready:
                rec["failure_reason"] = "PROVIDER_UNAVAILABLE"
                interval_rows.append(rec)
                failures.append({**rec, "reason": rec["failure_reason"]})
                continue
            try:
                candles = _fetch(t, iv) or []
                rec["bars"] = len(candles)
                rec["available"] = len(candles) > 0
                if candles:
                    last = candles[-1]
                    rec["latest_timestamp_utc"] = getattr(last, "normalized_utc_timestamp", None) or (
                        last.get("normalized_utc_timestamp") if isinstance(last, dict) else None
                    )
                    rec["latest_timestamp_cairo"] = getattr(last, "normalized_cairo_timestamp", None) or (
                        last.get("normalized_cairo_timestamp") if isinstance(last, dict) else None
                    )
                    rec["timestamp_semantics"] = getattr(last, "timestamp_semantics", None) or (
                        last.get("timestamp_semantics") if isinstance(last, dict) else None
                    )
                    rec["volume_semantics"] = getattr(last, "volume_semantics", None) or (
                        last.get("volume_semantics") if isinstance(last, dict) else None
                    )
                    rec["provider_mode"] = getattr(last, "provider_mode", rec["provider_mode"]) or (
                        last.get("provider_mode") if isinstance(last, dict) else rec["provider_mode"]
                    )
                    ts = rec["latest_timestamp_utc"]
                    if ts:
                        rec["freshness"], _ = classify_freshness(ts)
                    any_ok = True
                else:
                    rec["failure_reason"] = "NO_DATA"
                    failures.append({**rec, "reason": "NO_DATA"})
            except Exception as e:
                rec["failure_reason"] = _classify_tv_failure(e)
                rec["available"] = False
                failures.append({**rec, "reason": rec["failure_reason"], "error": str(e)})
            interval_rows.append(rec)
            rows.append(rec)
        by_ticker[t] = {
            "ticker": t,
            "intraday_available": any_ok,
            "intervals": interval_rows,
            "queried_at": utc_now(),
        }

    return {
        "queried_tickers": queried,
        "rows": rows,
        "failures": failures,
        "by_ticker": by_ticker,
        "intraday_enriched": sum(1 for v in by_ticker.values() if v.get("intraday_available")),
        "note": "Intraday enrichment must not redefine Funnel Fair Value or quality scores",
    }
