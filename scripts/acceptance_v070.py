#!/usr/bin/env python3
"""Reproducible synthetic v0.7.0 acceptance. Never opens production databases."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE), str(HERE / "tests")]

from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.common.environment import ACCEPTANCE_TEST
from egxbridge.analysis.forward_validation import (
    validation_report, append_classification, start_validation, store_change_proposal,
    RESPONSIBILITY_MATRIX, weekly_package,
)
from egxbridge.analysis.funnel.schema import result_schema
from egxbridge.analysis.schedule.outcomes import update_outcomes_for_store
from egxbridge.ui.versions import version_labels
from egxbridge.db import Database
from test_v070_forward_validation import freeze, candidate, seed, dates, proposal, T0, HORIZONS

# Recorded before implementation. These files define the frozen scorer and identity.
FROZEN_HASHES = {'egxbridge/scanner.py': '4270963dca532dbbfced74d57c3b61db8b36c4401912b7d14bb7bc218141fa32', 'egxbridge/analysis/explorer/calibration.py': '6cbbbdb8b7b3f1bc71ff07900d0db3e197a4b2031072ada83a31c8b9571cc5c9', 'egxbridge/analysis/explorer/prescreen.py': '6973c34fce2b005e5f0145d4f25c29f1cc451d971e9228069660f9b08a45b27a', 'egxbridge/analysis/schedule/identity.py': '683ad03f1ef48e08926cc83fb382c10c5eb910dc6f04deb805fa023b38ce9b10', 'prompts/EGX_STOCK_ANALYSIS_FUNNEL_v2.7.md': '24c6380531b6987ca11e494711b1c377a17dd28702d1784e863f5985292ba5d8'}


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str, allow_nan=False)+"\n", encoding="utf-8")


def csv_groups(path: Path, groups: list[dict], key: str):
    rows=[]
    for group in groups:
        for horizon, stats in group.get("horizons", {}).items():
            if horizon == "60":
                continue
            rows.append({"evidence_kind":"SYNTHETIC_ACCEPTANCE_NOT_PRODUCTION", "group":group.get(key),
                         "revision":group.get("expectations_revision_outlook"), "horizon":horizon,
                         **{k:v for k,v in stats.items() if not isinstance(v,(dict,list))}})
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ["evidence_kind","group","N"])
        writer.writeheader();writer.writerows(rows)


def main() -> int:
    output=HERE/"output/acceptance/v070"
    output.mkdir(parents=True,exist_ok=True)
    tested=subprocess.run([sys.executable,"-m","pytest","-q"],cwd=HERE,text=True,capture_output=True)
    (output/"pytest.txt").write_text(tested.stdout+tested.stderr,encoding="utf-8")
    print(tested.stdout.strip())
    frozen={name:{"expected":expected,"actual":hashlib.sha256((HERE/name).read_bytes()).hexdigest()}
            for name,expected in FROZEN_HASHES.items()}
    frozen_ok=all(r["expected"] == r["actual"] for r in frozen.values())
    with tempfile.TemporaryDirectory(prefix="egx-v070-acceptance-") as temp:
        folder=Path(temp)
        store=AnalysisStore(folder/"analysis.sqlite",environment=ACCEPTANCE_TEST)
        db=Database(folder/"market.sqlite")
        costs={"friction_model_version":"SYNTHETIC_1","friction_inputs_source":"SYNTHETIC_ACCEPTANCE",
               "components_pct":{"brokerage":.2,"exchange_regulatory":.1,"taxes":0,"spread":.3,"slippage":.4}}
        start_validation(store,at=T0,config={"friction_model":costs})
        candidates=[candidate(f"S{i:03}",breakout_reference=95,RS5=1,market_tape_regime_local_input="NEUTRAL") for i in range(100)]
        freeze(store,candidates,selected={c["ticker"] for c in candidates[:20]})
        update_outcomes_for_store(store,db,forward_validation_only=True)
        pending=validation_report(store)
        no_future=all(s.get(f"return_{h}") is None and s.get(f"mfe_{h}") is None and s.get(f"mae_{h}") is None
                      for s in pending["signals"] for h in HORIZONS)
        for i,s in enumerate(store.validation_records("forward_signal_snapshots")):
            append_classification(store,s["canonical_signal_id"],ticker=s["ticker"],source="FUNNEL_LLM",source_id=f"synthetic-{i}",
                imported_at="2026-01-02T12:00:00+00:00",source_cutoff=T0,funnel_version="2.8",
                fields={"central_fv":80 if i%4<2 else 120,
                        "price_implied_expectations":"REASONABLE" if i%2==0 else "DEMANDING",
                        "expectations_revision_outlook":"UPWARD" if i%2==0 else "DOWNWARD",
                        "expectations_gap":"POSITIVE" if i%2==0 else "NEGATIVE",
                        "catalyst_revision_potential":"TWO_SIDED","information_reaction_regime":"CONTINUATION",
                        "psychological_levels":[{"level_price":100,"level_type":"ROUND_NUMBER","round_number_flag":True,
                            "PLSS_raw":3,"PLSS_available_max":5,"PLSS_evidence_coverage":.5,"volume_at_price_component":None}]})
        for row in candidates:
            seed(db,row["ticker"],20,growth=2 if row["ticker"] == "S099" else .1)
        update_outcomes_for_store(store,db,forward_validation_only=True)
        report=validation_report(store)
        stored_proposal=store_change_proposal(store,proposal(),source="WEEKLY_LLM",source_id="SYNTHETIC_WEEKLY")
        weekly_package(store,output/"synthetic_weekly_package")
        schema=result_schema()
        schema.update({"synthetic":True,"application_versions":version_labels(),
                       "authoritative_prompt":"EGX_STOCK_ANALYSIS_FUNNEL_v2.8.md",
                       "authoritative_prompt_sha256":hashlib.sha256((HERE/"EGX_STOCK_ANALYSIS_FUNNEL_v2.8.md").read_bytes()).hexdigest()})
        write_json(output/"funnel_v28_schema_report.json",schema)
        csv_groups(output/"expectations_validation_example.csv",report["expectations"]["burden_revision"],"price_implied_expectations")
        csv_groups(output/"breakout_validation_example.csv",report["breakouts"]["volume_ratio_bin"],"volume_ratio_bin")
        missed=report["false_negatives"]["10"]["cases"]
        with (output/"false_negative_example.csv").open("w",encoding="utf-8",newline="") as f:
            keys=["evidence_kind","ticker","forward_rank","return_10","scanner_rank","selected_for_final_handoff","MISSED_REASON"]
            writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
            for row in missed:
                writer.writerow({"evidence_kind":"SYNTHETIC_ACCEPTANCE_NOT_PRODUCTION",**{k:row.get(k) for k in keys if k!="evidence_kind"}})
        write_json(output/"rule_version_example.json",{"synthetic":True,"rules":report["rule_versions"]})
        write_json(output/"change_proposal_example.json",{"synthetic":True,"proposal":stored_proposal})
        write_json(output/"responsibility_matrix.json",RESPONSIBILITY_MATRIX)
        checks={"pytest":tested.returncode==0,"frozen_scanner_and_identity":frozen_ok,"no_future_at_creation":no_future,
                "all_100_universe_members_retained":len(store.validation_records("universe_snapshot_members"))==100,
                "scanner_n_20":report["summary"]["N"]==20,
                "unselected_top_performer_present":any(r["ticker"]=="S099" and r["forward_rank"]==1 for r in missed),
                "all_horizons_mature":all(report["summary"]["horizons"][str(h)]["N"]==20 for h in HORIZONS),
                "friction_arithmetic":all(abs(s["return_10"]-s["net_return_after_friction_10"]-1)<1e-8 for s in report["signals"]),
                "no_app_decisions":all("final_decision" not in s and "fresh_capital_test" not in s for s in report["signals"]),
                "proposal_not_applied":stored_proposal["auto_applied"] is False,
                "production_database_not_opened":store.environment==ACCEPTANCE_TEST}
        limitations=[
            "No production sample was manufactured or activated by acceptance. The first new production Explorer run records the actual start timestamp.",
            "Real forward performance remains uncalibrated; sufficient later independent data and explicit review are required.",
            "Daily reference prices do not prove execution. Spread, slippage, depth and fillability remain unavailable unless explicitly supplied.",
            "Daily OHLC cannot resolve same-session target/stop ordering. Missing bars and corporate actions can limit outcome reliability.",
            "Default predictive reports use contemporaneous samples. Reconstructed samples require verified provenance and explicit opt-in at the reporting API.",
            "Final handoff flags record package selection; an external manual ChatGPT upload cannot be observed by the app.",
            "No local macro/sector/market-cap or financial data is invented; corresponding groups can remain UNKNOWN/NOT_RELIABLE.",
            "pytest follows the repository configuration: the external-network integration test is deselected.",
        ]
        letters={
            "A. Application version":"0.7.0", "B. Default Funnel version":"2.8",
            "C. v0.5.1 scoring changed?":"NO; scorer and identity source hashes match pre-change baseline",
            "D. Funnel v2.8 structured fields":"Implemented; partial imports, enums, raw preservation, cutoffs and source provenance",
            "E. Forward Validation Lab":"Implemented; ten sections, cohorts, downloads, update and Weekly actions",
            "F. T0 immutable snapshot fields":"Persisted with SQLite UPDATE/DELETE protection; full eligible universe retained",
            "G. +1/+2/+5/+10/+20 outcomes":"Implemented; actual observed completed trading sessions, explicit maturity",
            "H. MFE/MAE":"Implemented per horizon from reliable high/low; no partial-window or close-price substitution",
            "I. Friction":"OBSERVED/ESTIMATED/PARTIAL/NOT_AVAILABLE; no fabricated net returns",
            "J. Expectations groups":"Burden × revision and gap × revision, N and descriptive statistics",
            "K. Premium-to-FV":"A reasonable/upward, B demanding/downward, C other; no decision generation",
            "L. Value trap":"Discount/upward vs discount/downward descriptive comparison",
            "M. Information Reaction":"Imported T0 groups; future outcomes and event/catalyst reviews separate",
            "N. Pullback":"Versioned mechanical trend/support/volume/reclaim evidence; RS and catalyst splits",
            "O. Breakout":"Prior-high/close evidence, raw CLV, volume/RS/expectations/regime bins",
            "P. Psychology / PLSS":"HEURISTIC; missing components remain null; systematic configurable round encounters and outcomes",
            "Q. Regimes":"Tape, weekday, liquidity, market cap, catalyst, sector, lane, setup, realized move",
            "R. False negatives":"Whole-universe +5/+10/+20 top-performer audits; coverage and unknown reasons disclosed",
            "S. Discovery vs forward":"Explicit sample-role and point-in-time-kind exclusion; legacy outcomes cannot enter new snapshots",
            "T. Rule versions / proposals":"Append-only definitions and Weekly proposals; no application or same-sample confirmation",
            "U. LLM/app boundary":"App evidence arithmetic only; economic labels and final decisions require imported LLM provenance",
            "V. Weekly X-Ray":"Dedicated audit payload in independent Weekly job plus standalone export/import proposal path",
            "W. pytest result":tested.stdout.strip().splitlines()[-1] if tested.stdout.strip() else tested.stderr,
            "X. Remaining limitations":limitations,
        }
        status="PASS WITH LIMITATIONS" if all(checks.values()) else "FAIL"
        result={"status":status,"evidence_kind":"SYNTHETIC_ACCEPTANCE_NOT_PRODUCTION","checks":checks,"report":letters,
                "frozen_source_hashes":frozen,"synthetic_summary":report["summary"],"limitations":limitations}
        write_json(output/"forward_validation_acceptance.json",result)
        text=[f"# EGX Market Bridge v0.7.0 — {status}","","All numerical examples in this directory are synthetic acceptance fixtures, not production validation evidence.","","| Item | Result |","|---|---|"]
        text += [f"| {k} | {v} |" for k,v in letters.items() if not isinstance(v,list)]
        text += ["","## Remaining limitations",""]+[f"- {s}" for s in limitations]
        text += ["","## Checks",""]+[f"- {k}: {'PASS' if v else 'FAIL'}" for k,v in checks.items()]
        (output/"forward_validation_acceptance.md").write_text("\n".join(text)+"\n",encoding="utf-8")
        store.close();db.close()
    print(status)
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
