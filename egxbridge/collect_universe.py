"""Broad EGX universe daily collection (Yahoo primary). Incremental, conservative."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from statistics import median
from typing import Any
import argparse
import logging
import threading
import time

from egxbridge import __version__ as BRIDGE_VERSION
from egxbridge.config import Settings
from egxbridge.db import Database
from egxbridge.freshness import classify_freshness
from egxbridge.providers.base import ProviderError
from egxbridge.providers.yahoo import YahooProvider
from egxbridge.resilience import CircuitBreaker, RateLimiter, retry_call
from egxbridge.scanner import compute_scanner_metrics
from egxbridge.semantics import DAILY_BAR, DAILY_CLOSE, DAILY_FINAL_VOLUME
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
    if "no yahoo candles" in msg or "no data" in msg or "no yahoo quote" in msg:
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


def _latest_stored(db: Database, symbol: str, provider: str = "yahoo") -> dict[str, Any] | None:
    rows = db.fetch_candles(symbol, "1d", limit=1)
    yahoo = [r for r in rows if (r.get("provider") or "").lower() == provider]
    pool = yahoo or rows
    return pool[0] if pool else None


def _bar_count(db: Database, symbol: str, provider: str = "yahoo") -> int:
    try:
        row = db._conn.execute(
            "SELECT COUNT(*) AS c FROM candles WHERE symbol=? AND interval='1d' AND provider=?",
            (symbol.upper(), provider),
        ).fetchone()
        return int(row["c"] if hasattr(row, "keys") else row[0])
    except Exception:
        return 0


def _existing_row(db: Database, symbol: str, interval: str, timestamp: str, provider: str):
    return db._conn.execute(
        """SELECT open, high, low, close, volume FROM candles
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

    Conflicting historical bars are logged and kept unless refresh=True.
    """
    inserted = 0
    skipped = 0
    conflicts = 0
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
        if prev is not None:
            keys = ("open", "high", "low", "close", "volume")
            if all(_close_enough(prev[k] if hasattr(prev, "keys") else prev[i], d.get(k))
                   for i, k in enumerate(keys)):
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
                "selected_provider": d["provider"] if refresh else "local_existing",
                "reason": "incremental_history_conflict",
                "created_at": utc_now(),
            })
            log.warning("daily conflict %s %s kept=%s", d["symbol"], ts, "new" if refresh else "existing")
            if not refresh:
                skipped += 1
                continue
        db.upsert_candle(d)
        inserted += 1
    return {"inserted": inserted, "skipped": skipped, "conflicts": conflicts}


def _candle_to_store(c) -> dict[str, Any]:
    d = c.to_dict() if hasattr(c, "to_dict") else dict(c)
    d["price_observation_type"] = DAILY_CLOSE
    d["timestamp_semantics"] = d.get("timestamp_semantics") or DAILY_BAR
    d["volume_semantics"] = DAILY_FINAL_VOLUME
    d["volume_interval"] = "1d"
    return d


def collect_one_symbol(
    rec: UniverseRecord,
    *,
    db: Database,
    yahoo: YahooProvider,
    registry: SymbolRegistry,
    limiter: RateLimiter,
    limiter_lock: threading.Lock,
    breaker: CircuitBreaker,
    history_days: int,
    min_cache_bars: int,
    refresh: bool,
    dry_run: bool,
) -> dict[str, Any]:
    t0 = time.time()
    sym = rec.canonical_symbol
    out: dict[str, Any] = {
        "ticker": sym,
        "security_type": rec.security_type,
        "yahoo_alias": rec.provider_alias_yahoo,
        "status": UNKNOWN_FAILURE,
        "cache_hit": False,
        "network_fetch": False,
        "bars_stored": 0,
        "bars_fetched": 0,
        "latency_ms": None,
        "error": None,
        "incremental": False,
        "conflicts": 0,
    }
    if rec.security_type != EQUITY:
        out["status"] = EXCLUDED
        out["error"] = rec.exclusion_reason or f"EXCLUDED_{rec.security_type}"
        out["latency_ms"] = round((time.time() - t0) * 1000, 2)
        return out
    if not rec.mapped or not rec.provider_alias_yahoo:
        out["status"] = NO_MAPPING
        out["latency_ms"] = round((time.time() - t0) * 1000, 2)
        return out

    registry.register(
        rec.canonical_symbol,
        aliases={
            "yahoo": rec.provider_alias_yahoo,
            "tradingview": rec.provider_alias_tradingview,
            "egid": rec.provider_alias_egid,
        },
    )
    db.upsert_symbol(
        rec.canonical_symbol,
        name=rec.display_name_if_known,
        aliases={
            "yahoo": rec.provider_alias_yahoo,
            "tradingview": rec.provider_alias_tradingview,
            "egid": rec.provider_alias_egid,
        },
    )

    existing_n = _bar_count(db, sym)
    latest = _latest_stored(db, sym)
    start = None
    cairo_today = datetime.now(ZoneInfo("Africa/Cairo")).date()
    if latest and not refresh and existing_n >= min_cache_bars:
        sess = (latest.get("session_date") or str(latest.get("timestamp") or ""))[:10]
        try:
            sess_d = datetime.fromisoformat(sess).date()
        except Exception:
            sess_d = None
        if sess_d is not None and sess_d >= cairo_today:
            out["status"] = CACHE_HIT
            out["cache_hit"] = True
            out["bars_stored"] = existing_n
            out["latency_ms"] = round((time.time() - t0) * 1000, 2)
            return out
    if latest and not refresh:
        sess = (latest.get("session_date") or str(latest.get("timestamp") or ""))[:10]
        try:
            d0 = datetime.fromisoformat(sess)
            start = (d0 - timedelta(days=OVERLAP_CALENDAR_DAYS)).date().isoformat()
            out["incremental"] = True
        except Exception:
            start = None

    if dry_run:
        out["status"] = "DRY_RUN"
        out["bars_stored"] = existing_n
        out["latency_ms"] = round((time.time() - t0) * 1000, 2)
        return out

    if not breaker.allow():
        out["status"] = RATE_LIMITED
        out["error"] = "circuit_breaker_open"
        out["latency_ms"] = round((time.time() - t0) * 1000, 2)
        return out

    try:
        with limiter_lock:
            limiter.wait()
        n_bars = max(int(history_days), 120)

        def _fetch():
            if start:
                return yahoo.get_candles(sym, "1d", n_bars=n_bars, start=start)
            return yahoo.get_candles(sym, "1d", n_bars=n_bars)

        candles = retry_call(_fetch, retries=1, base_delay=0.8, retry_on=(ProviderError, TimeoutError, OSError))
        breaker.record_success()
        out["network_fetch"] = True
        out["bars_fetched"] = len(candles or [])
        out["latency_ms"] = getattr(yahoo, "_latency_ms", None)
        if not candles:
            out["status"] = NO_DATA
            return out
        payload = [_candle_to_store(c) for c in candles]
        merge = merge_daily_candles(db, payload, refresh=refresh)
        out["conflicts"] = merge["conflicts"]
        out["bars_stored"] = _bar_count(db, sym)
        if merge["inserted"] == 0 and existing_n >= min_cache_bars:
            out["cache_hit"] = True
        latest2 = _latest_stored(db, sym)
        ts = (latest2 or {}).get("normalized_utc_timestamp") or (latest2 or {}).get("timestamp")
        fclass, _ = classify_freshness(ts) if ts else ("UNKNOWN", None)
        if fclass == "STALE_UNEXPECTED":
            out["status"] = STALE_UNEXPECTED
        elif fclass == "STALE_EXPECTED":
            out["status"] = STALE_EXPECTED
        else:
            out["status"] = SUCCESS
        return out
    except Exception as e:
        breaker.record_failure()
        out["status"] = classify_failure(e, has_mapping=True)
        out["error"] = str(e)
        out["network_fetch"] = True
        out["latency_ms"] = getattr(yahoo, "_latency_ms", None) or round((time.time() - t0) * 1000, 2)
        log.warning("collect failed %s: %s", sym, e)
        return out


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
    include_non_equity: bool = False,
) -> dict[str, Any]:
    t0 = time.time()
    settings = settings or Settings.load(HERE / "config.json")
    if db is None:
        db = Database(settings.db_path(HERE))
    registry = SymbolRegistry.from_config({"symbol_aliases": settings.symbol_aliases})
    built = build_canonical_universe(db=db, explicit=symbols)
    records: list[UniverseRecord] = list(built["records"])
    if not include_non_equity:
        work = [r for r in records if r.security_type == EQUITY]
    else:
        work = records

    yahoo = yahoo or YahooProvider(registry, enabled=True, timeout=int(settings.request_timeout_seconds or 20))
    limiter = RateLimiter(min_interval_seconds=max(float(settings.rate_limit_seconds or 0.5), 0.5))
    limiter_lock = threading.Lock()
    breaker = CircuitBreaker(fail_threshold=8, cool_down_seconds=45)

    results: list[dict[str, Any]] = []
    workers = max(1, min(int(max_workers or 1), 4))

    def _job(rec: UniverseRecord) -> dict[str, Any]:
        try:
            return collect_one_symbol(
                rec, db=db, yahoo=yahoo, registry=registry,
                limiter=limiter, limiter_lock=limiter_lock, breaker=breaker,
                history_days=history_days, min_cache_bars=min_cache_bars,
                refresh=refresh, dry_run=dry_run,
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

    if workers == 1:
        for rec in work:
            results.append(_job(rec))
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_job, rec): rec.canonical_symbol for rec in work}
            for fut in as_completed(futs):
                try:
                    results.append(fut.result())
                except Exception as e:
                    results.append({
                        "ticker": futs[fut],
                        "status": UNKNOWN_FAILURE,
                        "error": str(e),
                        "cache_hit": False,
                        "network_fetch": False,
                    })

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
    elapsed = time.time() - t0
    performance = {
        "total_universe_collection_time_seconds": round(elapsed, 3),
        "successful_symbols": len(ok),
        "failed_symbols": len(failed),
        "excluded_symbols": sum(1 for r in results if r.get("status") == EXCLUDED),
        "cache_hits": sum(1 for r in results if r.get("cache_hit")),
        "network_fetches": sum(1 for r in results if r.get("network_fetch")),
        "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "median_latency_ms": round(median(latencies), 2) if latencies else None,
        "max_workers": workers,
        "history_days": history_days,
        "bridge_version": BRIDGE_VERSION,
    }
    return {
        "universe": built,
        "results": results,
        "performance": performance,
        "generated_at": utc_now(),
    }


def enrich_metrics_fields(metrics: dict[str, Any], *, latest_session: str | None = None) -> dict[str, Any]:
    """Add Explorer extras without changing scanner formulas."""
    m = dict(metrics or {})
    m["days_of_history"] = m.get("bars")
    m["latest_session"] = latest_session or m.get("latest_completed_market_session") or m.get("session_date")
    if "latest_close" not in m and m.get("last_close") is not None:
        m["latest_close"] = m["last_close"]
    return m


def compute_daily_metrics_for_symbol(db: Database, symbol: str, *, limit: int = 300) -> dict[str, Any]:
    rows = db.fetch_candles(symbol, "1d", limit=limit)
    # Prefer yahoo daily
    yahoo = [r for r in rows if (r.get("provider") or "").lower() == "yahoo"]
    pool = yahoo or rows
    pool = sorted(pool, key=lambda c: c.get("normalized_utc_timestamp") or c.get("timestamp") or "")
    metrics = compute_scanner_metrics(pool)
    latest_session = None
    if pool:
        latest_session = pool[-1].get("session_date") or str(pool[-1].get("timestamp") or "")[:10]
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
