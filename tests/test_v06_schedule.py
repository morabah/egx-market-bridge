"""v0.6 schedule integration, PIT snapshots, outcomes — scoring_version frozen at 0.5.1."""
from __future__ import annotations

from pathlib import Path
import json

from egxbridge.analysis.common.environment import UNIT_TEST
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.calibration import (
    LONG_HORIZON_CAP, SAT_SCALE_6M, MOVE_PENALTY, VOL_PENALTY,
    CLEAN_PULLBACK_MIN, PREBREAKOUT_NEAR, SCORING_VERSION, SCORE_KIND,
    calibrate_candidate,
)
from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
from egxbridge.analysis.explorer.intraday_select import (
    select_intraday_enrichment, LANE_A, LANE_B, LANE_C, LANE_D, quality_ok,
    scale_lane_slots,
)
from egxbridge.analysis.explorer.models import ExplorerRunConfig
from egxbridge.analysis.funnel.registry import FunnelRegistry
from egxbridge.analysis.schedule.decisions import build_daily_decision
from egxbridge.analysis.schedule.handoff import prepare_schedule_handoffs
from egxbridge.analysis.schedule.importer import import_schedule_result
from egxbridge.analysis.schedule.metrics import calibration_status_for_n
from egxbridge.analysis.schedule.outcomes import (
    compute_outcomes, unique_trading_sessions, sessions_after, update_outcomes_for_store,
)
from egxbridge.analysis.schedule.session import classify_session_phase
from egxbridge.analysis.schedule.snapshots import (
    build_signal_snapshot, persist_snapshots, snapshots_have_no_future_bars, snapshot_id,
)
from egxbridge.analysis.schedule.types import ANALYSIS_PREMARKET, ANALYSIS_EXPLORER, SCORING_VERSION as SS
from egxbridge.db import Database
from egxbridge.scanner import compute_scanner_metrics


def _cand(ticker, lane, quality, score, **kwargs):
    row = {
        "ticker": ticker,
        "candidate_lane": lane,
        "FORWARD_SETUP_QUALITY": quality,
        "candidate_score_calibrated": score,
        "available": True,
    }
    row.update(kwargs)
    return row


def test_v051_scoring_constants_frozen():
    assert SCORING_VERSION == "0.5.1"
    assert SS == "0.5.1"
    assert SCORE_KIND == "HEURISTIC_UNCALIBRATED"
    assert LONG_HORIZON_CAP == 4.0
    assert SAT_SCALE_6M == 40.0
    assert MOVE_PENALTY["EXTREME"] == 18.0
    assert VOL_PENALTY["EXTREME"] == 8.0
    assert CLEAN_PULLBACK_MIN == -12.0
    assert PREBREAKOUT_NEAR == -2.0
    a = calibrate_candidate({
        "available": True, "daily_return_pct": 1, "return_1w_pct": 2, "return_1m_pct": 4,
        "return_3m_pct": 8, "return_6m_pct": 12, "rvol_20": 1.4, "dist_from_20d_high_pct": -3,
        "last_close": 10, "sma_20": 9.7, "sma_50": 9.4, "breakout_20d": False, "breakout_60d": False,
        "realized_vol_20d_ann_pct": 32, "bars": 80,
    })
    b = calibrate_candidate({
        "available": True, "daily_return_pct": 1, "return_1w_pct": 2, "return_1m_pct": 4,
        "return_3m_pct": 8, "return_6m_pct": 12, "rvol_20": 1.4, "dist_from_20d_high_pct": -3,
        "last_close": 10, "sma_20": 9.7, "sma_50": 9.4, "breakout_20d": False, "breakout_60d": False,
        "realized_vol_20d_ann_pct": 32, "bars": 80,
    })
    assert a["candidate_score_calibrated"] == b["candidate_score_calibrated"]


