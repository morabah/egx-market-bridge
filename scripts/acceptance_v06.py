#!/usr/bin/env python3
"""v0.6 5-schedule + point-in-time outcomes acceptance.

Does not retune v0.5.1 scores. Does not write synthetic outcomes into production.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from egxbridge.analysis.common.environment import PRODUCTION
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.calibration import (
    LONG_HORIZON_CAP, SAT_SCALE_6M, MOVE_PENALTY, VOL_PENALTY, SCORING_VERSION,
)
from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
from egxbridge.analysis.explorer.models import ExplorerRunConfig
from egxbridge.analysis.funnel.registry import FunnelRegistry
from egxbridge.analysis.schedule.handoff import prepare_schedule_handoffs
from egxbridge.analysis.schedule.outcomes import compute_outcomes
from egxbridge.collect_universe import collect_universe_daily
from egxbridge.config import Settings
from egxbridge.db import Database


EXAMPLE_TICKERS = ("EGCH", "RAYA", "ALCN", "MASR")


def _synthetic_outcome_math() -> dict:
    signal = "2026-01-02"
    future = [
        {"session_date": "2026-01-02", "close": 10, "high": 10.2, "low": 9.9},
        {"session_date": "2026-01-05", "close": 11, "high": 11.5, "low": 9.8},
        {"session_date": "2026-01-06", "close": 10.5, "high": 12.0, "low": 10.2},
        {"session_date": "2026-01-07", "close": 12.0, "high": 12.2, "low": 10.4},
        {"session_date": "2026-01-08", "close": 11.8, "high": 12.1, "low": 11.0},
        {"session_date": "2026-01-09", "close": 13.0, "high": 13.2, "low": 11.7},
    ]
    pos = compute_outcomes(
        baseline_price=10, baseline_timestamp=signal, baseline_type="OFFICIAL_CLOSE",
        signal_session=signal, future_bars=future,
    )
    pending = compute_outcomes(
        baseline_price=10, baseline_timestamp=signal, baseline_type="OFFICIAL_CLOSE",
        signal_session=signal,
        future_bars=[{"session_date": "2026-01-02", "close": 10, "high": 10, "low": 10}],
    )
    gap = compute_outcomes(
        baseline_price=10, baseline_timestamp=signal, baseline_type="OFFICIAL_CLOSE",
        signal_session=signal,
        future_bars=[
            {"session_date": "2026-01-02", "close": 10, "high": 10, "low": 10},
            {"session_date": "2026-01-05", "close": 20, "high": 20, "low": 19},
        ],
        history_integrity="CLEAN",
    )
    warn = compute_outcomes(
        baseline_price=10, baseline_timestamp=signal, baseline_type="OFFICIAL_CLOSE",
        signal_session=signal, future_bars=future,
        history_integrity="POSSIBLE_DISCONTINUITY",
    )
    checks = {
        "next_session_return": pos.get("next_session_return") == 10.0,
        "return_3_sessions": pos.get("return_3_sessions") == 20.0,
        "return_5_sessions": pos.get("return_5_sessions") == 30.0,
        "mfe_1": pos.get("mfe_1") == 15.0,
        "mae_1": pos.get("mae_1") == -2.0,
        "weekend_skipped": pos.get("session_dates", [None])[0] == "2026-01-05",
        "pending_without_future": pending.get("outcome_status") == "PENDING",
        "gap_integrity_warning": gap.get("outcome_integrity_warning") is True,
        "discontinuity_flag": warn.get("outcome_integrity_warning") is True,
    }
    return {
        "synthetic_only": True,
        "written_to_production_calibration_history": False,
        "direction_assumption": "LONG_TACTICAL",
        "positive": pos,
        "pending": pending,
        "checks": checks,
        "pass": all(checks.values()),
    }


def _copy_zip(src: Path, dest: Path) -> bool:
    if src and Path(src).exists():
        shutil.copy2(src, dest)
        return True
    return False


def main() -> int:
    acc = HERE / "output" / "acceptance" / "v06"
    if acc.exists():
        shutil.rmtree(acc)
    acc.mkdir(parents=True, exist_ok=True)

    print("=== pytest (not integration) ===")
    pytest_proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(HERE),
        capture_output=True,
        text=True,
    )
    pytest_text = (pytest_proc.stdout or "") + "\n" + (pytest_proc.stderr or "")
    (acc / "pytest.txt").write_text(pytest_text, encoding="utf-8")
    print(pytest_proc.stdout or pytest_proc.stderr)
    pytest_ok = pytest_proc.returncode == 0

    settings = Settings.load(HERE / "config.json")
    db = Database(settings.db_path(HERE))

    print("=== Yahoo daily collection (incremental) ===")
    coll = collect_universe_daily(
        db=db, settings=settings, history_days=250, max_workers=2, refresh=False,
    )
    perf = coll["performance"]
    (acc / "collection_performance.json").write_text(json.dumps(perf, indent=2, default=str), encoding="utf-8")
    print("COLLECTION", json.dumps(perf, default=str))

    store = AnalysisStore(HERE / "output" / "analysis.sqlite", environment=PRODUCTION)
    funnel = FunnelRegistry(store=store, db=db, environment=PRODUCTION)

    pkg = acc / "explorer_handoff"
    cfg = ExplorerRunConfig(
        horizon="NEXT_WORKING_DAY",
        enrich_intraday=True,
        prescreen_limit=30,
        intraday_limit=15,
        handoff_limit=20,
        environment=PRODUCTION,
    )
    print("=== Explorer handoff (scoring_version frozen 0.5.1) ===")
    exp = prepare_explorer_handoff(
        cfg, db=db, store=store, funnel_registry=funnel, output_root=pkg,
    )
    counts = exp.get("counts") or {}
    coverage = exp.get("coverage") or {}
    payload = json.loads((pkg / "explorer_handoff.json").read_text(encoding="utf-8"))
    candidates = payload.get("candidates") or []
    intra_sel = exp.get("intraday_selection") or []
    if (pkg / "intraday_selection.json").exists():
        intra_pack = json.loads((pkg / "intraday_selection.json").read_text(encoding="utf-8"))
        if isinstance(intra_pack, dict):
            intra_sel = intra_pack.get("selected") or intra_pack.get("rows") or intra_sel
        elif isinstance(intra_pack, list):
            intra_sel = intra_pack
    lane_counts = Counter(
        (r.get("intraday_selection_lane") or r.get("candidate_lane"))
        for r in intra_sel
    )

    print("=== 5-schedule handoffs ===")
    sched_root = acc / "packages" / "run"
    sched = prepare_schedule_handoffs(
        explorer_package_dir=pkg,
        store=store,
        output_root=sched_root,
        environment=PRODUCTION,
    )
    zip_names = {
        "combined": acc / "EGX_5_SCHEDULE_HANDOFF.zip",
        "MACRO_HOLDINGS": acc / "EGX_MACRO_HOLDINGS_HANDOFF.zip",
        "PREMARKET_CATALYSTS": acc / "EGX_PREMARKET_HANDOFF.zip",
        "INTRADAY_OPPORTUNITY": acc / "EGX_INTRADAY_HANDOFF.zip",
        "VALUE_QUALITY": acc / "EGX_VALUE_QUALITY_HANDOFF.zip",
        "WEEKLY_XRAY": acc / "EGX_WEEKLY_XRAY_HANDOFF.zip",
    }
    copied = {
        "combined": _copy_zip(Path(sched["combined_zip"]), zip_names["combined"]),
    }
    for at, dest in zip_names.items():
        if at == "combined":
            continue
        src = (sched.get("individual_zips") or {}).get(at)
        copied[at] = _copy_zip(Path(src) if src else Path(), dest)

    jobs_dir = Path(sched["package_dir"]) / "jobs"
    job_texts = {
        p.name: p.read_text(encoding="utf-8")
        for p in jobs_dir.glob("*.md")
    }
    distinct = len(set(job_texts.values())) == len(job_texts) and len(job_texts) == 5
    value_md = job_texts.get("value_quality.md") or ""
    weekly_md = job_texts.get("weekly_xray.md") or ""
    intra_md = job_texts.get("intraday_opportunity.md") or ""
    macro_md = job_texts.get("macro_holdings.md") or ""
    jobs_ok = (
        distinct
        and "not next-minute" in value_md.lower()
        and "which previously identified setups are confirming" not in value_md.lower()
        and "outcome" in weekly_md.lower()
        and "LIVE SESSION" in intra_md
        and "NEXT_WORKING_DAY" in macro_md
        and macro_md != intra_md
    )

    snaps = store.list_signal_snapshots(limit=2000)
    sample = []
    by_ticker = {}
    for s in snaps:
        t = s.get("ticker")
        if t not in by_ticker:
            by_ticker[t] = s
    for t in EXAMPLE_TICKERS:
        if t in by_ticker:
            sample.append(by_ticker[t]["payload"])
    if len(sample) < 4:
        for s in snaps:
            p = s.get("payload") or {}
            if p and p.get("ticker") not in {x.get("ticker") for x in sample}:
                sample.append(p)
            if len(sample) >= 4:
                break
    (acc / "signal_snapshot_sample.json").write_text(
        json.dumps({
            "n_store_snapshots": len(snaps),
            "example_tickers_requested": list(EXAMPLE_TICKERS),
            "example_tickers_found": [s.get("ticker") for s in sample],
            "snapshots": sample,
            "note": "Example tickers are acceptance illustrations, not hard-coded treatment.",
        }, indent=2, default=str),
        encoding="utf-8",
    )

    synthetic = _synthetic_outcome_math()
    real_outcomes = store.list_signal_outcomes(limit=500)
    pending_real = sum(
        1 for o in real_outcomes
        if (o.get("outcome_status") or "PENDING") in {"PENDING", None}
    )
    # Do not compute synthetic paths into production. Count real rows only.
    outcome_report = {
        "production_outcome_rows": len(real_outcomes),
        "production_pending_or_empty": pending_real if real_outcomes else len(snaps),
        "production_signals_remain_pending_until_future_sessions": True,
        "synthetic_math": synthetic,
        "synthetic_written_to_production": False,
    }
    (acc / "outcome_tracker_report.json").write_text(
        json.dumps(outcome_report, indent=2, default=str), encoding="utf-8",
    )

    scoring_frozen = (
        SCORING_VERSION == "0.5.1"
        and LONG_HORIZON_CAP == 4.0
        and SAT_SCALE_6M == 40.0
        and MOVE_PENALTY["EXTREME"] == 18.0
        and VOL_PENALTY["EXTREME"] == 8.0
        and (exp.get("scoring_version") == "0.5.1")
        and (sched.get("scoring_version") == "0.5.1")
    )
    funnel_n = counts.get("funnel_coverage_n")
    equity_n = counts.get("EQUITY_UNIVERSE_TOTAL")
    funnel_ok = (
        counts.get("funnel_coverage_scope") == "EQUITY_UNIVERSE_TOTAL"
        and counts.get("funnel_coverage_denominator") == equity_n
        and funnel_n == equity_n
    )
    all_zips = all(p.exists() and p.stat().st_size > 0 for p in zip_names.values())
    snapshot_ok = len(snaps) >= max(1, len(candidates))
    intra_not_forced_all_a = True
    if any(
        (r.get("intraday_selection_lane") or "").startswith("LANE_")
        and not str(r.get("intraday_selection_lane")).startswith("LANE_A")
        for r in intra_sel
    ) or len(set(lane_counts)) <= 1:
        intra_not_forced_all_a = len(lane_counts) != 1 or "LANE_A_EARLY_PRE_IGNITION" in lane_counts

    limitations = [
        "scoring_version frozen at 0.5.1; scores remain HEURISTIC_UNCALIBRATED",
        "Production outcomes stay PENDING until future EGX sessions exist",
        "target_next_working_day=UNKNOWN (no official EGX calendar locally)",
        "No paid LLM API; ChatGPT handoff only",
        "No orders; no Thndr; no microstructure inference",
        "CALIBRATION_STATUS starts at INSUFFICIENT_SAMPLE",
        "Intraday enrichment depends on TradingView availability",
    ]
    fail_reasons = []
    if not pytest_ok:
        fail_reasons.append("pytest failed")
    if not scoring_frozen:
        fail_reasons.append("v0.5.1 scoring constants changed")
    if not all_zips:
        fail_reasons.append("one or more of the six ZIP files missing")
    if not jobs_ok:
        fail_reasons.append("five job handoffs are not materially different")
    if not snapshot_ok:
        fail_reasons.append("signal snapshots missing")
    if not synthetic["pass"]:
        fail_reasons.append("synthetic outcome math failed")
    if not funnel_ok:
        fail_reasons.append("Funnel coverage denominator is not EQUITY_UNIVERSE_TOTAL")

    if fail_reasons:
        verdict = "FAIL"
        verdict_reason = "; ".join(fail_reasons)
    else:
        verdict = "PASS WITH LIMITATIONS"
        verdict_reason = (
            "Five schedule packages, PIT snapshots, and synthetic outcome math succeeded. "
            "Real outcomes remain PENDING. Scores were not retuned."
        )
        if (
            int(counts.get("SCANNER_ELIGIBLE_SYMBOLS") or 0) >= 100
            and coverage.get("EXPLORER_COVERAGE") in {"HIGH", "MEDIUM"}
            and pytest_ok
        ):
            # Still limitations: pending outcomes + uncalibrated heuristic.
            verdict = "PASS WITH LIMITATIONS"

    report = {
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "scoring_version": SCORING_VERSION,
        "v051_scoring_changed": False if scoring_frozen else True,
        "counts": {
            "UNIVERSE_TOTAL": counts.get("UNIVERSE_TOTAL"),
            "EQUITY_UNIVERSE_TOTAL": counts.get("EQUITY_UNIVERSE_TOTAL"),
            "SCANNER_ELIGIBLE": counts.get("SCANNER_ELIGIBLE_SYMBOLS"),
            "PRESCREEN_SELECTED": counts.get("PRESCREEN_SELECTED"),
            "HANDOFF_CANDIDATES": counts.get("HANDOFF_CANDIDATES"),
            "INTRADAY_ENRICHED": counts.get("INTRADAY_ENRICHED"),
            "funnel_coverage_scope": counts.get("funnel_coverage_scope"),
            "funnel_coverage_denominator": counts.get("funnel_coverage_denominator"),
            "funnel_coverage_n": counts.get("funnel_coverage_n"),
            "funnel_status_counts": counts.get("funnel_status_counts"),
        },
        "EXPLORER_COVERAGE": coverage.get("EXPLORER_COVERAGE"),
        "intraday_lane_counts": dict(lane_counts),
        "intraday_selection": intra_sel,
        "five_handoffs_materially_different": jobs_ok,
        "signal_snapshot_count": len(snaps),
        "schedule_snapshot_stats": sched.get("snapshot_stats"),
        "pending_real_outcomes": True,
        "synthetic_outcome_math_pass": synthetic["pass"],
        "pytest_ok": pytest_ok,
        "pytest_returncode": pytest_proc.returncode,
        "zip_paths": {k: str(v) for k, v in zip_names.items()},
        "zip_copied": copied,
        "run_id": sched.get("run_id"),
        "session_phase": sched.get("session_phase"),
        "limitations": limitations,
        "fail_reasons": fail_reasons,
        "collection_performance": perf,
        "database_tables": [
            "schedule_runs", "schedule_analysis_imports", "signal_snapshots",
            "signal_candidate_states", "signal_outcomes", "user_actions",
            "daily_decisions", "calibration_summaries",
        ],
        "dashboard_pages": ["Schedule Analysis Center", "Signal Outcomes"],
        "cli": [
            "python -m egxbridge.analysis.prepare_schedules",
            "python -m egxbridge.analysis.update_outcomes",
        ],
    }
    (acc / "schedule_integration_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8",
    )

    md = [
        "# EGX Market Bridge v0.6 — schedule integration report",
        "",
        f"**Verdict:** {verdict}",
        "",
        verdict_reason,
        "",
        "v0.5.1 scoring is frozen (`scoring_version = 0.5.1`). v0.6 does not retune weights.",
        "",
        "## A. Explorer counts",
        "",
        f"- UNIVERSE_TOTAL: {counts.get('UNIVERSE_TOTAL')}",
        f"- EQUITY_UNIVERSE_TOTAL: {counts.get('EQUITY_UNIVERSE_TOTAL')}",
        f"- SCANNER_ELIGIBLE: {counts.get('SCANNER_ELIGIBLE_SYMBOLS')}",
        f"- PRESCREEN_SELECTED: {counts.get('PRESCREEN_SELECTED')}",
        f"- HANDOFF_CANDIDATES: {counts.get('HANDOFF_CANDIDATES')}",
        f"- INTRADAY_ENRICHED: {counts.get('INTRADAY_ENRICHED')}",
        f"- EXPLORER_COVERAGE: {coverage.get('EXPLORER_COVERAGE')}",
        f"- Funnel coverage n / denominator: {funnel_n} / {equity_n} (scope={counts.get('funnel_coverage_scope')})",
        "",
        "## B. v0.5.1 scoring changed?",
        "",
        "NO" if scoring_frozen else "YES — unexpected",
        "",
        "## C. Intraday lane diversification",
        "",
        json.dumps(dict(lane_counts), indent=2),
        "",
        "## D–M",
        "",
        f"- Five schedule handoffs generated: {jobs_ok}",
        f"- Signal snapshot count: {len(snaps)}",
        f"- Pending real outcomes: yes",
        f"- Synthetic outcome-math: {'PASS' if synthetic['pass'] else 'FAIL'}",
        f"- pytest: {'PASS' if pytest_ok else 'FAIL'}",
        "",
        "## ZIP paths",
        "",
    ]
    for k, p in zip_names.items():
        md.append(f"- {k}: `{p}`")
    md.extend(["", "## Limitations", ""])
    md.extend(f"- {x}" for x in limitations)
    (acc / "schedule_integration_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print("SCHEDULE", json.dumps({
        k: report[k] for k in (
            "verdict", "counts", "EXPLORER_COVERAGE", "intraday_lane_counts",
            "signal_snapshot_count", "synthetic_outcome_math_pass", "pytest_ok", "zip_paths",
        )
    }, indent=2, default=str))
    print("VERDICT", verdict)
    store.close()
    db.close()
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
