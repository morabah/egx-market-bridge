"""Build the 5-schedule ChatGPT handoff packages from an Explorer run."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import hashlib

from egxbridge import __version__ as BRIDGE_VERSION
from egxbridge.analysis import WORKFLOW_VERSION
from egxbridge.analysis.common.ai_mode import AI_CHATGPT_HANDOFF, assert_handoff_only
from egxbridge.analysis.common.environment import PRODUCTION, UNIT_TEST, normalize_environment
from egxbridge.analysis.common.models import utc_now
from egxbridge.analysis.common.data_stamp import (
    build_data_stamp,
    dated_zip_name,
    job_stamp_preamble,
    write_package_stamp,
    write_zip_sidecar,
)
from egxbridge.analysis.common.packaging import write_json, write_text, zip_directory, list_files_relative
from egxbridge.analysis.explorer.calibration import SCORING_VERSION, SCORE_KIND
from egxbridge.analysis.schedule.types import (
    ANALYSIS_TYPES, ANALYSIS_MACRO, ANALYSIS_PREMARKET, ANALYSIS_INTRADAY,
    ANALYSIS_VALUE, ANALYSIS_WEEKLY, ANALYSIS_EXPLORER, JOB_FILE, JOB_ZIP_PREFIX,
    RESULT_ENVELOPE_VERSION, HANDOFF_SCHEMA_VERSION, SUPPORTED_RESULT_ENVELOPE_VERSION,
    RESULT_SCHEMA_FILES, ANALYSIS_OBSERVATIONS_N_SEMANTICS, DEPRECATED_FIELDS,
    STALE_EVIDENCE_PHASES, NOT_LIVE_CONFIRMATION_TEXT,
)
from egxbridge.analysis.schedule.session import session_context, parse_dt
from egxbridge.analysis.schedule.result_schemas import (
    build_all_job_schemas, result_schema_index,
)
from egxbridge.analysis.schedule.identity import LIVE_PHASES, has_current_session_evidence
from egxbridge.analysis.schedule.market_summary import build_market_summary
from egxbridge.analysis.schedule.jobs import RENDERERS
from egxbridge.analysis.schedule.snapshots import build_signal_snapshot, persist_snapshots
from egxbridge.analysis.schedule.identity import make_explorer_run_id, persist_job_observations
from egxbridge.analysis.schedule.metrics import summarize_outcomes, group_summaries, false_positive_cases, calibration_status_for_n
from egxbridge.analysis.schedule.decisions import suggested_funnel_action, persist_daily_decision, build_daily_decision
from egxbridge.storage import rows_to_csv


HERE = Path(__file__).resolve().parents[3]
EXPLORER_PACKAGE_VERSION = "0.6.0"


COMPACT_FIELDS = (
    "ticker", "canonical_signal_id", "signal_family_id", "parent_signal_id",
    "market_state_fingerprint", "analysis_type", "schedule_run_id", "explorer_run_id",
    "candidate_lane", "candidate_families", "candidate_score_calibrated",
    "forward_setup_score", "FORWARD_SETUP_QUALITY", "MOVE_ALREADY_REALIZED",
    "RVOL20", "rvol_20", "distance_20d_high", "dist_from_20d_high_pct",
    "VOLATILITY_RISK", "TECHNICAL_HISTORY_INTEGRITY", "funnel_status",
    "intraday_available", "intraday_selection_reason", "intraday_selection_lane",
    "intraday_selection_rank_within_lane", "calibrated_rank", "legacy_rank",
    "daily_return", "return_1w", "return_1m", "return_3m", "return_6m",
    "recommended_deep_analysis",
    "session_date", "latest_session", "expected_session", "daily_bars_lagging", "daily_provider",
)


def _compact(c: dict[str, Any]) -> dict[str, Any]:
    row = {k: c.get(k) for k in COMPACT_FIELDS if c.get(k) is not None}
    m = c.get("metrics") or {}
    for key in ("latest_session", "expected_session", "daily_bars_lagging", "daily_provider"):
        row[key] = c.get(key) if c.get(key) is not None else m.get(key)
    row["session_date"] = c.get("session_date") or row.get("latest_session")
    row.setdefault("RVOL20", c.get("RVOL20") or m.get("rvol_20"))
    row.setdefault("distance_20d_high", c.get("distance_20d_high") or m.get("dist_from_20d_high_pct"))
    row.setdefault("funnel_status", c.get("funnel_status"))
    row["bridge_suggested_funnel_action"] = suggested_funnel_action(c.get("funnel_status"))
    row["score_kind"] = SCORE_KIND
    row["scoring_version"] = SCORING_VERSION
    row["not_a_probability"] = True
    row["canonical_ticker"] = c.get("canonical_ticker") or c.get("ticker")
    row["eligibility_state"] = c.get("eligibility_state")
    row["recovery_state"] = c.get("recovery_state")
    intra = c.get("intraday") or {}
    ohlcv = intra.get("ohlcv") if isinstance(intra, dict) else None
    if ohlcv:
        row["intraday_ohlcv"] = {
            k: v for k, v in ohlcv.items() if v
        }
    vol = c.get("session_volume") or (intra.get("session_volume") if isinstance(intra, dict) else None)
    if vol:
        row["session_volume"] = vol
    row["depth"] = c.get("depth") or (intra.get("depth") if isinstance(intra, dict) else None)
    row["trades"] = c.get("trades") or (intra.get("trades") if isinstance(intra, dict) else None)
    if isinstance(intra, dict):
        for k in (
            "intraday_fetch_state", "provider_symbol", "attempt_count",
            "error_class", "error_message_sanitized", "bars_returned_1m",
            "bars_returned_5m", "bars_returned_15m", "latest_bar_timestamp",
            "cache_status", "status", "age_seconds", "fallback_used", "fallback_source",
        ):
            if intra.get(k) is not None:
                row[k] = intra.get(k)
    fctx = c.get("funnel_context") or c.get("funnel_ctx") or {}
    row["imported_funnel_v28"] = {"fields": fctx.get("structured_fields") or {},
        "provenance": fctx.get("structured_provenance") or {}, "funnel_version": fctx.get("funnel_version"),
        "classification_source": "FUNNEL_LLM", "missing_fields": "NOT_ANALYZED"}
    return row


def _attach_identity(
    rows: list[dict[str, Any]],
    ident_map: dict[str, dict[str, Any]],
    *,
    analysis_type: str,
    schedule_run_id: str | None,
    explorer_run_id: str | None,
) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        t = str(row.get("ticker") or "").upper()
        ident = ident_map.get(t) or {}
        merged = dict(row)
        merged["ticker"] = t
        merged["canonical_signal_id"] = ident.get("canonical_signal_id") or row.get("canonical_signal_id")
        merged["signal_family_id"] = ident.get("signal_family_id") or row.get("signal_family_id")
        merged["parent_signal_id"] = ident.get("parent_signal_id") if ident.get("parent_signal_id") is not None else row.get("parent_signal_id")
        merged["market_state_fingerprint"] = ident.get("market_state_fingerprint") or row.get("market_state_fingerprint")
        merged["analysis_type"] = analysis_type
        merged["schedule_run_id"] = schedule_run_id
        merged["explorer_run_id"] = ident.get("explorer_run_id") or explorer_run_id
        out.append(merged)
    return out


class IdentityConflictError(ValueError):
    """Package representations disagree on canonical identity for a ticker."""

    def __init__(self, conflicts: list[dict[str, Any]]):
        self.conflicts = conflicts
        msg = "IDENTITY_CONFLICT: " + json.dumps(conflicts, default=str)
        super().__init__(msg)


def identity_tuple(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("canonical_signal_id") or ""),
        str(row.get("signal_family_id") or ""),
        str(row.get("market_state_fingerprint") or ""),
    )


def reconcile_identity_groups(groups: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Same-layer representations of a ticker must share canonical identity fields."""
    by_ticker: dict[str, dict[str, tuple[str, str, str]]] = {}
    for source, rows in groups.items():
        for row in rows or []:
            t = str(row.get("ticker") or "").upper()
            if not t:
                continue
            by_ticker.setdefault(t, {})[source] = identity_tuple(row)
    conflicts = []
    for ticker, sources in by_ticker.items():
        vals = list(sources.values())
        if len(set(vals)) > 1:
            conflicts.append({
                "ticker": ticker,
                "by_source": {k: {"canonical_signal_id": v[0], "signal_family_id": v[1], "market_state_fingerprint": v[2]} for k, v in sources.items()},
            })
    return conflicts


