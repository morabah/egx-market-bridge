#!/usr/bin/env python3
"""Offline v0.7.1 acceptance; all databases are temporary ACCEPTANCE_TEST stores."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.common.environment import ACCEPTANCE_TEST
from egxbridge.analysis.forward_validation import validation_report
from egxbridge.analysis.schedule.session import (
    PRE_OPEN_END, CONTINUOUS_END, CLOSING_AUCTION_END, TRADING_AT_LAST_END,
    classify_session_phase,
)
from egxbridge.analysis.schedule.outcomes import completed_through
from egxbridge.ui.versions import version_labels
from test_v070_forward_validation import freeze
from test_v071_operational_integrity import (
    BOUNDARIES, VALUATION, OLD_AUDIT, ARCHIVED_AUDIT, CURRENT_AUDIT, cairo_at, valuation_case,
)

EVIDENCE_KIND = "SYNTHETIC_ACCEPTANCE_NOT_PRODUCTION"
OUTPUT = ROOT / "output/acceptance/v071"
FILES_CHANGED = """.github/workflows/tests.yml
ARCHITECTURE.md
README.md
dashboard.py
docs/FORWARD_VALIDATION.md
docs/OPERATIONAL_INTEGRITY.md
egxbridge/__init__.py
egxbridge/analysis/__init__.py
egxbridge/analysis/common/ai_mode.py
egxbridge/analysis/forward_validation.py
egxbridge/analysis/funnel/completion.py
egxbridge/analysis/funnel/importer.py
egxbridge/analysis/funnel/schema.py
egxbridge/analysis/schedule/outcomes.py
egxbridge/analysis/schedule/session.py
egxbridge/freshness.py
egxbridge/ui/actions.py
prompts/README.md
scripts/acceptance_v071.py
tests/fixtures/v071_frozen_sources.json
tests/test_v064_daily_operator.py
tests/test_v06_schedule.py
tests/test_v071_operational_integrity.py""".splitlines() + [OLD_AUDIT + " → " + ARCHIVED_AUDIT, CURRENT_AUDIT]


def write_json(name, payload):
    (OUTPUT / name).write_text(json.dumps({"evidence_kind": EVIDENCE_KIND, **payload},
        indent=2, ensure_ascii=False, default=str, allow_nan=False) + "\n", encoding="utf-8")


def source_checks():
    baseline = json.loads((ROOT / "tests/fixtures/v071_frozen_sources.json").read_text())
    results = {}
    for name, expected in baseline.items():
        path = ARCHIVED_AUDIT if name == OLD_AUDIT else name
        actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest() if (ROOT / path).is_file() else None
        results[name] = {"current_path": path, "before": expected, "after": actual, "unchanged": actual == expected}
    return results


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    tested = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, text=True, capture_output=True)
    (OUTPUT / "pytest.txt").write_text(tested.stdout + tested.stderr, encoding="utf-8")
    print(tested.stdout.strip(), flush=True)
    pytest_result = (tested.stdout.strip().splitlines() or [tested.stderr])[-1]
    labels = version_labels(environment=ACCEPTANCE_TEST)
    frozen = source_checks()
    write_json("frozen_source_hashes.json", {"files": frozen})
    boundaries = [{"cairo_timestamp": cairo_at(clock).isoformat(), "expected": phase,
        "actual": classify_session_phase(cairo_at(clock))} for clock, phase in BOUNDARIES]
    weekends = [{"cairo_timestamp": cairo_at("12:00:00", day).isoformat(), "expected": "POST_CLOSE",
        "actual": classify_session_phase(cairo_at("12:00:00", day))} for day in ("2026-09-04", "2026-09-05")]
    completed = [{"cairo_timestamp": cairo_at(clock).isoformat(), "expected": expected,
        "actual": completed_through(cairo_at(clock))} for clock, expected in (
            ("14:29:59", "2026-09-05"), ("14:30:00", "2026-09-06"))]
    before = {"PRE_OPEN_END": [10, 0], "CONTINUOUS_END": [14, 20],
        "CLOSING_AUCTION_END": [14, 30], "TRADING_AT_LAST_END": [14, 45]}
    after = dict(zip(before, (PRE_OPEN_END, CONTINUOUS_END, CLOSING_AUCTION_END, TRADING_AT_LAST_END)))
    write_json("session_boundary_report.json", {"timezone": "Africa/Cairo", "constants_before": before,
        "constants_after": after, "boundaries": boundaries, "weekends": weekends, "completed_through": completed,
        "interpretation": "Configured normal cash-market clock bands, not a live exchange calendar/feed; no holiday guessing.",
        "pre_edit_timing_inventory": {"operational_lines": 9, "preserved_historical_output_lines": 243,
            "operational_owners": ["egxbridge/analysis/schedule/session.py", "egxbridge/freshness.py"],
            "derived_outcomes": "completed_through imports TRADING_AT_LAST_END"}})

    cases, case_errors = {}, {}
    with tempfile.TemporaryDirectory(prefix="egx-v071-acceptance-") as temp:
        folder = Path(temp)
        inputs = {
            "A_structured_only": (VALUATION, ""),
            "B_legacy_only": ({}, "Fair Value: 35\nValuation date: 2026-09-06"),
            "C_conflict": (VALUATION, "Fair Value: 40"),
            "D_horizon_price": ({**VALUATION, "expected_horizon_market_price": 43,
                "economic_terminal_value": 47, "robust_fv_range": "32–41", "expected_return_spread": "POSITIVE"}, ""),
            "partial_no_date": ({"central_fv": 37}, ""),
            "partial_no_fv": ({"expected_horizon_market_price": 43}, ""),
        }
        for name, (fields, prose) in inputs.items():
            try:
                cases[name] = valuation_case(folder / name, fields, prose, environment=ACCEPTANCE_TEST)
            except Exception as exc:
                case_errors[name] = str(exc)
        store = AnalysisStore(folder / "forward.sqlite", environment=ACCEPTANCE_TEST)
        freeze(store)
        signals = validation_report(store)["signals"]
        decision_fields = {"final_decision", "fresh_capital_test", "price_implied_expectations",
            "expectations_gap", "expectations_revision_outlook"}
        no_local_decision = bool(signals) and all(not (decision_fields & set(s)) for s in signals)
        production_not_opened = store.environment == ACCEPTANCE_TEST and all(
            c["environment"] == ACCEPTANCE_TEST and c["forward_signal_n"] == 0 for c in cases.values())
        store.close()
        write_json("funnel_v28_valuation_persistence_report.json", {"cases": cases, "errors": case_errors,
            "production_not_opened": production_not_opened,
            "temporary_database_paths": "All paths in examples were isolated under a deleted temporary directory."})

    current_audit = (ROOT / CURRENT_AUDIT).read_text() if (ROOT / CURRENT_AUDIT).is_file() else ""
    concepts = ["Intrinsic Value", "Central/PW Fair Value", "Robust Fair Value Range", "Highest Credible Bull FV",
        "Price-Implied Expectations", "Expectations Burden", "Expectations Gap", "Expectations Revision Outlook",
        "Expectations Revision Confidence", "Catalyst Revision Potential", "Information-Reaction Regime",
        "Rerating Attribution", "Economic Terminal Value", "Expected Horizon Market Price", "Expected Return Spread",
        "Value-Creating Growth", "Fresh Capital Test", "Economic Quality", "Expectations Revision Edge",
        "Risk-Adjusted Return", "Opportunity Cost", "Final domain-separated conclusion"]
    audit = {"historical_path": ARCHIVED_AUDIT, "current_path": CURRENT_AUDIT,
        "historical_unchanged": frozen[OLD_AUDIT]["unchanged"], "obsolete_root_asset_absent": not (ROOT / OLD_AUDIT).exists(),
        "current_present": bool(current_audit), "concept_coverage": {c: c in current_audit for c in concepts},
        "automatic_packaging": False, "ownership_document": "prompts/README.md"}
    write_json("stage12_versioning_report.json", audit)

    a = cases.get("A_structured_only", {})
    c = cases.get("C_conflict", {})
    d = cases.get("D_horizon_price", {})
    ap = a.get("result", {}).get("project", {})
    cp = c.get("result", {}).get("project", {})
    dp = d.get("result", {}).get("project", {})
    conflicts = c.get("result", {}).get("valuation_diagnostics", [])
    checks = {
        "A_application_071": labels["application_version"] == "0.7.1",
        "B_workflow_071": labels["workflow_version"] == "0.7.1",
        "C_funnel_28": labels["funnel_prompt_version"] == "2.8",
        "D_scanner_051": labels["scoring_version"] == "0.5.1" and labels["score_kind"] == "HEURISTIC_UNCALIBRATED",
        "E_data_031": labels["market_data_schema_version"] == "0.3.1",
        "F_exact_session_boundaries": all(r["expected"] == r["actual"] for r in boundaries + weekends),
        "G_completed_through_boundary": all(r["expected"] == r["actual"] for r in completed),
        "H_structured_only_persistence": ap.get("structured_fields", {}).get("central_fv") == 37 and
            ap.get("last_valuation_date") == "2026-09-06" and ap.get("valuation_status") == "UPDATED" and
            a.get("persisted_keys", {}).get("Fair Value") == "37.0" and bool(a.get("history")) and a.get("raw_preserved") is True,
        "I_structured_wins_explicit_conflict": cp.get("structured_fields", {}).get("central_fv") == 37 and
            c.get("persisted_keys", {}).get("Fair Value") == "37.0" and any(
                x["code"] == "VALUATION_SOURCE_CONFLICT" and x["structured_value"] == 37 and x["legacy_text_value"] == 40
                for x in conflicts) and c.get("raw_preserved") is True,
        "J_horizon_price_separate": dp.get("structured_fields", {}).get("central_fv") == 37 and
            dp.get("structured_fields", {}).get("expected_horizon_market_price") == 43 and
            d.get("persisted_keys", {}).get("Fair Value") == "37.0",
        "K_partial_not_complete": len(cases) == len(inputs) and all(
            x["result"]["project"]["funnel_completion_status"] != "COMPLETE" and x["result"]["project"]["delta_eligible"] == "NO"
            for x in cases.values()),
        "L_historical_master_preserved": frozen["prompts/EGX_STOCK_ANALYSIS_FUNNEL_v2.7.md"]["unchanged"],
        "M_current_master_preserved": frozen["EGX_STOCK_ANALYSIS_FUNNEL_v2.8.md"]["unchanged"],
        "N_historical_audit_archived": audit["historical_unchanged"] and audit["obsolete_root_asset_absent"],
        "O_current_audit_present": audit["current_present"] and all(audit["concept_coverage"].values()),
        "P_forward_validation_regressions": tested.returncode == 0,
        "Q_frozen_sources": all(r["unchanged"] for name, r in frozen.items() if name.startswith("egxbridge/")),
        "R_no_automatic_final_decision": no_local_decision and labels["ai_mode"] == "CHATGPT_HANDOFF",
        "pytest": tested.returncode == 0, "no_case_errors": not case_errors,
        "production_not_opened": production_not_opened,
        "CI_workflow_present": (ROOT / ".github/workflows/tests.yml").is_file(),
    }
    license_files = [p.name for p in ROOT.iterdir() if p.is_file() and (p.name.upper().startswith("LICENSE") or p.name.upper().startswith("COPYING"))]
    limitations = [
        "GitHub-hosted Python 3.11/3.12 execution awaits push/PR; this report records the local Python " + platform.python_version() + " run.",
        "No exchange holiday calendar or live session feed was added; clock bands cannot prove an actual session occurred.",
        "External live-network integration tests remain excluded by pytest.ini; no provider/broker/LLM credentials were used.",
        "No production validation records were enrolled or fabricated; all examples are synthetic and isolated.",
        "Stage-12 audits remain manually selected assets; no new automatic packaging workflow was added.",
    ]
    if not license_files:
        limitations.insert(0, "LICENSE_DECISION_REQUIRED = YES; no license selected by this patch.")
    status = "PASS WITH LIMITATIONS" if all(checks.values()) else "FAIL"
    report = {
        "1_files_changed": FILES_CHANGED, "2_versions": labels, "3_session_constants": {"before": before, "after": after},
        "4_session_boundary_tests": {"exact_bands": boundaries, "weekends": weekends}, "5_completed_through": completed,
        "6_structured_valuation": "Central FV, valid date/status, history and existing readers updated from normalized fields; optional fields retained.",
        "7_source_conflicts": "Structured valuation wins; legacy extraction, diagnostics and complete raw response retained.",
        "8_completion_regression": checks["K_partial_not_complete"], "9_v27_audit": ARCHIVED_AUDIT,
        "10_v28_audit": CURRENT_AUDIT, "11_scanner_source_changed": "NO" if checks["Q_frozen_sources"] else "YES",
        "12_canonical_identity_changed": "NO" if frozen["egxbridge/analysis/schedule/identity.py"]["unchanged"] else "YES",
        "13_forward_validation_regression": checks["P_forward_validation_regressions"], "14_pytest": pytest_result,
        "15_acceptance_v071": status, "16_CI_workflow": ".github/workflows/tests.yml",
        "17_license": {"existing_files_preserved": license_files, "LICENSE_DECISION_REQUIRED": "NO" if license_files else "YES"},
        "18_limitations": limitations,
    }
    write_json("operational_integrity_acceptance.json", {"status": status, "checks": checks, "report": report})
    lines = [f"# EGX Market Bridge v0.7.1 — {status}", "", EVIDENCE_KIND, "",
        "All databases were temporary ACCEPTANCE_TEST stores. Production tables were not opened.", ""]
    for key, value in report.items():
        lines += [f"## {key.replace('_', ' ')}", ""]
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            lines += [f"- {item}" for item in value]
        elif isinstance(value, (list, dict)):
            lines += ["```json", json.dumps(value, indent=2, ensure_ascii=False, default=str), "```"]
        else:
            lines.append(str(value))
        lines.append("")
    lines += ["", "## Acceptance checks", ""] + [f"- {key}: {value}" for key, value in checks.items()]
    (OUTPUT / "operational_integrity_acceptance.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
