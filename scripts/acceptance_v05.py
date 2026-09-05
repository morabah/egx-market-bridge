#!/usr/bin/env python3
"""v0.5 broad-universe Explorer acceptance — isolated from production Funnel state."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from egxbridge.analysis.common.environment import ACCEPTANCE_TEST, PRODUCTION
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
from egxbridge.analysis.explorer.models import ExplorerRunConfig
from egxbridge.analysis.funnel.registry import FunnelRegistry
from egxbridge.collect_universe import collect_universe_daily
from egxbridge.config import Settings
from egxbridge.db import Database


def main() -> int:
    settings = Settings.load(HERE / "config.json")
    db = Database(settings.db_path(HERE))

    acc = HERE / "output" / "acceptance" / "v05"
    if acc.exists():
        shutil.rmtree(acc)
    acc.mkdir(parents=True, exist_ok=True)

    print("=== Yahoo daily collection (equity universe) ===")
    coll = collect_universe_daily(
        db=db, settings=settings, history_days=250, max_workers=2, refresh=False,
    )
    perf = coll["performance"]
    print("COLLECTION", json.dumps(perf))
    (acc / "collection_performance.json").write_text(json.dumps(perf, indent=2), encoding="utf-8")

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
    print("=== Explorer handoff ===")
    exp = prepare_explorer_handoff(
        cfg, db=db, store=store, funnel_registry=funnel, output_root=pkg,
    )
    src_zip = Path(exp["zip_path"])
    dest_zip = acc / "EGX_EXPLORER_HANDOFF.zip"
    if src_zip.exists():
        shutil.copy2(src_zip, dest_zip)

    counts = exp.get("counts") or {}
    coverage = exp.get("coverage") or {}
    report = {
        "UNIVERSE_TOTAL": counts.get("UNIVERSE_TOTAL"),
        "EQUITY_UNIVERSE_TOTAL": counts.get("EQUITY_UNIVERSE_TOTAL"),
        "MAPPED_SYMBOLS": counts.get("MAPPED_SYMBOLS"),
        "DAILY_DATA_AVAILABLE": counts.get("DAILY_DATA_AVAILABLE"),
        "DAILY_DATA_UNAVAILABLE": counts.get("DAILY_DATA_UNAVAILABLE"),
        "SCANNER_ELIGIBLE_SYMBOLS": counts.get("SCANNER_ELIGIBLE_SYMBOLS"),
        "PRESCREEN_SELECTED": counts.get("PRESCREEN_SELECTED"),
        "INTRADAY_ENRICHED": counts.get("INTRADAY_ENRICHED"),
        "HANDOFF_CANDIDATES": counts.get("HANDOFF_CANDIDATES"),
        "daily_data_coverage_pct": counts.get("daily_data_coverage_pct"),
        "scanner_eligible_coverage_pct": counts.get("scanner_eligible_coverage_pct"),
        "EXPLORER_COVERAGE": coverage.get("EXPLORER_COVERAGE"),
        "selection_basis": coverage.get("selection_basis"),
        "selection_bias_risk": coverage.get("selection_bias_risk"),
        "market_wide_confidence_allowed": coverage.get("market_wide_confidence_allowed"),
        "production_ready": bool(
            coverage.get("EXPLORER_COVERAGE") in {"HIGH", "MEDIUM"}
            and (counts.get("scanner_eligible_coverage_pct") or 0) >= 70
        ),
        "collection_performance": perf,
        "zip_path": str(dest_zip),
        "package_dir": str(pkg),
    }
    payload = json.loads((pkg / "explorer_handoff.json").read_text(encoding="utf-8"))
    top20 = []
    for c in (payload.get("candidates") or [])[:20]:
        top20.append({
            "ticker": c.get("ticker"),
            "score": c.get("candidate_score") or c.get("prescreen_score"),
            "candidate_families": c.get("candidate_families"),
            "main_reasons": (c.get("candidate_reasons") or [])[:6],
            "main_warnings": c.get("candidate_warnings"),
            "Funnel_status": c.get("funnel_status"),
            "intraday_available": c.get("intraday_available"),
        })
    report["top20_prescreen"] = top20
    (acc / "coverage_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = [
        "# EGX Market Bridge v0.5 coverage report",
        "",
        f"- UNIVERSE_TOTAL: {report['UNIVERSE_TOTAL']}",
        f"- EQUITY_UNIVERSE_TOTAL: {report['EQUITY_UNIVERSE_TOTAL']}",
        f"- MAPPED_SYMBOLS: {report['MAPPED_SYMBOLS']}",
        f"- DAILY_DATA_AVAILABLE: {report['DAILY_DATA_AVAILABLE']}",
        f"- DAILY_DATA_UNAVAILABLE: {report['DAILY_DATA_UNAVAILABLE']}",
        f"- SCANNER_ELIGIBLE_SYMBOLS: {report['SCANNER_ELIGIBLE_SYMBOLS']}",
        f"- PRESCREEN_SELECTED: {report['PRESCREEN_SELECTED']}",
        f"- INTRADAY_ENRICHED: {report['INTRADAY_ENRICHED']}",
        f"- HANDOFF_CANDIDATES: {report['HANDOFF_CANDIDATES']}",
        f"- daily_data_coverage_pct: {report['daily_data_coverage_pct']}",
        f"- scanner_eligible_coverage_pct: {report['scanner_eligible_coverage_pct']}",
        f"- EXPLORER_COVERAGE: {report['EXPLORER_COVERAGE']}",
        f"- selection_basis: {report['selection_basis']}",
        f"- production_ready: {report['production_ready']}",
        "",
        "## Top 20 pre-screen candidates",
        "",
    ]
    for row in top20:
        md.append(
            f"- {row['ticker']} score={row['score']} families={row['candidate_families']} "
            f"funnel={row['Funnel_status']} intraday={row['intraday_available']}"
        )
        md.append(f"  reasons: {row['main_reasons']}")
        md.append(f"  warnings: {row['main_warnings']}")
    if not report["production_ready"]:
        md.append("")
        md.append("Explorer is **not** declared production-ready at this coverage level.")
    (acc / "coverage_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    shutil.copy2(pkg / "universe_failures.csv", acc / "universe_failures.csv")
    shutil.copy2(pkg / "prescreen_candidates.csv", acc / "prescreen_candidates.csv")

    print("COVERAGE", json.dumps({k: report[k] for k in report if k not in {"top20_prescreen", "collection_performance"}}, indent=2))
    print("ZIP", dest_zip)
    store.close()
    db.close()
    if report["EXPLORER_COVERAGE"] == "INSUFFICIENT":
        print("ACCEPTANCE_NOTE INSUFFICIENT_COVERAGE")
    print("PASS_SCRIPT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
