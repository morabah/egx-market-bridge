"""v0.4.3 final workflow integrity tests."""
from __future__ import annotations

from pathlib import Path

from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.common.provenance import _classify_stored_quote, bridge_market_evidence
from egxbridge.analysis.funnel.state import create_project, load_project, save_project
from egxbridge.analysis.funnel.importer import import_funnel_result
from egxbridge.analysis.funnel.delta import prepare_delta_handoff
from egxbridge.analysis.funnel.handoff import prepare_funnel_handoff
from egxbridge.analysis.funnel.models import FUNNEL_STAGES
from egxbridge.analysis.funnel.completion import (
    sync_completion_fields,
    compute_funnel_completion_status,
    compute_delta_eligible,
    compute_completion_basis,
    FUNNEL_COMPLETION_PARTIAL,
    FUNNEL_COMPLETION_COMPLETE,
    FUNNEL_COMPLETION_NOT_STARTED,
    DELTA_ELIGIBLE_NO,
    DELTA_ELIGIBLE_YES,
    COMPLETION_BASIS_FULL_AUTOMATED,
    COMPLETION_BASIS_INTERACTIVE,
    COMPLETION_BASIS_PARTIAL,
    COMPLETION_BASIS_NONE,
    REQUIRED_INTERACTIVE_STAGES,
)
from egxbridge.db import Database


FULL_AUTO_BODY = """# FULL AUTOMATED FUNNEL RESULT
analysis_scope = FULL_FUNNEL
run_mode = FULL_AUTOMATED_RUN
result_type = COMPLETE_FUNNEL_RESULT

VALUATION STATUS = NOT_RELIABLE
Fair Value: not established this cycle.
Final Decision: do not establish Fair Value.
"""


def _import_all_interactive(ticker: str, store, ws: Path):
    for sid in REQUIRED_INTERACTIVE_STAGES:
        if sid == "11":
            body = (
                f"# Stage {sid} Final Decision\n"
                "VALUATION STATUS = NOT_RELIABLE\n"
                "Fair Value: not established.\n"
                "Final Decision recorded.\n"
            )
        else:
            body = f"# Stage {sid} result\nStage {sid} completed with real imported content.\n"
        import_funnel_result(
            ticker, body, stage_id=sid, store=store, workspace_root=ws, advance_stage=False,
        )


