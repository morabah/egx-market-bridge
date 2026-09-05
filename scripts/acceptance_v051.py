#!/usr/bin/env python3
"""v0.5.1 Explorer signal-calibration acceptance — isolated Funnel reads from PRODUCTION."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from egxbridge.analysis.common.environment import PRODUCTION
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
from egxbridge.analysis.explorer.models import ExplorerRunConfig
from egxbridge.analysis.funnel.registry import FunnelRegistry
from egxbridge.collect_universe import collect_universe_daily
from egxbridge.config import Settings
from egxbridge.db import Database
from egxbridge.storage import rows_to_csv


def _corr_cell(profile: dict, key: str) -> dict:
    return (profile or {}).get(key) or {}


def _md_corr_table(title: str, profile: dict) -> list[str]:
    lines = [f"## {title}", "", "| field | n | pearson | spearman |", "|---|---:|---:|---:|"]
    for k in (
        "daily_return_pct", "return_1w_pct", "return_1m_pct",
        "return_3m_pct", "return_6m_pct", "rvol_20", "dist_from_20d_high_pct",
    ):
        c = _corr_cell(profile, k)
        lines.append(f"| {k} | {c.get('n')} | {c.get('pearson')} | {c.get('spearman')} |")
    lines.append("")
    return lines


def main() -> int:
    settings = Settings.load(HERE / "config.json")
    db = Database(settings.db_path(HERE))

    acc = HERE / "output" / "acceptance" / "v051"
    if acc.exists():
        shutil.rmtree(acc)
    acc.mkdir(parents=True, exist_ok=True)

    print("=== Yahoo daily collection (incremental, equity universe) ===")
    coll = collect_universe_daily(
        db=db, settings=settings, history_days=250, max_workers=2, refresh=False,
    )
    perf = coll["performance"]
    print("COLLECTION", json.dumps(perf, default=str))
    (acc / "collection_performance.json").write_text(json.dumps(perf, indent=2, default=str), encoding="utf-8")

    store = AnalysisStore(HERE / "output" / "analysis.sqlite", environment=PRODUCTION)
    funnel = FunnelRegistry(store=store, db=db, environment=PRODUCTION)

    pkg = acc / "handoff"
    cfg = ExplorerRunConfig(
        horizon="NEXT_WORKING_DAY",
        enrich_intraday=True,
        prescreen_limit=30,
        intraday_limit=15,
        handoff_limit=20,
        environment=PRODUCTION,
    )
    print("=== Explorer handoff (calibrated) ===")
    exp = prepare_explorer_handoff(
        cfg, db=db, store=store, funnel_registry=funnel, output_root=pkg,
    )
    src_zip = Path(exp["zip_path"])
    dest_zip = acc / "EGX_EXPLORER_HANDOFF.zip"
    if src_zip.exists():
        shutil.copy2(src_zip, dest_zip)

    counts = exp.get("counts") or {}
    coverage = exp.get("coverage") or {}
    corr_legacy = exp.get("correlation_legacy") or {}
    corr_cal = exp.get("correlation_calibrated") or {}
    ranked = exp.get("ranked_comparison") or []
    prescreen_all = exp.get("prescreen_all") or []
    payload = json.loads((pkg / "explorer_handoff.json").read_text(encoding="utf-8"))
    candidates = payload.get("candidates") or []

    # Copy package artifacts into the v051 acceptance folder.
    for name in (
        "legacy_vs_calibrated_ranking.csv",
        "prescreen_candidates_calibrated.csv",
        "history_integrity_flags.csv",
        "prescreen_candidates.csv",
        "signal_calibration_diagnostics.json",
    ):
        src = pkg / name
        if src.exists():
            shutil.copy2(src, acc / name)

    if ranked:
        rows_to_csv(acc / "legacy_vs_calibrated_ranking.csv", ranked)

    top20 = []
    by_rank = {r.get("ticker"): r for r in ranked}
    for c in candidates[:20]:
        t = c.get("ticker")
        rr = by_rank.get(t) or {}
        m = c
        top20.append({
            "ticker": t,
            "legacy_score": c.get("candidate_score_legacy") or rr.get("legacy_score"),
            "legacy_rank": c.get("legacy_rank") or rr.get("legacy_rank"),
            "calibrated_score": c.get("candidate_score_calibrated") or c.get("candidate_score"),
            "calibrated_rank": c.get("calibrated_rank") or rr.get("calibrated_rank"),
            "rank_change": c.get("rank_change") if c.get("rank_change") is not None else rr.get("rank_change"),
            "candidate_lane": c.get("candidate_lane"),
            "candidate_families": c.get("candidate_families"),
            "MOVE_ALREADY_REALIZED": c.get("MOVE_ALREADY_REALIZED"),
            "FORWARD_SETUP_QUALITY": c.get("FORWARD_SETUP_QUALITY"),
            "TECHNICAL_HISTORY_INTEGRITY": c.get("TECHNICAL_HISTORY_INTEGRITY"),
            "VOLATILITY_RISK": c.get("VOLATILITY_RISK"),
            "RVOL20": c.get("RVOL20") or c.get("rvol_20"),
            "distance_20d_high": c.get("distance_20d_high") or c.get("dist_from_20d_high_pct"),
            "return_1w": c.get("return_1w") or c.get("return_1w_pct"),
            "return_1m": c.get("return_1m") or c.get("return_1m_pct"),
            "return_3m": c.get("return_3m") or c.get("return_3m_pct"),
            "return_6m": c.get("return_6m") or c.get("return_6m_pct"),
            "intraday_available": c.get("intraday_available"),
            "reason_for_change": c.get("reason_for_change") or rr.get("reason_for_change"),
        })

    biggest = sorted(
        [r for r in ranked if r.get("rank_change") is not None],
        key=lambda r: abs(int(r.get("rank_change") or 0)),
        reverse=True,
    )[:15]

    legacy_6m = abs((_corr_cell(corr_legacy, "return_6m_pct").get("spearman") or 0) or 0)
    cal_6m = abs((_corr_cell(corr_cal, "return_6m_pct").get("spearman") or 0) or 0)
    legacy_3m = abs((_corr_cell(corr_legacy, "return_3m_pct").get("spearman") or 0) or 0)
    cal_3m = abs((_corr_cell(corr_cal, "return_3m_pct").get("spearman") or 0) or 0)
    dominance_reduced = cal_6m < legacy_6m or cal_3m < legacy_3m
    still_overwhelming = cal_6m >= 0.75 and cal_6m >= max(
        abs((_corr_cell(corr_cal, "rvol_20").get("spearman") or 0) or 0),
        abs((_corr_cell(corr_cal, "dist_from_20d_high_pct").get("spearman") or 0) or 0),
        0.0,
    )

    eligible = int(counts.get("SCANNER_ELIGIBLE_SYMBOLS") or 0)
    coverage_ok = eligible >= 100 and (counts.get("scanner_eligible_coverage_pct") or 0) >= 70

    if still_overwhelming:
        verdict = "FAIL"
        verdict_reason = "calibrated ranking still overwhelmingly explained by 6M return"
    elif not coverage_ok:
        verdict = "FAIL"
        verdict_reason = "scanner-eligible coverage regressed below the v0.5 bar"
    elif dominance_reduced and coverage_ok:
        verdict = "PASS WITH LIMITATIONS"
        verdict_reason = "forward-setup ranking reduced 3M/6M dominance; scores remain HEURISTIC_UNCALIBRATED"
        if cal_6m < 0.45 and coverage.get("EXPLORER_COVERAGE") in {"HIGH", "MEDIUM"}:
            verdict = "PASS"
            verdict_reason = "calibrated rank is no longer 3M/6M-dominated; coverage preserved"
    else:
        verdict = "PASS WITH LIMITATIONS"
        verdict_reason = "coverage preserved; 3M/6M correlation did not fall as far as hoped"

    report = {
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "score_kind": "HEURISTIC_UNCALIBRATED",
        "not_a_probability": True,
        "UNIVERSE_TOTAL": counts.get("UNIVERSE_TOTAL"),
        "EQUITY_UNIVERSE_TOTAL": counts.get("EQUITY_UNIVERSE_TOTAL"),
        "MAPPED_SYMBOLS": counts.get("MAPPED_SYMBOLS"),
        "DAILY_DATA_AVAILABLE": counts.get("DAILY_DATA_AVAILABLE"),
        "DAILY_DATA_UNAVAILABLE": counts.get("DAILY_DATA_UNAVAILABLE"),
        "SCANNER_ELIGIBLE": counts.get("SCANNER_ELIGIBLE_SYMBOLS"),
        "SCANNER_ELIGIBLE_SYMBOLS": counts.get("SCANNER_ELIGIBLE_SYMBOLS"),
        "PRESCREEN_SELECTED": counts.get("PRESCREEN_SELECTED"),
        "INTRADAY_ENRICHED": counts.get("INTRADAY_ENRICHED"),
        "HANDOFF_CANDIDATES": counts.get("HANDOFF_CANDIDATES"),
        "daily_data_coverage_pct": counts.get("daily_data_coverage_pct"),
        "scanner_eligible_coverage_pct": counts.get("scanner_eligible_coverage_pct"),
        "EXPLORER_COVERAGE": coverage.get("EXPLORER_COVERAGE"),
        "selection_basis": coverage.get("selection_basis"),
        "lane_tops": exp.get("lane_tops"),
        "intraday_queried_tickers": exp.get("intraday_queried_tickers"),
        "correlation_legacy": corr_legacy,
        "correlation_calibrated": corr_cal,
        "legacy_6m_spearman_abs": legacy_6m,
        "calibrated_6m_spearman_abs": cal_6m,
        "legacy_3m_spearman_abs": legacy_3m,
        "calibrated_3m_spearman_abs": cal_3m,
        "dominance_reduced": dominance_reduced,
        "still_overwhelming_6m": still_overwhelming,
        "top20_calibrated": top20,
        "biggest_rank_changes": biggest,
        "zip_path": str(dest_zip),
        "package_dir": str(pkg),
        "collection_performance": perf,
    }
    (acc / "signal_calibration_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8",
    )

    md = [
        "# EGX Market Bridge v0.5.1 — signal calibration report",
        "",
        f"**Verdict:** {verdict}",
        "",
        verdict_reason,
        "",
        "Scores are **HEURISTIC_UNCALIBRATED**. They are not probabilities of profit.",
        "",
        "## Coverage",
        "",
        f"- UNIVERSE_TOTAL: {report['UNIVERSE_TOTAL']}",
        f"- EQUITY_UNIVERSE_TOTAL: {report['EQUITY_UNIVERSE_TOTAL']}",
        f"- MAPPED_SYMBOLS: {report['MAPPED_SYMBOLS']}",
        f"- DAILY_DATA_AVAILABLE: {report['DAILY_DATA_AVAILABLE']}",
        f"- SCANNER_ELIGIBLE: {report['SCANNER_ELIGIBLE']}",
        f"- PRESCREEN_SELECTED: {report['PRESCREEN_SELECTED']}",
        f"- INTRADAY_ENRICHED: {report['INTRADAY_ENRICHED']}",
        f"- HANDOFF_CANDIDATES: {report['HANDOFF_CANDIDATES']}",
        f"- daily_data_coverage_pct: {report['daily_data_coverage_pct']}",
        f"- scanner_eligible_coverage_pct: {report['scanner_eligible_coverage_pct']}",
        f"- EXPLORER_COVERAGE: {report['EXPLORER_COVERAGE']}",
        "",
        "## Scoring change",
        "",
        "Legacy `prescreen_score` added `abs(return) * weight * 0.35` with no cap, so +478% 6M dwarfed RVOL.",
        "Calibrated rank uses `ln(1+|r|/scale)` with scales 1d=4, 1w=8, 1m=15, 3m=25, 6m=40, then caps combined 3M+6M tactical context at 4 points, downweighted by history integrity.",
        "Primary rank key is forward_setup_score (0–100 heuristic) minus documented MOVE/VOL penalties.",
        "",
        * _md_corr_table("Legacy correlation profile", corr_legacy),
        * _md_corr_table("Calibrated correlation profile", corr_cal),
        "## Top 20 calibrated candidates",
        "",
        "| ticker | legacy_score | legacy_rank | calibrated_score | calibrated_rank | rank_change | lane | MOVE | FORWARD | integrity | vol | RVOL20 | d20 | 1W | 1M | 3M | 6M | intraday |",
        "|---|---:|---:|---:|---:|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in top20:
        fams = ",".join(row.get("candidate_families") or [])
        md.append(
            f"| {row['ticker']} | {row['legacy_score']} | {row['legacy_rank']} | "
            f"{row['calibrated_score']} | {row['calibrated_rank']} | {row['rank_change']} | "
            f"{row['candidate_lane']} | {row['MOVE_ALREADY_REALIZED']} | {row['FORWARD_SETUP_QUALITY']} | "
            f"{row['TECHNICAL_HISTORY_INTEGRITY']} | {row['VOLATILITY_RISK']} | {row['RVOL20']} | "
            f"{row['distance_20d_high']} | {row['return_1w']} | {row['return_1m']} | "
            f"{row['return_3m']} | {row['return_6m']} | {row['intraday_available']} |"
        )
        md.append(f"|  families: {fams} ||||||||||||||||||")
    md.extend(["", "## Biggest ranking changes vs legacy", ""])
    for r in biggest:
        md.append(
            f"- {r.get('ticker')}: legacy_rank={r.get('legacy_rank')} → calibrated_rank={r.get('calibrated_rank')} "
            f"(Δ {r.get('rank_change')}) — {r.get('reason_for_change')}"
        )
    md.extend([
        "",
        "## Intraday enrichment selection",
        "",
        f"Queried: {exp.get('intraday_queried_tickers')}",
        "Priority families: PRE_BREAKOUT, EARLY_MOMENTUM, FRESH_CONTINUATION, CONTINUATION, EARLY_REVERSAL — then calibrated score, not legacy 6M rank.",
        "",
        f"## ZIP",
        "",
        str(dest_zip),
        "",
    ])
    (acc / "signal_calibration_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print("CALIBRATION", json.dumps({
        k: report[k] for k in report
        if k not in {"top20_calibrated", "biggest_rank_changes", "collection_performance", "correlation_legacy", "correlation_calibrated"}
    }, indent=2, default=str))
    print("ZIP", dest_zip)
    store.close()
    db.close()
    print("VERDICT", verdict)
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