def assert_identity_consistent(groups: dict[str, list[dict[str, Any]]]) -> None:
    conflicts = reconcile_identity_groups(groups)
    if conflicts:
        raise IdentityConflictError(conflicts)


def _overlay_identity(
    candidate: dict[str, Any],
    ident: dict[str, Any],
    *,
    analysis_type: str,
    schedule_run_id: str | None,
    explorer_run_id: str | None,
) -> dict[str, Any]:
    row = dict(candidate)
    t = str(candidate.get("ticker") or "").upper()
    row["ticker"] = t
    row["canonical_signal_id"] = ident.get("canonical_signal_id") or candidate.get("canonical_signal_id")
    row["signal_family_id"] = ident.get("signal_family_id") or candidate.get("signal_family_id")
    row["parent_signal_id"] = ident.get("parent_signal_id") if ident.get("parent_signal_id") is not None else candidate.get("parent_signal_id")
    row["market_state_fingerprint"] = ident.get("market_state_fingerprint") or candidate.get("market_state_fingerprint")
    row["analysis_type"] = analysis_type
    row["schedule_run_id"] = schedule_run_id
    row["explorer_run_id"] = ident.get("explorer_run_id") or explorer_run_id
    return row


def _is_live_intraday_row(candidate: dict[str, Any]) -> bool:
    intra = candidate.get("intraday") or {}
    fetch_state = None
    status = None
    if isinstance(intra, dict):
        fetch_state = intra.get("intraday_fetch_state") or candidate.get("intraday_fetch_state")
        status = intra.get("status") or intra.get("cache_status") or candidate.get("intraday_cache_status")
    if fetch_state in {"STALE_ONLY", "STALE_CACHE"} or status == "STALE_CACHE":
        return False
    if fetch_state and fetch_state != "SUCCESS":
        return False
    return has_current_session_evidence(candidate)


def live_session_evidence_available(
    candidates: list[dict[str, Any]],
    session_meta: dict[str, Any] | None,
    diagnostics: dict[str, Any] | None = None,
) -> bool:
    phase = (session_meta or {}).get("session_phase")
    if phase in STALE_EVIDENCE_PHASES or phase not in LIVE_PHASES:
        return False
    state = (diagnostics or {}).get("provider_state") or (diagnostics or {}).get("INTRADAY_PROVIDER_STATE")
    if state == "FAILED":
        return False
    return any(_is_live_intraday_row(c) for c in candidates)


def _deprecated_count_fields(generated_n: Any) -> dict[str, Any]:
    return {
        "analysis_observations_n": generated_n,
        "analysis_observations_n_semantics": ANALYSIS_OBSERVATIONS_N_SEMANTICS,
        "deprecated_fields": list(DEPRECATED_FIELDS),
    }


def _rebuild_universe_identity(payload: dict[str, Any], *, environment: str | None = None) -> list[dict[str, Any]]:
    from egxbridge.analysis.explorer.universe_state import (
        identity_row, ensure_canonical_identities, eligibility_state,
    )
    from egxbridge.symbols import load_name_aliases, canonicalize_any
    from egxbridge.universe import EQUITY, build_canonical_universe, assess_universe_coverage

    rows = list(payload.get("universe_identity") or [])
    aliases = load_name_aliases()
    expected = None
    if not rows:
        if environment == UNIT_TEST:
            tickers = []
            for c in payload.get("candidates") or []:
                if c.get("ticker"):
                    tickers.append(str(c["ticker"]).upper())
            for t in payload.get("counts", {}).get("SCANNER_ELIGIBLE_SYMBOLS_LIST") or []:
                tickers.append(str(t).upper())
            expected = list(dict.fromkeys(tickers))
            rows = [
                identity_row(canonical_ticker=t, instrument_type="EQUITY", data_status="SCANNER_ELIGIBLE")
                for t in expected
            ]
        else:
            built = build_canonical_universe()
            assessed = assess_universe_coverage(built, db=None)
            expected = list((assessed.get("status_by_symbol") or {}).keys())
            for t, st in (assessed.get("status_by_symbol") or {}).items():
                rows.append(identity_row(
                    canonical_ticker=t,
                    current_name=st.get("current_name") or "",
                    aliases=st.get("aliases") or [t],
                    instrument_type=st.get("instrument_type") or st.get("security_type") or EQUITY,
                    data_status=st.get("data_status"),
                    eligibility_reason=st.get("exclusion_reason"),
                ))
                rows[-1]["eligibility_state"] = eligibility_state(
                    st.get("data_status"), security_type=st.get("security_type"),
                )
                rows[-1]["universe_state"] = rows[-1]["eligibility_state"]
    else:
        expected = [str(r.get("canonical_ticker") or "").upper() for r in rows if r.get("canonical_ticker")]
        if len(expected) >= 50:
            for canon in aliases:
                c = canonicalize_any(canon)
                if c and c not in expected:
                    expected.append(c)
    return ensure_canonical_identities(rows, name_aliases=aliases, expected_tickers=expected)


