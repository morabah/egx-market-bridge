#!/usr/bin/env python3
"""Acceptance packages for EGX Market Bridge v0.4.3 final workflow integrity."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from egxbridge.db import Database
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.funnel.registry import FunnelRegistry
from egxbridge.analysis.funnel.state import create_project, load_project
from egxbridge.analysis.funnel.completion import (
    compute_funnel_completion_status,
    compute_delta_eligible,
    compute_completion_basis,
    sync_completion_fields,
)
from egxbridge.analysis.funnel.importer import import_funnel_result
from egxbridge.analysis.explorer.registry import ExplorerRegistry
from egxbridge.analysis.explorer.models import ExplorerRunConfig


FULL_AUTO = """# FULL AUTOMATED FUNNEL RESULT
analysis_scope = FULL_FUNNEL
run_mode = FULL_AUTOMATED_RUN
result_type = COMPLETE_FUNNEL_RESULT

VALUATION STATUS = NOT_RELIABLE
Fair Value: not established this cycle.
Final Decision: do not establish Fair Value.
"""


def main():
    from egxbridge.analysis.common.environment import ACCEPTANCE_TEST

    db_path = HERE / "output" / "egx_bridge.sqlite"
    db = Database(db_path) if db_path.exists() else None
    store_path = HERE / "output" / "acceptance.sqlite"
    if store_path.exists():
        store_path.unlink()
    store = AnalysisStore(store_path, environment=ACCEPTANCE_TEST)
    ws = HERE / "workspace" / "acceptance" / "funnels"
    if ws.exists():
        shutil.rmtree(ws)
    funnel = FunnelRegistry(
        workspace_root=ws, store=store, db=db, environment=ACCEPTANCE_TEST,
    )
    acc = HERE / "output" / "acceptance" / "funnel"
    acc.mkdir(parents=True, exist_ok=True)

    # --- TEST A: PARTIAL INTERACTIVE (-1, 0, 11 only) ---
    create_project("MASR", root=ws, store=store)
    import_funnel_result("MASR", "# Stage -1\nScope locked.\n", stage_id="-1", store=store, workspace_root=ws)
    import_funnel_result("MASR", "# Stage 0\nBusiness map.\n", stage_id="0", store=store, workspace_root=ws)
    import_funnel_result(
        "MASR",
        "# Stage 11 Final Decision stub\nVALUATION STATUS = NOT_RELIABLE\nFair Value not established.\n",
        stage_id="11",
        store=store,
        workspace_root=ws,
        advance_stage=False,
    )
    p = load_project("MASR", ws)
    sync_completion_fields(p, store=store, workspace_root=ws)
    assert compute_funnel_completion_status(p, store=store, workspace_root=ws) == "PARTIAL"
    assert compute_delta_eligible(p, store=store, workspace_root=ws) == "NO"
    assert compute_completion_basis(p, store=store, workspace_root=ws) == "PARTIAL"
    delta_a = funnel.prepare_delta("MASR")
    assert delta_a.get("status") == "DELTA_NOT_AVAILABLE"
    (acc / "MASR_TEST_A_PARTIAL.json").write_text(json.dumps({
        "funnel_completion_status": p.funnel_completion_status,
        "delta_eligible": p.delta_eligible,
        "completion_basis": p.completion_basis,
        "verified_completed_stages": p.verified_completed_stages,
        "delta_gate": delta_a,
    }, indent=2), encoding="utf-8")
    print("TEST_A_PARTIAL_OK", p.funnel_completion_status, p.delta_eligible)

    # Stage handoffs for packaging (genuine transitions on clean project reused)
    stage = funnel.prepare_stage("MASR", stage=p.current_stage)
    shutil.copy2(stage["zip_path"], acc / "MASR_CHATGPT_FUNNEL_HANDOFF.zip")
    shutil.copy2(stage["zip_path"], acc / "MASR_STAGE_HANDOFF.zip")

    # --- TEST B: FULL AUTOMATED BASELINE ---
    ws_b = HERE / "workspace" / "acceptance" / "funnels_full"
    if ws_b.exists():
        shutil.rmtree(ws_b)
    store_b_path = HERE / "output" / "acceptance_full.sqlite"
    if store_b_path.exists():
        store_b_path.unlink()
    store_b = AnalysisStore(store_b_path, environment=ACCEPTANCE_TEST)
    funnel_b = FunnelRegistry(
        workspace_root=ws_b, store=store_b, db=db, environment=ACCEPTANCE_TEST,
    )
    create_project("MASR", root=ws_b, store=store_b, run_mode="FULL_AUTOMATED_RUN")
    import_funnel_result(
        "MASR", FULL_AUTO, store=store_b, workspace_root=ws_b,
        run_mode="FULL_AUTOMATED_RUN", advance_stage=False,
    )
    pb = load_project("MASR", ws_b)
    sync_completion_fields(pb, store=store_b, workspace_root=ws_b)
    assert compute_funnel_completion_status(pb, store=store_b, workspace_root=ws_b) == "COMPLETE"
    assert compute_completion_basis(pb, store=store_b, workspace_root=ws_b) == "FULL_AUTOMATED_VERIFIED"
    assert compute_delta_eligible(pb, store=store_b, workspace_root=ws_b) == "YES"
    delta_b = funnel_b.prepare_delta("MASR")
    assert delta_b.get("delta") is True and delta_b.get("zip_path")
    shutil.copy2(delta_b["zip_path"], acc / "MASR_DELTA_AFTER_COMPLETE.zip")
    # Also use FULL automated delta package as NEXT for distinctness check context
    shutil.copy2(delta_b["zip_path"], acc / "MASR_NEXT_STAGE_HANDOFF.zip")
    (acc / "MASR_TEST_B_FULL_AUTOMATED.json").write_text(json.dumps({
        "funnel_completion_status": pb.funnel_completion_status,
        "delta_eligible": pb.delta_eligible,
        "completion_basis": pb.completion_basis,
        "delta_ok": True,
        "zip": delta_b.get("zip_path"),
    }, indent=2), encoding="utf-8")
    print("TEST_B_FULL_AUTOMATED_OK", pb.completion_basis, pb.delta_eligible)
    print("DELTA_ELIGIBILITY_OK")

    # Yahoo daily semantics smoke via handoff market_snapshot
    pkg = Path(delta_b["package_dir"])
    snap = json.loads((pkg / "market" / "market_snapshot.json").read_text(encoding="utf-8"))
    q = snap.get("quote") or {}
    if q.get("raw_reference") and "daily_close" in str(q.get("raw_reference")):
        assert q.get("price_observation_type") == "DAILY_CLOSE"
        assert q.get("timestamp_semantics") == "DAILY_BAR"
        assert q.get("volume_semantics") == "DAILY_FINAL_VOLUME"
        print("YAHOO_DAILY_SEMANTICS_OK")
    else:
        print("YAHOO_DAILY_SEMANTICS_SKIPPED_NO_QUOTE")

    # Explorer
    explorer = ExplorerRegistry(store=store_b, db=db, funnel_registry=funnel_b)
    exp = explorer.prepare(ExplorerRunConfig(horizon="NEXT_WORKING_DAY"))
    acc_exp = HERE / "output" / "acceptance" / "explorer"
    acc_exp.mkdir(parents=True, exist_ok=True)
    shutil.copy2(exp["zip_path"], acc_exp / "EGX_EXPLORER_HANDOFF.zip")

    store.close()
    store_b.close()
    if db:
        db.close()
    print("FUNNEL_ZIP", acc / "MASR_CHATGPT_FUNNEL_HANDOFF.zip")
    print("EXPLORER_ZIP", acc_exp / "EGX_EXPLORER_HANDOFF.zip")
    print("PASS")


if __name__ == "__main__":
    main()