def test_intraday_selection_not_all_lane_a():
    rows = [_cand(f"A{i}", LANE_A, "STRONG", 80 - i) for i in range(12)]
    rows += [_cand(f"C{i}", LANE_C, "GOOD", 70 - i) for i in range(4)]
    rows += [_cand(f"B{i}", LANE_B, "GOOD", 65 - i) for i in range(2)]
    sel = select_intraday_enrichment(rows, 15)
    lanes = {r["intraday_selection_lane"] for r in sel}
    assert LANE_C in lanes
    assert LANE_B in lanes
    assert not all(r["intraday_selection_lane"] == LANE_A for r in sel)
    tickers = [r["ticker"] for r in sel]
    assert any(t.startswith("C") for t in tickers)
    assert any(t.startswith("B") for t in tickers)


def test_intraday_does_not_force_empty_lane_or_weak_fill():
    rows = [_cand(f"A{i}", LANE_A, "STRONG", 80 - i) for i in range(15)]
    rows.append(_cand("WEAKB", LANE_B, "WEAK", 10))
    sel = select_intraday_enrichment(rows, 15)
    assert all(r["ticker"] != "WEAKB" for r in sel)
    assert all(r["intraday_selection_lane"] == LANE_A for r in sel)


def test_intraday_leftover_flows_to_strongest():
    rows = [_cand(f"A{i}", LANE_A, "STRONG", 90 - i) for i in range(10)]
    rows.append(_cand("B1", LANE_B, "GOOD", 50))
    sel = select_intraday_enrichment(rows, 10)
    tickers = [r["ticker"] for r in sel]
    assert "B1" in tickers
    assert "A0" in tickers
    leftover = [r for r in sel if r["intraday_selection_reason"].startswith("leftover")]
    assert leftover


def test_intraday_selection_does_not_change_calibrated_scores():
    rows = [
        _cand("X", LANE_A, "STRONG", 77.15, extra=1),
        _cand("Y", LANE_C, "GOOD", 66.0),
    ]
    before = {r["ticker"]: r["candidate_score_calibrated"] for r in rows}
    select_intraday_enrichment(rows, 2)
    after = {r["ticker"]: r["candidate_score_calibrated"] for r in rows}
    assert before == after


