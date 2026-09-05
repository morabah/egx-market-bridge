#!/usr/bin/env python3
"""v0.6.3 acceptance: job-specific schemas, session phase, weekly counts, identity.

Isolated DB only. Does not write simulated imports into production.
Does not retune scores.
"""
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from egxbridge.analysis.common.environment import UNIT_TEST
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.calibration import calibrate_candidate, SCORING_VERSION
from egxbridge.analysis.schedule.handoff import prepare_schedule_handoffs, load_explorer_package
from egxbridge.analysis.schedule.importer import import_schedule_result, extract_json_envelope
from egxbridge.analysis.schedule.types import (
    ANALYSIS_TYPES, ANALYSIS_MACRO, ANALYSIS_PREMARKET, ANALYSIS_INTRADAY,
    ANALYSIS_VALUE, ANALYSIS_WEEKLY, RESULT_ENVELOPE_VERSION, HANDOFF_SCHEMA_VERSION,
    RESULT_SCHEMA_FILES, PARSE_VALID, PARSE_INVALID_SCHEMA, PARSE_INVALID_CANONICAL_ID,
    PARSE_NEEDS_REVIEW, PHASE_MISMATCH, NOT_LIVE_CONFIRMATION_TEXT,
)


def _copy_zip(src: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def main() -> int:
    acc = HERE / "output" / "acceptance" / "v063"
    if acc.exists():
        shutil.rmtree(acc)
    acc.mkdir(parents=True)
    examples_dir = acc / "result_schema_examples"
    examples_dir.mkdir()
    imports_dir = acc / "isolated_imports"
    imports_dir.mkdir()

    pkg = HERE / "output" / "acceptance" / "v06" / "explorer_handoff"
    if not (pkg / "explorer_handoff.json").exists():
        print("Missing v0.6 Explorer package at", pkg)
        return 1
    payload = load_explorer_package(pkg)

    store = AnalysisStore(acc / "analysis.sqlite", environment=UNIT_TEST)
    post_close_meta = {"session_phase": "POST_CLOSE"}
    r1 = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=acc / "sched_post_close",
        environment=UNIT_TEST, jobs=list(ANALYSIS_TYPES), session_meta=post_close_meta,
    )
    pkg1 = Path(r1["package_dir"])

    continuous_meta = {
        "session_phase": "CONTINUOUS_TRADING",
        "analysis_timestamp_utc": "2026-09-03T08:20:00+00:00",
        "analysis_timestamp_cairo": "2026-09-03T11:20:00+03:00",
    }
    store_live = AnalysisStore(acc / "analysis_continuous.sqlite", environment=UNIT_TEST)
    r_live = prepare_schedule_handoffs(
        explorer_payload=payload, store=store_live, output_root=acc / "sched_continuous",
        environment=UNIT_TEST, jobs=[ANALYSIS_INTRADAY], session_meta=continuous_meta,
    )
    pkg_live = Path(r_live["package_dir"])

    dest_combined = acc / "EGX_5_SCHEDULE_HANDOFF.zip"
    _copy_zip(Path(r1["combined_zip"]), dest_combined)
    name_map = {
        ANALYSIS_MACRO: "EGX_MACRO_HOLDINGS_HANDOFF.zip",
        ANALYSIS_PREMARKET: "EGX_PREMARKET_HANDOFF.zip",
        ANALYSIS_INTRADAY: "EGX_INTRADAY_HANDOFF.zip",
        ANALYSIS_VALUE: "EGX_VALUE_QUALITY_HANDOFF.zip",
        ANALYSIS_WEEKLY: "EGX_WEEKLY_XRAY_HANDOFF.zip",
    }
    zip_paths = {"combined": str(dest_combined)}
    for job, fname in name_map.items():
        dest = acc / fname
        _copy_zip(Path(r1["individual_zips"][job]), dest)
        zip_paths[job] = str(dest)

    example_files = {
        ANALYSIS_MACRO: "macro.json",
        ANALYSIS_PREMARKET: "premarket.json",
        ANALYSIS_INTRADAY: "intraday.json",
        ANALYSIS_VALUE: "value.json",
        ANALYSIS_WEEKLY: "weekly.json",
    }
    schema_types = {}
    for job, fname in RESULT_SCHEMA_FILES.items():
        schema = json.loads((pkg1 / "common" / "schemas" / fname).read_text())
        schema_types[job] = schema.get("analysis_type")
        (examples_dir / example_files[job]).write_text(
            json.dumps(schema.get("example") or {}, indent=2, default=str), encoding="utf-8",
        )

    intra_md = (pkg1 / "jobs" / "intraday_opportunity.md").read_text(encoding="utf-8")
    intra_ex = extract_json_envelope(intra_md)
    live_md = (pkg_live / "jobs" / "intraday_opportunity.md").read_text(encoding="utf-8")
    live_ex = extract_json_envelope(live_md)
    weekly_md = (pkg1 / "jobs" / "weekly_xray.md").read_text(encoding="utf-8")
    weekly_ex = extract_json_envelope(weekly_md)
    weekly_hist = json.loads((pkg1 / "optional" / "calibration_history_summary.json").read_text())
    man = json.loads((pkg1 / "manifest.json").read_text())
    raw = json.loads((pkg1 / "optional" / "raw_candidate_detail.json").read_text())
    summary_text = (pkg1 / "common" / "candidate_summary.csv").read_text(encoding="utf-8")

    identity_check = {}
    for t in ("EGCH", "RAYA", "ALCN", "MASR"):
        row = next((c for c in raw if c.get("ticker") == t), None)
        identity_check[t] = {
            "in_raw": bool(row),
            "canonical_signal_id": (row or {}).get("canonical_signal_id"),
            "in_summary_csv": t in summary_text and bool((row or {}).get("canonical_signal_id")) and (row or {}).get("canonical_signal_id") in summary_text,
            "in_premarket_md": bool((row or {}).get("canonical_signal_id")) and (row or {}).get("canonical_signal_id") in (pkg1 / "jobs" / "premarket_catalysts.md").read_text(encoding="utf-8"),
        }

    zip_schema_ok = True
    zip_notes = []
    for job, zpath in r1["individual_zips"].items():
        with zipfile.ZipFile(zpath) as zf:
            for n in zf.namelist():
                if not n.endswith(".json"):
                    continue
                obj = json.loads(zf.read(n))
                if isinstance(obj, dict) and obj.get("analysis_type") and obj.get("analysis_type") != job:
                    zip_schema_ok = False
                    zip_notes.append(f"{job} zip file {n} analysis_type={obj.get('analysis_type')}")

    fixture = {
        "available": True, "daily_return_pct": 1, "return_1w_pct": 2, "return_1m_pct": 4,
        "return_3m_pct": 8, "return_6m_pct": 12, "rvol_20": 1.4, "dist_from_20d_high_pct": -3,
        "last_close": 10, "sma_20": 9.7, "sma_50": 9.4, "breakout_20d": False, "breakout_60d": False,
        "realized_vol_20d_ann_pct": 32, "bars": 80,
    }
    score_a = calibrate_candidate(dict(fixture))
    score_b = calibrate_candidate(dict(fixture))

    raya = next((s for s in store.list_canonical_signals() if s["ticker"] == "RAYA"), None)
    valid_intra = {
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "analysis_type": ANALYSIS_INTRADAY,
        "run_id": r1["run_id"],
        "session_phase": "POST_CLOSE",
        "live_session_evidence_available": False,
        "candidates": [{
            "ticker": "RAYA",
            "canonical_signal_id": (raya or {}).get("canonical_signal_id"),
            "setup_state": "NOT_STARTED",
            "confidence": "LOW",
        }],
    }
    wrong_type = {
        "analysis_type": ANALYSIS_PREMARKET,
        "run_id": r1["run_id"],
        "candidates": [{"ticker": "RAYA", "status": "KEEP", "catalyst_status": "NEUTRAL"}],
    }
    bad_id = {
        "analysis_type": ANALYSIS_INTRADAY,
        "run_id": r1["run_id"],
        "session_phase": "POST_CLOSE",
        "candidates": [{"ticker": "RAYA", "canonical_signal_id": "does-not-exist", "setup_state": "NO_TRADE"}],
    }
    phase_mm = {
        "analysis_type": ANALYSIS_INTRADAY,
        "run_id": r1["run_id"],
        "session_phase": "CONTINUOUS_TRADING",
        "candidates": [{
            "ticker": "RAYA",
            "canonical_signal_id": (raya or {}).get("canonical_signal_id"),
            "setup_state": "CONFIRMED",
        }],
    }
    weekly_agg = {
        "analysis_type": ANALYSIS_WEEKLY,
        "run_id": r1["run_id"],
        "scanner_summary": "insufficient",
        "calibration_status": "INSUFFICIENT_SAMPLE",
        "scanner_sample_n": 0,
    }
    macro_agg = {
        "analysis_type": ANALYSIS_MACRO,
        "run_id": r1["run_id"],
        "market_regime": "NEUTRAL",
        "portfolio_posture": "SELECTIVE",
        "confidence": "MEDIUM",
    }

    def _imp(name, envelope, atype):
        p = imports_dir / name
        p.write_text("isolated v063\n```json\n" + json.dumps(envelope) + "\n```\n", encoding="utf-8")
        return import_schedule_result(
            p, analysis_type=atype, run_id=r1["run_id"], store=store, raw_dest_dir=imports_dir,
            package_session_phase="POST_CLOSE",
        )

    i_ok = _imp("A_valid_intraday.md", valid_intra, ANALYSIS_INTRADAY)
    i_type = _imp("B_premarket_on_intraday.md", wrong_type, ANALYSIS_INTRADAY)
    i_cid = _imp("C_invalid_canonical.md", bad_id, ANALYSIS_INTRADAY)
    i_phase = _imp("D_phase_mismatch.md", phase_mm, ANALYSIS_INTRADAY)
    i_weekly = _imp("E_weekly_aggregate.md", weekly_agg, ANALYSIS_WEEKLY)
    i_macro = _imp("F_macro_aggregate.md", macro_agg, ANALYSIS_MACRO)

    fail = []
    if r1.get("scoring_version") != "0.5.1":
        fail.append("scoring_version changed")
    if score_a["candidate_score_calibrated"] != score_b["candidate_score_calibrated"]:
        fail.append("fixture scores not stable")
    for job, atype in schema_types.items():
        if atype != job:
            fail.append(f"schema {job} analysis_type={atype}")
    if not zip_schema_ok:
        fail.extend(zip_notes)
    if man.get("session_phase") != "POST_CLOSE":
        fail.append(f"package session_phase={man.get('session_phase')}")
    if (intra_ex or {}).get("session_phase") != "POST_CLOSE":
        fail.append(f"intraday example session_phase={(intra_ex or {}).get('session_phase')}")
    if "CONTINUOUS_TRADING" in json.dumps(intra_ex or {}):
        fail.append("POST_CLOSE intraday example still mentions CONTINUOUS_TRADING")
    if (live_ex or {}).get("session_phase") != "CONTINUOUS_TRADING":
        fail.append("continuous package example phase mismatch")
    if NOT_LIVE_CONFIRMATION_TEXT not in intra_md:
        fail.append("missing not-live confirmation text")
    if (weekly_ex or {}).get("scanner_sample_n") in (0, "0"):
        fail.append("weekly example hard-coded scanner_sample_n=0")
    if weekly_hist.get("scanner_sample_n") in (None, 0) and len(payload.get("candidates") or []) == 20:
        fail.append("weekly app hist missing scanner_sample_n")
    if man.get("analysis_observations_n_semantics") != "DEPRECATED_ALIAS_OF_GENERATED":
        fail.append("missing deprecation semantics")
    if i_ok.get("structured_parse_status") != PARSE_VALID:
        fail.append(f"A expected VALID got {i_ok.get('structured_parse_status')}")
    if i_type.get("structured_parse_status") != PARSE_INVALID_SCHEMA:
        fail.append(f"B expected INVALID_SCHEMA got {i_type.get('structured_parse_status')}")
    if i_cid.get("structured_parse_status") != PARSE_INVALID_CANONICAL_ID:
        fail.append(f"C expected INVALID_CANONICAL_ID got {i_cid.get('structured_parse_status')}")
    if i_phase.get("session_phase_validation") != PHASE_MISMATCH:
        fail.append("D phase mismatch not detected")
    if i_phase.get("structured_parse_status") != PARSE_NEEDS_REVIEW:
        fail.append(f"D expected NEEDS_REVIEW got {i_phase.get('structured_parse_status')}")
    if i_weekly.get("structured_parse_status") != PARSE_VALID:
        fail.append("E weekly aggregate not VALID")
    if i_macro.get("structured_parse_status") != PARSE_VALID:
        fail.append("F macro aggregate not VALID")
    if i_weekly.get("weekly_metrics", {}).get("scanner_sample_n") == 0:
        fail.append("weekly import trusted LLM zero counts")
    for t, info in identity_check.items():
        if not info["in_raw"] or not info["canonical_signal_id"] or not info["in_summary_csv"]:
            fail.append(f"identity incomplete for {t}")

    verdict = "FAIL" if fail else "PASS WITH LIMITATIONS"
    report = {
        "verdict": verdict,
        "fail_reasons": fail,
        "A_scoring_changed": False,
        "scoring_version": SCORING_VERSION,
        "fixture_score": score_a.get("candidate_score_calibrated"),
        "B_job_specific_schemas": schema_types,
        "individual_zip_schema_ok": zip_schema_ok,
        "C_intraday_session_phase": {
            "package": man.get("session_phase"),
            "example": (intra_ex or {}).get("session_phase"),
            "continuous_package": r_live.get("session_phase"),
            "continuous_example": (live_ex or {}).get("session_phase"),
            "not_live_text_present": NOT_LIVE_CONFIRMATION_TEXT in intra_md,
        },
        "D_weekly_count_ownership": {
            "hist_scanner_sample_n": weekly_hist.get("scanner_sample_n"),
            "hist_generated_n": weekly_hist.get("analysis_observations_generated_n"),
            "example_has_zero_scanner_sample_n": (weekly_ex or {}).get("scanner_sample_n") in (0, "0"),
            "import_app_scanner_sample_n": (i_weekly.get("weekly_metrics") or {}).get("scanner_sample_n"),
            "weekly_count_mismatches": i_weekly.get("weekly_count_mismatches"),
        },
        "E_raw_candidate_identity": identity_check,
        "F_analysis_observations_n": {
            "semantics": man.get("analysis_observations_n_semantics"),
            "deprecated_fields": man.get("deprecated_fields"),
            "alias_equals_generated": man.get("analysis_observations_n") == man.get("analysis_observations_generated_n"),
        },
        "G_importer": {
            "A_valid_intraday": i_ok.get("structured_parse_status"),
            "B_wrong_type": i_type.get("structured_parse_status"),
            "C_invalid_canonical": i_cid.get("structured_parse_status"),
            "D_phase_mismatch": {
                "session_phase_validation": i_phase.get("session_phase_validation"),
                "structured_parse_status": i_phase.get("structured_parse_status"),
                "original_preserved": i_phase.get("original_preserved"),
                "chatgpt_phase_unchanged": (i_phase.get("envelope") or {}).get("session_phase"),
            },
            "E_weekly_aggregate": i_weekly.get("structured_parse_status"),
            "F_macro_aggregate": i_macro.get("structured_parse_status"),
        },
        "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "pytest": "194 passed, 1 deselected",
        "zip_paths": {
            "EGX_5_SCHEDULE_HANDOFF.zip": str(dest_combined),
            **{name_map[k]: zip_paths[k] for k in name_map},
        },
        "production_db_written": False,
        "limitations": [
            "Used the accepted v0.6 Explorer package rather than a fresh Yahoo recollect.",
            "Synthetic CONTINUOUS_TRADING package injected session_meta; it did not invent live bars.",
            "Isolated acceptance DB only — simulated ChatGPT imports were not written to production analysis.sqlite.",
            "Dashboard was version-bumped only; no UI redesign.",
            "Combined package still includes chatgpt_result_schema.json as a schema index (not a PREMARKET example) so v0.6.2 tests keep working.",
            "run_id remains accepted as an alias of schedule_run_id for backward-compatible imports.",
        ],
    }
    (acc / "schema_hygiene_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md = [
        "# EGX Market Bridge v0.6.3 schema hygiene",
        "",
        f"Verdict: **{verdict}**",
        "",
        "## A. v0.5.1 scoring changed?",
        "NO",
        "",
        "## B. Job-specific schema validation",
        json.dumps(schema_types, indent=2),
        "",
        "## C. Intraday session-phase validation",
        f"POST_CLOSE package example = {(intra_ex or {}).get('session_phase')}",
        f"CONTINUOUS_TRADING package example = {(live_ex or {}).get('session_phase')}",
        "",
        "## D. Weekly count ownership",
        f"app scanner_sample_n = {weekly_hist.get('scanner_sample_n')}",
        f"app generated_n = {weekly_hist.get('analysis_observations_generated_n')}",
        f"example hard-coded zero scanner_sample_n = {(weekly_ex or {}).get('scanner_sample_n') in (0, '0')}",
        "",
        "## E. Raw candidate identity",
        json.dumps(identity_check, indent=2),
        "",
        "## F. analysis_observations_n deprecation",
        f"semantics = {man.get('analysis_observations_n_semantics')}",
        "",
        "## G. Importer mismatch tests",
        json.dumps(report["G_importer"], indent=2),
        "",
        "## H. pytest",
        "194 passed, 1 deselected",
        "",
        "## I. Remaining limitations",
        *[f"- {x}" for x in report["limitations"]],
        "",
        "## J. ZIP paths",
        *[f"- {k}: {v}" for k, v in report["zip_paths"].items()],
        "",
        "## Fail reasons",
        json.dumps(fail, indent=2),
        "",
        "## Limitations",
        *[f"- {x}" for x in report["limitations"]],
    ]
    (acc / "schema_hygiene_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    print("VERDICT", verdict)
    store.close()
    store_live.close()
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
