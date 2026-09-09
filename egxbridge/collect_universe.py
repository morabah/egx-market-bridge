"""Broad EGX universe daily collection (Yahoo primary). Incremental, conservative."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any
import argparse
import logging
import json
import threading
import time

from egxbridge import __version__ as BRIDGE_VERSION
from egxbridge.config import Settings
from egxbridge.db import Database
from egxbridge.daily_bars import daily_session_status, select_daily_pool, session_of, completed_session_rows, captured_after_session_close, ohlcv_issue
from egxbridge.providers.base import ProviderError
from egxbridge.providers.tradingview import TradingViewProvider
from egxbridge.providers.yahoo import YahooProvider
from egxbridge.resilience import CircuitBreaker, RateLimiter
from egxbridge.scanner import compute_scanner_metrics
from egxbridge.semantics import DAILY_BAR, DAILY_CLOSE, DAILY_FINAL_VOLUME, previous_egx_session_date
from egxbridge.symbols import SymbolRegistry
from egxbridge.universe import (
    EQUITY,
    UniverseRecord,
    build_canonical_universe,
)

HERE = Path(__file__).resolve().parent.parent
log = logging.getLogger("egxbridge.collect_universe")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

SUCCESS = "SUCCESS"
NO_MAPPING = "NO_MAPPING"
NO_DATA = "NO_DATA"
PROVIDER_ERROR = "PROVIDER_ERROR"
RATE_LIMITED = "RATE_LIMITED"
TIMEOUT = "TIMEOUT"
INVALID_SYMBOL = "INVALID_SYMBOL"
STALE_EXPECTED = "STALE_EXPECTED"
STALE_UNEXPECTED = "STALE_UNEXPECTED"
UNKNOWN_FAILURE = "UNKNOWN_FAILURE"
CACHE_HIT = "CACHE_HIT"
EXCLUDED = "EXCLUDED_SECURITY_TYPE"

OVERLAP_CALENDAR_DAYS = 14
OHLCV_EPS = 1e-6
RETRY_COOLDOWN_SECONDS = 900
COLLECTION_BUDGET_SECONDS = 300


def _f(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def classify_failure(exc: BaseException, *, has_mapping: bool) -> str:
    if not has_mapping:
        return NO_MAPPING
    msg = str(exc).lower()
    code = getattr(exc, "code", None)
    http = getattr(exc, "http_status", None)
    if http == 429 or "429" in msg or "rate limit" in msg or "too many" in msg:
        return RATE_LIMITED
    if "timeout" in msg or "timed out" in msg:
        return TIMEOUT
    if "invalid" in msg or "delisted" in msg or "not found" in msg:
        return INVALID_SYMBOL
    if "no yahoo candles" in msg or "no tv candles" in msg or "no data" in msg or "no yahoo quote" in msg:
        return NO_DATA
    if isinstance(exc, ProviderError):
        if code == "NO_DATA":
            return NO_DATA
        return PROVIDER_ERROR
    return UNKNOWN_FAILURE


def _close_enough(a, b) -> bool:
    fa, fb = _f(a), _f(b)
    if fa is None and fb is None:
        return True
    if fa is None or fb is None:
        return False
    return abs(fa - fb) <= OHLCV_EPS


def _bar_count(db: Database, symbol: str, provider: str | None = "yahoo") -> int:
    try:
        if provider:
            row = db._conn.execute(
                "SELECT COUNT(*) AS c FROM candles WHERE symbol=? AND interval='1d' AND provider=?",
                (symbol.upper(), provider),
            ).fetchone()
        else:
            row = db._conn.execute(
                "SELECT COUNT(*) AS c FROM candles WHERE symbol=? AND interval='1d'",
                (symbol.upper(),),
            ).fetchone()
        return int(row["c"] if hasattr(row, "keys") else row[0])
    except Exception:
        return 0


def _existing_row(db: Database, symbol: str, interval: str, timestamp: str, provider: str):
    return db._conn.execute(
        """SELECT open, high, low, close, volume, capture_timestamp, semantics_json FROM candles
           WHERE symbol=? AND interval=? AND timestamp=? AND provider=?""",
        (symbol, interval, timestamp, provider),
    ).fetchone()


def merge_daily_candles(
    db: Database,
    candles: list[dict[str, Any]],
    *,
    refresh: bool = False,
) -> dict[str, int]:
    """De-dupe by canonical_symbol + session/timestamp + provider + interval.

    Recent provider corrections replace old values with an audit trail. Older history
    is retained unless refresh=True; older captures never overwrite newer captures.
    """
    inserted = 0
    skipped = 0
    conflicts = 0
    rejected = 0
    recent_cutoff = (datetime.fromisoformat(previous_egx_session_date()) - timedelta(days=OVERLAP_CALENDAR_DAYS)).date().isoformat()
    with db._conn:
        for c in candles:
            d = dict(c)
            d.setdefault("interval", "1d")
            d.setdefault("provider", "yahoo")
            d["price_observation_type"] = d.get("price_observation_type") or DAILY_CLOSE
            d["timestamp_semantics"] = d.get("timestamp_semantics") or DAILY_BAR
            d["volume_semantics"] = d.get("volume_semantics") or DAILY_FINAL_VOLUME
            d["volume_interval"] = d.get("volume_interval") or "1d"
            ts = d.get("normalized_utc_timestamp") or d.get("timestamp")
            if not ts or not d.get("symbol"):
                skipped += 1
                continue
            prev = _existing_row(db, d["symbol"], d["interval"], ts, d["provider"])
            issue = ohlcv_issue(d)
            if issue:
                rejected += 1
                db.insert_conflict({
                    "symbol": d["symbol"], "field": "daily_ohlcv_validation",
                    "provider_a": d["provider"], "provider_b": d["provider"],
                    "timestamp_a": ts, "timestamp_b": ts,
                    "value_b": json.dumps(d, default=str),
                    "selected_provider": "local_existing" if prev else "REJECTED",
                    "reason": issue, "created_at": utc_now(),
                }, commit=False)
                continue
            if prev is not None:
                old_capture = prev["capture_timestamp"] or ""
                if old_capture and d.get("capture_timestamp") and d["capture_timestamp"] < old_capture:
                    skipped += 1
                    continue
                replace = refresh or session_of(d) >= recent_cutoff
                keys = ("open", "high", "low", "close", "volume")
                if all(_close_enough(prev[k] if hasattr(prev, "keys") else prev[i], d.get(k))
                       for i, k in enumerate(keys)):
                    semantics = json.loads(prev["semantics_json"] or "{}")
                    old_final = semantics.get("daily_session_complete") is not False and captured_after_session_close({**dict(prev), **semantics})
                    if not old_final and d.get("daily_session_complete") is True and captured_after_session_close(d):
                        db.upsert_candle(d, commit=False)
                        inserted += 1
                        continue
                    skipped += 1
                    continue
                conflicts += 1
                db.insert_conflict({
                    "symbol": d["symbol"],
                    "field": "daily_ohlcv",
                    "provider_a": d["provider"],
                    "value_a": {k: (prev[k] if hasattr(prev, "keys") else prev[i]) for i, k in enumerate(keys)},
                    "timestamp_a": ts,
                    "provider_b": d["provider"],
                    "value_b": {k: d.get(k) for k in keys},
                    "timestamp_b": ts,
                    "selected_provider": d["provider"] if replace else "local_existing",
                    "reason": "incremental_history_conflict",
                    "created_at": utc_now(),
                }, commit=False)
                log.warning("daily conflict %s %s kept=%s", d["symbol"], ts, "new" if replace else "existing")
                if not replace:
                    skipped += 1
                    continue
            db.upsert_candle(d, commit=False)
            inserted += 1
    return {"inserted": inserted, "skipped": skipped, "conflicts": conflicts, "rejected": rejected}


def _candle_to_store(c) -> dict[str, Any]:
    d = c.to_dict() if hasattr(c, "to_dict") else dict(c)
    d["price_observation_type"] = DAILY_CLOSE
    d["timestamp_semantics"] = d.get("timestamp_semantics") or DAILY_BAR
    d["volume_semantics"] = DAILY_FINAL_VOLUME
    d["volume_interval"] = "1d"
    d["daily_session_complete"] = d.get("daily_session_complete") is not False and captured_after_session_close(d)
    return d


def collect_one_symbol(
    rec: UniverseRecord, *, db: Database, yahoo: YahooProvider | None,
    registry: SymbolRegistry, limiter: RateLimiter, limiter_lock: threading.Lock,
    breaker: CircuitBreaker, history_days: int, min_cache_bars: int,
    refresh: bool, dry_run: bool, tradingview: TradingViewProvider | None = None,
    use_tradingview_fallback: bool = False, expected_session: str | None = None,
    tv_breaker: CircuitBreaker | None = None,
    previous_result: dict[str, Any] | None = None,
    deadline: float | None = None,
) -> dict[str, Any]:
    t0 = time.monotonic()
    sym = rec.canonical_symbol
    expected = expected_session or previous_egx_session_date()
    out = {
        "ticker": sym, "company_name": rec.display_name_if_known,
        "security_type": rec.security_type, "yahoo_alias": rec.provider_alias_yahoo,
        "status": UNKNOWN_FAILURE, "cache_hit": False, "network_fetch": False,
        "bars_stored": 0, "bars_fetched": 0, "error": None,
        "incremental": False, "conflicts": 0, "started_at": utc_now(),
        "expected_session": expected, "attempts": [],
    }
    def finish(status):
        out["status"] = status
        out["finished_at"] = utc_now()
        out["latency_ms"] = round((time.monotonic() - t0) * 1000, 2)
        return out

    if rec.security_type != EQUITY:
        out["error"] = rec.exclusion_reason or f"EXCLUDED_{rec.security_type}"
        return finish(EXCLUDED)
    if not rec.mapped:
        return finish(NO_MAPPING)
    if not dry_run:
        db.upsert_symbol(sym, name=rec.display_name_if_known, aliases={
            "yahoo": rec.provider_alias_yahoo, "tradingview": rec.provider_alias_tradingview,
            "egid": rec.provider_alias_egid,
        })

    def stored_pool():
        return select_daily_pool(db.fetch_candles(sym, "1d", limit=5000), through_session=expected)

    def describe(pool, provider):
        latest = pool[-1] if pool else {}
        out.update({
            "provider": provider, "bars_stored": len(pool),
            "first_session": session_of(pool[0]) if pool else None,
            "latest_session": session_of(latest) or None,
            "source_timestamp": latest.get("normalized_utc_timestamp") or latest.get("timestamp"),
            "data_captured_at": latest.get("capture_timestamp"),
            "data_state": "MISSING" if not pool else "STALE" if session_of(latest) < expected else "CURRENT",
            "history_sufficient": len(pool) >= min_cache_bars,
        })
    pool, provider, _ = stored_pool()
    describe(pool, provider)
    if not refresh and out["data_state"] == "CURRENT" and out["history_sufficient"]:
        out["cache_hit"] = True
        return finish(CACHE_HIT)
    if dry_run:
        return finish("DRY_RUN")
    previous = previous_result or {}
    if not refresh and previous.get("expected_session") == expected:
        try:
            retry_at = datetime.fromisoformat(previous["retry_after"])
            if datetime.now(timezone.utc) < retry_at:
                out.update(retry_deferred=True, retry_after=previous["retry_after"], error=previous.get("error"))
                return finish(previous.get("status") or NO_DATA)
        except (KeyError, TypeError, ValueError):
            pass

    n_bars = max(int(history_days), int(min_cache_bars), 120)
    providers = [("yahoo", yahoo, breaker)] if yahoo is not None else []
    if use_tradingview_fallback and tradingview is not None:
        providers.append(("tradingview", tradingview, tv_breaker or CircuitBreaker()))
    last_failure = NO_DATA
    for name, provider_obj, circuit in providers:
        if not getattr(provider_obj, "enabled", True):
            out["attempts"].append({"provider": name, "status": "DISABLED"})
            continue
        provider_rows = [r for r in db.fetch_candles(sym, "1d", limit=5000) if r.get("provider") == name]
        own_pool, _, _ = select_daily_pool(provider_rows, through_session=expected)
        start = None
        if not refresh and len(own_pool) >= min_cache_bars:
            start = (datetime.fromisoformat(session_of(own_pool[-1])) - timedelta(days=OVERLAP_CALENDAR_DAYS)).date().isoformat()
        for attempt in range(2):
            if deadline is not None and time.monotonic() >= deadline:
                out["attempts"].append({"provider": name, "status": "COLLECTION_TIME_LIMIT"})
                out["error"] = "Collection time limit reached. Remaining data gaps can be retried manually."
                last_failure = "COLLECTION_TIME_LIMIT"
                break
            with limiter_lock:
                allowed = circuit.allow()
                if allowed:
                    limiter.wait()
            if not allowed:
                out["attempts"].append({"provider": name, "status": "CIRCUIT_OPEN"})
                if not out["network_fetch"]:
                    last_failure = "CIRCUIT_OPEN"
                break
            out["network_fetch"] = True
            detail = {"provider": name, "attempt": attempt + 1, "started_at": utc_now()}
            try:
                kwargs = {"start": start} if name == "yahoo" and start else {}
                candles = provider_obj.get_candles(sym, "1d", n_bars=n_bars, **kwargs) or []
                payload = [_candle_to_store(c) for c in candles]
                for row in payload:
                    row["provider"] = name
                payload = completed_session_rows(payload, through_session=expected)
                with limiter_lock:
                    circuit.record_success()
                merge = merge_daily_candles(db, payload, refresh=refresh)
                out["conflicts"] += merge["conflicts"]
                out["bars_fetched"] += len(payload) - merge["rejected"]
                out["incremental"] = out["incremental"] or bool(kwargs)
                detail.update(status="INVALID_DATA" if merge["rejected"] else SUCCESS if payload else NO_DATA,
                              bars=len(payload) - merge["rejected"], rejected_bars=merge["rejected"])
                if name == "tradingview" and payload:
                    out["fallback_provider"] = name
                last_failure = NO_DATA
            except Exception as exc:
                last_failure = classify_failure(exc, has_mapping=True)
                detail.update(status=last_failure, error=str(exc)[:240])
                out["error"] = str(exc)[:240]
                with limiter_lock:
                    if last_failure in {NO_DATA, INVALID_SYMBOL, NO_MAPPING}:
                        circuit.record_success()
                    else:
                        circuit.record_failure()
            detail["finished_at"] = utc_now()
            out["attempts"].append(detail)
            # Empty/missing symbols and rate limits are not improved by immediate retries.
            if detail["status"] not in {TIMEOUT, PROVIDER_ERROR, UNKNOWN_FAILURE} or attempt == 1:
                break
            time.sleep(0.8)
        pool, selected, _ = stored_pool()
        describe(pool, selected)
        if out["data_state"] == "CURRENT" and out["history_sufficient"]:
            break
    if out["data_state"] != "CURRENT" or not out["history_sufficient"]:
        out["retry_after"] = (datetime.now(timezone.utc) + timedelta(seconds=RETRY_COOLDOWN_SECONDS)).isoformat()
    if out["data_state"] == "CURRENT":
        return finish(SUCCESS)
    if pool:
        return finish(STALE_UNEXPECTED)
    return finish(last_failure)


def collect_universe_daily(
    *,
    db: Database | None = None,
    settings: Settings | None = None,
    symbols: list[str] | None = None,
    history_days: int = 250,
    max_workers: int = 2,
    refresh: bool = False,
    dry_run: bool = False,
    min_cache_bars: int = 120,
    yahoo: YahooProvider | None = None,
    tradingview: TradingViewProvider | None = None,
    supplemental_fetch=None,
    include_non_equity: bool = False,
    force_tradingview_fallback: bool | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    t0 = time.monotonic()
    started_at = utc_now()
    use_supplemental = supplemental_fetch is not None or yahoo is None
    root = root or HERE
    settings = settings or Settings.load(root / "config.json")
    owned_db = db is None
    if db is None:
        db = Database(settings.db_path(root))
    discovery = None
    if not dry_run and symbols is None and yahoo is None:
        from egxbridge.collector import refresh_universe
        discovery = refresh_universe(settings, root, force=False)
    registry = SymbolRegistry.from_config({"symbol_aliases": settings.symbol_aliases})
    built = build_canonical_universe(db=db, explicit=symbols, settings=settings, root=root)
    records: list[UniverseRecord] = list(built["records"])
    if not include_non_equity:
        work = [r for r in records if r.security_type == EQUITY]
    else:
        work = records

    for rec in records:
        registry.register(rec.canonical_symbol, aliases={
            "yahoo": rec.provider_alias_yahoo, "tradingview": rec.provider_alias_tradingview,
            "egid": rec.provider_alias_egid,
        })
    yahoo = yahoo or YahooProvider(registry, enabled=(settings.enabled_providers or {}).get("yahoo", True), timeout=int(settings.request_timeout_seconds or 20))
    expected = previous_egx_session_date()
    use_tv = force_tradingview_fallback is not False and not dry_run
    if use_tv and tradingview is None and (settings.enabled_providers or {}).get("tradingview", True):
        tradingview = TradingViewProvider(registry, username=settings.tradingview_username or "", password=settings.tradingview_password or "", request_timeout=int(settings.request_timeout_seconds or 20))
        if tradingview._tv is None:
            tradingview = None
    use_tv = use_tv and tradingview is not None
    lag_probe = {"expected_session": expected, "use_tradingview_fallback": use_tv,
                 "note": "Fallback decided per company; no repeated sample probes."}
    limiter = RateLimiter(min_interval_seconds=max(float(settings.rate_limit_seconds or 0.5), 0.5))
    limiter_lock = threading.Lock()
    breaker = CircuitBreaker(fail_threshold=8, cool_down_seconds=45)
    tv_breaker = CircuitBreaker(fail_threshold=3, cool_down_seconds=45)

    results: list[dict[str, Any]] = []
    workers = max(1, min(int(max_workers or 1), 4))

    report_path = db.path.parent / "daily_collection_report.json"
    try:
        previous_report = json.loads(report_path.read_text(encoding="utf-8"))
        previous_results = {r["ticker"]: r for r in previous_report.get("results", [])}
    except (OSError, ValueError, KeyError, TypeError):
        previous_results = {}
    worker_state = threading.local()
    worker_dbs = []
    run_id = db.start_run([r.canonical_symbol for r in work]) if not dry_run else None

    def _job(rec: UniverseRecord, primary: bool = True) -> dict[str, Any]:
        try:
            if workers > 1 and not hasattr(worker_state, "db"):
                worker_state.db = Database(db.path)
                with limiter_lock:
                    worker_dbs.append(worker_state.db)
            return collect_one_symbol(
                rec, db=worker_state.db if workers > 1 else db, yahoo=yahoo if primary else None, registry=registry,
                limiter=limiter, limiter_lock=limiter_lock, breaker=breaker,
                history_days=history_days, min_cache_bars=min_cache_bars,
                refresh=refresh, dry_run=dry_run,
                tradingview=tradingview if use_tv and not primary else None,
                use_tradingview_fallback=use_tv and not primary,
                expected_session=expected, tv_breaker=tv_breaker,
                previous_result=previous_results.get(rec.canonical_symbol) if primary else None,
                deadline=t0 + COLLECTION_BUDGET_SECONDS,
            )
        except Exception as e:
            return {
                "ticker": rec.canonical_symbol,
                "security_type": rec.security_type,
                "status": UNKNOWN_FAILURE,
                "error": str(e),
                "cache_hit": False,
                "network_fetch": False,
                "bars_stored": 0,
                "bars_fetched": 0,
                "latency_ms": None,
            }

    ex = None
    try:
        if workers == 1:
            for rec in work:
                results.append(_job(rec))
        else:
            ex = ThreadPoolExecutor(max_workers=workers)
            futs = {ex.submit(_job, rec): rec.canonical_symbol for rec in work}
            for fut in as_completed(futs):
                results.append(fut.result())
        # Reach the entire catalog with the primary source before slow fallbacks
        # consume the shared time budget. Reuse the same collector and workers.
        if use_tv:
            primary_by = {r["ticker"]: r for r in results}
            gaps = [r for r in work if r.security_type == EQUITY and r.mapped
                    and not primary_by[r.canonical_symbol].get("retry_deferred")
                    and (primary_by[r.canonical_symbol].get("data_state") != "CURRENT"
                         or not primary_by[r.canonical_symbol].get("history_sufficient"))]
            fallback_results = ([_job(r, False) for r in gaps] if ex is None else
                                [f.result() for f in as_completed([ex.submit(_job, r, False) for r in gaps])])
            for result in fallback_results:
                first = primary_by[result["ticker"]]
                result["attempts"] = first.get("attempts", []) + result.get("attempts", [])
                result["started_at"] = first.get("started_at")
                for field in ("bars_fetched", "conflicts", "latency_ms"):
                    result[field] = (first.get(field) or 0) + (result.get(field) or 0)
                for field in ("network_fetch", "incremental", "cache_hit"):
                    result[field] = bool(first.get(field) or result.get(field))
                primary_by[result["ticker"]] = result
            results = list(primary_by.values())
    except BaseException:
        if run_id is not None:
            db.finish_run(run_id, "INTERRUPTED", notes="Collection interrupted; pending companies were not retried.")
        if owned_db:
            db.close()
        raise
    finally:
        if ex is not None:
            ex.shutdown(wait=True, cancel_futures=True)
        for connection in worker_dbs:
            connection.close()

    # Preserve excluded registry names in the failure/status table
    done = {r.get("ticker") for r in results}
    for rec in records:
        if rec.canonical_symbol not in done:
            results.append({
                "ticker": rec.canonical_symbol,
                "security_type": rec.security_type,
                "yahoo_alias": rec.provider_alias_yahoo,
                "status": EXCLUDED,
                "error": rec.exclusion_reason or f"EXCLUDED_{rec.security_type}",
                "cache_hit": False,
                "network_fetch": False,
                "bars_stored": 0,
                "bars_fetched": 0,
                "latency_ms": None,
            })

    results.sort(key=lambda r: r.get("ticker") or "")
    latencies = [float(r["latency_ms"]) for r in results if r.get("latency_ms") is not None]
    ok = [r for r in results if r.get("status") in {SUCCESS, CACHE_HIT, STALE_EXPECTED}]
    failed = [r for r in results if r.get("status") not in {SUCCESS, CACHE_HIT, STALE_EXPECTED, EXCLUDED, "DRY_RUN"}]
    supplemental = {"status": "NOT_REQUESTED", "network_attempts": 0}
    if not dry_run and use_supplemental and (settings.enabled_providers or {}).get("egxpilot", True):
        from egxbridge.providers.egxpilot import fetch_market_snapshot
        supplemental = (supplemental_fetch or fetch_market_snapshot)(
            [r.canonical_symbol for r in work], timeout=settings.request_timeout_seconds,
        )
    elapsed = time.monotonic() - t0
    performance = {
        "total_universe_collection_time_seconds": round(elapsed, 3),
        "successful_symbols": len(ok),
        "current_symbols": sum(r.get("data_state") == "CURRENT" for r in results),
        "stale_symbols": sum(r.get("data_state") == "STALE" for r in results),
        "missing_symbols": sum(r.get("data_state") == "MISSING" for r in results),
        "network_attempts": sum(1 for r in results for a in r.get("attempts", []) if a.get("attempt")) + supplemental.get("network_attempts", 0),
        "supplemental_snapshot_requests": supplemental.get("network_attempts", 0),
        "rejected_daily_bars": sum(a.get("rejected_bars", 0) for r in results for a in r.get("attempts", [])),
        "provider_circuit_skips": sum(a.get("status") == "CIRCUIT_OPEN" for r in results for a in r.get("attempts", [])),
        "collection_time_limit_skips": sum(a.get("status") == "COLLECTION_TIME_LIMIT" for r in results for a in r.get("attempts", [])),
        "collection_budget_seconds": COLLECTION_BUDGET_SECONDS,
        "failed_symbols": len(failed),
        "insufficient_history_symbols": sum(r.get("history_sufficient") is False for r in results if r.get("data_state") == "CURRENT"),
        "excluded_symbols": sum(1 for r in results if r.get("status") == EXCLUDED),
        "cache_hits": sum(1 for r in results if r.get("cache_hit")),
        "network_fetches": sum(1 for r in results if r.get("network_fetch")),
        "deferred_retries": sum(1 for r in results if r.get("retry_deferred")),
        "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "median_latency_ms": round(median(latencies), 2) if latencies else None,
        "max_workers": workers,
        "history_days": history_days,
        "bridge_version": BRIDGE_VERSION,
        "tradingview_fallback_used": use_tv,
        "expected_session": expected,
        "yahoo_probe_session": lag_probe.get("yahoo_session"),
        "tradingview_probe_session": lag_probe.get("tradingview_session"),
    }
    report = {
        "source_database": str(Path(db.path).resolve()),
        "status": "DRY_RUN" if dry_run else "OK" if work and not failed and not performance["insufficient_history_symbols"] and not performance["rejected_daily_bars"] and not (discovery and discovery.get("status") != "OK") else "PARTIAL",
        "scope": "SELECTED_SYMBOLS" if symbols else "FULL_KNOWN_UNIVERSE",
        "started_at": started_at, "finished_at": utc_now(),
        "expected_session": expected, "results": results, "performance": performance,
        "supplemental_market_snapshot": supplemental,
        "catalog_status": built.get("catalog_status"), "discovery": discovery,
        "equity_count": built.get("EQUITY_UNIVERSE_TOTAL"),
        "exchange_completeness_verified": False,
    }
    if not dry_run:
        from egxbridge.storage import jdump
        jdump(report_path, report)
        db.finish_run(run_id, report["status"], [r["ticker"] + ": " + r["status"] for r in failed],
                      notes=json.dumps({"kind": "universe_daily", "report_path": str(report_path)}))
    if owned_db:
        db.close()
    return {"universe": built, "results": results, "performance": performance,
            "lag_probe": lag_probe, "generated_at": report["finished_at"],
            "status": report["status"], "report": report, "report_path": str(report_path)}



def collection_report_for_db(db, *, as_of: datetime) -> dict[str, Any]:
    """Freeze only a completed report from the database used by this package."""
    unavailable = {"status": "UNAVAILABLE", "reason": "No verified collection report for this database and cutoff."}
    if db is None or not getattr(db, "path", None):
        return unavailable
    db_path = Path(db.path).resolve()
    try:
        report = json.loads((db_path.parent / "daily_collection_report.json").read_text())
        finished = datetime.fromisoformat(report["finished_at"].replace("Z", "+00:00"))
        if report.get("source_database") == str(db_path) and finished <= as_of:
            return report
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return unavailable


def enrich_metrics_fields(metrics: dict[str, Any], *, latest_session: str | None = None) -> dict[str, Any]:
    """Add Explorer extras without changing scanner formulas."""
    m = dict(metrics or {})
    m["days_of_history"] = m.get("bars")
    m["latest_session"] = latest_session or m.get("latest_completed_market_session") or m.get("session_date")
    if "latest_close" not in m and m.get("last_close") is not None:
        m["latest_close"] = m["last_close"]
    return m


def compute_daily_metrics_for_symbol(db: Database, symbol: str, *, limit: int = 300) -> dict[str, Any]:
    rows = db.fetch_candles(symbol, "1d", limit=5000)
    pool, provider, note = select_daily_pool(rows)
    pool = pool[-limit:]
    metrics = compute_scanner_metrics(pool)
    latest_session = session_of(pool[-1]) if pool else None
    metrics["daily_provider"] = provider
    metrics["daily_provider_note"] = note
    status = daily_session_status(pool)
    metrics["expected_session"] = status.get("expected_session")
    metrics["daily_bars_lagging"] = status.get("lagging")
    return enrich_metrics_fields(metrics, latest_session=latest_session)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Collect Yahoo daily OHLCV for the EGX equity universe")
    p.add_argument("--daily-only", action="store_true", default=True, help="Daily Yahoo collection only (default)")
    p.add_argument("--refresh", action="store_true", help="Refetch and allow overwrite of conflicting bars")
    p.add_argument("--max-workers", type=int, default=2)
    p.add_argument("--history-days", type=int, default=250)
    p.add_argument("--prescreen-limit", type=int, default=30)
    p.add_argument("--intraday-limit", type=int, default=15)
    p.add_argument("--symbols", default="", help="Optional comma-separated canonical override")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--run-explorer", action="store_true", help="After collection, prepare Explorer handoff")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    symbols = [s.strip().upper() for s in (args.symbols or "").split(",") if s.strip()] or None
    settings = Settings.load(HERE / "config.json")
    db = Database(settings.db_path(HERE))
    res = collect_universe_daily(
        db=db,
        settings=settings,
        symbols=symbols,
        history_days=args.history_days,
        max_workers=args.max_workers,
        refresh=args.refresh,
        dry_run=args.dry_run,
    )
    perf = res["performance"]
    print(
        f"COLLECT_UNIVERSE ok={perf['successful_symbols']} fail={perf['failed_symbols']} "
        f"cache={perf['cache_hits']} net={perf['network_fetches']} "
        f"time_s={perf['total_universe_collection_time_seconds']}"
    )
    if args.run_explorer and not args.dry_run:
        from egxbridge.analysis.common.environment import PRODUCTION
        from egxbridge.analysis.common.persistence import AnalysisStore
        from egxbridge.analysis.explorer.models import ExplorerRunConfig
        from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
        from egxbridge.analysis.funnel.registry import FunnelRegistry

        store = AnalysisStore(HERE / "output" / "analysis.sqlite", environment=PRODUCTION)
        funnel = FunnelRegistry(store=store, db=db, environment=PRODUCTION)
        cfg = ExplorerRunConfig(
            universe=symbols or [],
            prescreen_limit=args.prescreen_limit,
            intraday_limit=args.intraday_limit,
            enrich_intraday=True,
        )
        exp = prepare_explorer_handoff(cfg, db=db, store=store, funnel_registry=funnel)
        print("EXPLORER_ZIP", exp.get("zip_path"))
        store.close()
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
