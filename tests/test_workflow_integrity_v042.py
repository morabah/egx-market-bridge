"""v0.4.2 workflow integrity + explorer coverage tests."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from egxbridge.analysis.common.candle_export import enrich_candle_row
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.funnel.state import create_project, load_project, save_project
from egxbridge.analysis.funnel.handoff import prepare_funnel_handoff
from egxbridge.analysis.funnel.delta import prepare_delta_handoff
from egxbridge.analysis.funnel.importer import import_funnel_result
from egxbridge.analysis.funnel.completion import (
    compute_funnel_completion_status,
    compute_delta_eligible,
    sync_completion_fields,
    sanitize_fair_value,
    FUNNEL_COMPLETION_COMPLETE,
    FUNNEL_COMPLETION_PARTIAL,
    FUNNEL_COMPLETION_NOT_STARTED,
    DELTA_ELIGIBLE_NO,
    DELTA_ELIGIBLE_YES,
)
from egxbridge.analysis.funnel.registry import FunnelRegistry
from egxbridge.analysis.explorer.prescreen import normalize_scanner_metrics, select_handoff_candidates
from egxbridge.analysis.explorer.universe import build_explorer_universe
from egxbridge.analysis.explorer.candidate_context import recommend_deep_analysis, build_candidate_row
from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
from egxbridge.analysis.explorer.models import ExplorerRunConfig
from egxbridge.db import Database
from egxbridge.scanner import compute_scanner_metrics


def test_canonical_timestamp_not_legacy():
    row = enrich_candle_row({
        "symbol": "MASR", "interval": "5m", "provider": "tradingview",
        "timestamp": "2026-09-03T14:25:00+00:00",
        "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1,
        "capture_timestamp": "2026-09-05T00:00:00+00:00",
    })
    assert row["timestamp"] == "2026-09-03T11:25:00+00:00"
    assert row["timestamp_utc"] == "2026-09-03T11:25:00+00:00"
    assert row["legacy_unnormalized_timestamp"] == "2026-09-03T14:25:00+00:00"
    assert row["normalized_cairo_timestamp"] == "2026-09-03T14:25:00+03:00"


def test_fake_completed_stages_not_complete(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    p = create_project("MASR", root=ws, store=store)
    p.completed_stages = ["-1", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
    save_project(p, root=ws, store=store)
    sync_completion_fields(p, store=store, workspace_root=ws)
    assert compute_funnel_completion_status(p, store=store, workspace_root=ws) == FUNNEL_COMPLETION_NOT_STARTED
    assert compute_delta_eligible(p, store=store, workspace_root=ws) == DELTA_ELIGIBLE_NO
    assert not (p.funnel_completion_status == "COMPLETE" and p.delta_eligible == "YES")
    store.close()


def test_real_stage11_import_enables_delta(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    create_project("MASR", root=ws, store=store)
    import_funnel_result("MASR", "# Stage -1\nScope.\n", stage_id="-1", store=store, workspace_root=ws)
    p = load_project("MASR", ws)
    assert compute_funnel_completion_status(p, store=store, workspace_root=ws) == FUNNEL_COMPLETION_PARTIAL
    assert compute_delta_eligible(p, store=store, workspace_root=ws) == DELTA_ELIGIBLE_NO
    res = prepare_delta_handoff(p, store=store, workspace_root=ws, output_root=tmp_path / "out")
    assert res["status"] == "DELTA_NOT_AVAILABLE"

    # Stage 11 alone (with -1) is still PARTIAL — not a complete interactive Funnel
    import_funnel_result(
        "MASR",
        "# Stage 11 Final Decision\nVALUATION STATUS = NOT_RELIABLE\nFair Value not established.\n",
        stage_id="11",
        store=store,
        workspace_root=ws,
        advance_stage=False,
    )
    p2 = load_project("MASR", ws)
    sync_completion_fields(p2, store=store, workspace_root=ws)
    assert compute_funnel_completion_status(p2, store=store, workspace_root=ws) == FUNNEL_COMPLETION_PARTIAL
    assert compute_delta_eligible(p2, store=store, workspace_root=ws) == DELTA_ELIGIBLE_NO

    # FULL_AUTOMATED tagged result establishes COMPLETE
    import_funnel_result(
        "MASR",
        "# FULL\nanalysis_scope = FULL_FUNNEL\nrun_mode = FULL_AUTOMATED_RUN\n"
        "result_type = COMPLETE_FUNNEL_RESULT\nVALUATION STATUS = NOT_RELIABLE\nFinal Decision.\n",
        store=store,
        workspace_root=ws,
        run_mode="FULL_AUTOMATED_RUN",
        advance_stage=False,
    )
    p3 = load_project("MASR", ws)
    sync_completion_fields(p3, store=store, workspace_root=ws)
    assert compute_funnel_completion_status(p3, store=store, workspace_root=ws) == FUNNEL_COMPLETION_COMPLETE
    assert compute_delta_eligible(p3, store=store, workspace_root=ws) == DELTA_ELIGIBLE_YES
    res2 = prepare_delta_handoff(p3, store=store, workspace_root=ws, output_root=tmp_path / "out2")
    assert res2.get("delta") is True
    store.close()


def test_stage_transition_handoffs_distinct(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    db = Database(tmp_path / "m.sqlite")
    create_project("MASR", root=ws, store=store)
    out = tmp_path / "out"
    r1 = prepare_funnel_handoff(
        load_project("MASR", ws), db=db, store=store, workspace_root=ws, output_root=out / "a",
        run_mode="INTERACTIVE_STAGE_BY_STAGE", stage="-1",
    )
    import_funnel_result("MASR", "STAGE_M1_BODY", stage_id="-1", store=store, workspace_root=ws)
    r2 = prepare_funnel_handoff(
        load_project("MASR", ws), db=db, store=store, workspace_root=ws, output_root=out / "b",
        run_mode="INTERACTIVE_STAGE_BY_STAGE", stage="0",
    )
    import_funnel_result("MASR", "STAGE_0_BODY", stage_id="0", store=store, workspace_root=ws)
    r3 = prepare_funnel_handoff(
        load_project("MASR", ws), db=db, store=store, workspace_root=ws, output_root=out / "c",
        run_mode="INTERACTIVE_STAGE_BY_STAGE", stage="0.5",
    )
    p1 = json.loads(Path(r1["package_dir"], "project_state.json").read_text())
    p2 = json.loads(Path(r2["package_dir"], "project_state.json").read_text())
    p3 = json.loads(Path(r3["package_dir"], "project_state.json").read_text())
    assert p1["current_stage"] == "-1" and p1["completed_stages"] == []
    assert p2["current_stage"] == "0" and p2["completed_stages"] == ["-1"]
    assert p3["current_stage"] == "0.5" and p3["completed_stages"] == ["-1", "0"]
    texts = "\n".join(
        f.read_text(encoding="utf-8")
        for f in (Path(r3["package_dir"]) / "previous_stage_results").glob("*.md")
    )
    assert "STAGE_M1_BODY" in texts and "STAGE_0_BODY" in texts
    assert Path(r1["zip_path"]).read_bytes() != Path(r2["zip_path"]).read_bytes()
    assert Path(r2["zip_path"]).read_bytes() != Path(r3["zip_path"]).read_bytes()
    store.close()
    db.close()


def test_breakout_false_preserved():
    candles = []
    for i in range(30):
        candles.append({
            "timestamp": f"2026-08-{(i % 28) + 1:02d}T00:00:00+00:00",
            "open": 10, "high": 12, "low": 9, "close": 10.5, "volume": 1000,
            "normalized_utc_timestamp": f"2026-08-{(i % 28) + 1:02d}T00:00:00+00:00",
        })
    # last close below high_20 → breakout False
    candles[-1]["close"] = 10.0
    candles[-1]["high"] = 10.1
    m = compute_scanner_metrics(candles)
    assert m["breakout_flag_20d"] is False
    assert m["breakout_20d"] is False
    n = normalize_scanner_metrics({"breakout_flag_20d": False, "breakout_flag_60d": False, "available": True})
    assert n["breakout_20d"] is False
    assert n["breakout_60d"] is False
    row = build_candidate_row("X", n, {"funnel_status": "NOT_FOUND"})
    assert row["breakout_20d"] is False


def test_placeholder_fv_sanitized():
    assert sanitize_fair_value("PLACEHOLDER_PENDING") is None
    assert sanitize_fair_value("9.5") == "9.5"


def test_explorer_partial_status_continue_funnel(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    funnel = FunnelRegistry(workspace_root=ws, store=store)
    funnel.create("MASR")
    import_funnel_result("MASR", "partial only", stage_id="-1", store=store, workspace_root=ws)
    ctx = funnel.context_fields("MASR")
    assert ctx["funnel_status"] in {"PARTIAL", "REQUIRES_CONTINUATION"}
    assert ctx["delta_eligible"] == "NO"
    assert recommend_deep_analysis(ctx["funnel_status"]) == "CONTINUE_FUNNEL"
    store.set_key_value("MASR", "Fair Value", "PLACEHOLDER_PENDING")
    ctx2 = funnel.context_fields("MASR")
    assert ctx2["Fair Value Range"] is None
    store.close()


def test_explorer_universe_not_hardcoded_ten(tmp_path: Path):
    uni = build_explorer_universe(None)
    assert uni["UNIVERSE_TOTAL"] > 10
    assert len(uni["MAPPED_SYMBOLS"]) > 10
    assert uni["data_eligible_count"] == 0
    assert len(uni["DATA_UNAVAILABLE_SYMBOLS"]) == uni["EQUITY_UNIVERSE_TOTAL"]


def test_explorer_two_stage_and_unavailable(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite")
    db = Database(tmp_path / "m.sqlite")
    for i, close in enumerate([10, 10.5, 11, 10.8, 11.2] * 15):
        db.upsert_candle({
            "symbol": "COMI", "interval": "1d",
            "timestamp": f"2026-07-{(i % 28) + 1:02d}T00:00:00+00:00",
            "normalized_utc_timestamp": f"2026-07-{(i % 28) + 1:02d}T00:00:00+00:00",
            "normalized_cairo_timestamp": f"2026-07-{(i % 28) + 1:02d}T02:00:00+03:00",
            "open": close, "high": close + 0.2, "low": close - 0.2, "close": close,
            "volume": 5000 + i * 10, "provider": "yahoo",
            "capture_timestamp": "2026-09-05T00:00:00+00:00",
            "freshness_class": "DELAYED",
            "session_date": f"2026-07-{(i % 28) + 1:02d}",
        })
    funnel = FunnelRegistry(workspace_root=tmp_path / "funnels", store=store, db=db)
    res = prepare_explorer_handoff(
        ExplorerRunConfig(horizon="NEXT_WORKING_DAY"),
        db=db, store=store, funnel_registry=funnel, output_root=tmp_path / "exp",
    )
    assert res["universe_total"] > 10
    assert res["data_eligible_count"] >= 1
    assert res["orders_generated"] is False
    assert (tmp_path / "exp" / "universe_coverage.json").exists()
    assert (tmp_path / "exp" / "prescreen_stage_a.json").exists()
    assert (tmp_path / "exp" / "data_unavailable.csv").exists()
    cov = json.loads((tmp_path / "exp" / "universe_coverage.json").read_text())
    assert "MASR" in cov["DATA_UNAVAILABLE_SYMBOLS"] or "DATA_UNAVAILABLE" in str(cov)
    # COMI should be eligible
    assert "COMI" in cov["DATA_AVAILABLE_SYMBOLS"]
    store.close()
    db.close()