def test_funnel_coverage_equities_only_excludes_index(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    db = Database(tmp_path / "m.sqlite")
    for i in range(60):
        day = 1 + i
        month = 1 + (day - 1) // 28
        d = (day - 1) % 28 + 1
        ts = f"2026-{month:02d}-{d:02d}T00:00:00+00:00"
        close = 10 + (i % 5) * 0.1
        db.upsert_candle({
            "symbol": "COMI", "interval": "1d", "timestamp": ts,
            "normalized_utc_timestamp": ts, "open": close, "high": close + 0.2,
            "low": close - 0.2, "close": close, "volume": 4000,
            "provider": "yahoo", "capture_timestamp": "2026-09-05T00:00:00+00:00",
            "session_date": ts[:10],
        })
    funnel = FunnelRegistry(workspace_root=tmp_path / "funnels", store=store, db=db, environment=UNIT_TEST)
    out = tmp_path / "exp"
    res = prepare_explorer_handoff(
        ExplorerRunConfig(universe=["COMI", "MASR", "EGX30", "KASABF"], enrich_intraday=False, environment=UNIT_TEST),
        db=db, store=store, funnel_registry=funnel, output_root=out,
    )
    counts = res["counts"]
    assert counts["UNIVERSE_TOTAL"] == 4
    assert counts["EQUITY_UNIVERSE_TOTAL"] == 2
    assert counts["funnel_coverage_scope"] == "EQUITY_UNIVERSE_TOTAL"
    assert counts["funnel_coverage_denominator"] == 2
    assert counts["funnel_coverage_n"] == 2
    fc = json.loads((out / "funnel_coverage.json").read_text())
    assert sum(int(v) for v in fc.values()) == 2
    fcsv = (out / "funnel_context.csv").read_text(encoding="utf-8")
    assert "EGX30" not in fcsv
    assert "KASABF" not in fcsv
    uni = (out / "universe.csv").read_text(encoding="utf-8")
    assert "EGX30" in uni
    assert "KASABF" in uni
    store.close()
    db.close()


def test_snapshot_immutable_against_later_market_and_funnel(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    cand = {
        "ticker": "RAYA", "candidate_score_calibrated": 78.4, "forward_setup_score": 80,
        "FORWARD_SETUP_QUALITY": "STRONG", "MOVE_ALREADY_REALIZED": "LOW",
        "candidate_lane": LANE_A, "last_close": 2.5, "funnel_status": "NOT_FOUND",
        "metrics": {"last_close": 2.5, "rvol_20": 3.3},
        "TECHNICAL_HISTORY_INTEGRITY": "NOT_VERIFIED",
    }
    snap = build_signal_snapshot(
        cand, run_id="run1", environment=UNIT_TEST, generated_at="2026-09-05T10:00:00+00:00",
        latest_session="2026-09-03",
        session_meta={"analysis_timestamp_utc": "2026-09-05T10:00:00+00:00",
                      "analysis_timestamp_cairo": "2026-09-05T13:00:00+03:00",
                      "session_phase": "POST_CLOSE"},
    )
    assert snap["scoring_version"] == "0.5.1"
    assert snapshots_have_no_future_bars(snap)
    persist_snapshots(store, [snap])
    original = store.get_signal_snapshot(snap["snapshot_id"])["payload"]
    mutated = dict(snap)
    mutated["candidate_score_calibrated"] = 1.0
    mutated["price_at_snapshot"] = 99.0
    persist_snapshots(store, [mutated])
    again = store.get_signal_snapshot(snap["snapshot_id"])["payload"]
    assert again["candidate_score_calibrated"] == original["candidate_score_calibrated"]
    assert again["price_at_snapshot"] == original["price_at_snapshot"]
    store.set_key_value("RAYA", "Fair Value", "HACKED")
    still = store.get_signal_snapshot(snap["snapshot_id"])["payload"]
    assert still["candidate_score_calibrated"] == original["candidate_score_calibrated"]
    assert store.get_key_value("RAYA", "Fair Value") == "HACKED"
    assert still.get("funnel_status") == "NOT_FOUND"
    import_schedule_result(
        "# news\n```json\n{\"analysis_type\":\"PREMARKET_CATALYSTS\",\"candidates\":[{\"ticker\":\"RAYA\",\"status\":\"PROMOTE\"}]}\n```\n",
        analysis_type=ANALYSIS_PREMARKET, run_id="run1", store=store,
    )
    after_import = store.get_signal_snapshot(snap["snapshot_id"])["payload"]
    assert after_import["candidate_score_calibrated"] == original["candidate_score_calibrated"]
    assert after_import.get("catalyst_status") is None
    store.close()


def test_duplicate_snapshot_id_keeps_first(tmp_path: Path):
    store = AnalysisStore(tmp_path / "s.sqlite", environment=UNIT_TEST)
    a = build_signal_snapshot(
        {"ticker": "EGCH", "candidate_score_calibrated": 82, "last_close": 10},
        run_id="r", environment=UNIT_TEST, generated_at="t0",
        latest_session="2026-09-03",
        session_meta={"analysis_timestamp_utc": "t0", "analysis_timestamp_cairo": "t0", "session_phase": "POST_CLOSE"},
    )
    persist_snapshots(store, [a])
    b = dict(a)
    b["candidate_score_calibrated"] = 0
    stats = persist_snapshots(store, [b])
    assert stats["ignored_duplicates"] == 1
    assert store.get_signal_snapshot(a["snapshot_id"])["payload"]["candidate_score_calibrated"] == 82
    store.close()


def test_outcome_math_positive_negative_gap_missing_and_warning():
    signal = "2026-01-02"
    future = [
        {"session_date": "2026-01-02", "close": 10, "high": 10.2, "low": 9.9},
        {"session_date": "2026-01-05", "close": 11, "high": 11.5, "low": 9.8},  # skip weekend
        {"session_date": "2026-01-06", "close": 10.5, "high": 12.0, "low": 10.2},
        {"session_date": "2026-01-07", "close": 12.0, "high": 12.2, "low": 10.4},
        {"session_date": "2026-01-08", "close": 11.8, "high": 12.1, "low": 11.0},
        {"session_date": "2026-01-09", "close": 13.0, "high": 13.2, "low": 11.7},
    ]
    nxt = sessions_after(future, signal)
    assert [b["session_date"] for b in nxt[:3]] == ["2026-01-05", "2026-01-06", "2026-01-07"]
    pos = compute_outcomes(
        baseline_price=10, baseline_timestamp=signal, baseline_type="OFFICIAL_CLOSE",
        signal_session=signal, future_bars=future,
    )
    assert pos["next_session_return"] == 10.0
    assert pos["return_3_sessions"] == 20.0
    assert pos["return_5_sessions"] == 30.0
    assert pos["mfe_1"] == 15.0
    assert pos["mae_1"] == -2.0
    assert pos["mfe_3"] == 22.0
    assert pos["mae_3"] == -2.0
    assert pos["outcome_status"] == "COMPLETE_FOR_5D"
    assert pos["positive_close_1"] is True
    neg_bars = [
        {"session_date": "2026-01-02", "close": 10, "high": 10, "low": 10},
        {"session_date": "2026-01-05", "close": 9, "high": 9.5, "low": 8.8},
    ]
    neg = compute_outcomes(
        baseline_price=10, baseline_timestamp=signal, baseline_type="OFFICIAL_CLOSE",
        signal_session=signal, future_bars=neg_bars,
    )
    assert neg["next_session_return"] == -10.0
    assert neg["positive_close_1"] is False
    assert neg["outcome_status"] == "PARTIAL"
    pending = compute_outcomes(
        baseline_price=10, baseline_timestamp=signal, baseline_type="OFFICIAL_CLOSE",
        signal_session=signal, future_bars=[{"session_date": "2026-01-02", "close": 10, "high": 10, "low": 10}],
    )
    assert pending["outcome_status"] == "PENDING"
    gap_bars = [
        {"session_date": "2026-01-02", "close": 10, "high": 10, "low": 10},
        {"session_date": "2026-01-05", "close": 20, "high": 20, "low": 19},
    ]
    gap = compute_outcomes(
        baseline_price=10, baseline_timestamp=signal, baseline_type="OFFICIAL_CLOSE",
        signal_session=signal, future_bars=gap_bars, history_integrity="CLEAN",
    )
    assert gap["outcome_integrity_warning"] is True
    warn = compute_outcomes(
        baseline_price=10, baseline_timestamp=signal, baseline_type="OFFICIAL_CLOSE",
        signal_session=signal, future_bars=future, history_integrity="POSSIBLE_DISCONTINUITY",
    )
    assert warn["outcome_integrity_warning"] is True


def test_outcome_does_not_alter_snapshot_rank(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    snap = build_signal_snapshot(
        {"ticker": "ALCN", "candidate_score_calibrated": 78.3883, "last_close": 5.0},
        run_id="r", environment=UNIT_TEST, generated_at="t0",
        latest_session="2026-09-03",
        session_meta={"analysis_timestamp_utc": "t0", "analysis_timestamp_cairo": "t0", "session_phase": "POST_CLOSE"},
    )
    persist_snapshots(store, [snap])
    store.upsert_signal_outcome({
        "snapshot_id": snap["snapshot_id"], "ticker": "ALCN",
        "outcome_status": "PARTIAL", "next_session_return": 4.2,
        "outcome_baseline_price": 5.0, "outcome_baseline_type": "OFFICIAL_CLOSE",
    })
    payload = store.get_signal_snapshot(snap["snapshot_id"])["payload"]
    assert payload["candidate_score_calibrated"] == 78.3883
    store.close()


def test_import_preserves_raw_and_optional_envelope(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    store.set_key_value("MASR", "Fair Value", "8.5")
    raw = "Prose reasoning here.\n\n```json\n{\"analysis_type\":\"PREMARKET_CATALYSTS\",\"run_id\":\"abc\",\"candidates\":[{\"ticker\":\"MASR\",\"status\":\"KEEP\",\"catalyst_status\":\"NO_MATERIAL_CATALYST_FOUND\"}]}\n```\n"
    res = import_schedule_result(raw, analysis_type=ANALYSIS_PREMARKET, run_id="abc", store=store)
    assert res["original_preserved"] is True
    assert res["envelope_parsed"] is True
    assert res["modifies_funnel_fair_value"] is False
    assert (Path(res["saved_path"])).read_text(encoding="utf-8") == raw
    assert store.get_key_value("MASR", "Fair Value") == "8.5"
    bad = import_schedule_result("Prose only {\n not json", analysis_type=ANALYSIS_PREMARKET, run_id="abc", store=store)
    assert bad["envelope_parsed"] is False
    assert "Prose only" in Path(bad["saved_path"]).read_text(encoding="utf-8")
    store.close()


def test_session_phase_bands():
    assert classify_session_phase("2026-09-03T07:00:00+03:00") == "PRE_OPEN"
    assert classify_session_phase("2026-09-03T11:00:00+03:00") == "CONTINUOUS_TRADING"
    assert classify_session_phase("2026-09-03T14:25:00+03:00") == "CLOSING_AUCTION"
    assert classify_session_phase("2026-09-03T14:40:00+03:00") == "TRADING_AT_LAST"
    assert classify_session_phase("2026-09-03T16:00:00+03:00") == "POST_CLOSE"
    assert classify_session_phase("2026-09-05T11:00:00+03:00") == "POST_CLOSE"  # Saturday


def test_schedule_packages_are_materially_different(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = {
        "latest_completed_market_session": "2026-09-03",
        "counts": {
            "UNIVERSE_TOTAL": 139, "EQUITY_UNIVERSE_TOTAL": 135,
            "SCANNER_ELIGIBLE_SYMBOLS": 110, "PRESCREEN_SELECTED": 30,
            "HANDOFF_CANDIDATES": 2, "INTRADAY_ENRICHED": 2,
            "funnel_coverage_scope": "EQUITY_UNIVERSE_TOTAL",
            "funnel_coverage_denominator": 135, "funnel_coverage_n": 135,
        },
        "coverage": {"EXPLORER_COVERAGE": "HIGH", "selection_basis": "BROAD_UNIVERSE", "selection_bias_risk": "LOW"},
        "funnel_coverage": {"NOT_FOUND": 134, "PARTIAL": 1},
        "candidates": [
            _cand("EGCH", LANE_A, "STRONG", 82.3, funnel_status="NOT_FOUND", last_close=10, RVOL20=3.1),
            _cand("RAYA", LANE_A, "STRONG", 78.4, funnel_status="NOT_FOUND", last_close=2.5, RVOL20=3.3, intraday_available=True),
        ],
        "intraday_selection": [{"ticker": "RAYA", "intraday_selection_lane": LANE_A, "intraday_selection_reason": "lane_quota"}],
        "intraday_queried_tickers": ["RAYA"],
        "ranked_comparison": [
            {"ticker": "EGCH", "legacy_rank": 38, "calibrated_rank": 1},
            {"ticker": "SKIP", "legacy_rank": 1, "calibrated_rank": 91, "FORWARD_SETUP_QUALITY": "MIXED"},
        ],
    }
    out = tmp_path / "sched"
    res = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=out, environment=UNIT_TEST,
    )
    pkg = Path(res["package_dir"])
    macro = (pkg / "jobs" / "macro_holdings.md").read_text(encoding="utf-8")
    intra = (pkg / "jobs" / "intraday_opportunity.md").read_text(encoding="utf-8")
    value = (pkg / "jobs" / "value_quality.md").read_text(encoding="utf-8")
    weekly = (pkg / "jobs" / "weekly_xray.md").read_text(encoding="utf-8")
    assert macro != intra
    assert "not next-minute" in value.lower() or "not live-session" in value.lower()
    assert "which previously identified setups are confirming" not in value.lower()
    assert "LIVE SESSION" in intra
    assert "NEXT_WORKING_DAY" in macro
    assert "outcome" in weekly.lower()
    assert Path(res["combined_zip"]).exists()
    assert len(res["individual_zips"]) == 5
    assert res["scoring_version"] == "0.5.1"
    snaps = json.loads((pkg / "optional" / "signal_snapshots.json").read_text())
    assert {s["ticker"] for s in snaps} >= {"EGCH", "RAYA"}
    store.close()


def test_no_paid_ai_and_offline_package(tmp_path: Path):
    import os
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(k, None)
    root = Path(__file__).resolve().parents[1] / "egxbridge"
    banned = ("import openai", "from openai", "import anthropic", "from anthropic", "google.generativeai")
    for p in root.rglob("*.py"):
        text = p.read_text(encoding="utf-8").lower()
        for tok in banned:
            assert tok not in text, f"{p} {tok}"
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    res = prepare_schedule_handoffs(
        explorer_payload={
            "counts": {"EQUITY_UNIVERSE_TOTAL": 2, "HANDOFF_CANDIDATES": 1, "funnel_coverage_denominator": 2, "funnel_coverage_n": 2},
            "coverage": {},
            "candidates": [_cand("MASR", LANE_A, "STRONG", 70, last_close=4)],
        },
        store=store, output_root=tmp_path / "s", environment=UNIT_TEST,
    )
    assert res["orders_generated"] is False
    assert Path(res["combined_zip"]).exists()
    store.close()


def test_false_breakout_still_false():
    candles = []
    base = 10.0
    for i in range(30):
        close = base if i < 29 else base - 1
        candles.append({
            "timestamp": f"2026-01-{i + 1:02d}T00:00:00+00:00",
            "normalized_utc_timestamp": f"2026-01-{i + 1:02d}T00:00:00+00:00",
            "open": base, "high": base + 2, "low": base - 0.5, "close": close, "volume": 1000 + i,
        })
    m = compute_scanner_metrics(candles)
    assert m["breakout_20d"] is False


def test_lane_slots_sum_to_limit_and_lane_d_may_receive_slot():
    slots = scale_lane_slots(15)
    assert sum(slots.values()) == 15
    assert slots[LANE_A] == 8
    assert slots[LANE_C] == 4
    rows = [_cand(f"A{i}", LANE_A, "STRONG", 80 - i) for i in range(10)]
    rows.append(_cand("D1", LANE_D, "MIXED", 40))
    sel = select_intraday_enrichment(rows, 15)
    assert any(r["ticker"] == "D1" for r in sel)
    assert any(r["intraday_selection_reason"].startswith("lane_quota") for r in sel if r["ticker"] == "D1")


def test_leftover_slots_when_other_lanes_empty():
    rows = [_cand(f"A{i}", LANE_A, "STRONG", 90 - i) for i in range(12)]
    sel = select_intraday_enrichment(rows, 15)
    assert len(sel) == 12
    assert any(r["intraday_selection_reason"].startswith("leftover") for r in sel)
    assert all(r["intraday_selection_lane"] == LANE_A for r in sel)


def test_weekend_is_not_a_trading_session():
    bars = [
        {"session_date": "2026-01-02", "close": 10, "high": 10, "low": 10},
        {"session_date": "2026-01-05", "close": 11, "high": 11, "low": 11},
    ]
    sess = unique_trading_sessions(bars)
    assert [b["session_date"] for b in sess] == ["2026-01-02", "2026-01-05"]
    after = sessions_after(bars, "2026-01-02")
    assert len(after) == 1
    assert after[0]["session_date"] == "2026-01-05"


def test_snapshot_id_stable_and_scoring_version_hashed():
    a = snapshot_id(
        environment=UNIT_TEST, analysis_type=ANALYSIS_EXPLORER, ticker="egch",
        analysis_timestamp="t0", data_cutoff="c0", scoring_version="0.5.1",
    )
    b = snapshot_id(
        environment=UNIT_TEST, analysis_type=ANALYSIS_EXPLORER, ticker="EGCH",
        analysis_timestamp="t0", data_cutoff="c0", scoring_version="0.5.1",
    )
    assert a == b
    c = snapshot_id(
        environment=UNIT_TEST, analysis_type=ANALYSIS_EXPLORER, ticker="EGCH",
        analysis_timestamp="t0", data_cutoff="c0", scoring_version="0.5.0",
    )
    assert a != c


def test_daily_decision_never_emits_buy():
    rec = build_daily_decision(
        run_id="r", latest_session="2026-09-03",
        market_regime="NEUTRAL", portfolio_posture="SELECTIVE",
        candidates=[_cand("RAYA", LANE_A, "STRONG", 78)],
    )
    assert rec["orders_generated"] is False
    assert rec["no_automatic_buy"] is True
    assert rec["candidates"][0]["FINAL_TACTICAL_STATUS"] != "BUY"
    blob = json.dumps(rec)
    assert '"BUY"' not in blob or rec["candidates"][0]["FINAL_TACTICAL_STATUS"] is None


def test_calibration_status_starts_insufficient():
    assert calibration_status_for_n(0) == "INSUFFICIENT_SAMPLE"
    assert calibration_status_for_n(9) == "INSUFFICIENT_SAMPLE"
    assert calibration_status_for_n(10) == "EARLY_SAMPLE"


def test_update_outcomes_uses_future_sessions_only_and_does_not_mutate_snapshot(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    db = Database(tmp_path / "m.sqlite")
    snap = build_signal_snapshot(
        {"ticker": "TOY", "candidate_score_calibrated": 71.25, "last_close": 10.0,
         "TECHNICAL_HISTORY_INTEGRITY": "CLEAN"},
        run_id="r", environment=UNIT_TEST, generated_at="t0",
        latest_session="2026-01-02",
        session_meta={"analysis_timestamp_utc": "t0", "analysis_timestamp_cairo": "t0", "session_phase": "POST_CLOSE"},
    )
    persist_snapshots(store, [snap])
    pending = update_outcomes_for_store(store, db, pending_only=True)
    out0 = store.list_signal_outcomes()
    if out0:
        assert out0[0]["outcome_status"] in {"PENDING", "NOT_EVALUABLE"} or out0[0].get("next_session_return") is None
    for i, close in enumerate([10, 11, 10.5, 12, 11.8, 13]):
        day = 2 + i
        ts = f"2026-01-{day:02d}T00:00:00+00:00"
        db.upsert_candle({
            "symbol": "TOY", "interval": "1d", "timestamp": ts,
            "normalized_utc_timestamp": ts, "open": close, "high": close + 0.5,
            "low": close - 0.2, "close": close, "volume": 1000,
            "provider": "yahoo", "capture_timestamp": "2026-01-10T00:00:00+00:00",
            "session_date": ts[:10],
        })
    update_outcomes_for_store(store, db, pending_only=True)
    payload = store.get_signal_snapshot(snap["snapshot_id"])["payload"]
    assert payload["candidate_score_calibrated"] == 71.25
    assert snapshots_have_no_future_bars(payload)
    oc = store.list_signal_outcomes()[0]
    assert oc["next_session_return"] == 10.0
    assert oc["return_3_sessions"] == 20.0
    assert oc["outcome_status"] == "COMPLETE_FOR_5D"
    store.close()
    db.close()
    assert pending["note"]


def test_quality_ok_rejects_weak():
    assert quality_ok({"FORWARD_SETUP_QUALITY": "STRONG"}) is True
    assert quality_ok({"FORWARD_SETUP_QUALITY": "WEAK"}) is False


def test_schedule_manifest_lists_job_files(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    res = prepare_schedule_handoffs(
        explorer_payload={
            "latest_completed_market_session": "2026-09-03",
            "counts": {"EQUITY_UNIVERSE_TOTAL": 1, "HANDOFF_CANDIDATES": 1, "funnel_coverage_n": 1, "funnel_coverage_denominator": 1},
            "coverage": {"EXPLORER_COVERAGE": "INSUFFICIENT"},
            "candidates": [_cand("ALCN", LANE_C, "GOOD", 61, last_close=5.1, funnel_status="NOT_FOUND")],
        },
        store=store, output_root=tmp_path / "pkg", environment=UNIT_TEST,
    )
    man = json.loads((Path(res["package_dir"]) / "manifest.json").read_text())
    files = man["included_files"]
    assert "jobs/macro_holdings.md" in files
    assert "jobs/intraday_opportunity.md" in files
    assert "jobs/weekly_xray.md" in files
    assert "common/market_summary.json" in files
    daily = json.loads((Path(res["package_dir"]) / "optional" / "daily_decision.json").read_text())
    assert daily["no_automatic_buy"] is True
    weekly = json.loads((Path(res["package_dir"]) / "optional" / "calibration_history_summary.json").read_text())
    assert "INSUFFICIENT_SAMPLE" in json.dumps(weekly)
    assert man["scoring_version"] == "0.5.1"
    assert man["target_next_working_day"] == "UNKNOWN"
    store.close()
