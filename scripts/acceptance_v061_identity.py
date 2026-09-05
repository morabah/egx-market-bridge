#!/usr/bin/env python3
"""v0.6.1 signal-identity acceptance. Does not retune scores or invent outcomes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from egxbridge.analysis.common.environment import PRODUCTION
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.schedule.handoff import prepare_schedule_handoffs, load_explorer_package
from egxbridge.analysis.schedule.identity import backfill_canonical_from_legacy_snapshots
from egxbridge.analysis.schedule.types import ANALYSIS_TYPES


def _find_explorer() -> Path | None:
    # Prefer the accepted v0.6 20-candidate package, not pytest last_run leftovers.
    candidates = [
        HERE / "output" / "acceptance" / "v06" / "explorer_handoff",
        HERE / "output" / "explorer_handoff",
    ]
    last = HERE / "workspace" / "explorer" / "last_run.json"
    if last.exists():
        try:
            pkg = Path((json.loads(last.read_text(encoding="utf-8")) or {}).get("package_dir") or "")
            candidates.append(pkg)
        except Exception:
            pass
    for p in candidates:
        if p.exists() and (p / "explorer_handoff.json").exists():
            return p
    return None


def main() -> int:
    acc = HERE / "output" / "acceptance" / "v061_identity"
    acc.mkdir(parents=True, exist_ok=True)
    pkg = _find_explorer()
    if not pkg:
        print("No Explorer package found. Run Explorer first.")
        return 1
    payload = load_explorer_package(pkg)
    n_cand = len(payload.get("candidates") or [])
    # Isolated acceptance DB — do not mix with production or write outcomes.
    store = AnalysisStore(acc / "analysis.sqlite", environment=PRODUCTION)
    backfill_canonical_from_legacy_snapshots(store)
    before_c = {s["canonical_signal_id"] for s in store.list_canonical_signals(limit=5000)}
    before_o = len(store.list_analysis_observations(limit=20000))

    r1 = prepare_schedule_handoffs(
        explorer_payload=payload, store=store,
        output_root=acc / "sched_1", environment=PRODUCTION, jobs=list(ANALYSIS_TYPES),
    )
    r2 = prepare_schedule_handoffs(
        explorer_payload=payload, store=store,
        output_root=acc / "sched_2", environment=PRODUCTION, jobs=list(ANALYSIS_TYPES),
    )
    after = store.list_canonical_signals(limit=5000)
    obs = store.list_analysis_observations(limit=20000)
    by_ticker = {}
    for s in after:
        t = s.get("ticker")
        by_ticker.setdefault(t, set()).add(s.get("canonical_signal_id"))
    examples = {}
    for t in ("RAYA", "EGCH", "ALCN", "MASR"):
        ids = sorted(by_ticker.get(t) or [])
        examples[t] = {
            "canonical_signal_ids": ids,
            "canonical_n": len(ids),
            "observations_n": len(store.list_analysis_observations(ticker=t, limit=500)),
        }
    new_c = {s["canonical_signal_id"] for s in after} - before_c
    scanner_n = r1.get("canonical_signals_n")
    obs_n = r1.get("analysis_observations_n")
    reuse_ok = r2.get("canonical_signals_n") == r1.get("canonical_signals_n")
    examples_reuse = all(v["canonical_n"] <= 2 for v in examples.values() if v["canonical_n"])
    # ≤2 allows a genuine intraday child; not 5× jobs.
    not_times_jobs = scanner_n is not None and scanner_n <= n_cand + 5
    fail = []
    if n_cand < 1:
        fail.append("no candidates")
    if not reuse_ok:
        fail.append("second packaging inflated canonical n")
    if not (obs_n and obs_n > (scanner_n or 0)):
        fail.append("observations not greater than canonical n")
    if not not_times_jobs:
        fail.append("scanner n looks like jobs × candidates")
    if r1.get("scoring_version") != "0.5.1":
        fail.append("scoring_version changed")
    verdict = "FAIL" if fail else "PASS WITH LIMITATIONS"
    report = {
        "verdict": verdict,
        "fail_reasons": fail,
        "explorer_package": str(pkg),
        "handoff_candidates": n_cand,
        "explorer_run_id": payload.get("explorer_run_id") or r1.get("explorer_run_id"),
        "first_pack_canonical_signals_n": scanner_n,
        "first_pack_analysis_observations_n": obs_n,
        "second_pack_canonical_signals_n": r2.get("canonical_signals_n"),
        "second_pack_analysis_observations_n": r2.get("analysis_observations_n"),
        "store_canonical_total": len(after),
        "store_observations_total": len(obs),
        "new_canonical_this_run": len(new_c),
        "observations_before": before_o,
        "examples": examples,
        "examples_not_multiplied_by_jobs": examples_reuse,
        "scoring_version": r1.get("scoring_version"),
        "outcomes_manufactured": False,
        "limitations": [
            "Production outcomes were not computed (no retroactive manufacture).",
            "Historical v0.6 snapshots remain immutable provenance.",
            "Scores remain HEURISTIC_UNCALIBRATED / scoring_version=0.5.1.",
        ],
    }
    (acc / "signal_identity_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    print("VERDICT", verdict)
    store.close()
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
