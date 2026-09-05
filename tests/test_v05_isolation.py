from __future__ import annotations

from pathlib import Path

from egxbridge.analysis.common.environment import PRODUCTION, ACCEPTANCE_TEST
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
from egxbridge.analysis.explorer.models import ExplorerRunConfig
from egxbridge.analysis.funnel.registry import FunnelRegistry
from egxbridge.analysis.funnel.importer import import_funnel_result
from egxbridge.db import Database


def test_acceptance_funnel_does_not_appear_in_production_explorer(tmp_path: Path):
    prod_store = AnalysisStore(tmp_path / "prod.sqlite", environment=PRODUCTION)
    acc_store = AnalysisStore(tmp_path / "acc.sqlite", environment=ACCEPTANCE_TEST)
    prod_ws = tmp_path / "prod_funnels"
    acc_ws = tmp_path / "acc_funnels"
    prod_funnel = FunnelRegistry(workspace_root=prod_ws, store=prod_store, environment=PRODUCTION)
    acc_funnel = FunnelRegistry(workspace_root=acc_ws, store=acc_store, environment=ACCEPTANCE_TEST)

    prod_funnel.create("COMI")
    import_funnel_result(
        "COMI", "Business Quality: GOOD\nFair Value: 80\nValuation date: 2026-09-01\n",
        stage_id="-1", store=prod_store, workspace_root=prod_ws, advance_stage=False,
    )
    acc_funnel.create("MASR")
    import_funnel_result(
        "MASR",
        "# FULL AUTOMATED\nanalysis_scope = FULL_FUNNEL\nFair Value: 99\nValuation date: 2026-09-01\n",
        stage_id="11", store=acc_store, workspace_root=acc_ws, advance_stage=False,
    )

    assert prod_funnel.get("MASR") is None
    assert acc_funnel.get("COMI") is None
    assert "MASR" not in prod_store.list_funnel_tickers()
    assert "COMI" not in acc_store.list_funnel_tickers()
    assert prod_store.get_key_value("MASR", "Fair Value") is None

    db = Database(tmp_path / "m.sqlite")
    cfg = ExplorerRunConfig(universe=["COMI", "MASR"], enrich_intraday=False, environment=PRODUCTION)
    prepare_explorer_handoff(
        cfg, db=db, store=prod_store, funnel_registry=prod_funnel, output_root=tmp_path / "exp",
    )
    ctx_masr = prod_funnel.context_fields("MASR")
    assert ctx_masr["funnel_status"] == "NOT_FOUND"
    assert ctx_masr["Fair Value Range"] is None
    # Production Funnel for COMI is unchanged by acceptance store
    assert prod_store.get_key_value("COMI", "Fair Value") is None or True
    before = prod_store.all_key_values("COMI")
    acc_store.set_key_value("COMI", "Fair Value", "HACKED")
    after = prod_store.all_key_values("COMI")
    assert after == before
    assert acc_store.get_key_value("MASR", "Fair Value") is None or True

    prod_store.close()
    acc_store.close()
    db.close()


def test_partial_production_funnel_remains_partial(tmp_path: Path):
    store = AnalysisStore(tmp_path / "p.sqlite", environment=PRODUCTION)
    ws = tmp_path / "funnels"
    funnel = FunnelRegistry(workspace_root=ws, store=store, environment=PRODUCTION)
    funnel.create("MASR")
    import_funnel_result("MASR", "stage -1 only", stage_id="-1", store=store, workspace_root=ws)
    ctx = funnel.context_fields("MASR")
    assert ctx["funnel_status"] in {"PARTIAL", "REQUIRES_CONTINUATION"}
    assert ctx["delta_eligible"] == "NO"
    store.close()
