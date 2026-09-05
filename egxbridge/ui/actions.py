"""Thin wrappers around existing backend actions. No duplicated analysis math."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import shutil

from egxbridge.analysis.common.environment import PRODUCTION
from egxbridge.analysis.schedule.types import ANALYSIS_TYPES
from egxbridge.ui.workflow_state import NEXT_SESSION_JOBS, ALL_JOBS


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


def refresh_market_data(*, root: Path | None = None, force_refetch: bool = False) -> dict[str, Any]:
    """Collect universe daily bars + focus snapshot. Direct Python APIs only."""
    root = root or HERE
    try:
        from egxbridge.config import Settings
        from egxbridge.db import Database
        from egxbridge.collect_universe import collect_universe_daily
        from egxbridge.collector import run_once
    except Exception as e:
        return _fail(_user_exc(e, "Could not load collection modules."))
    settings = Settings.load(root / "config.json")
    db = Database(settings.db_path(root))
    try:
        uni = collect_universe_daily(db=db, settings=settings, refresh=force_refetch)
        snap = run_once(settings, root)
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
    symbols = (snap or {}).get("symbols") or []
    if equity_n and ok_n and ok_n < equity_n:
        msg = (
            f"Yahoo daily collection returned data for {ok_n} / {equity_n} equities. "
            "Explorer can continue with the eligible names that have usable history."
        )
    else:
        msg = f"Market data refresh completed. Daily coverage {ok_n} equities; snapshot symbols {len(symbols)}."
    return _ok(
        msg,
        universe=uni,
        snapshot=snap,
        daily_ok=ok_n,
        daily_failed=fail_n,
        snapshot_status=(snap or {}).get("status"),
        generated_at=(snap or {}).get("generated_at"),
    )


def run_broad_explorer(*, store, db, funnel_registry, enrich_intraday: bool = False) -> dict[str, Any]:
    try:
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
) -> dict[str, Any]:
    """Daily Operator quick path: skip closed-market Yahoo/TV round-trips when data is already usable."""
    from egxbridge.ui.workflow_state import explorer_should_enrich_intraday, should_skip_market_refresh

    snap = snapshot or {}
    notes: list[str] = []
    if force_collect or not should_skip_market_refresh(snap):
        collect_result = refresh_market_data(root=root)
        if not collect_result.get("ok"):
            return collect_result
        notes.append(collect_result.get("message") or "Market data refreshed.")
    else:
        notes.append(
            "Skipped Yahoo refetch — the market is closed and latest-session daily bars are already usable."
        )
        collect_result = {"ok": True, "skipped": True, "message": notes[-1]}
    enrich = explorer_should_enrich_intraday(snap.get("session_phase"), force=force_tv)
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
    extra = {"result": res, "zip_path": str(alias) if alias else (res or {}).get("combined_zip")}
    return _ok(f"Prepared one ChatGPT handoff ZIP with: {names}.", **extra)


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
    return _ok(f"Imported Funnel result for {t}. Original preserved.", result=res)


def refresh_intraday(*, explorer_payload: dict[str, Any] | None, root: Path | None = None) -> dict[str, Any]:
    root = root or HERE
    payload = explorer_payload or {}
    tickers = list(payload.get("intraday_queried_tickers") or [])
    if not tickers:
        tickers = [
            str(c.get("ticker")).upper()
            for c in (payload.get("candidates") or [])
            if c.get("ticker") and (c.get("intraday_available") or c.get("intraday_selection_reason"))
        ]
    if not tickers:
        return _fail("Prepare Intraday requires intraday-selected candidates. Run Broad Explorer first.")
    try:
        from egxbridge.config import Settings
        from egxbridge.symbols import SymbolRegistry
        from egxbridge.providers.tradingview import TradingViewProvider
        from egxbridge.analysis.explorer.intraday import enrich_shortlist_intraday
        from egxbridge.analysis.schedule.session import parse_dt
        from datetime import datetime, timezone
        settings = Settings.load(root / "config.json")
        registry = SymbolRegistry.from_config({"symbol_aliases": settings.symbol_aliases})
        tv = TradingViewProvider(
            registry,
            enabled=bool((settings.enabled_providers or {}).get("tradingview", True)),
            username=settings.tradingview_username,
            password=settings.tradingview_password,
        )
        pack = enrich_shortlist_intraday(tickers, tv=tv)
    except Exception as e:
        return _fail(_user_exc(e, "Intraday refresh did not complete."))
    stamps = []
    now = datetime.now(timezone.utc)
    for rec in pack.get("rows") or []:
        dt = parse_dt(rec.get("latest_timestamp_utc"))
        if dt:
            stamps.append(dt)
    age = None
    if stamps:
        latest = max(stamps)
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        age = max(0.0, (now - latest.astimezone(timezone.utc)).total_seconds())
    enriched = int(pack.get("intraday_enriched") or 0)
    requested = len(tickers)
    msg = f"Intraday refresh completed. {enriched} / {requested} candidates returned TradingView bars."
    if requested and enriched < requested:
        msg += f" {requested - enriched} candidates will lack intraday confirmation."
    return _ok(msg, result=pack, age_seconds=age, enriched=enriched, requested=requested)


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