def _recover_from_explorer_payload(payload: dict[str, Any], candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from egxbridge.analysis.explorer.session_screen import recover_missing_tickers

    existing_log = list(payload.get("missing_ticker_recovery_log") or [])
    if existing_log:
        return candidates, existing_log
    metrics = payload.get("scanner_eligible_metrics") or []
    snaps = payload.get("session_snapshots") or {}
    if isinstance(snaps, dict) and "snapshots" in snaps:
        snaps = snaps.get("snapshots") or {}
    shortlist = {str(c.get("ticker") or "").upper() for c in candidates if c.get("ticker")}
    scored = [{"ticker": r.get("ticker"), "metrics": r} for r in metrics if r.get("ticker")]
    log = recover_missing_tickers(scored, shortlist_tickers=shortlist, snapshots=snaps)
    present = {str(c.get("ticker") or "").upper() for c in candidates}
    for rec in log:
        t = rec.get("ticker")
        if not t or t in present:
            continue
        src = next((r for r in scored if str(r.get("ticker") or "").upper() == t), {"ticker": t, "metrics": {}})
        candidates.append({
            "ticker": t,
            "canonical_ticker": rec.get("canonical_ticker") or t,
            "metrics": src.get("metrics") or {},
            "recovery_state": rec.get("downstream_state"),
            "missing_ticker_recovery": rec,
            "intraday_selection_reason": "RECOVERED_CURRENT_MOVER",
            "intraday_selection_lane": "RECOVERY",
            "eligibility_state": "COVERED",
            "not_in_prior_shortlist": True,
            "intraday": {"ticker": t, "intraday_available": False, "intervals": [], "ohlcv": {},
                         "intraday_fetch_state": "UNKNOWN_FAILURE"},
        })
        present.add(t)
    return candidates, log


def _run_id(generated_at: str) -> str:
    tag = generated_at.replace(":", "").replace("-", "")[:15]
    h = hashlib.sha256(generated_at.encode()).hexdigest()[:8]
    return f"{tag}_{h}"


def load_explorer_package(package_dir: Path, *, db=None, store=None, require_current: bool = False) -> dict[str, Any]:
    payload = json.loads((package_dir / "explorer_handoff.json").read_text(encoding="utf-8"))
    if require_current:
        from egxbridge.semantics import previous_egx_session_date
        expected = previous_egx_session_date()
        required = ("daily_ohlcv.jsonl", "daily_collection_report.json", "daily_rejected_ohlcv.jsonl", "daily_collection_rejections.jsonl")
        identities = payload.get("universe_identity") or []
        equities = sum(r.get("instrument_type") == "EQUITY" for r in identities)
        daily = (payload.get("data_stamp") or {}).get("daily_coverage") or {}
        source_coverage = payload.get("universe_coverage") or {}
        from egxbridge.collect_universe import collection_report_for_db
        report = collection_report_for_db(db, as_of=parse_dt(utc_now()))
        collected = parse_dt(report.get("finished_at"))
        created = parse_dt(payload.get("generated_at"))
        needs_rebuild = (
            payload.get("environment") != PRODUCTION
            or not all((package_dir / name).is_file() for name in required)
            or not payload.get("daily_data_status")
            or daily.get("expected_session") != expected
            or (payload.get("counts") or {}).get("EQUITY_UNIVERSE_TOTAL") != equities
            or not source_coverage.get("reconcile_ok")
            or (payload.get("counts") or {}).get("SCANNER_ELIGIBLE_SYMBOLS") != source_coverage.get("scanner_eligible")
            or bool(collected and (not created or collected > created))
            or any(c.get("data_status") == "SCANNER_ELIGIBLE" and (
                c.get("latest_session") != expected or c.get("daily_bars_lagging") is not False
            ) for c in payload.get("candidates") or [])
        )
        if needs_rebuild:
            if db is None:
                raise ValueError("Daily evidence is missing or outdated. Run Broad Explorer from the market database before exporting.")
            from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
            from egxbridge.analysis.explorer.models import ExplorerRunConfig
            result = prepare_explorer_handoff(ExplorerRunConfig(environment=PRODUCTION), db=db, store=store)
            package_dir = Path(result["package_dir"])
            payload = json.loads((package_dir / "explorer_handoff.json").read_text(encoding="utf-8"))
    payload["_package_dir"] = str(package_dir)
    from egxbridge.analysis.schedule.market_summary import load_scanner_eligible_metrics, compute_breadth, MARKET_BREADTH_SCOPE, SHORTLIST_BREADTH_LABEL
    if not payload.get("scanner_eligible_metrics"):
        payload["scanner_eligible_metrics"] = load_scanner_eligible_metrics(payload)
    if not payload.get("market_breadth") and payload.get("scanner_eligible_metrics"):
        payload["market_breadth"] = compute_breadth(
            payload["scanner_eligible_metrics"], scope=MARKET_BREADTH_SCOPE, label="BROAD_MARKET_EVIDENCE",
        )
        payload["candidate_breadth"] = compute_breadth(
            payload.get("candidates") or [], scope=SHORTLIST_BREADTH_LABEL, label=SHORTLIST_BREADTH_LABEL,
        )
    return payload


def _missed_opportunities(explorer: dict[str, Any]) -> list[dict[str, Any]]:
    """Scanner-eligible names not in the handoff shortlist. Future moves stay null (no look-ahead)."""
    handoff = {c.get("ticker") for c in (explorer.get("candidates") or [])}
    ranked = explorer.get("ranked_comparison") or []
    out = []
    for r in ranked:
        t = r.get("ticker")
        if t in handoff:
            continue
        out.append({
            "ticker": t,
            "not_selected_reason": "NOT_IN_HANDOFF_SHORTLIST",
            "legacy_rank": r.get("legacy_rank"),
            "calibrated_rank": r.get("calibrated_rank"),
            "FORWARD_SETUP_QUALITY": r.get("FORWARD_SETUP_QUALITY"),
            "MOVE_ALREADY_REALIZED": r.get("MOVE_ALREADY_REALIZED"),
            "future_move": None,
            "no_lookahead": True,
        })
    return out[:40]


def _weekly_history(store, explorer: dict[str, Any]) -> dict[str, Any]:
    from egxbridge.analysis.schedule.identity import backfill_canonical_from_legacy_snapshots
    from egxbridge.analysis.schedule.metrics import scanner_performance, analysis_value_add, observation_counts
    if store:
        backfill_canonical_from_legacy_snapshots(store)
    canonical = store.list_canonical_signals(limit=2000) if store else []
    observations = store.list_analysis_observations(limit=5000) if store else []
    outcomes = store.list_canonical_outcomes(limit=2000) if store else []
    by_cid = {o.get("canonical_signal_id"): o for o in outcomes}
    joined_scanner = []
    for s in canonical:
        p = s.get("payload") or {}
        o = by_cid.get(s.get("canonical_signal_id")) or {}
        joined_scanner.append({**o, "payload": p, "ticker": s.get("ticker"), "canonical_signal_id": s.get("canonical_signal_id")})
    joined_obs = []
    for obs in observations:
        o = by_cid.get(obs.get("canonical_signal_id")) or {}
        joined_obs.append({**obs, **o, "payload": obs.get("payload") or {}})
    n_out = sum(1 for o in outcomes if o.get("next_session_return") is not None)
    complete = sum(1 for o in outcomes if (o.get("outcome_status") or "") in {"COMPLETE", "COMPLETE_FOR_5D"} or o.get("return_5_sessions") is not None)
    pending = max(0, len(canonical) - complete)
    oc = observation_counts(observations)
    hist = {
        "canonical_signals_n": len(canonical),
        "scanner_sample_n": len(canonical),
        "analysis_observations_n": oc["analysis_observations_generated_n"],
        "analysis_observations_n_semantics": ANALYSIS_OBSERVATIONS_N_SEMANTICS,
        "deprecated_fields": list(DEPRECATED_FIELDS),
        "analysis_observations_generated_n": oc["analysis_observations_generated_n"],
        "analysis_observations_imported_n": oc["analysis_observations_imported_n"],
        "analysis_observations_evaluable_n": oc["analysis_observations_evaluable_n"],
        "outcomes_complete_n": complete,
        "outcomes_pending_n": pending,
        "snapshot_count": None,
        "outcome_row_count": len(outcomes),
        "n_with_1_session_outcome": n_out,
        "CALIBRATION_STATUS": calibration_status_for_n(n_out),
        "scanner_performance": scanner_performance(joined_scanner),
        "analysis_value_add": analysis_value_add(joined_obs),
        "summary": summarize_outcomes(joined_scanner, unit="canonical_signal_id") if joined_scanner else summarize_outcomes([], unit="canonical_signal_id"),
        "false_positives": false_positive_cases(joined_scanner),
        "missed_opportunities_pit_only": _missed_opportunities(explorer),
        "pending_real_outcomes": n_out == 0,
        "note": (
            "SCANNER PERFORMANCE n = scanner_sample_n (canonical_signal_id). "
            "Do not use analysis_observations_generated_n as scanner sample size. "
            "Value-add n = analysis_observations_evaluable_n. "
            "Production outcomes stay PENDING until future sessions exist."
        ),
        "weekly_metrics": "APP_GENERATED",
        "scoring_version_frozen": SCORING_VERSION,
    }
    from egxbridge.analysis.forward_validation import validation_report
    hist["FORWARD_VALIDATION_AUDIT"] = validation_report(store) if store else {"status": "NOT_STARTED"}
    if outcomes:
        hist["grouped"] = group_summaries(joined_scanner)
    return hist


def prepare_schedule_handoffs(
    *,
    explorer_package_dir: Path | None = None,
    explorer_payload: dict[str, Any] | None = None,
    jobs: list[str] | None = None,
    store=None,
    db=None,
    output_root: Path | None = None,
    environment: str | None = None,
    portfolio_context: str = "",
    persist_signals: bool = True,
    session_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assert_handoff_only()
    env = normalize_environment(environment or getattr(store, "environment", None) or PRODUCTION)
    if explorer_payload is None:
        if explorer_package_dir is None:
            from egxbridge.ui.snapshot import resolve_explorer_package
            resolved = resolve_explorer_package(HERE)
            if resolved.get("package_dir"):
                explorer_package_dir = Path(resolved["package_dir"])
        if not explorer_package_dir or not Path(explorer_package_dir).exists():
            raise FileNotFoundError("No Explorer package found. Run Explorer first.")
        explorer_payload = load_explorer_package(Path(explorer_package_dir), db=db, store=store, require_current=env == PRODUCTION)
        explorer_package_dir = Path(explorer_payload["_package_dir"])
    elif env == PRODUCTION:
        if explorer_package_dir is None:
            raise ValueError("A production handoff requires the Explorer package and its daily source files.")
        explorer_payload = load_explorer_package(Path(explorer_package_dir), db=db, store=store, require_current=True)
        explorer_package_dir = Path(explorer_payload["_package_dir"])
    jobs = list(jobs or ANALYSIS_TYPES)
    for j in jobs:
        if j not in ANALYSIS_TYPES:
            raise ValueError(f"Unknown job: {j}")

    generated_at = utc_now()
    run_id = _run_id(generated_at)
    sess = dict(session_meta) if session_meta else session_context()
    if "session_phase" not in sess:
        sess = {**session_context(), **sess}
    counts = explorer_payload.get("counts") or {}
    coverage = explorer_payload.get("coverage") or {}
    identity_rows = _rebuild_universe_identity(explorer_payload, environment=env)
    explorer_payload["universe_identity"] = identity_rows
    from egxbridge.analysis.explorer.universe_state import build_universe_coverage
    from egxbridge.analysis.explorer.intraday_fetch import apply_provider_state_to_coverage
    uni_cov = build_universe_coverage(identity_rows)
    fetch_diag = explorer_payload.get("intraday_fetch_diagnostics") or {}
    uni_cov = apply_provider_state_to_coverage(uni_cov, fetch_diag)
    explorer_payload["universe_coverage"] = uni_cov
    from egxbridge.analysis.explorer.coverage import classify_explorer_coverage
    equity_count = sum(r.get("instrument_type") == "EQUITY" for r in identity_rows)
    counts = {**counts, "UNIVERSE_TOTAL": len(identity_rows), "universe_total": len(identity_rows),
              "EQUITY_UNIVERSE_TOTAL": equity_count, "SCANNER_ELIGIBLE_SYMBOLS": uni_cov["scanner_eligible"],
              "scanner_candidate_count": uni_cov["scanner_eligible"]}
    coverage = {
        **classify_explorer_coverage(
            equity_universe_total=equity_count,
            mapped_symbols=sum(r.get("instrument_type") == "EQUITY" and r.get("eligibility_state") != "SOURCE_MISSING" for r in identity_rows),
            daily_data_available=min(int(counts.get("DAILY_DATA_AVAILABLE") or 0), equity_count),
            scanner_eligible=uni_cov["scanner_eligible"],
            thresholds=coverage.get("coverage_thresholds"),
        ),
        "whole_egx_claim_allowed": bool(uni_cov.get("whole_egx_claim_allowed")),
        "market_wide_confidence_allowed": bool(uni_cov.get("whole_egx_claim_allowed")),
        "run_scope": uni_cov.get("run_scope") or coverage.get("selection_basis"),
    }
    counts.update({key: coverage[key] for key in (
        "mapped_coverage_pct", "daily_data_coverage_pct", "scanner_eligible_coverage_pct",
        "eligible_coverage_pct", "EXPLORER_COVERAGE", "exploratory_coverage_quality",
        "selection_basis", "selection_bias_risk", "market_wide_confidence_allowed", "whole_egx_claim_allowed",
    )})
    explorer_payload["coverage"] = coverage
    explorer_payload["counts"] = counts
    explorer_payload["selection_basis"] = coverage["selection_basis"]
    explorer_payload["selection_bias_risk"] = coverage["selection_bias_risk"]
    candidates = list(explorer_payload.get("candidates") or [])
    candidates, recovery_log = _recover_from_explorer_payload(explorer_payload, candidates)
    explorer_payload["candidates"] = candidates
    explorer_payload["missing_ticker_recovery_log"] = recovery_log
    explorer_payload["recovered_tickers"] = [r["ticker"] for r in recovery_log if r.get("recovered")]
    latest_session = explorer_payload.get("latest_completed_market_session")
    explorer_run_id = explorer_payload.get("explorer_run_id") or make_explorer_run_id(
        environment=env,
        latest_session=latest_session,
        generated_at=explorer_payload.get("generated_at") or explorer_payload.get("package_generated_at") or "payload-unbound",
    )
    funnel_meta = {
        "scope": counts.get("funnel_coverage_scope") or "EQUITY_UNIVERSE_TOTAL",
        "denominator": counts.get("funnel_coverage_denominator") or counts.get("EQUITY_UNIVERSE_TOTAL"),
        "n": counts.get("funnel_coverage_n"),
        "counts": explorer_payload.get("funnel_coverage") or counts.get("funnel_status_counts") or {},
    }
    limitations = [
        "No official EGX calendar — target_next_working_day=UNKNOWN",
        "No bid/ask/depth/trades — do not infer microstructure",
        "forward_setup_score is HEURISTIC_UNCALIBRATED, not a probability",
        "scoring_version frozen at 0.5.1 — v0.6 does not retune weights",
        "No paid LLM API; ChatGPT handoff only",
        "Do not infer market regime from candidate shortlist breadth",
    ]
    live_available = live_session_evidence_available(candidates, sess, fetch_diag)
    if fetch_diag.get("provider_state") == "FAILED":
        limitations.append(
            f"INTRADAY_PROVIDER_STATE=FAILED: {fetch_diag.get('success') or 0}/"
            f"{fetch_diag.get('selected') or 0} selected tickers returned live bars. "
            "This is not ordinary missing data."
        )
        live_available = False
    elif fetch_diag.get("provider_state") == "NOT_REQUESTED":
        limitations.append("Intraday live collection was not requested. Cached bars retain their original timestamps and cache status.")
        live_available = False
    if (sess.get("session_phase") in STALE_EVIDENCE_PHASES) or not live_available:
        limitations.append(NOT_LIVE_CONFIRMATION_TEXT)
        limitations.append("Check each intraday bar's session, timestamp and cache status; cached observations may be older or from an incomplete session.")
    market = build_market_summary(
        coverage=coverage,
        counts=counts,
        scanner_rows=candidates,
        latest_session=latest_session,
        session_meta=sess,
        data_limitations=limitations,
        portfolio_context=portfolio_context,
        explorer_payload=explorer_payload,
    )
    compact_all = [_compact(c) for c in candidates]
    top5 = compact_all[:5]
    intra_sel = explorer_payload.get("intraday_selection") or []
    intra_tickers = {r.get("ticker") for r in intra_sel} or set(explorer_payload.get("intraday_queried_tickers") or [])
    intra_cands = []
    for c in candidates:
        if c.get("ticker") in intra_tickers or c.get("intraday_available") or c.get("recovery_state"):
            row = _compact(c)
            row["intraday"] = c.get("intraday")
            row["session_phase"] = sess.get("session_phase")
            intra_cands.append(row)
    if not intra_cands:
        intra_cands = compact_all[:15]

    value_cands = []
    for c in candidates:
        row = _compact(c)
        row["funnel_context"] = c.get("funnel_context")
        row["recommended_deep_analysis"] = c.get("recommended_deep_analysis")
        row["bridge_suggested_funnel_action"] = suggested_funnel_action(c.get("funnel_status"))
        value_cands.append(row)

    data_stamp = build_data_stamp(
        packaged_at=generated_at,
        session_close_date=latest_session,
        session_phase=sess.get("session_phase"),
        explorer_payload=explorer_payload,
        package_kind="CHATGPT_HANDOFF",
    )
    date_tag = generated_at[:10]
    out_root = Path(output_root) if output_root else HERE / "output" / "schedule_handoff" / run_id
    if out_root.exists():
        import shutil
        shutil.rmtree(out_root)
    common = out_root / "common"
    jobs_dir = out_root / "jobs"
    optional = out_root / "optional"
    common.mkdir(parents=True, exist_ok=True)
    jobs_dir.mkdir(parents=True, exist_ok=True)
    optional.mkdir(parents=True, exist_ok=True)

    snapshots = [
        build_signal_snapshot(
            c, run_id=run_id, environment=env, analysis_type=ANALYSIS_EXPLORER,
            generated_at=generated_at, latest_session=latest_session, session_meta=sess,
            price_basis="OFFICIAL_CLOSE", explorer_run_id=explorer_run_id,
        )
        for c in candidates
    ]
    snap_stats = {"inserted": 0, "ignored_duplicates": 0, "snapshot_ids": [s["snapshot_id"] for s in snapshots]}
    identity_stats = {"canonical_signals_n": 0, "analysis_observations_n": 0, "canonical_reused": 0}
    if persist_signals and store:
        snap_stats = persist_snapshots(
            store, snapshots, persist_identity=False, schedule_run_id=run_id,
        )
        identity_stats = persist_job_observations(
            store,
            candidates=candidates,
            jobs=jobs,
            environment=env,
            explorer_run_id=explorer_run_id,
            latest_session=latest_session,
            schedule_run_id=run_id,
            analysis_timestamp=generated_at,
            session_meta=sess,
        )
    else:
        from egxbridge.analysis.schedule.identity import resolve_signal_identity
        cids = []
        by_ident: dict[str, dict[str, Any]] = {}
        job_idents: dict[str, dict[str, dict[str, Any]]] = {j: {} for j in jobs}
        for c in candidates:
            ident = resolve_signal_identity(
                c, environment=env, explorer_run_id=explorer_run_id,
                latest_session=latest_session, analysis_type=ANALYSIS_EXPLORER,
                session_meta=sess, price_basis="OFFICIAL_CLOSE",
            )
            t = str(c.get("ticker") or "").upper()
            by_ident[t] = ident
            cids.append(ident["canonical_signal_id"])
            for j in jobs:
                job_idents[j][t] = ident
        identity_stats = {
            "canonical_signals_n": len(dict.fromkeys(cids)),
            "analysis_observations_n": len(jobs) * len(candidates),
            "analysis_observations_generated_n": len(jobs) * len(candidates),
            "canonical_ids": list(dict.fromkeys(cids)),
            "scanner_sample_n": len(dict.fromkeys(cids)),
            "canonical_reused": 0,
            "by_ticker_identity": by_ident,
            "identities_by_job": job_idents,
            "by_ticker": {t: v["canonical_signal_id"] for t, v in by_ident.items()},
        }

    ident_map = identity_stats.get("by_ticker_identity") or {}
    job_maps = identity_stats.get("identities_by_job") or {}
    compact_all = _attach_identity(
        compact_all, ident_map,
        analysis_type=ANALYSIS_EXPLORER, schedule_run_id=run_id, explorer_run_id=explorer_run_id,
    )
    top5 = compact_all[:5]
    intra_cands = _attach_identity(
        intra_cands, job_maps.get(ANALYSIS_INTRADAY) or ident_map,
        analysis_type=ANALYSIS_INTRADAY, schedule_run_id=run_id, explorer_run_id=explorer_run_id,
    )
    value_cands = _attach_identity(
        value_cands, job_maps.get(ANALYSIS_VALUE) or ident_map,
        analysis_type=ANALYSIS_VALUE, schedule_run_id=run_id, explorer_run_id=explorer_run_id,
    )
    premarket_cands = _attach_identity(
        compact_all, job_maps.get(ANALYSIS_PREMARKET) or ident_map,
        analysis_type=ANALYSIS_PREMARKET, schedule_run_id=run_id, explorer_run_id=explorer_run_id,
    )

    weekly = _weekly_history(store, explorer_payload)
    uni_cov = explorer_payload.get("universe_coverage") or {}

    explorer_snapshot = {
        "run_id": run_id,
        "explorer_run_id": explorer_run_id,
        "scoring_version": SCORING_VERSION,
        "score_kind": SCORE_KIND,
        "not_a_probability": True,
        "bridge_version": BRIDGE_VERSION,
        "explorer_version": EXPLORER_PACKAGE_VERSION,
        "generated_at": generated_at,
        "data_stamp": data_stamp,
        "latest_completed_market_session": latest_session,
        "coverage": coverage,
        "counts": {
            k: counts.get(k) for k in (
                "UNIVERSE_TOTAL", "EQUITY_UNIVERSE_TOTAL", "SCANNER_ELIGIBLE_SYMBOLS",
                "PRESCREEN_SELECTED", "INTRADAY_ENRICHED", "HANDOFF_CANDIDATES",
                "funnel_coverage_scope", "funnel_coverage_denominator", "funnel_coverage_n",
                "EXPLORER_COVERAGE", "selection_basis",
            )
        },
        "candidates": compact_all,
        "intraday_selection": intra_sel,
        "snapshot_ids": snap_stats["snapshot_ids"],
        "canonical_signal_ids": identity_stats.get("canonical_ids") or [s.get("canonical_signal_id") for s in snapshots],
        "canonical_signals_n": identity_stats.get("canonical_signals_n") or len({s.get("canonical_signal_id") for s in snapshots}),
        "analysis_observations_generated_n": identity_stats.get("analysis_observations_generated_n") or identity_stats.get("analysis_observations_n") or 0,
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
        "no_lookahead": True,
        "universe_coverage": uni_cov,
        "recovered_tickers": list(explorer_payload.get("recovered_tickers") or []),
        "intraday_fetch_diagnostics": fetch_diag,
        "intraday_fetch_by_ticker": explorer_payload.get("intraday_fetch_by_ticker") or {},
        "whole_egx_claim_allowed": bool(uni_cov.get("whole_egx_claim_allowed")),
        "exploratory_coverage_quality": coverage.get("exploratory_coverage_quality") or coverage.get("EXPLORER_COVERAGE"),
    }
    generated_n = explorer_snapshot["analysis_observations_generated_n"]
    explorer_snapshot.update(_deprecated_count_fields(generated_n))
    write_json(common / "explorer_snapshot.json", explorer_snapshot)
    write_json(common / "market_summary.json", market)
    rows_to_csv(common / "candidate_summary.csv", compact_all or [{"note": "none"}])
    detailed = explorer_payload.get("intraday_fetch_by_ticker") or {}
    intraday_rows = {r["ticker"]: dict(r) for r in intra_cands}
    for ticker, result in detailed.items():
        intraday_rows[ticker] = {**intraday_rows.get(ticker, {}), **result, "ticker": ticker}
    rows_to_csv(common / "intraday_summary.csv", [
        {**{k: v for k, v in row.items() if k not in {"intraday", "intraday_ohlcv", "ohlcv"}},
         "ohlcv_files": "intraday_1m.jsonl|intraday_5m.jsonl|intraday_15m.jsonl"}
        for row in intraday_rows.values()
    ] or [{"note": "none"}])
    write_json(common / "intraday_fetch_by_ticker.json", detailed)
    write_json(common / "daily_collection_report.json", explorer_payload.get("daily_collection_report") or {"status": "UNAVAILABLE"})
    write_json(common / "supplemental_market_snapshot.json", (explorer_payload.get("daily_collection_report") or {}).get("supplemental_market_snapshot") or {"status": "NOT_REQUESTED"})
    write_json(common / "daily_data_status.json", explorer_payload.get("daily_data_status") or [])
    funnel_rows = []
    for c in candidates:
        fc = c.get("funnel_context") or {}
        funnel_rows.append({
            "ticker": c.get("ticker"),
            "funnel_status": c.get("funnel_status"),
            "Economic Valuation": fc.get("Economic Valuation"),
            "Fair Value Range": fc.get("Fair Value Range"),
            "Investment Classification": fc.get("Investment Classification"),
            "Integrated Risk": fc.get("Integrated Risk"),
            "bridge_suggested_funnel_action": suggested_funnel_action(c.get("funnel_status")),
            "fair_value_manufactured": False,
        })
    rows_to_csv(common / "funnel_context.csv", funnel_rows or [{"note": "none"}])
    write_json(common / "provider_quality.json", {"execution_grade": "NO", "missing": ["depth", "trades", "bid_ask", "official_egx_calendar"]})
    uni_cov = explorer_payload.get("universe_coverage") or uni_cov
    write_json(common / "universe_coverage.json", uni_cov)
    write_json(common / "missing_ticker_recovery_log.json", explorer_payload.get("missing_ticker_recovery_log") or [])
    write_json(common / "session_snapshots.json", explorer_payload.get("session_snapshots") or {})
    if explorer_package_dir:
        pkg = Path(explorer_package_dir)
        import shutil
        for name in ("intraday_1m.jsonl", "intraday_5m.jsonl", "intraday_15m.jsonl", "universe_identity.csv", "daily_ohlcv.jsonl", "daily_rejected_ohlcv.jsonl", "daily_collection_rejections.jsonl"):
            src = pkg / name
            if src.exists():
                shutil.copy2(src, common / name)
    rows_to_csv(common / "universe_identity.csv", identity_rows or [{"note": "none"}])
    write_json(common / "intraday_fetch_diagnostics.json", fetch_diag or {})
    write_json(common / "data_limitations.json", {
        "limitations": limitations,
        "session": sess,
        "live_session_evidence_available": live_available,
        "not_live_confirmation_text": None if live_available else NOT_LIVE_CONFIRMATION_TEXT,
    })
    daily = build_daily_decision(
        run_id=run_id,
        latest_session=latest_session,
        market_regime="NOT_RELIABLE",
        portfolio_posture="NOT_RELIABLE",
        candidates=candidates,
    )
    raw_detail = [
        _overlay_identity(
            c, ident_map.get(str(c.get("ticker") or "").upper()) or {},
            analysis_type=ANALYSIS_EXPLORER, schedule_run_id=run_id, explorer_run_id=explorer_run_id,
        )
        for c in candidates
    ]
    assert_identity_consistent({
        "candidate_summary": compact_all,
        "raw_candidate_detail": raw_detail,
        "signal_snapshots": snapshots,
        "premarket_candidates": premarket_cands,
        "value_candidates": value_cands,
    })
    write_json(optional / "raw_candidate_detail.json", raw_detail)
    write_json(optional / "calibration_history_summary.json", weekly)
    write_json(optional / "forward_validation_audit.json", weekly.get("FORWARD_VALIDATION_AUDIT") or {})
    write_json(optional / "signal_snapshots.json", snapshots)
    canon_blob = {
        "explorer_run_id": explorer_run_id,
        "canonical_signals_n": identity_stats.get("canonical_signals_n"),
        "analysis_observations_generated_n": generated_n,
        "analysis_observations_imported_n": (weekly or {}).get("analysis_observations_imported_n") or 0,
        "analysis_observations_evaluable_n": (weekly or {}).get("analysis_observations_evaluable_n") or 0,
        "by_ticker": identity_stats.get("by_ticker"),
        "canonical_ids": identity_stats.get("canonical_ids"),
        "scanner_sample_n": identity_stats.get("scanner_sample_n") or identity_stats.get("canonical_signals_n"),
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
        "note": "Scanner sample size is canonical_signals_n. Generated observations are not ChatGPT decisions.",
    }
    canon_blob.update(_deprecated_count_fields(generated_n))
    write_json(optional / "canonical_signals.json", canon_blob)
    job_ctx = {
        "run_id": run_id,
        "latest_session": latest_session,
        "session_meta": sess,
        "session_phase": sess.get("session_phase"),
        "market_summary": market,
        "top_candidates_compact": top5,
        "handoff_candidates_compact": premarket_cands,
        "intraday_candidates": intra_cands,
        "data_limitations": limitations,
        "value_candidates": value_cands,
        "funnel_coverage_meta": funnel_meta,
        "weekly_history": weekly,
        "live_session_evidence_available": live_available,
        "data_stamp": data_stamp,
    }
    schemas_dir = common / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    job_schemas = build_all_job_schemas(job_ctx)
    for job, schema in job_schemas.items():
        write_json(schemas_dir / RESULT_SCHEMA_FILES[job], schema)
    schema_index = result_schema_index(job_ctx)
    write_json(common / "chatgpt_result_schema.json", schema_index)
    write_json(common / "result_schemas.json", schema_index)
    write_json(optional / "chatgpt_result_schema.json", schema_index)
    write_json(optional / "daily_decision.json", daily)
    persist_daily_decision(
        store, daily, date_tag=date_tag,
        write_workspace_file=env == PRODUCTION,
    )

    write_package_stamp(out_root, data_stamp)
    written_jobs = {}
    for job in jobs:
        text = job_stamp_preamble(data_stamp) + RENDERERS[job](job_ctx)
        write_text(jobs_dir / JOB_FILE[job], text)
        written_jobs[job] = text

    manifest = {
        "run_id": run_id,
        "bridge_version": BRIDGE_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "explorer_version": EXPLORER_PACKAGE_VERSION,
        "scoring_version": SCORING_VERSION,
        "score_kind": SCORE_KIND,
        "not_a_probability": True,
        "ai_mode": AI_CHATGPT_HANDOFF,
        "generated_at": generated_at,
        "generated_at_cairo": data_stamp.get("packaged_at_cairo"),
        "source_cutoff_cairo": (data_stamp.get("intraday") or {}).get("last_bar_cairo") or data_stamp.get("packaged_at_cairo"),
        "source_cutoff_by_provider": {
            "yahoo": explorer_payload.get("latest_completed_market_session"),
            "tradingview": (data_stamp.get("intraday") or {}).get("last_bar_cairo"),
        },
        "latest_bar_timestamp": (data_stamp.get("intraday") or {}).get("last_bar_utc"),
        "latest_trade_timestamp": None,
        "latest_depth_timestamp": None,
        "data_stamp": data_stamp,
        "latest_completed_market_session": latest_session,
        "target_next_working_day": "UNKNOWN",
        "session_phase": sess.get("session_phase"),
        "equity_universe_total": counts.get("EQUITY_UNIVERSE_TOTAL"),
        "scanner_eligible": counts.get("SCANNER_ELIGIBLE_SYMBOLS"),
        "universe_expected": uni_cov.get("expected_equities"),
        "universe_eligible": uni_cov.get("scanner_eligible"),
        "universe_covered": uni_cov.get("covered"),
        "intraday_basic_count": counts.get("INTRADAY_BASIC", 0),
        "daily_snapshot_count": counts.get("DAILY_SNAPSHOTS", 0),
        "intraday_deep_enriched_count": counts.get("INTRADAY_ENRICHED"),
        "intraday_ohlcv_count": counts.get("INTRADAY_OHLCV"),
        "trade_tape_count": 0,
        "depth_count": 0,
        "missing_tickers": uni_cov.get("missing_tickers") or [],
        "recovered_tickers": list(explorer_payload.get("recovered_tickers") or []),
        "alias_corrections": list(explorer_payload.get("alias_corrections") or []),
        "coverage_status": uni_cov.get("coverage_status") or coverage.get("EXPLORER_COVERAGE"),
        "run_scope": uni_cov.get("run_scope") or coverage.get("selection_basis"),
        "lookahead_guard_pass": bool(explorer_payload.get("lookahead_guard_pass", True)),
        "future_timestamp_records_rejected": int(explorer_payload.get("future_timestamp_records_rejected") or 0),
        "stale_records_rejected": int(explorer_payload.get("stale_records_rejected") or 0),
        "universe_coverage": uni_cov,
        "prescreen_count": counts.get("PRESCREEN_SELECTED"),
        "handoff_candidate_count": counts.get("HANDOFF_CANDIDATES") or len(candidates),
        "intraday_enriched_count": counts.get("INTRADAY_ENRICHED"),
        "intraday_fetch_diagnostics": fetch_diag,
        "exploratory_coverage_quality": coverage.get("exploratory_coverage_quality") or coverage.get("EXPLORER_COVERAGE"),
        "whole_egx_claim_allowed": bool(uni_cov.get("whole_egx_claim_allowed")),
        "market_wide_confidence_allowed": bool(uni_cov.get("whole_egx_claim_allowed")),
        "EXPLORER_COVERAGE": coverage.get("EXPLORER_COVERAGE"),
        "selection_basis": coverage.get("selection_basis"),
        "selection_bias_risk": coverage.get("selection_bias_risk"),
        "included_jobs": jobs,
        "funnel_coverage": funnel_meta,
        "data_limitations": limitations,
        "snapshot_count": len(snapshots),
        "canonical_signals_n": identity_stats.get("canonical_signals_n"),
        "analysis_observations_n": identity_stats.get("analysis_observations_generated_n") or identity_stats.get("analysis_observations_n"),
        "analysis_observations_generated_n": identity_stats.get("analysis_observations_generated_n") or identity_stats.get("analysis_observations_n"),
        "analysis_observations_imported_n": weekly.get("analysis_observations_imported_n") or 0,
        "analysis_observations_evaluable_n": weekly.get("analysis_observations_evaluable_n") or 0,
        "explorer_run_id": explorer_run_id,
        "scanner_sample_n": identity_stats.get("scanner_sample_n") or identity_stats.get("canonical_signals_n"),
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "supported_result_envelope_version": SUPPORTED_RESULT_ENVELOPE_VERSION,
        "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
        "analysis_observations_n_semantics": ANALYSIS_OBSERVATIONS_N_SEMANTICS,
        "deprecated_fields": list(DEPRECATED_FIELDS),
        "result_schemas": {
            job: f"common/schemas/{RESULT_SCHEMA_FILES[job]}" for job in ANALYSIS_TYPES
        },
        "live_session_evidence_available": live_available,
        "identity_integrity": "OK",
        "MARKET_BREADTH_SCOPE": "SCANNER_ELIGIBLE_EQUITY_UNIVERSE",
        "orders_generated": False,
        "remote_llm_call": False,
        "package_dir": str(out_root),
        "included_files": [],
    }
    write_json(out_root / "manifest.json", manifest)
    manifest["included_files"] = list_files_relative(out_root)
    write_json(out_root / "manifest.json", manifest)

    zip_root = out_root.parent
    combined_zip = zip_root / dated_zip_name("EGX_CHATGPT_HANDOFF", data_stamp)
    zip_directory(out_root, combined_zip, arc_root="EGX_CHATGPT_HANDOFF")
    write_zip_sidecar(combined_zip, data_stamp)

    individual = {}
    import shutil
    tmp_parent = out_root / "_individual"
    tmp_parent.mkdir(exist_ok=True)
    for job in jobs:
        job_root = tmp_parent / job
        (job_root / "jobs").mkdir(parents=True, exist_ok=True)
        (job_root / "common").mkdir(parents=True, exist_ok=True)
        shutil.copy2(jobs_dir / JOB_FILE[job], job_root / "jobs" / JOB_FILE[job])
        shutil.copy2(common / "data_limitations.json", job_root / "common" / "data_limitations.json")
        shutil.copy2(common / "daily_collection_report.json", job_root / "common" / "daily_collection_report.json")
        shutil.copy2(common / "supplemental_market_snapshot.json", job_root / "common" / "supplemental_market_snapshot.json")
        shutil.copy2(out_root / "DATA_STAMP.md", job_root / "DATA_STAMP.md")
        shutil.copy2(out_root / "DATA_STAMP.json", job_root / "DATA_STAMP.json")
        job_schema_name = RESULT_SCHEMA_FILES[job]
        (job_root / "common" / "schemas").mkdir(parents=True, exist_ok=True)
        shutil.copy2(common / "schemas" / job_schema_name, job_root / "common" / "schemas" / job_schema_name)
        shutil.copy2(common / "schemas" / job_schema_name, job_root / "common" / "result_schema.json")
        if job == ANALYSIS_MACRO:
            shutil.copy2(common / "market_summary.json", job_root / "common" / "market_summary.json")
            rows_to_csv(job_root / "common" / "candidate_summary.csv", top5 or [{"note": "none"}])
        elif job == ANALYSIS_PREMARKET:
            shutil.copy2(common / "candidate_summary.csv", job_root / "common" / "candidate_summary.csv")
        elif job == ANALYSIS_INTRADAY:
            shutil.copy2(common / "intraday_summary.csv", job_root / "common" / "intraday_summary.csv")
            for name in ("intraday_1m.jsonl", "intraday_5m.jsonl", "intraday_15m.jsonl", "universe_coverage.json", "intraday_fetch_by_ticker.json", "intraday_fetch_diagnostics.json"):
                src = common / name
                if src.exists():
                    shutil.copy2(src, job_root / "common" / name)
        elif job == ANALYSIS_VALUE:
            shutil.copy2(common / "funnel_context.csv", job_root / "common" / "funnel_context.csv")
            shutil.copy2(common / "candidate_summary.csv", job_root / "common" / "candidate_summary.csv")
        elif job == ANALYSIS_WEEKLY:
            shutil.copy2(optional / "calibration_history_summary.json", job_root / "common" / "calibration_history_summary.json")
        job_man = {
            **{k: manifest[k] for k in (
                "run_id", "bridge_version", "explorer_version", "scoring_version",
                "generated_at", "latest_completed_market_session", "target_next_working_day",
                "session_phase", "ai_mode",
            )},
            "result_envelope_version": RESULT_ENVELOPE_VERSION,
            "supported_result_envelope_version": SUPPORTED_RESULT_ENVELOPE_VERSION,
            "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
            "analysis_type": job,
            "result_schema": f"common/schemas/{RESULT_SCHEMA_FILES[job]}",
            "result_schemas": {job: f"common/schemas/{RESULT_SCHEMA_FILES[job]}"},
            "deprecated_fields": list(DEPRECATED_FIELDS),
            "analysis_observations_n_semantics": ANALYSIS_OBSERVATIONS_N_SEMANTICS,
            "live_session_evidence_available": live_available,
            "included_jobs": [job],
            "references_full_package": str(combined_zip),
            "job_minimized": True,
            "data_stamp": data_stamp,
        }
        write_json(job_root / "manifest.json", job_man)
        zpath = zip_root / dated_zip_name(JOB_ZIP_PREFIX[job], data_stamp)
        zip_directory(job_root, zpath, arc_root=JOB_ZIP_PREFIX[job])
        write_zip_sidecar(zpath, data_stamp)
        individual[job] = str(zpath)
    shutil.rmtree(tmp_parent, ignore_errors=True)

    if store:
        store.insert_schedule_run(run_id, manifest, package_dir=str(out_root))

    if env == PRODUCTION and output_root is None:
        ws = HERE / "workspace" / "schedule"
        ws.mkdir(parents=True, exist_ok=True)
        write_json(ws / "last_run.json", {
            "run_id": run_id,
            "package_dir": str(out_root),
            "combined_zip": str(combined_zip),
            "individual_zips": individual,
            "manifest": manifest,
            "snapshot_stats": snap_stats,
            "environment": env,
        })

    return {
        "run_id": run_id,
        "package_dir": str(out_root),
        "combined_zip": str(combined_zip),
        "individual_zips": individual,
        "manifest": manifest,
        "snapshot_stats": snap_stats,
        "identity_stats": identity_stats,
        "explorer_run_id": explorer_run_id,
        "canonical_signals_n": identity_stats.get("canonical_signals_n"),
        "analysis_observations_n": identity_stats.get("analysis_observations_generated_n") or identity_stats.get("analysis_observations_n"),
        "analysis_observations_n_semantics": ANALYSIS_OBSERVATIONS_N_SEMANTICS,
        "analysis_observations_generated_n": identity_stats.get("analysis_observations_generated_n") or identity_stats.get("analysis_observations_n"),
        "analysis_observations_imported_n": weekly.get("analysis_observations_imported_n") or 0,
        "analysis_observations_evaluable_n": weekly.get("analysis_observations_evaluable_n") or 0,
        "scanner_sample_n": identity_stats.get("scanner_sample_n") or identity_stats.get("canonical_signals_n"),
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
        "supported_result_envelope_version": SUPPORTED_RESULT_ENVELOPE_VERSION,
        "live_session_evidence_available": live_available,
        "jobs": jobs,
        "ai_mode": AI_CHATGPT_HANDOFF,
        "orders_generated": False,
        "scoring_version": SCORING_VERSION,
        "session_phase": sess.get("session_phase"),
    }
