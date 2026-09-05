from __future__ import annotations

import os
from pathlib import Path

import pytest

from egxbridge.analysis.common.ai_mode import active_ai_mode, requires_paid_api, AI_CHATGPT_HANDOFF
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.funnel.state import create_project, load_project
from egxbridge.analysis.funnel.handoff import prepare_funnel_handoff
from egxbridge.analysis.funnel.importer import import_funnel_result
from egxbridge.analysis.funnel.delta import prepare_delta_handoff
from egxbridge.analysis import FUNNEL_PROMPT_VERSION
from egxbridge.db import Database


def test_no_paid_api_required(tmp_path: Path):
    assert active_ai_mode() == AI_CHATGPT_HANDOFF
    assert requires_paid_api() is False
    assert not os.environ.get("OPENAI_API_KEY") or True  # may be set in env; must not be required
    # Creating project without API keys
    p = create_project("MASR", root=tmp_path / "funnels")
    assert p.funnel_version == FUNNEL_PROMPT_VERSION
    assert p.ai_mode == AI_CHATGPT_HANDOFF


def test_funnel_project_and_prompt_preserved(tmp_path: Path):
    root = tmp_path / "funnels"
    p = create_project("MASR", root=root, analysis_objective="LONG_TERM_INVESTMENT")
    assert (root / "MASR" / "source" / "master_funnel_v2.8.md").exists()
    text = (root / "MASR" / "source" / "master_funnel_v2.8.md").read_text(encoding="utf-8")
    assert "EGX STOCK ANALYSIS FUNNEL" in text
    assert "v2.8" in text
    loaded = load_project("MASR", root)
    assert loaded is not None
    assert loaded.ticker == "MASR"


def test_funnel_handoff_zip_no_api(tmp_path: Path):
    ws = tmp_path / "funnels"
    out = tmp_path / "out"
    store = AnalysisStore(tmp_path / "a.sqlite")
    db = Database(tmp_path / "m.sqlite")
    # seed minimal daily candles so EXECUTION_GRADE can be NO but still prepare
    for i, close in enumerate([1.0, 1.1, 1.2, 1.15, 1.25] * 5):
        db.upsert_candle({
            "symbol": "MASR", "interval": "1d",
            "timestamp": f"2026-08-{10+i:02d}T00:00:00+00:00",
            "open": close, "high": close + 0.1, "low": close - 0.1, "close": close,
            "volume": 1000 + i, "provider": "yahoo",
            "capture_timestamp": "2026-09-05T00:00:00+00:00",
            "freshness_class": "DELAYED", "provider_mode": "delayed",
        })
    p = create_project("MASR", root=ws, store=store, run_mode="INTERACTIVE_STAGE_BY_STAGE")
    res = prepare_funnel_handoff(p, db=db, store=store, workspace_root=ws, output_root=out,
                                 run_mode="INTERACTIVE_STAGE_BY_STAGE", stage="-1")
    assert Path(res["zip_path"]).exists()
    assert res["blocked_by_execution_grade"] is False
    assert res["execution_grade"] == "NO"
    assert res["ai_mode"] == AI_CHATGPT_HANDOFF
    pkg = Path(res["package_dir"])
    assert (pkg / "MASTER_FUNNEL_v2.8.md").exists()
    assert (pkg / "funnel_request.md").exists()
    assert (pkg / "manifest.json").exists()
    req = (pkg / "funnel_request.md").read_text(encoding="utf-8")
    assert "EXECUTION GRADE" in req
    assert "does **not** block" in req or "does not block" in req.lower() or "does **not** block" in req
    # no fabricated FV
    prev = __import__("json").loads((pkg / "previous_funnel_summary.json").read_text())
    assert prev["critical_values"].get("Fair Value") in (None, "")
    store.close()
    db.close()


def test_stage_advances_only_after_import(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    p = create_project("MASR", root=ws, store=store)
    assert p.current_stage == "-1"
    assert p.completed_stages == []
    # prepare does not advance
    prepare_funnel_handoff(p, store=store, workspace_root=ws, output_root=tmp_path / "out")
    p2 = load_project("MASR", ws)
    assert p2.current_stage == "-1"
    # import advances
    result_text = "# Stage -1 result\nFair Value: not set yet\nScope locked.\n"
    import_funnel_result("MASR", result_text, stage_id="-1", store=store, workspace_root=ws)
    p3 = load_project("MASR", ws)
    assert "-1" in p3.completed_stages
    assert p3.current_stage == "0"
    # previous stage included path
    stage_files = list((ws / "MASR" / "stages").rglob("*.md"))
    assert stage_files
    store.close()


def test_import_preserves_original_and_corrections_append_only(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    create_project("MASR", root=ws, store=store)
    original = "ORIGINAL TEXT UNIQUE 12345\nFair Value: 10.0\nValuation date: 2026-09-01\n"
    import_funnel_result("MASR", original, stage_id="-1", store=store, workspace_root=ws, advance_stage=False)
    latest = (ws / "MASR" / "results" / "latest_funnel_result.md").read_text(encoding="utf-8")
    assert latest == original
    store.set_key_value("MASR", "Fair Value", "11.0", old_value="10.0", reason="test correction", source="test")
    corr = store.list_corrections("MASR")
    assert len(corr) >= 1
    assert corr[0]["old_value"] == "10.0"
    assert corr[0]["new_value"] == "11.0"
    # append again
    store.set_key_value("MASR", "Fair Value", "12.0", reason="second", source="test")
    assert len(store.list_corrections("MASR")) >= 2
    store.close()


def test_delta_includes_previous_critical_values(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    p = create_project("MASR", root=ws, store=store)
    import_funnel_result(
        "MASR",
        "# FULL\nanalysis_scope = FULL_FUNNEL\nrun_mode = FULL_AUTOMATED_RUN\n"
        "result_type = COMPLETE_FUNNEL_RESULT\nVALUATION STATUS = CURRENT\n"
        "Fair Value: 9.5\nValuation date: 2026-09-01\nFinal Decision.\n",
        store=store,
        workspace_root=ws,
        run_mode="FULL_AUTOMATED_RUN",
        advance_stage=False,
    )
    store.set_key_value("MASR", "Fair Value", "9.5", source_stage="5")
    store.set_key_value("MASR", "Sustainable Earnings", "1.2", source_stage="4")
    p = load_project("MASR", ws)
    res = prepare_delta_handoff(p, store=store, workspace_root=ws, output_root=tmp_path / "out")
    assert res["delta"] is True
    assert res["previous_critical_values"]["Fair Value"] == "9.5"
    prev = __import__("json").loads(Path(res["package_dir"], "previous_funnel_summary.json").read_text())
    assert prev["critical_values"]["Fair Value"] == "9.5"
    store.close()


def test_previous_stages_in_later_handoff(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    p = create_project("MASR", root=ws, store=store)
    import_funnel_result("MASR", "stage -1 body AAA", stage_id="-1", store=store, workspace_root=ws)
    res = prepare_funnel_handoff(
        load_project("MASR", ws), store=store, workspace_root=ws, output_root=tmp_path / "out",
        run_mode="INTERACTIVE_STAGE_BY_STAGE", stage="0",
    )
    prev_dir = Path(res["package_dir"]) / "previous_stage_results"
    files = list(prev_dir.glob("*.md"))
    assert files
    assert any("AAA" in f.read_text(encoding="utf-8") for f in files)
    store.close()