def test_claimed_stages_cannot_establish_complete(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    p = create_project("MASR", root=ws, store=store)
    p.completed_stages = list(FUNNEL_STAGES)
    p.claimed_completed_stages = list(FUNNEL_STAGES)
    save_project(p, root=ws, store=store)
    sync_completion_fields(p, store=store, workspace_root=ws)
    assert compute_funnel_completion_status(p, store=store, workspace_root=ws) == FUNNEL_COMPLETION_NOT_STARTED
    assert compute_delta_eligible(p, store=store, workspace_root=ws) == DELTA_ELIGIBLE_NO
    assert compute_completion_basis(p, store=store, workspace_root=ws) == COMPLETION_BASIS_NONE
    store.close()


def test_partial_interactive_stage_m1_0_11_only(tmp_path: Path):
    """TEST A — Stage -1 + 0 + 11 only remains PARTIAL."""
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    create_project("MASR", root=ws, store=store)
    import_funnel_result("MASR", "# Stage -1\nScope.\n", stage_id="-1", store=store, workspace_root=ws)
    import_funnel_result("MASR", "# Stage 0\nBusiness.\n", stage_id="0", store=store, workspace_root=ws)
    import_funnel_result(
        "MASR",
        "# Stage 11 Final Decision\nVALUATION STATUS = NOT_RELIABLE\nFair Value not established.\n",
        stage_id="11",
        store=store,
        workspace_root=ws,
        advance_stage=False,
    )
    p = load_project("MASR", ws)
    sync_completion_fields(p, store=store, workspace_root=ws)
    assert compute_funnel_completion_status(p, store=store, workspace_root=ws) == FUNNEL_COMPLETION_PARTIAL
    assert compute_delta_eligible(p, store=store, workspace_root=ws) == DELTA_ELIGIBLE_NO
    assert compute_completion_basis(p, store=store, workspace_root=ws) == COMPLETION_BASIS_PARTIAL
    res = prepare_delta_handoff(p, store=store, workspace_root=ws, output_root=tmp_path / "out")
    assert res["status"] == "DELTA_NOT_AVAILABLE"
    store.close()


def test_verified_interactive_all_stages_complete(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    create_project("MASR", root=ws, store=store)
    _import_all_interactive("MASR", store, ws)
    p = load_project("MASR", ws)
    sync_completion_fields(p, store=store, workspace_root=ws)
    assert compute_funnel_completion_status(p, store=store, workspace_root=ws) == FUNNEL_COMPLETION_COMPLETE
    assert compute_completion_basis(p, store=store, workspace_root=ws) == COMPLETION_BASIS_INTERACTIVE
    assert compute_delta_eligible(p, store=store, workspace_root=ws) == DELTA_ELIGIBLE_YES
    res = prepare_delta_handoff(p, store=store, workspace_root=ws, output_root=tmp_path / "out")
    assert res.get("delta") is True
    req = Path(res["package_dir"], "funnel_request.md").read_text(encoding="utf-8")
    assert "CURRENT OPERATION = DELTA" in req or "CURRENT OPERATION: **DELTA**" in req
    assert "CURRENT STAGE (underlying Funnel state)" in req
    proj = __import__("json").loads(Path(res["package_dir"], "project_state.json").read_text())
    assert proj.get("current_operation") == "DELTA"
    assert proj.get("current_stage") != "DELTA"
    store.close()


def test_full_automated_baseline_complete_and_delta(tmp_path: Path):
    """TEST B — tagged FULL_AUTOMATED_RUN establishes COMPLETE."""
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    create_project("MASR", root=ws, store=store, run_mode="FULL_AUTOMATED_RUN")
    import_funnel_result(
        "MASR", FULL_AUTO_BODY, store=store, workspace_root=ws,
        run_mode="FULL_AUTOMATED_RUN", advance_stage=False,
    )
    p = load_project("MASR", ws)
    sync_completion_fields(p, store=store, workspace_root=ws)
    assert compute_funnel_completion_status(p, store=store, workspace_root=ws) == FUNNEL_COMPLETION_COMPLETE
    assert compute_completion_basis(p, store=store, workspace_root=ws) == COMPLETION_BASIS_FULL_AUTOMATED
    assert compute_delta_eligible(p, store=store, workspace_root=ws) == DELTA_ELIGIBLE_YES
    res = prepare_delta_handoff(p, store=store, workspace_root=ws, output_root=tmp_path / "out")
    assert res.get("delta") is True
    assert Path(res["zip_path"]).exists()
    store.close()


def test_yahoo_daily_close_semantics():
    q = _classify_stored_quote({
        "provider": "yahoo",
        "last": 7.98,
        "volume": 1000,
        "raw_reference": "yahoo:MASR.CA:daily_close",
        "provider_timestamp": "2026-09-02T21:00:00+00:00",
        "capture_timestamp": "2026-09-05T00:00:00+00:00",
    })
    assert q["price_observation_type"] == "DAILY_CLOSE"
    assert q["timestamp_semantics"] == "DAILY_BAR"
    assert q["volume_semantics"] == "DAILY_FINAL_VOLUME"
    assert q["volume_interval"] == "1d"


def test_actual_quote_observation_remains_quote():
    q = _classify_stored_quote({
        "provider": "egid",
        "last": 10.0,
        "bid": 9.9,
        "ask": 10.1,
        "raw_reference": "egid:quote",
        "provider_timestamp": "2026-09-03T12:00:00+00:00",
    })
    assert q["price_observation_type"] == "LIVE_QUOTE"
    assert q["timestamp_semantics"] == "QUOTE_OBSERVATION"


def test_yahoo_daily_in_bridge_evidence(tmp_path: Path):
    db = Database(tmp_path / "m.sqlite")
    db.insert_quote({
        "symbol": "MASR", "provider": "yahoo", "last": 7.98,
        "volume": 1e6, "provider_timestamp": "2026-09-02T21:00:00+00:00",
        "capture_timestamp": "2026-09-05T00:00:00+00:00",
        "freshness_class": "STALE_EXPECTED", "provider_mode": "delayed",
        "raw_reference": "yahoo:MASR.CA:daily_close",
    })
    db.upsert_candle({
        "symbol": "MASR", "interval": "1d",
        "timestamp": "2026-09-02T21:00:00+00:00",
        "normalized_utc_timestamp": "2026-09-02T21:00:00+00:00",
        "normalized_cairo_timestamp": "2026-09-03T00:00:00+03:00",
        "session_date": "2026-09-03",
        "open": 7.5, "high": 8.0, "low": 7.4, "close": 7.98, "volume": 1e6,
        "provider": "yahoo",
        "capture_timestamp": "2026-09-05T00:00:00+00:00",
        "freshness_class": "STALE_EXPECTED",
        "price_observation_type": "DAILY_CLOSE",
        "volume_semantics": "DAILY_FINAL_VOLUME",
        "timestamp_semantics": "DAILY_BAR",
    })
    ev = bridge_market_evidence(db, "MASR")
    q = ev["quote"]
    assert q["price_observation_type"] == "DAILY_CLOSE"
    assert q["timestamp_semantics"] == "DAILY_BAR"
    assert q["volume_semantics"] == "DAILY_FINAL_VOLUME"
    db.close()


def test_delta_operation_separate_from_stage(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    create_project("MASR", root=ws, store=store)
    import_funnel_result(
        "MASR", FULL_AUTO_BODY, store=store, workspace_root=ws,
        run_mode="FULL_AUTOMATED_RUN", advance_stage=False,
    )
    p = load_project("MASR", ws)
    underlying = p.current_stage
    res = prepare_delta_handoff(p, store=store, workspace_root=ws, output_root=tmp_path / "out")
    assert res.get("delta") is True
    proj = __import__("json").loads(Path(res["package_dir"], "project_state.json").read_text())
    assert proj["current_operation"] == "DELTA"
    assert proj["current_stage"] == underlying
    assert proj["current_stage"] != "DELTA"
    store.close()
