"""Read-only operator snapshot from existing packages, store, and session clock."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from egxbridge.analysis.common.environment import PRODUCTION
from egxbridge.analysis.common.ai_mode import AI_CHATGPT_HANDOFF
from egxbridge.analysis.schedule.session import session_context, parse_dt, CAIRO
from egxbridge.analysis.schedule.types import ANALYSIS_TYPES
from egxbridge.analysis.schedule.decisions import suggested_funnel_action
from egxbridge.analysis.schedule.metrics import observation_counts, calibration_status_for_n
from egxbridge.ui.versions import version_labels
from egxbridge.ui.workflow_state import (
    freshness_state, freshness_note, explorer_status, recommended_jobs, intraday_card_state,
    next_recommended_action, build_step_statuses, is_weekend,
    NEXT_SESSION_JOBS, INTRADAY_ACTIONABLE_MAX_AGE_SECONDS,
)


HERE = Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _existing(path: str | Path | None) -> Path | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    text = str(p)
    if "pytest-of-" in text or "/T/pytest" in text or "pytest-" in text:
        return None
    return p


def _candidate_n(payload: dict[str, Any]) -> int:
    return len(payload.get("candidates") or []) or int(
        payload.get("handoff_candidate_count") or (payload.get("counts") or {}).get("HANDOFF_CANDIDATES") or 0
    )


def _package_from_dir(pkg: Path | None) -> dict[str, Any]:
    if not pkg or not pkg.exists():
        return {}
    if (pkg / "explorer_handoff.json").exists():
        return _load_json(pkg / "explorer_handoff.json")
    return {}


def resolve_explorer_package(root: Path | None = None) -> dict[str, Any]:
    """Resolve the latest *usable* Explorer package.

    Ignore last_run.json when its package_dir is a vanished pytest temp path.
    If the dashboard alias only has a tiny leftover shortlist, prefer the
    accepted broad-universe package when present.
    """
    root = root or HERE
    last_raw = _load_json(root / "workspace" / "explorer" / "last_run.json")
    last = last_raw if _existing(last_raw.get("package_dir")) else {}
    pkg = _existing(last.get("package_dir"))
    alias = root / "output" / "explorer_handoff"
    v06 = root / "output" / "acceptance" / "v06" / "explorer_handoff"
    if pkg is None:
        if (alias / "explorer_handoff.json").exists():
            pkg = alias
        elif alias.exists():
            kids = sorted([p for p in alias.iterdir() if p.is_dir()], reverse=True)
            for k in kids:
                if (k / "explorer_handoff.json").exists() or (k / "candidate_metrics.csv").exists():
                    pkg = k
                    break
        payload_alias = _package_from_dir(pkg)
        if _candidate_n(payload_alias) < 10 and (v06 / "explorer_handoff.json").exists():
            if _candidate_n(_package_from_dir(v06)) >= 10:
                pkg = v06
                last = {}
    payload = _package_from_dir(pkg)
    counts = dict(payload.get("counts") or {})
    if last.get("counts") and pkg and str(pkg) == str(last.get("package_dir")):
        counts = {**counts, **(last.get("counts") or {})}
    coverage = payload.get("coverage") or {}
    if last.get("coverage") and pkg and str(pkg) == str(last.get("package_dir")):
        coverage = last.get("coverage") or coverage
    man = _load_json((pkg / "manifest.json") if pkg else Path()) or {}
    if last.get("manifest") and pkg and str(pkg) == str(last.get("package_dir")):
        man = {**(last.get("manifest") or {}), **man}
    uni = _load_json((pkg / "universe_coverage.json") if pkg else Path()) or {}
    if uni:
        counts = {**uni, **counts}
    zip_path = last.get("zip_path")
    if zip_path and not Path(zip_path).exists():
        zip_path = None
    return {
        "last_run": last or last_raw,
        "package_dir": str(pkg) if pkg else None,
        "payload": payload,
        "counts": counts,
        "coverage": coverage,
        "manifest": man,
        "candidates": list(payload.get("candidates") or []),
        "zip_path": zip_path,
        "explorer_run_id": last.get("explorer_run_id") or payload.get("explorer_run_id") or man.get("explorer_run_id"),
        "generated_at": man.get("generated_at") or payload.get("generated_at") or last.get("generated_at"),
        "latest_session": (
            payload.get("latest_completed_market_session")
            or counts.get("latest_completed_market_session")
            or man.get("latest_session")
            or payload.get("latest_session")
        ),
        "scoring_version": man.get("scoring_version") or payload.get("scoring_version") or "0.5.1",
        "intraday_queried_tickers": list(payload.get("intraday_queried_tickers") or []),
    }


def resolve_schedule_package(root: Path | None = None) -> dict[str, Any]:
    root = root or HERE
    last = _load_json(root / "workspace" / "schedule" / "last_run.json")
    pkg = _existing(last.get("package_dir"))
    man = last.get("manifest") or {}
    if pkg and (pkg / "manifest.json").exists():
        man = {**man, **_load_json(pkg / "manifest.json")}
    zips = last.get("individual_zips") or {}
    combined = last.get("combined_zip")
    if combined and not Path(combined).exists():
        combined = None
    return {
        "last_run": last,
        "package_dir": str(pkg) if pkg else None,
        "manifest": man,
        "run_id": last.get("run_id") or man.get("run_id"),
        "combined_zip": combined,
        "individual_zips": {k: v for k, v in zips.items() if v and Path(v).exists()},
        "generated_at": man.get("generated_at"),
        "latest_session": man.get("latest_completed_market_session"),
        "included_jobs": man.get("included_jobs") or list(ANALYSIS_TYPES),
        "candidate_count": man.get("handoff_candidate_count"),
        "explorer_run_id": man.get("explorer_run_id"),
        "session_phase": man.get("session_phase"),
    }


def _import_status_for_job(store, job: str, schedule_run_id: str | None) -> dict[str, Any]:
    if store is None:
        return {"status": "NOT IMPORTED", "imported_at": None, "run_id": None, "envelope": None}
    rec = store.latest_schedule_import(job)
    if not rec:
        return {"status": "NOT IMPORTED", "imported_at": None, "run_id": None, "envelope": None}
    same = (not schedule_run_id) or rec.get("run_id") == schedule_run_id
    return {
        "status": "IMPORTED" if same else "IMPORTED (other run)",
        "imported_at": rec.get("imported_at"),
        "run_id": rec.get("run_id"),
        "envelope": rec.get("envelope"),
        "structured_parse_status": None,
        "same_package": same,
        "raw_path": rec.get("raw_result_path"),
    }


def _funnel_rows(candidates: list[dict[str, Any]], value_import: dict[str, Any] | None) -> list[dict[str, Any]]:
    env = (value_import or {}).get("envelope") or {}
    by_t = {}
    for c in env.get("candidates") or []:
        if isinstance(c, dict) and c.get("ticker"):
            by_t[str(c["ticker"]).upper()] = c
    cand_by = {str(c.get("ticker") or "").upper(): c for c in candidates if c.get("ticker")}
    rows = []
    if by_t:
        for t, chat in by_t.items():
            local = cand_by.get(t) or {}
            chat_action = chat.get("funnel_action") or chat.get("FUNNEL_ACTION")
            action = chat_action or suggested_funnel_action(local.get("funnel_status"))
            rows.append({
                "ticker": t,
                "funnel_status": local.get("funnel_status") or chat.get("funnel_status") or "NOT_FOUND",
                "recommended_action": action,
                "source": "CHATGPT ANALYSIS" if chat_action else "LOCAL HEURISTIC",
                "canonical_signal_id": local.get("canonical_signal_id") or chat.get("canonical_signal_id"),
            })
        return rows
    for t, c in cand_by.items():
        action = suggested_funnel_action(c.get("funnel_status"))
        if action in {"CONTINUE_FUNNEL", "RUN_DELTA"}:
            rows.append({
                "ticker": t,
                "funnel_status": c.get("funnel_status") or "NOT_FOUND",
                "recommended_action": action,
                "source": "LOCAL HEURISTIC",
                "canonical_signal_id": c.get("canonical_signal_id"),
            })
    return rows


def _plan_from_imports(imports: dict[str, dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    macro = ((imports.get("MACRO_HOLDINGS") or {}).get("envelope")) or {}
    pre = ((imports.get("PREMARKET_CATALYSTS") or {}).get("envelope")) or {}
    if not macro and not pre:
        return None
    by_t = {}
    for c in pre.get("candidates") or []:
        if isinstance(c, dict) and c.get("ticker"):
            by_t[str(c["ticker"]).upper()] = c
    watch, wait, avoid = [], [], []
    for t, row in by_t.items():
        st = (row.get("next_session_status") or row.get("status") or "").upper()
        if st in {"PROMOTE"}:
            watch.append(t)
        elif st in {"WATCH_ONLY", "KEEP"}:
            wait.append(t)
        elif st in {"REMOVE", "DOWNGRADE"}:
            avoid.append(t)
    funnel = []
    val = ((imports.get("VALUE_QUALITY") or {}).get("envelope")) or {}
    for c in val.get("candidates") or []:
        if not isinstance(c, dict):
            continue
        act = c.get("funnel_action") or c.get("FUNNEL_ACTION")
        if act and act not in {"NO_ACTION"}:
            funnel.append({"ticker": str(c.get("ticker") or "").upper(), "action": act})
    return {
        "source": "CHATGPT ANALYSIS",
        "market_regime": macro.get("market_regime") or macro.get("MARKET_REGIME"),
        "portfolio_posture": macro.get("portfolio_posture") or macro.get("PORTFOLIO_POSTURE"),
        "priority_watch": watch,
        "wait_for_confirmation": wait,
        "avoid_chase": avoid,
        "funnel_action": funnel,
    }


def _latest_session_from_handoff(handoff: dict[str, Any]) -> str | None:
    dates = []
    for s in handoff.get("symbols") or []:
        q = s.get("quote") or {}
        d = q.get("session_date") or q.get("effective_session_date") or s.get("session_date")
        if d:
            dates.append(str(d)[:10])
    return max(dates) if dates else None


def _intraday_age_seconds(candidates: list[dict[str, Any]], now: datetime | None = None) -> float | None:
    now = now or datetime.now(timezone.utc)
    stamps = []
    for c in candidates:
        intra = c.get("intraday") or {}
        if not isinstance(intra, dict):
            continue
        for key in ("captured_at", "timestamp", "provider_timestamp", "normalized_utc_timestamp"):
            raw = intra.get(key)
            dt = parse_dt(raw) if raw else None
            if dt:
                stamps.append(dt)
        rows = intra.get("interval_rows") or intra.get("rows") or intra.get("intervals") or []
        for r in rows:
            if not isinstance(r, dict):
                continue
            dt = parse_dt(
                r.get("normalized_utc_timestamp")
                or r.get("latest_timestamp_utc")
                or r.get("timestamp")
                or r.get("provider_timestamp")
            )
            if dt:
                stamps.append(dt)
    if not stamps:
        return None
    latest = max(stamps)
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    return max(0.0, (now - latest.astimezone(timezone.utc)).total_seconds())


def gather_operator_snapshot(
    *,
    root: Path | None = None,
    store=None,
    db=None,
    environment: str = PRODUCTION,
    session_meta: dict[str, Any] | None = None,
    now: datetime | None = None,
    intraday_age_seconds: float | None = None,
) -> dict[str, Any]:
    root = root or HERE
    sess = dict(session_meta) if session_meta else session_context(now)
    labels = version_labels(environment=environment)
    handoff = _load_json(root / "output" / "chatgpt_handoff.json")
    explorer = resolve_explorer_package(root)
    schedule = resolve_schedule_package(root)
    candidates = explorer.get("candidates") or []
    counts = explorer.get("counts") or {}
    cairo_wd = None
    cairo_iso = sess.get("analysis_timestamp_cairo")
    cdt = parse_dt(cairo_iso)
    if cdt is not None:
        cairo_wd = cdt.astimezone(CAIRO).weekday()
    weekend = is_weekend(cairo_wd)
    market_session = (
        explorer.get("latest_session")
        or schedule.get("latest_session")
        or _latest_session_from_handoff(handoff)
    )
    payload = explorer.get("payload") or {}
    daily_n = int(
        counts.get("DAILY_DATA_AVAILABLE")
        or counts.get("daily_data_available")
        or payload.get("data_eligible_count")
        or 0
    )
    equity_n = int(
        counts.get("EQUITY_UNIVERSE_TOTAL")
        or counts.get("equity_universe_total")
        or payload.get("equity_universe_total")
        or payload.get("universe_total")
        or 0
    )
    scanner_n = int(
        counts.get("SCANNER_ELIGIBLE_SYMBOLS")
        or counts.get("scanner_eligible_symbols")
        or counts.get("scanner_candidate_count")
        or payload.get("scanner_candidate_count")
        or 0
    )
    data_usable = bool(handoff or scanner_n or daily_n or candidates)
    hs = handoff.get("status")
    if not handoff and not daily_n and not candidates:
        market_data_status = "NOT RUN"
        provider_status = "NOT RUN"
    elif hs == "PARTIAL":
        market_data_status = "READY_WITH_LIMITATIONS"
        provider_status = "PARTIAL"
    elif hs in {"OK", "READY"}:
        market_data_status = "READY"
        provider_status = "OK"
    else:
        market_data_status = "READY" if data_usable else "NOT RUN"
        provider_status = hs or ("READY" if data_usable else "NOT RUN")
    provider_rows: list[dict[str, Any]] = []
    if db is not None:
        try:
            provider_rows = list(db.fetch_provider_status() or [])
        except Exception:
            provider_rows = []
    if not provider_rows and handoff.get("providers"):
        provider_rows = list(handoff.get("providers") or [])
    provider_summary = [
        {
            "name": r.get("name") or r.get("provider"),
            "state": r.get("health_state") or r.get("status") or r.get("state"),
        }
        for r in provider_rows
    ]
    latest_collection_at = handoff.get("generated_at")
    if db is not None and not latest_collection_at:
        try:
            runs = db.fetch_runs(limit=1) or []
            if runs:
                latest_collection_at = runs[0].get("finished_at") or runs[0].get("started_at")
        except Exception:
            pass
    unexpected = False
    if sess.get("session_phase") in {"CONTINUOUS_TRADING"} and handoff:
        classes = [(s.get("quote") or {}).get("freshness_class") or s.get("freshness") for s in handoff.get("symbols") or []]
        if classes and all(c in {"STALE_EXPECTED", "STALE"} for c in classes if c):
            unexpected = True
    fresh = freshness_state(session_phase=sess.get("session_phase"), unexpected_stale=unexpected)
    cov = (explorer.get("coverage") or {}).get("EXPLORER_COVERAGE") or counts.get("EXPLORER_COVERAGE")
    exp_status = explorer_status(
        has_explorer=bool(explorer.get("package_dir") or candidates),
        candidate_count=len(candidates),
        explorer_session=explorer.get("latest_session"),
        market_session=market_session,
        coverage=cov,
    )
    rec_jobs = recommended_jobs(session_phase=sess.get("session_phase"), cairo_weekday=cairo_wd)
    imports = {}
    imported_current = 0
    if store:
        for job in ANALYSIS_TYPES:
            imports[job] = _import_status_for_job(store, job, schedule.get("run_id"))
            if imports[job]["status"] == "IMPORTED":
                imported_current += 1
    rec_imported = sum(1 for j in rec_jobs["recommended"] if (imports.get(j) or {}).get("status") == "IMPORTED")
    funnel_rows = _funnel_rows(candidates, imports.get("VALUE_QUALITY"))
    funnel_needed = [
        r for r in funnel_rows
        if (r.get("recommended_action") or "") not in {"NO_ACTION", "REVIEW_EXISTING_FUNNEL", "NO_FUNNEL_ACTION"}
    ]
    oc = {"analysis_observations_generated_n": 0, "analysis_observations_imported_n": 0, "analysis_observations_evaluable_n": 0}
    canon_n = pending = complete_1 = complete_3 = complete_5 = complete_20 = not_eval = 0
    if store:
        obs = store.list_analysis_observations(limit=5000)
        oc = observation_counts(obs)
        canon = store.list_canonical_signals(limit=2000)
        canon_n = len(canon)
        outs = store.list_canonical_outcomes(limit=2000)
        for o in outs:
            detail = json.loads(o.get("payload_json") or "{}")
            if detail.get("maturity_20") == "MATURE":
                complete_20 += 1
            st_out = o.get("outcome_status") or ""
            if st_out == "NOT_EVALUABLE":
                not_eval += 1
            if o.get("return_5_sessions") is not None or st_out in {"COMPLETE", "COMPLETE_FOR_5D"}:
                complete_5 += 1
            if o.get("return_3_sessions") is not None:
                complete_3 += 1
            if o.get("next_session_return") is not None:
                complete_1 += 1
        pending = max(0, canon_n - complete_20 - not_eval)
    age = intraday_age_seconds
    if age is None:
        age = _intraday_age_seconds(candidates, now=now)
    intra = intraday_card_state(session_phase=sess.get("session_phase"), age_seconds=age)
    outcomes_update_recommended = bool(pending and not weekend and sess.get("session_phase") not in {"PRE_OPEN"})
    # Weekend: pending is expected; do not push outcomes as next action.
    if weekend:
        outcomes_update_recommended = False
    snap = {
        "versions": labels,
        "environment": environment,
        "ai_mode": AI_CHATGPT_HANDOFF,
        "session_phase": sess.get("session_phase"),
        "session_meta": sess,
        "cairo_time": sess.get("analysis_timestamp_cairo"),
        "utc_time": sess.get("analysis_timestamp_utc"),
        "cairo_weekday": cairo_wd,
        "weekend": weekend,
        "latest_completed_market_session": market_session,
        "handoff": handoff,
        "handoff_status": handoff.get("status"),
        "handoff_generated_at": handoff.get("generated_at"),
        "latest_collection_at": latest_collection_at,
        "data_usable": data_usable,
        "market_data_status": market_data_status,
        "provider_status": provider_status,
        "provider_summary": provider_summary,
        "freshness": fresh,
        "freshness_note": freshness_note(fresh, session_phase=sess.get("session_phase")),
        "unexpected_stale": unexpected,
        "equity_universe": equity_n,
        "daily_data_available": daily_n,
        "scanner_eligible": scanner_n,
        "prescreen": int(counts.get("PRESCREEN_SELECTED") or counts.get("prescreen_selected") or payload.get("prescreen_selected") or 0),
        "handoff_candidates": int(counts.get("HANDOFF_CANDIDATES") or counts.get("handoff_candidate_count") or payload.get("handoff_candidate_count") or len(candidates)),
        "intraday_requested": (
            len(explorer.get("intraday_queried_tickers") or payload.get("intraday_queried_tickers") or [])
            or int(counts.get("intraday_limit") or 0)
            or 15
        ),
        "intraday_enriched": int(counts.get("INTRADAY_ENRICHED") or counts.get("intraday_enriched") or payload.get("intraday_enriched") or 0),
        "has_intraday_selected": bool(
            explorer.get("intraday_queried_tickers")
            or payload.get("intraday_queried_tickers")
            or any(c.get("intraday_available") or c.get("intraday_selection_reason") for c in candidates)
        ),
        "explorer": explorer,
        "explorer_status": exp_status,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "schedule": schedule,
        "schedules_prepared": bool(schedule.get("run_id") and schedule.get("package_dir")),
        "next_session_jobs": list(NEXT_SESSION_JOBS),
        "imports": imports,
        "imported_n": imported_current,
        "generated_n": oc.get("analysis_observations_generated_n") or 0,
        "evaluable_n": oc.get("analysis_observations_evaluable_n") or 0,
        "chatgpt_imported_n": oc.get("analysis_observations_imported_n") or 0,
        "recommended_jobs": rec_jobs["recommended"],
        "recommended_jobs_n": len(rec_jobs["recommended"]),
        "recommended_imported_n": rec_imported,
        "weekly_recommended": rec_jobs.get("weekly_recommended"),
        "weekly_imported": (imports.get("WEEKLY_XRAY") or {}).get("status") == "IMPORTED",
        "job_recommendations": rec_jobs,
        "funnel_rows": funnel_rows,
        "funnel_action_n": len(funnel_needed),
        "funnel_action_required": bool(funnel_needed),
        "intraday": intra,
        "intraday_age_seconds": age,
        "intraday_max_age_seconds": INTRADAY_ACTIONABLE_MAX_AGE_SECONDS,
        "canonical_n": canon_n,
        "outcomes_pending_n": pending,
        "outcomes_1s_n": complete_1,
        "outcomes_3s_n": complete_3,
        "outcomes_5s_n": complete_5,
        "outcomes_not_evaluable_n": not_eval,
        "outcomes_update_recommended": outcomes_update_recommended,
        "calibration_status": calibration_status_for_n(complete_1 or canon_n),
        "plan": _plan_from_imports(imports, candidates),
        "coverage": cov,
        "scoring_version": explorer.get("scoring_version") or "0.5.1",
    }
    snap["next_action"] = next_recommended_action(snap)
    snap["readiness"] = build_step_statuses(snap)
    return snap
