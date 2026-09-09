"""Intraday fetch reliability: diagnostics, retries, stale cache, fallback.

Does not change CSS / QB / BRAE / scoring weights.
"""
from __future__ import annotations

import re
import time
from collections import Counter
from typing import Any, Callable

from egxbridge.analysis.common.data_stamp import delay_seconds
from egxbridge.analysis.common.models import utc_now
from egxbridge.analysis.explorer.session_volume import serialize_ohlcv, timestamp_guard
from egxbridge.universe import tradingview_alias, yahoo_alias


SUCCESS = "SUCCESS"
NOT_REQUESTED = "NOT_REQUESTED"
SKIPPED = "SKIPPED"
EMPTY_RESPONSE = "EMPTY_RESPONSE"
PROVIDER_ERROR = "PROVIDER_ERROR"
SYMBOL_NOT_FOUND = "SYMBOL_NOT_FOUND"
RATE_LIMITED = "RATE_LIMITED"
TIMEOUT = "TIMEOUT"
STALE_ONLY = "STALE_ONLY"
PARSE_ERROR = "PARSE_ERROR"
UNKNOWN_FAILURE = "UNKNOWN_FAILURE"

FETCH_STATES = (
    SUCCESS,
    NOT_REQUESTED,
    SKIPPED,
    EMPTY_RESPONSE,
    PROVIDER_ERROR,
    SYMBOL_NOT_FOUND,
    RATE_LIMITED,
    TIMEOUT,
    STALE_ONLY,
    PARSE_ERROR,
    UNKNOWN_FAILURE,
)

PERMANENT_STATES = {SYMBOL_NOT_FOUND, PARSE_ERROR, EMPTY_RESPONSE, RATE_LIMITED}

PROVIDER_HEALTHY = "HEALTHY"
PROVIDER_DEGRADED = "DEGRADED"
PROVIDER_FAILED = "FAILED"

# 0/N or abnormally few live bars must never look like ordinary missing data.
FAILED_SUCCESS_PCT = 20.0
HEALTHY_SUCCESS_PCT = 70.0

_SECRET_RE = re.compile(
    r"(?i)(password|passwd|token|secret|api[_-]?key|authorization)\s*[:=]\s*\S+"
)


def sanitize_error_message(exc: BaseException | str | None, *, max_len: int = 240) -> str | None:
    if exc is None:
        return None
    text = str(exc).strip()
    if not text:
        return None
    text = _SECRET_RE.sub(r"\1=***", text)
    text = re.sub(r"\S+@\S+", "***@***", text)
    if "Traceback" in text or 'File "' in text:
        text = text.splitlines()[-1] if text.splitlines() else "error"
    return text[:max_len]


def classify_fetch_error(exc: BaseException | None) -> str:
    if exc is None:
        return UNKNOWN_FAILURE
    msg = str(exc).lower()
    http = getattr(exc, "http_status", None)
    code = str(getattr(exc, "code", "") or "").upper()
    name = type(exc).__name__.lower()
    if http == 429 or "429" in msg or "rate limit" in msg or "too many" in msg:
        return RATE_LIMITED
    if http in {404, 400} and any(k in msg for k in ("symbol", "ticker", "not found")):
        return SYMBOL_NOT_FOUND
    if "timeout" in msg or "timed out" in msg or name in {"timeouterror", "readtimeout", "connecttimeout"}:
        return TIMEOUT
    if any(k in msg for k in (
        "symbol not found", "unknown symbol", "invalid symbol", "no such symbol",
        "not mapped", "no tv mapping", "ticker not found",
    )):
        return SYMBOL_NOT_FOUND
    if any(k in msg for k in ("json", "parse", "decode", "expecting value", "invalid literal")):
        return PARSE_ERROR
    if code in {"SYMBOL_NOT_FOUND", "NOT_FOUND"}:
        return SYMBOL_NOT_FOUND
    if code == EMPTY_RESPONSE or "no tv candles for " in msg or "no yahoo candles for " in msg:
        return EMPTY_RESPONSE
    if isinstance(exc, (ValueError, TypeError, KeyError)) and "candle" in msg:
        return PARSE_ERROR
    if "disabled" in msg or "unavailable" in msg or "import" in msg:
        return PROVIDER_ERROR
    return PROVIDER_ERROR


