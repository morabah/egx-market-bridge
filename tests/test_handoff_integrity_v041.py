"""v0.4.1 handoff integrity regression tests."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from egxbridge.analysis.common.candle_export import enrich_candle_row, timing_safe_candles, LEGACY_UNNORMALIZED
from egxbridge.analysis.common.provenance import bridge_market_evidence
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.funnel.state import create_project, load_project
from egxbridge.analysis.funnel.handoff import prepare_funnel_handoff
from egxbridge.analysis.funnel.delta import prepare_delta_handoff
from egxbridge.analysis.funnel.importer import import_funnel_result
from egxbridge.analysis.funnel.completion import (
    compute_funnel_completion_status,
    compute_delta_eligible,
    FUNNEL_COMPLETION_PARTIAL,
    FUNNEL_COMPLETION_COMPLETE,
    DELTA_ELIGIBLE_NO,
    DELTA_ELIGIBLE_YES,
)
from egxbridge.db import Database


def test_tradingview_cairo_naive_to_normalized_utc():
    row = enrich_candle_row({
        "symbol": "MASR",
        "interval": "5m",
        "provider": "tradingview",
        "timestamp": "2026-09-03T14:25:00+00:00",
        "open": 7.9, "high": 8.0, "low": 7.8, "close": 7.95, "volume": 1000,
        "capture_timestamp": "2026-09-05T00:00:00+00:00",
    })
    assert row["normalized_cairo_timestamp"] == "2026-09-03T14:25:00+03:00"
    assert row["normalized_utc_timestamp"] == "2026-09-03T11:25:00+00:00"
    assert row["timestamp_utc"] == "2026-09-03T11:25:00+00:00"
    assert row["timestamp"] == "2026-09-03T11:25:00+00:00"
    assert row["timestamp_normalization_status"] == "NORMALIZED"
    assert row["session_date"] == "2026-09-03"
    assert row.get("provider_timezone_if_known") == "Africa/Cairo"


def test_legacy_unnormalized_excluded_from_timing():
    rows = timing_safe_candles([
        {
            "symbol": "X", "interval": "5m", "provider": "unknown_feed",
            "timestamp": "not-a-timestamp", "close": 1.0, "volume": 1,
            "capture_timestamp": "2026-09-05T00:00:00+00:00",
        },
        {
            "symbol": "X", "interval": "5m", "provider": "tradingview",
            "timestamp": "2026-09-03T14:25:00+00:00", "close": 1.0, "volume": 1,
            "capture_timestamp": "2026-09-05T00:00:00+00:00",
        },
    ])
    assert len(rows) == 1
    assert rows[0]["normalized_utc_timestamp"] == "2026-09-03T11:25:00+00:00"
    assert all(r["timestamp_normalization_status"] != LEGACY_UNNORMALIZED for r in rows)


def test_handoff_preserves_semantics_and_session(tmp_path: Path):
    ws = tmp_path / "funnels"
    out = tmp_path / "out"
    store = AnalysisStore(tmp_path / "a.sqlite")
    db = Database(tmp_path / "m.sqlite")
    # Yahoo daily session 2026-09-03
    db.upsert_candle({
        "symbol": "MASR", "interval": "1d",
        "timestamp": "2026-09-02T21:00:00+00:00",
        "normalized_utc_timestamp": "2026-09-02T21:00:00+00:00",
        "normalized_cairo_timestamp": "2026-09-03T00:00:00+03:00",
        "provider_raw_timestamp": "2026-09-03 00:00:00+03:00",
        "provider_timezone_if_known": "Africa/Cairo",
        "session_date": "2026-09-03",
        "timestamp_semantics": "DAILY_BAR",
        "volume_semantics": "DAILY_FINAL_VOLUME",
        "price_observation_type": "DAILY_CLOSE",
        "open": 7.5, "high": 8.0, "low": 7.4, "close": 7.98, "volume": 1e6,
        "provider": "yahoo",
        "capture_timestamp": "2026-09-05T00:00:00+00:00",
        "freshness_class": "STALE_EXPECTED",
    })
    # Legacy TV 14:25 mislabeled UTC
    db.upsert_candle({
        "symbol": "MASR", "interval": "5m",
        "timestamp": "2026-09-03T14:25:00+00:00",
        "open": 7.9, "high": 8.0, "low": 7.8, "close": 7.95, "volume": 1000,
        "provider": "tradingview",
        "capture_timestamp": "2026-09-05T00:00:00+00:00",
        "freshness_class": "DELAYED",
    })
    p = create_project("MASR", root=ws, store=store)
    res = prepare_funnel_handoff(p, db=db, store=store, workspace_root=ws, output_root=out)
    pkg = Path(res["package_dir"])
    assert res["latest_completed_market_session"] == "2026-09-03"
    assert res["session_date"] == "2026-09-03"
    assert res["execution_grade"] == "NO"
    assert isinstance(res["research_data_quality_score"], float)
    assert isinstance(res["execution_data_quality_score"], float)

    # market/ path consistency
    assert (pkg / "market" / "daily_candles.csv").exists()
    assert (pkg / "market" / "intraday_candles.csv").exists()
    assert (pkg / "market" / "data_quality.json").exists()
    readme = (pkg / "README.md").read_text(encoding="utf-8")
    assert "market/" in readme

    dq = json.loads((pkg / "market" / "data_quality.json").read_text())
    assert dq["research_data_quality_score"] is not None
    assert dq["research_data_quality_grade"]
    assert dq["execution_data_quality_score"] is not None
    assert dq["execution_grade"] == "NO"
    assert dq["latest_completed_market_session"] == "2026-09-03"

    # Intraday TV 14:25 Cairo → 11:25 UTC
    with (pkg / "market" / "intraday_candles.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    tv = [r for r in rows if r.get("provider") == "tradingview"]
    assert tv
    assert any(r.get("normalized_utc_timestamp") == "2026-09-03T11:25:00+00:00" for r in tv)
    assert any(r.get("normalized_cairo_timestamp") == "2026-09-03T14:25:00+03:00" for r in tv)
    assert any(r.get("timestamp_semantics") for r in tv)
    assert any(r.get("volume_semantics") for r in tv)
    assert any(r.get("price_observation_type") for r in tv)
    assert any(r.get("session_date") == "2026-09-03" for r in tv)

    prov = json.loads((pkg / "market" / "provider_provenance.json").read_text())
    assert "timestamp_normalization_status" in (prov.get("intraday") or [{}])[0]
    assert "timestamp_semantics" in (prov.get("intraday") or [{}])[0]

    man = json.loads((pkg / "manifest.json").read_text())
    assert man["latest_session"] == "2026-09-03"
    store.close()
    db.close()


def test_partial_funnel_not_delta_eligible(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    p = create_project("MASR", root=ws, store=store)
    import_funnel_result("MASR", "# Stage -1\nScope locked.\n", stage_id="-1", store=store, workspace_root=ws)
    p2 = load_project("MASR", ws)
    assert compute_funnel_completion_status(p2, store=store, workspace_root=ws) == FUNNEL_COMPLETION_PARTIAL
    assert compute_delta_eligible(p2, store=store, workspace_root=ws) == DELTA_ELIGIBLE_NO
    assert p2.valuation_status != "UPDATED"

    res = prepare_delta_handoff(p2, store=store, workspace_root=ws, output_root=tmp_path / "out")
    assert res["status"] == "DELTA_NOT_AVAILABLE"
    assert res["reason"] == "REQUIRES_FULL_BUILD"
    assert res["delta_eligible"] == "NO"
    assert res.get("zip_path") is None
    store.close()


def test_complete_baseline_delta_works(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    p = create_project("MASR", root=ws, store=store)
    import_funnel_result(
        "MASR",
        "# FULL\nanalysis_scope = FULL_FUNNEL\nrun_mode = FULL_AUTOMATED_RUN\n"
        "result_type = COMPLETE_FUNNEL_RESULT\nVALUATION STATUS = NOT_RELIABLE\n"
        "Fair Value: not established.\nFinal Decision.\n",
        store=store,
        workspace_root=ws,
        run_mode="FULL_AUTOMATED_RUN",
        advance_stage=False,
    )
    p = load_project("MASR", ws)
    assert compute_funnel_completion_status(p, store=store, workspace_root=ws) == FUNNEL_COMPLETION_COMPLETE
    assert compute_delta_eligible(p, store=store, workspace_root=ws) == DELTA_ELIGIBLE_YES

    store.set_key_value("MASR", "Fair Value", "9.5", source_stage="5")
    res = prepare_delta_handoff(p, store=store, workspace_root=ws, output_root=tmp_path / "out")
    assert res.get("status") == "OK"
    assert res["delta"] is True
    assert Path(res["zip_path"]).exists()
    prev = json.loads(Path(res["package_dir"], "previous_funnel_summary.json").read_text())
    assert prev["critical_values"]["Fair Value"] == "9.5"
    assert prev["funnel_completion_status"] == "COMPLETE"
    assert prev["delta_eligible"] == "YES"
    store.close()


def test_no_valuation_updated_without_fair_value(tmp_path: Path):
    ws = tmp_path / "funnels"
    store = AnalysisStore(tmp_path / "a.sqlite")
    create_project("MASR", root=ws, store=store)
    import_funnel_result(
        "MASR",
        "# Stage -1\nFair Value: not established yet\n",
        stage_id="-1",
        store=store,
        workspace_root=ws,
    )
    p = load_project("MASR", ws)
    assert p.last_valuation_date is None
    assert p.valuation_status != "UPDATED"
    # With FV but no valuation date → NOT_ESTABLISHED
    import_funnel_result(
        "MASR",
        "# Stage 5\nFair Value: 12.5\n",
        stage_id="5",
        store=store,
        workspace_root=ws,
        advance_stage=False,
    )
    p2 = load_project("MASR", ws)
    assert p2.valuation_status == "NOT_ESTABLISHED"
    # With both → UPDATED
    import_funnel_result(
        "MASR",
        "# Stage 5\nFair Value: 12.5\nValuation date: 2026-09-03\n",
        stage_id="5",
        store=store,
        workspace_root=ws,
        advance_stage=False,
    )
    p3 = load_project("MASR", ws)
    assert p3.valuation_status == "UPDATED"
    assert p3.last_valuation_date == "2026-09-03"
    store.close()


def test_evidence_excludes_legacy_from_freshness_inputs(tmp_path: Path):
    db = Database(tmp_path / "m.sqlite")
    db.upsert_candle({
        "symbol": "MASR", "interval": "1d",
        "timestamp": "2026-09-02T21:00:00+00:00",
        "open": 1, "high": 1, "low": 1, "close": 7.98, "volume": 100,
        "provider": "yahoo",
        "capture_timestamp": "2026-09-05T00:00:00+00:00",
        "freshness_class": "STALE_EXPECTED",
    })
    ev = bridge_market_evidence(db, "MASR")
    assert ev["latest_completed_market_session"] == "2026-09-03"
    assert all(
        r.get("timestamp_normalization_status") == "NORMALIZED"
        for r in (ev.get("daily_candles_timing_safe") or [])
    )
    db.close()
