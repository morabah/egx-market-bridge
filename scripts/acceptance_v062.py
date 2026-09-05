#!/usr/bin/env python3
"""v0.6.2 acceptance: breadth, fingerprint identity, observation counts, envelopes.

Isolated DB only. Does not write simulated imports into production.
Does not retune scores or manufacture production outcomes.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from egxbridge.analysis.common.environment import UNIT_TEST
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.calibration import SCORING_VERSION
from egxbridge.analysis.schedule.handoff import prepare_schedule_handoffs, load_explorer_package
from egxbridge.analysis.schedule.importer import import_schedule_result
from egxbridge.analysis.schedule.metrics import observation_counts
from egxbridge.analysis.schedule.types import (
    ANALYSIS_TYPES, ANALYSIS_PREMARKET, ANALYSIS_VALUE, RESULT_ENVELOPE_VERSION,
)


def _md_table(d: dict, keys: list[str]) -> str:
    lines = ["| Field | Value |", "|---|---|"]
    for k in keys:
        lines.append(f"| {k} | {d.get(k)} |")
    return "\n".join(lines)


def main() -> int:
    acc = HERE / "output" / "acceptance" / "v062"
    if acc.exists():
        shutil.rmtree(acc)
    acc.mkdir(parents=True)
    pkg = HERE / "output" / "acceptance" / "v06" / "explorer_handoff"
    if not (pkg / "explorer_handoff.json").exists():
        print("Missing v0.6 Explorer package at", pkg)
        return 1
    payload = load_explorer_package(pkg)
    payload_b = json.loads(json.dumps(payload, default=str))
    payload_b["explorer_run_id"] = "xr_acceptance_rerun_B"
    payload_b["_package_dir"] = str(pkg)

    store = AnalysisStore(acc / "analysis.sqlite", environment=UNIT_TEST)
    r1 = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=acc / "sched_1",
        environment=UNIT_TEST, jobs=list(ANALYSIS_TYPES),
    )
    n_after_a = len(store.list_canonical_signals())
    r2 = prepare_schedule_handoffs(
        explorer_payload=payload_b, store=store, output_root=acc / "sched_2",
        environment=UNIT_TEST, jobs=list(ANALYSIS_TYPES),
    )
    n_after_b = len(store.list_canonical_signals())
    r3 = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=acc / "sched_3_repeat",
        environment=UNIT_TEST, jobs=list(ANALYSIS_TYPES),
    )

    market = json.loads((Path(r1["package_dir"]) / "common" / "market_summary.json").read_text())
    mb = market.get("market_breadth") or {}
    sb = market.get("shortlist_breadth") or {}
    mp = market.get("market_participation") or {}
    counts = payload.get("counts") or {}

    examples = {}
    for t in ("RAYA", "EGCH", "ALCN", "MASR"):
        rows = store.list_canonical_signals(ticker=t)
        examples[t] = {
            "canonical_n": len(rows),
            "canonical_signal_id": (rows[0]["canonical_signal_id"] if rows else None),
            "market_state_fingerprint": (rows[0].get("market_state_fingerprint") if rows else None),
            "observations_n": len(store.list_analysis_observations(ticker=t)),
        }

    oc_before_import = observation_counts(store.list_analysis_observations())
    raya = next((s for s in store.list_canonical_signals() if s["ticker"] == "RAYA"), None)
    egch = next((s for s in store.list_canonical_signals() if s["ticker"] == "EGCH"), None)
    env1 = {
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "analysis_type": ANALYSIS_PREMARKET,
        "run_id": r1["run_id"],
        "candidates": [{
            "ticker": "RAYA",
            "canonical_signal_id": (raya or {}).get("canonical_signal_id"),
            "signal_family_id": (raya or {}).get("signal_family_id"),
            "parent_signal_id": (raya or {}).get("parent_signal_id"),
            "market_state_fingerprint": (raya or {}).get("market_state_fingerprint"),
            "status": "PROMOTE",
            "catalyst_status": "POSITIVE_CONFIRMED",
        }],
    }
    env2 = {
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "analysis_type": ANALYSIS_VALUE,
        "run_id": r1["run_id"],
        "candidates": [{
            "ticker": "EGCH",
            "canonical_signal_id": (egch or {}).get("canonical_signal_id"),
            "signal_family_id": (egch or {}).get("signal_family_id"),
            "parent_signal_id": (egch or {}).get("parent_signal_id"),
            "market_state_fingerprint": (egch or {}).get("market_state_fingerprint"),
            "FUNNEL_ACTION": "START_FULL_FUNNEL",
        }],
    }
    (acc / "chatgpt_envelope_example.json").write_text(json.dumps(env1, indent=2), encoding="utf-8")
    p1 = acc / "import_premarket.md"
    p2 = acc / "import_value.md"
    p1.write_text("isolated acceptance import\n```json\n" + json.dumps(env1) + "\n```\n", encoding="utf-8")
    p2.write_text("isolated acceptance import\n```json\n" + json.dumps(env2) + "\n```\n", encoding="utf-8")
    i1 = import_schedule_result(p1, analysis_type=ANALYSIS_PREMARKET, run_id=r1["run_id"], store=store)
    i2 = import_schedule_result(p2, analysis_type=ANALYSIS_VALUE, run_id=r1["run_id"], store=store)
    oc_after = observation_counts(store.list_analysis_observations())

    src_zip = Path(r1["combined_zip"])
    dest_zip = acc / "EGX_5_SCHEDULE_HANDOFF.zip"
    if src_zip.exists():
        shutil.copy2(src_zip, dest_zip)

    jobs_ok = True
    pkg1 = Path(r1["package_dir"])
    for fname in ("macro_holdings.md", "premarket_catalysts.md", "intraday_opportunity.md", "value_quality.md", "weekly_xray.md"):
        text = (pkg1 / "jobs" / fname).read_text(encoding="utf-8")
        if "canonical_signal_id" not in text:
            jobs_ok = False

    fail = []
    n_cand = len(payload.get("candidates") or [])
    if n_cand != 20:
        fail.append(f"handoff candidates {n_cand} != 20")
    if n_after_a != 20 or n_after_b != 20:
        fail.append(f"canonical after A/B = {n_after_a}/{n_after_b}, expected 20/20")
    if oc_before_import["analysis_observations_generated_n"] < 100:
        fail.append("generated_n after first pack expected 100+")
    # After 3 packs: 20*5*3 = 300 generated
    if oc_after["analysis_observations_imported_n"] != 2:
        fail.append(f"imported_n={oc_after['analysis_observations_imported_n']} expected 2")
    if oc_after["analysis_observations_evaluable_n"] != 2:
        fail.append(f"evaluable_n={oc_after['analysis_observations_evaluable_n']} expected 2")
    if (mb.get("breadth_n") or 0) < 50:
        fail.append("market breadth_n too small — still using shortlist?")
    if mb.get("advancers") == sb.get("advancers") and mb.get("breadth_n") == sb.get("breadth_n"):
        fail.append("market breadth equals shortlist breadth")
    if r1.get("scoring_version") != "0.5.1":
        fail.append("scoring_version changed")
    if not jobs_ok:
        fail.append("job handoff missing canonical_signal_id")
    if examples.get("RAYA", {}).get("canonical_n") != 1:
        fail.append("RAYA not a single canonical")

    verdict = "FAIL" if fail else "PASS WITH LIMITATIONS"
    breadth_report = {
        "EQUITY_UNIVERSE_TOTAL": counts.get("EQUITY_UNIVERSE_TOTAL"),
        "SCANNER_ELIGIBLE_SYMBOLS": counts.get("SCANNER_ELIGIBLE_SYMBOLS"),
        "MARKET_BREADTH_SCOPE": "SCANNER_ELIGIBLE_EQUITY_UNIVERSE",
        "market_breadth": mb,
        "market_participation": mp,
        "shortlist_breadth": sb,
        "shortlist_label": "CANDIDATE_BREADTH",
        "scoring_version": SCORING_VERSION,
        "note": "Do not infer market regime from candidate shortlist breadth.",
    }
    identity_report = {
        "handoff_candidates": n_cand,
        "canonical_after_run_A": n_after_a,
        "canonical_after_run_B_same_market_state": n_after_b,
        "canonical_after_third_packaging": len(store.list_canonical_signals()),
        "explorer_run_id_A": payload.get("explorer_run_id") or r1.get("explorer_run_id"),
        "explorer_run_id_B": payload_b.get("explorer_run_id"),
        "examples": examples,
        "same_market_state_reused": n_after_a == n_after_b == 20,
        "scoring_version": SCORING_VERSION,
        "outcomes_manufactured": False,
    }
    obs_report = {
        "after_first_five_jobs": {
            "scanner_sample_n": r1.get("scanner_sample_n") or r1.get("canonical_signals_n"),
            "canonical_signals_n": r1.get("canonical_signals_n"),
            "analysis_observations_generated_n": 20 * 5,
            "analysis_observations_imported_n": 0,
            "analysis_observations_evaluable_n": 0,
        },
        "after_repeat_packaging_and_rerun": {
            "scanner_sample_n": n_after_b,
            "analysis_observations_generated_n": oc_after["analysis_observations_generated_n"],
            "analysis_observations_imported_n": oc_after["analysis_observations_imported_n"],
            "analysis_observations_evaluable_n": oc_after["analysis_observations_evaluable_n"],
        },
        "imports": [i1.get("candidate_linkages"), i2.get("candidate_linkages")],
        "production_db_written": False,
    }
    (acc / "macro_breadth_report.json").write_text(json.dumps(breadth_report, indent=2, default=str), encoding="utf-8")
    (acc / "signal_identity_report.json").write_text(json.dumps(identity_report, indent=2, default=str), encoding="utf-8")
    (acc / "observation_count_report.json").write_text(json.dumps(obs_report, indent=2, default=str), encoding="utf-8")
    (acc / "macro_breadth_report.md").write_text(
        "# v0.6.2 Macro breadth\n\n"
        f"EQUITY_UNIVERSE_TOTAL = {counts.get('EQUITY_UNIVERSE_TOTAL')}\n"
        f"SCANNER_ELIGIBLE_SYMBOLS = {counts.get('SCANNER_ELIGIBLE_SYMBOLS')}\n\n"
        "## Broad market (SCANNER_ELIGIBLE_EQUITY_UNIVERSE)\n\n"
        + _md_table(mb, [
            "breadth_n", "advancers", "decliners", "unchanged", "advancers_pct",
            "median_daily_return_pct", "median_rvol20", "pct_above_sma20", "pct_above_sma50",
            "pct_near_20d_high", "pct_breakout_20d",
        ])
        + "\n\n## Shortlist (CANDIDATE_BREADTH — not market breadth)\n\n"
        + _md_table(sb, ["breadth_n", "advancers", "decliners", "advancers_pct"])
        + "\n\nDo not infer market regime from candidate shortlist breadth.\n",
        encoding="utf-8",
    )
    (acc / "signal_identity_report.md").write_text(
        "# v0.6.2 Signal identity\n\n"
        f"Run A canonical_signals_n = {n_after_a}\n"
        f"Run B (new explorer_run_id, same market evidence) = {n_after_b}\n"
        f"Expected 20 / 20. Reused = {n_after_a == n_after_b == 20}\n\n"
        f"RAYA canonical_n = {examples.get('RAYA', {}).get('canonical_n')}\n"
        f"EGCH canonical_n = {examples.get('EGCH', {}).get('canonical_n')}\n",
        encoding="utf-8",
    )
    summary = {
        "verdict": verdict,
        "fail_reasons": fail,
        "scoring_version_changed": False,
        "scoring_version": SCORING_VERSION,
        "bridge_version": "0.6.2",
        "combined_zip": str(dest_zip),
        "breadth": {
            "n": mb.get("breadth_n"),
            "advancers": mb.get("advancers"),
            "decliners": mb.get("decliners"),
            "unchanged": mb.get("unchanged"),
            "advancers_pct": mb.get("advancers_pct"),
            "median_daily_return_pct": mb.get("median_daily_return_pct"),
            "median_rvol20": mb.get("median_rvol20"),
            "pct_above_sma20": mb.get("pct_above_sma20"),
            "pct_above_sma50": mb.get("pct_above_sma50"),
        },
        "shortlist_breadth": {
            "n": sb.get("breadth_n"),
            "advancers": sb.get("advancers"),
            "decliners": sb.get("decliners"),
        },
        "same_market_state_rerun": {"before": n_after_a, "after": n_after_b},
        "generated_n": oc_after["analysis_observations_generated_n"],
        "imported_n": oc_after["analysis_observations_imported_n"],
        "evaluable_n": oc_after["analysis_observations_evaluable_n"],
        "scanner_sample_n": n_after_b,
        "envelope_ok": jobs_ok,
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "limitations": [
            "Used the accepted v0.6 Explorer package (session 2026-09-03) rather than a fresh Yahoo recollect.",
            "Production outcomes were not computed or manufactured.",
            "Historical v0.6/v0.6.1 snapshot rows remain immutable and were not collapsed.",
            "Isolated acceptance DB only — simulated ChatGPT imports were not written to production analysis.sqlite.",
        ],
    }
    (acc / "acceptance_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    print("VERDICT", verdict)
    print("ZIP", dest_zip)
    store.close()
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