def classify_provider_state(*, selected: int, success: int) -> str:
    selected = max(0, int(selected or 0))
    success = max(0, int(success or 0))
    if selected <= 0:
        return PROVIDER_HEALTHY
    pct = 100.0 * success / float(selected)
    if success == 0 or pct < FAILED_SUCCESS_PCT:
        return PROVIDER_FAILED
    if pct < HEALTHY_SUCCESS_PCT:
        return PROVIDER_DEGRADED
    return PROVIDER_HEALTHY


def empty_ticker_diagnostics(ticker: str, *, provider_symbol: str | None = None) -> dict[str, Any]:
    t = str(ticker or "").upper()
    return {
        "ticker": t,
        "intraday_fetch_state": UNKNOWN_FAILURE,
        "provider_symbol": provider_symbol or tradingview_alias(t),
        "attempt_count": 0,
        "first_attempt_timestamp": None,
        "last_attempt_timestamp": None,
        "error_class": None,
        "error_message_sanitized": None,
        "bars_returned_1m": 0,
        "bars_returned_5m": 0,
        "bars_returned_15m": 0,
        "latest_bar_timestamp": None,
        "cache_status": None,
        "age_seconds": None,
        "fallback_used": False,
        "fallback_source": None,
    }


def summarize_fetch_diagnostics(
    per_ticker: dict[str, dict[str, Any]] | list[dict[str, Any]],
    *,
    retries: int = 0,
) -> dict[str, Any]:
    rows = list(per_ticker.values()) if isinstance(per_ticker, dict) else list(per_ticker or [])
    selected = len(rows)
    success = sum(1 for r in rows if r.get("intraday_fetch_state") == SUCCESS)
    skipped = sum(1 for r in rows if r.get("intraday_fetch_state") in {NOT_REQUESTED, SKIPPED})
    requested = selected - skipped
    failed = max(0, requested - success)
    reasons = Counter(str(r.get("intraday_fetch_state") or UNKNOWN_FAILURE) for r in rows if r.get("intraday_fetch_state") not in {NOT_REQUESTED, SKIPPED})
    reasons.pop(SUCCESS, None)
    pct = round(100.0 * success / float(requested), 2) if requested else None
    state = classify_provider_state(selected=requested, success=success) if requested else NOT_REQUESTED
    return {
        "selected": selected,
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "requested": requested,
        "attempt_count": sum(int(r.get("attempt_count") or 0) for r in rows),
        "success_pct": pct,
        "provider_state": state,
        "retries": int(retries or 0),
        "failures_by_reason": dict(reasons),
        "INTRADAY_PROVIDER_STATE": state,
    }


def apply_provider_state_to_coverage(coverage: dict[str, Any] | None, diagnostics: dict[str, Any] | None) -> dict[str, Any]:
    """Provider failure cannot look like a healthy whole-EGX run."""
    out = dict(coverage or {})
    state = (diagnostics or {}).get("provider_state") or (diagnostics or {}).get("INTRADAY_PROVIDER_STATE")
    if state in {PROVIDER_FAILED, PROVIDER_DEGRADED, NOT_REQUESTED}:
        out["whole_egx_claim_allowed"] = False
        out["run_scope"] = "PARTIAL_UNIVERSE"
        if state in {PROVIDER_FAILED, NOT_REQUESTED}:
            out["live_session_evidence_available"] = False
            out["coverage_status"] = out.get("coverage_status") or "NOT_RELIABLE"
    out["intraday_provider_state"] = state
    return out


