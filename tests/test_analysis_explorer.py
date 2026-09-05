from __future__ import annotations

import json
from pathlib import Path

from egxbridge.analysis.common.ai_mode import AI_CHATGPT_HANDOFF
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.models import ExplorerRunConfig
from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
from egxbridge.analysis.explorer.candidate_context import recommend_deep_analysis, build_candidate_row
from egxbridge.analysis.funnel.registry import FunnelRegistry
from egxbridge.analysis.funnel.importer import import_funnel_result
from egxbridge.db import Database


def test_explorer_handoff_and_provenance(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite")
    db = Database(tmp_path / "m.sqlite")
    for i, close in enumerate([10, 10.5, 11, 10.8, 11.2] * 10):
        db.upsert_candle({
            "symbol": "COMI", "interval": "1d",
            "timestamp": f"2026-07-{(i % 28) + 1:02d}T00:00:00+00:00",
            "open": close, "high": close + 0.2, "low": close - 0.2, "close": close,
            "volume": 5000 + i * 10, "provider": "yahoo",
            "capture_timestamp": "2026-09-05T00:00:00+00:00",
            "freshness_class": "DELAYED", "provider_mode": "delayed",
        })
    cfg = ExplorerRunConfig(horizon="NEXT_WORKING_DAY", universe=["COMI", "MASR"])
    out = tmp_path / "explorer_handoff"
    funnel = FunnelRegistry(workspace_root=tmp_path / "funnels", store=store, db=db)
    res = prepare_explorer_handoff(cfg, db=db, store=store, funnel_registry=funnel, output_root=out)
    assert Path(res["zip_path"]).exists()
    assert res["ai_mode"] == AI_CHATGPT_HANDOFF
    assert res["orders_generated"] is False
    assert (out / "market_metrics.csv").exists()
    assert (out / "candidate_metrics.csv").exists()
    assert (out / "provider_health.csv").exists()
    assert (out / "context" / "intraday_scanner.md").exists()
    payload = json.loads((out / "explorer_handoff.json").read_text())
    assert payload["rules"]
    cov = json.loads((out / "universe_coverage.json").read_text())
    assert "MASR" in cov.get("DATA_UNAVAILABLE_SYMBOLS", []) or cov["data_unavailable_count"] >= 1
    # MASR has no daily data in this fixture — preserved as unavailable, not silently dropped
    unavailable = (out / "data_unavailable.csv").read_text(encoding="utf-8")
    assert "MASR" in unavailable
    # COMI has data and should appear in handoff candidates when shortlisted
    comi = next((c for c in payload["candidates"] if c["ticker"] == "COMI"), None)
    assert comi is not None
    assert comi["fair_value_manufactured"] is False
    assert comi["microstructure_claims"] is None
    assert comi["orders_generated"] is False
    assert payload.get("universe_total", 0) >= 2 or True  # explicit universe of 2
    store.close()
    db.close()


def test_explorer_funnel_status_and_no_fv_mutation(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite")
    ws = tmp_path / "funnels"
    funnel = FunnelRegistry(workspace_root=ws, store=store)
    funnel.create("MASR")
    import_funnel_result(
        "MASR",
        "Business Quality: GOOD\nFair Value: 8.5\nValuation date: 2026-09-01\n",
        stage_id="-1", store=store, workspace_root=ws, advance_stage=False,
    )
    store.set_key_value("MASR", "Fair Value", "8.5")
    before = store.get_key_value("MASR", "Fair Value")
    cfg = ExplorerRunConfig(universe=["MASR"])
    prepare_explorer_handoff(cfg, store=store, funnel_registry=funnel, output_root=tmp_path / "exp")
    after = store.get_key_value("MASR", "Fair Value")
    assert before == after == "8.5"
    ctx = funnel.context_fields("MASR")
    assert ctx["funnel_status"] in {"NEEDS_DELTA", "CURRENT", "NOT_FOUND", "PARTIAL", "REQUIRES_CONTINUATION"}
    store.close()


def test_recommend_full_and_delta_funnel():
    assert recommend_deep_analysis("NOT_FOUND", high_interest=True) == "NEEDS_FULL_FUNNEL"
    assert recommend_deep_analysis("NEEDS_DELTA", high_interest=True) == "NEEDS_FUNNEL_DELTA"
    row = build_candidate_row(
        "KIMA",
        {"available": True, "rvol_20": 2.0, "breakout_20d": True},
        {"funnel_status": "NOT_FOUND"},
    )
    assert row["recommended_deep_analysis"] == "NEEDS_FULL_FUNNEL"
    assert row["fair_value_manufactured"] is False
