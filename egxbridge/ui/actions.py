"""Thin wrappers around existing backend actions. No duplicated analysis math."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import shutil

from egxbridge.analysis.common.environment import PRODUCTION
from egxbridge.analysis.schedule.types import ANALYSIS_TYPES
from egxbridge.ui.workflow_state import NEXT_SESSION_JOBS, ALL_JOBS


from egxbridge.analysis.common.data_stamp import copy_zip_sidecar


HERE = Path(__file__).resolve().parents[2]
CHATGPT_HANDOFF_ZIP_NAME = "EGX_CHATGPT_HANDOFF.zip"


def _ok(message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": True, "message": message, **extra}


def _fail(message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "message": message, **extra}


def _user_exc(exc: BaseException, fallback: str) -> str:
    text = str(exc).strip()
    if not text:
        return fallback
    if text.startswith("Traceback") or "File \"" in text:
        return fallback
    return f"{fallback} {text}"


def _reload_intraday_module():
    import importlib
    for name in (
        "egxbridge.analysis.common.missing",
        "egxbridge.analysis.explorer.universe_state",
        "egxbridge.analysis.explorer.session_volume",
        "egxbridge.analysis.explorer.session_screen",
        "egxbridge.analysis.explorer.intraday_fetch",
        "egxbridge.analysis.explorer.intraday",
        "egxbridge.analysis.explorer.coverage",
        "egxbridge.analysis.explorer.handoff",
    ):
        try:
            importlib.reload(importlib.import_module(name))
        except Exception:
            pass
    from egxbridge.analysis.explorer import intraday as intra
    return intra


def _enrich_shortlist_intraday(tickers, **kwargs):
    """Call enrich_shortlist_intraday from disk.

    Streamlit can keep an older function in sys.modules after actions.py reloads,
    which raised: unexpected keyword argument 'keep_ohlcv'.
    """
    import inspect
    intra = _reload_intraday_module()
    fn = intra.enrich_shortlist_intraday
    try:
        params = inspect.signature(fn).parameters
        if not any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
            kwargs = {k: v for k, v in kwargs.items() if k in params}
    except (TypeError, ValueError):
        pass
    return fn(tickers, **kwargs)


def refresh_market_data(
    *,
    root: Path | None = None,
    force_refetch: bool = False,
    symbols: list[str] | None = None,
    force_tradingview_fallback: bool | None = None,
) -> dict[str, Any]:
    """Collect daily evidence once. Intraday/focus diagnostics have separate actions."""
    root = root or HERE
    try:
        from egxbridge.config import Settings
        from egxbridge.db import Database
        from egxbridge.collect_universe import collect_universe_daily
    except Exception as e:
        return _fail(_user_exc(e, "Could not load collection modules."))
    settings = Settings.load(root / "config.json")
    db = Database(settings.db_path(root))
    try:
        uni = collect_universe_daily(
            db=db,
            settings=settings,
            symbols=symbols,
            refresh=force_refetch,
            force_tradingview_fallback=force_tradingview_fallback,
            root=root,
        )
    except Exception as e:
        return _fail(_user_exc(e, "Market data refresh did not complete."))
    finally:
        try:
            db.close()
        except Exception:
            pass
    perf = (uni or {}).get("performance") or {}
    ok_n = int(perf.get("successful_symbols") or 0)
    fail_n = int(perf.get("failed_symbols") or 0)
    universe = ((uni or {}).get("universe") or {})
    equity_n = int(universe.get("equity_count") or universe.get("EQUITY_UNIVERSE_TOTAL") or ok_n + fail_n or 0)
    tv_n = sum(1 for r in ((uni or {}).get("results") or []) if r.get("fallback_provider") == "tradingview")
    if symbols:
        msg = f"Daily catch-up for {len(symbols)} equities (ok={ok_n}, fail={fail_n})."
    elif equity_n and ok_n and ok_n < equity_n:
        msg = (
            f"Daily collection returned data for {ok_n} / {equity_n} equities. "
            "Explorer can continue with the eligible names that have usable history."
        )
    else:
        msg = f"Daily collection finished: {ok_n} / {equity_n} equities current; {fail_n} stale or unavailable."
    if tv_n:
        msg += f" TradingView daily fallback used for {tv_n} symbols where Yahoo lagged."
    elif perf.get("tradingview_fallback_used"):
        msg += " TradingView daily fallback was available for missing or stale data."
    msg += f" Expected session {perf.get('expected_session')}; {perf.get('cache_hits', 0)} cached, {perf.get('network_attempts', 0)} requests, {perf.get('deferred_retries', 0)} retries deferred. See the collection report for each company."
    return (_ok if ok_n else _fail)(
        msg,
        universe=uni,
        daily_ok=ok_n,
        daily_failed=fail_n,
        generated_at=(uni or {}).get("generated_at"),
        collection_report=(uni or {}).get("report"),
        tradingview_fallback_symbols=tv_n,
        lagging_targets=list(symbols or []),
    )


def run_broad_explorer(*, store, db, funnel_registry, enrich_intraday: bool = False) -> dict[str, Any]:
    try:
        _reload_intraday_module()
        from egxbridge.analysis.explorer.models import ExplorerRunConfig
        from egxbridge.analysis.explorer.registry import ExplorerRegistry
        explorer = ExplorerRegistry(store=store, db=db, funnel_registry=funnel_registry)
        res = explorer.prepare(ExplorerRunConfig(enrich_intraday=enrich_intraday))
    except Exception as e:
        return _fail(_user_exc(e, "Broad Explorer could not finish."))
    counts = (res or {}).get("counts") or {}
    requested = len((res or {}).get("intraday_queried_tickers") or [])
    enriched = int(counts.get("INTRADAY_ENRICHED") or 0)
    eligible = int(counts.get("SCANNER_ELIGIBLE_SYMBOLS") or (res or {}).get("scanner_candidate_count") or 0)
    daily = int(counts.get("DAILY_DATA_AVAILABLE") or (res or {}).get("data_eligible_count") or 0)
    equity = int(counts.get("EQUITY_UNIVERSE_TOTAL") or (res or {}).get("universe_total") or 0)
    parts = [
        f"Broad Explorer completed. Equity universe {equity}, daily data {daily}, "
        f"scanner eligible {eligible}, final candidates {(res or {}).get('handoff_candidate_count') or (res or {}).get('candidate_count')}."
    ]
    if enrich_intraday and requested and enriched < requested:
        parts.append(
            f"TradingView returned {enriched} / {requested} intraday candidates. "
            f"You can continue; {requested - enriched} candidates will lack intraday confirmation."
        )
    elif not enrich_intraday:
        parts.append(
            "TradingView was skipped (not in continuous trading). "
            "Candidate ranks still use daily evidence only; use Refresh Intraday when the market is live."
        )
    return _ok(" ".join(parts), result=res, counts=counts, enrich_intraday=bool(enrich_intraday))


def refresh_and_run_explorer(
    *,
    snapshot: dict[str, Any] | None,
    store,
    db,
    funnel_registry,
    root: Path | None = None,
    force_collect: bool = False,
    force_tv: bool = False,
    enrich_intraday: bool | None = None,
) -> dict[str, Any]:
    """Daily Operator scan path: daily bars + Explorer. Intraday is opt-in (slow)."""
    from egxbridge.ui.workflow_state import explorer_should_enrich_intraday

    snap = snapshot or {}
    notes: list[str] = []
    root = root or HERE
    # Always reconcile the full catalog. The collector itself skips current cached series.
    # A newest-session sample or an old shortlist cannot prove every company is current.
    collect_result = refresh_market_data(root=root, force_refetch=force_collect)
    if not collect_result.get("ok"):
        return collect_result
    notes.append(collect_result.get("message") or "Market data refreshed.")
    # Default: never attach TradingView intraday to Scan market (use Today's Intraday shortcut).
    if enrich_intraday is None:
        enrich = bool(force_tv) and explorer_should_enrich_intraday(
            snap.get("session_phase"), force=True,
        )
    else:
        enrich = bool(enrich_intraday)
    explorer_result = run_broad_explorer(
        store=store, db=db, funnel_registry=funnel_registry, enrich_intraday=enrich,
    )
    notes.append(explorer_result.get("message") or "")
    if not explorer_result.get("ok"):
        return {**explorer_result, "message": " ".join(n for n in notes if n), "collect": collect_result}
    return _ok(
        " ".join(n for n in notes if n),
        collect=collect_result,
        result=explorer_result.get("result"),
        counts=explorer_result.get("counts"),
        enrich_intraday=enrich,
        skipped_collect=bool(collect_result.get("skipped")),
    )


def prepare_schedule_jobs(
    jobs: list[str],
    *,
    store,
    db=None,
    explorer_package_dir: str | Path | None,
    session_meta: dict[str, Any] | None = None,
    environment: str = PRODUCTION,
) -> dict[str, Any]:
    if not explorer_package_dir or not Path(explorer_package_dir).exists():
        return _fail("Explorer has not been run yet. Run Broad Explorer before preparing schedules.")
    unknown = [j for j in jobs if j not in ANALYSIS_TYPES]
    if unknown:
        return _fail(f"Unknown analysis job: {unknown[0]}.")
    try:
        from egxbridge.analysis.schedule.handoff import prepare_schedule_handoffs
        res = prepare_schedule_handoffs(
            explorer_package_dir=Path(explorer_package_dir),
            jobs=list(jobs),
            store=store,
            db=db,
            environment=environment,
            session_meta=session_meta,
        )
    except FileNotFoundError:
        return _fail("Explorer has not been run yet. Run Broad Explorer before preparing schedules.")
    except Exception as e:
        return _fail(_user_exc(e, "Could not prepare ChatGPT analysis packages."))
    names = ", ".join(jobs)
    alias = publish_chatgpt_handoff_zip((res or {}).get("combined_zip"))
    stamp = ((res or {}).get("manifest") or {}).get("data_stamp")
    extra = {"result": res, "zip_path": str(alias) if alias else (res or {}).get("combined_zip"), "data_stamp": stamp}
    from egxbridge.analysis.common.data_stamp import stamp_caption
    cap = stamp_caption(stamp)
    msg = f"Prepared one ChatGPT handoff ZIP with: {names}."
    if cap:
        msg += " " + cap
    return _ok(msg, warning=cap or None, **extra)


def publish_chatgpt_handoff_zip(combined: str | Path | None, *, root: Path | None = None) -> Path | None:
    """Stable alias so the operator always has one ChatGPT upload file."""
    if not combined:
        return None
    src = Path(combined)
    if not src.exists():
        return None
    dest = (root or HERE) / "output" / CHATGPT_HANDOFF_ZIP_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    copy_zip_sidecar(src, dest)
    return dest


def prepare_next_session_package(**kwargs: Any) -> dict[str, Any]:
    return prepare_schedule_jobs(list(NEXT_SESSION_JOBS), **kwargs)


def prepare_all_jobs(**kwargs: Any) -> dict[str, Any]:
    return prepare_schedule_jobs(list(ALL_JOBS), **kwargs)


def prepare_recommended_jobs(recommended: list[str], **kwargs: Any) -> dict[str, Any]:
    jobs = list(recommended or NEXT_SESSION_JOBS)
    return prepare_schedule_jobs(jobs, **kwargs)


def import_chatgpt_result(
    source: Path | str,
    *,
    analysis_type: str,
    store,
    run_id: str | None = None,
) -> dict[str, Any]:
    try:
        from egxbridge.analysis.schedule.importer import import_schedule_result
        res = import_schedule_result(source, analysis_type=analysis_type, run_id=run_id, store=store)
    except Exception as e:
        return _fail(_user_exc(e, "Could not import ChatGPT result. Original file was not discarded if saved."))
    status = res.get("structured_parse_status")
    warn = None
    if status and status not in {"VALID", "PARSE_VALID", "OK"}:
        warn = status
    issues = res.get("schema_issues") or []
    msg = (
        f"Imported {analysis_type}. Parse status: {status or 'unknown'}. "
        f"Session-phase validation: {res.get('session_phase_validation') or 'n/a'}."
    )
    if issues:
        msg += " Warnings: " + "; ".join(str(x) for x in issues[:4])
    return _ok(msg, result=res, warning=warn)


def prepare_funnel(*, funnel_registry, ticker: str, mode: str) -> dict[str, Any]:
    t = (ticker or "").upper().strip()
    if not t:
        return _fail("Choose a ticker before preparing Funnel.")
    try:
        if mode == "CONTINUE_FUNNEL":
            res = funnel_registry.prepare_stage(t)
        elif mode == "PREPARE_DELTA":
            res = funnel_registry.prepare_delta(t)
        else:
            res = funnel_registry.prepare_full(t)
    except Exception as e:
        return _fail(_user_exc(e, f"Could not prepare Funnel for {t}."))
    if (res or {}).get("status") == "DELTA_NOT_AVAILABLE":
        return _fail(res.get("message") or "Delta is not available. Prepare a full Funnel instead.", result=res)
    return _ok(f"Funnel handoff ready for {t}.", result=res, zip_path=(res or {}).get("zip_path"))


def import_funnel_result(*, funnel_registry, ticker: str, source: Path | str) -> dict[str, Any]:
    t = (ticker or "").upper().strip()
    try:
        res = funnel_registry.import_result(t, source)
    except Exception as e:
        return _fail(_user_exc(e, f"Could not import Funnel result for {t}."))
    message = f"Imported Funnel result for {t}. Original preserved."
    if res.get("valuation_diagnostics"):
        message += " VALUATION_SOURCE_CONFLICT: structured valuation retained; conflicting prose is saved in valuation history."
    return _ok(message, result=res)


def refresh_intraday(*, explorer_payload: dict[str, Any] | None, root: Path | None = None) -> dict[str, Any]:
    """Fetch today's TradingView intraday bars and patch the current Explorer package."""
    root = root or HERE
    package_dir = None
    try:
        from egxbridge.ui.snapshot import resolve_explorer_package
        from egxbridge.storage import rows_to_csv
        from egxbridge.config import Settings
        from egxbridge.db import Database
        from egxbridge.symbols import SymbolRegistry
        from egxbridge.providers.tradingview import TradingViewProvider
        intra = _reload_intraday_module()
        LIVE_REFRESH_INTERVALS = intra.LIVE_REFRESH_INTERVALS
        resolve_intraday_tickers = intra.resolve_intraday_tickers
        from egxbridge.analysis.common.data_stamp import (
            bar_age_seconds,
            build_data_stamp,
            stamp_caption,
            write_package_stamp,
        )
        from egxbridge.analysis.schedule.session import session_context
        import json
    except Exception as e:
        return _fail(_user_exc(e, "Could not load intraday modules."))

    resolved = resolve_explorer_package(root)
    package_dir = resolved.get("package_dir")
    if not package_dir:
        return _fail("Prepare Intraday requires an Explorer shortlist. Run Broad Explorer first.")

    settings = Settings.load(root / "config.json")
    db = Database(settings.db_path(root))
    from egxbridge.analysis.common.persistence import AnalysisStore
    from egxbridge.analysis.common.environment import PRODUCTION
    store = AnalysisStore(settings.output_path(root) / "analysis.sqlite", environment=PRODUCTION)
    try:
        from egxbridge.analysis.schedule.handoff import load_explorer_package
        payload = load_explorer_package(Path(package_dir), db=db, store=store, require_current=True)
        package_dir = payload["_package_dir"]
        tickers = resolve_intraday_tickers(payload, limit=int(payload.get("intraday_limit") or 15) or 15)
        if not tickers:
            return _fail("Daily evidence was checked. No eligible candidates are available for intraday refresh; see the per-company data gaps.")
        registry = SymbolRegistry.from_config({"symbol_aliases": settings.symbol_aliases})
        tv = TradingViewProvider(
            registry,
            enabled=bool((settings.enabled_providers or {}).get("tradingview", True)),
            username=settings.tradingview_username,
            password=settings.tradingview_password,
            request_timeout=int(settings.request_timeout_seconds or 20),
        )
        if getattr(tv, "_tv", None) is None:
            tv = None
        pack = _enrich_shortlist_intraday(
            tickers,
            tv=tv,
            intervals=LIVE_REFRESH_INTERVALS,
            n_bars=180,
            db=db,
            store_candles=True,
            retries=1,
            keep_ohlcv=True,
            live_fetch=True,
            allow_yahoo_fallback=True,
        )
    except Exception as e:
        return _fail(_user_exc(e, "Intraday refresh did not complete."))
    finally:
        store.close()
        try:
            db.close()
        except Exception:
            pass

    by_ticker = pack.get("by_ticker") or {}
    candidates = list(payload.get("candidates") or [])
    for c in candidates:
        t = str(c.get("ticker") or "").upper()
        if t in by_ticker:
            c["intraday"] = by_ticker[t]
            c["intraday_available"] = bool(by_ticker[t].get("intraday_available"))
            c["session_volume"] = by_ticker[t].get("session_volume")
            c["depth"] = by_ticker[t].get("depth")
            c["trades"] = by_ticker[t].get("trades")
            if not c.get("intraday_selection_reason"):
                c["intraday_selection_reason"] = "LIVE_REFRESH"
    payload["candidates"] = candidates
    payload["intraday_queried_tickers"] = list(pack.get("queried_tickers") or tickers)
    payload["intraday_fetch_diagnostics"] = pack.get("intraday_fetch_diagnostics") or {}
    payload["intraday_fetch_by_ticker"] = {
        t: {k: v for k, v in rec.items() if k != "ohlcv"} for t, rec in by_ticker.items()
    }
    payload["intraday_refreshed_at"] = pack.get("fetched_at") or (by_ticker.get(tickers[0]) or {}).get("queried_at")
    payload["lookahead_guard_pass"] = bool(pack.get("lookahead_guard_pass", True))
    payload["future_timestamp_records_rejected"] = int(pack.get("future_timestamp_records_rejected") or 0)
    payload["stale_records_rejected"] = int(pack.get("stale_records_rejected") or 0)
    counts = dict(payload.get("counts") or {})
    counts["INTRADAY_ENRICHED"] = int(pack.get("intraday_enriched") or 0)
    counts["INTRADAY_TODAY"] = int(pack.get("today_session_enriched") or 0)
    counts["INTRADAY_OHLCV"] = int(pack.get("intraday_ohlcv_count") or 0)
    payload["counts"] = counts
    sess = session_context() or {}
    data_stamp = build_data_stamp(
        packaged_at=pack.get("fetched_at"),
        session_close_date=payload.get("latest_completed_market_session"),
        session_phase=sess.get("session_phase"),
        explorer_payload=payload,
        intraday_pack=pack,
        package_kind="INTRADAY_REFRESH",
    )
    payload["data_stamp"] = data_stamp

    if package_dir:
        pkg = Path(package_dir)
        try:
            handoff_path = pkg / "explorer_handoff.json"
            handoff_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            (pkg / "intraday_fetch_by_ticker.json").write_text(json.dumps(payload["intraday_fetch_by_ticker"], indent=2, default=str), encoding="utf-8")
            write_package_stamp(pkg, data_stamp)
            try:
                rows_to_csv(pkg / "intraday_enrichment.csv", pack.get("rows") or [{"note": "none"}])
                rows_to_csv(pkg / "intraday_failures.csv", pack.get("failures") or [{"note": "none"}])
            except Exception:
                pass
            try:
                from egxbridge.analysis.common.packaging import write_jsonl
                ohlcv_1m, ohlcv_5m, ohlcv_15m = [], [], []
                for t, rec in by_ticker.items():
                    series = rec.get("ohlcv") or {}
                    if series.get("1m"):
                        ohlcv_1m.append({"ticker": t, "security_id": t, "interval": "1m", "bars": series["1m"]})
                    if series.get("5m"):
                        ohlcv_5m.append({"ticker": t, "security_id": t, "interval": "5m", "bars": series["5m"]})
                    if series.get("15m"):
                        ohlcv_15m.append({"ticker": t, "security_id": t, "interval": "15m", "bars": series["15m"]})
                write_jsonl(pkg / "intraday_1m.jsonl", ohlcv_1m)
                write_jsonl(pkg / "intraday_5m.jsonl", ohlcv_5m)
                write_jsonl(pkg / "intraday_15m.jsonl", ohlcv_15m)
            except Exception:
                pass
            # Keep dated alias packages and the dashboard alias in sync when possible.
            alias = root / "output" / "explorer_handoff" / "explorer_handoff.json"
            if alias.exists() and alias.resolve() != handoff_path.resolve():
                try:
                    alias.write_text(handoff_path.read_text(encoding="utf-8"), encoding="utf-8")
                    write_package_stamp(alias.parent, data_stamp)
                except Exception:
                    pass
        except Exception as e:
            return _fail(_user_exc(e, "Intraday bars were fetched but the Explorer package could not be updated."))

    age = bar_age_seconds(pack)
    intra = data_stamp.get("intraday") or {}
    enriched = int(pack.get("intraday_enriched") or 0)
    today_n = int(pack.get("today_session_enriched") or 0)
    requested = len(tickers)
    phase = sess.get("session_phase")
    fetched = intra.get("fetched_at_cairo_display") or data_stamp.get("packaged_at_cairo_display")
    last_bar = intra.get("last_bar_cairo_display") or "none"
    delay = intra.get("last_bar_delay_seconds")
    delay_txt = f"{int(delay // 60)} min delayed" if delay is not None else "delay unknown"
    msg = (
        f"Today's Intraday fetched at {fetched}. "
        f"Newest TradingView candle: {last_bar} ({delay_txt}). "
        f"{enriched} / {requested} candidates returned bars"
        f" ({today_n} with today's session timestamps). "
        "This downloads delayed TV candles — it does not create live quotes."
    )
    if phase != "CONTINUOUS_TRADING":
        msg += " Market is not in continuous trading — bars may be the latest available, not live."
    if requested and enriched < requested:
        msg += f" {requested - enriched} candidates still lack intraday confirmation (TradingView can be flaky)."
    return _ok(
        msg,
        result=pack,
        age_seconds=age,
        enriched=enriched,
        requested=requested,
        today_session=pack.get("today_session"),
        today_session_enriched=today_n,
        package_dir=package_dir,
        tickers=tickers,
        data_stamp=data_stamp,
        warning=stamp_caption(data_stamp),
    )


def update_outcomes(*, store, db) -> dict[str, Any]:
    if store is None:
        return _fail("No analysis store is available, so outcomes cannot be updated.")
    try:
        from egxbridge.analysis.schedule.outcomes import update_outcomes_for_store
        res = update_outcomes_for_store(store, db)
    except Exception as e:
        return _fail(_user_exc(e, "Outcome update did not complete."))
    n = (res or {}).get("updated") or (res or {}).get("updated_n") or 0
    return _ok(f"Signal outcomes updated ({n} rows).", result=res)


def save_upload(uploaded, *, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / uploaded.name
    dest.write_bytes(uploaded.getvalue())
    return dest