def load_stale_bars(
    db,
    ticker: str,
    interval: str,
    *,
    cutoff: str | None,
    limit: int = 400,
) -> dict[str, Any] | None:
    if db is None:
        return None
    try:
        raw = db.fetch_candles(str(ticker).upper(), interval, limit=limit) or []
    except Exception:
        return None
    if not raw:
        return None
    provider = raw[0].get("provider")
    chronological = list(reversed([r for r in raw if r.get("provider") == provider]))
    series, _stats = serialize_ohlcv(chronological, cutoff=cutoff, current_session_only=False)
    if not series:
        return None
    last = series[-1]
    src_ts = last.get("timestamp")
    age = delay_seconds(cutoff or utc_now(), src_ts) if src_ts else None
    guard = timestamp_guard(src_ts, cutoff=cutoff or utc_now())
    for bar in series:
        bar["status"] = "STALE_CACHE"
        bar["cache_status"] = "STALE_CACHE"
        bar["age_seconds"] = delay_seconds(cutoff or utc_now(), bar.get("timestamp"))
        bar["point_in_time_valid"] = bool(timestamp_guard(bar.get("timestamp"), cutoff=cutoff or utc_now()).get("point_in_time_valid"))
    return {
        "series": series,
        "last": last,
        "age_seconds": age,
        "source_timestamp": src_ts,
        "status": "STALE_CACHE",
        "point_in_time_valid": bool(guard.get("point_in_time_valid")),
        "provider": (raw[0].get("provider") if isinstance(raw[0], dict) else None) or "cache",
    }


def fetch_interval_with_retry(
    fn: Callable[[], Any],
    *,
    retries: int = 2,
    base_delay: float = 0.8,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Bounded exponential backoff. Permanent mapping/parse failures are not retried."""
    attempts = 0
    first_ts = None
    last_ts = None
    state = UNKNOWN_FAILURE
    error_class = None
    error_message = None
    candles: list[Any] = []
    max_tries = max(0, int(retries)) + 1
    for i in range(max_tries):
        attempts += 1
        now = utc_now()
        first_ts = first_ts or now
        last_ts = now
        try:
            candles = list(fn() or [])
            if candles:
                return {
                    "state": SUCCESS,
                    "candles": candles,
                    "attempt_count": attempts,
                    "first_attempt_timestamp": first_ts,
                    "last_attempt_timestamp": last_ts,
                    "error_class": None,
                    "error_message_sanitized": None,
                }
            state = EMPTY_RESPONSE
            error_class = EMPTY_RESPONSE
            error_message = "provider returned zero bars"
        except Exception as exc:
            state = classify_fetch_error(exc)
            error_class = type(exc).__name__
            error_message = sanitize_error_message(exc)
            candles = []
            if state in PERMANENT_STATES:
                break
        if state in PERMANENT_STATES:
            break
        if i < max_tries - 1:
            delay = float(base_delay) * (2 ** i)
            if delay > 0:
                sleep(delay)
    return {
        "state": state,
        "candles": candles,
        "attempt_count": attempts,
        "first_attempt_timestamp": first_ts,
        "last_attempt_timestamp": last_ts,
        "error_class": error_class,
        "error_message_sanitized": error_message,
    }


def build_yahoo_fallback() -> Callable[..., Any] | None:
    try:
        from egxbridge.config import Settings
        from egxbridge.providers.yahoo import YahooProvider
        from egxbridge.symbols import SymbolRegistry

        settings = Settings.load()
        registry = SymbolRegistry.from_config({"symbol_aliases": settings.symbol_aliases})
        yahoo = YahooProvider(
            registry,
            enabled=bool((settings.enabled_providers or {}).get("yahoo", True)),
        )
        if not getattr(yahoo, "enabled", True):
            return None

        def _fetch(symbol: str, interval: str, n_bars: int):
            return yahoo.get_candles(symbol, interval, n_bars=n_bars)

        return _fetch
    except Exception:
        return None


def provider_symbol_for(ticker: str, *, source: str = "tradingview") -> str:
    t = str(ticker or "").upper()
    if source == "yahoo":
        return yahoo_alias(t)
    return tradingview_alias(t)
