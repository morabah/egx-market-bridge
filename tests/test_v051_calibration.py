"""v0.5.1 Explorer signal calibration — families, scores, integrity, lanes."""
from __future__ import annotations

from pathlib import Path

from egxbridge.analysis.common.ai_mode import AI_CHATGPT_HANDOFF
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.calibration import (
    LONG_HORIZON_CAP,
    SCORE_KIND,
    audit_legacy_contributions,
    calibrate_candidate,
    classify_candidate_families,
    classify_history_integrity,
    classify_move_already_realized,
    classify_volatility_risk,
    diversify_by_lane,
    long_horizon_context_points,
    rvol_context,
    select_intraday_tickers,
)
from egxbridge.analysis.explorer.candidate_context import build_candidate_row
from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
from egxbridge.analysis.explorer.models import ExplorerRunConfig
from egxbridge.analysis.explorer.prescreen import prescreen_score, select_handoff_candidates
from egxbridge.analysis.funnel.registry import FunnelRegistry
from egxbridge.db import Database
from egxbridge.scanner import compute_scanner_metrics


def _m(**kwargs):
    base = {
        "available": True,
        "daily_return_pct": 0.5,
        "return_1w_pct": 1.0,
        "return_1m_pct": 4.0,
        "return_3m_pct": 8.0,
        "return_6m_pct": 12.0,
        "rvol_20": 1.4,
        "dist_from_20d_high_pct": -3.0,
        "dist_from_60d_high_pct": -5.0,
        "last_close": 10.0,
        "sma_20": 9.7,
        "sma_50": 9.4,
        "breakout_20d": False,
        "breakout_60d": False,
        "realized_vol_20d_ann_pct": 32.0,
        "atr_14": 0.25,
        "bars": 120,
        "days_of_history": 120,
    }
    base.update(kwargs)
    return base


def test_six_month_return_cannot_linearly_dominate_calibrated_score():
    extreme = _m(
        daily_return_pct=-1.0, return_1w_pct=-2.0, return_1m_pct=5.0,
        return_3m_pct=150.0, return_6m_pct=500.0, rvol_20=0.7,
        dist_from_20d_high_pct=-18.0, dist_from_60d_high_pct=-22.0,
        last_close=10.0, sma_20=12.0, sma_50=11.5, realized_vol_20d_ann_pct=90.0,
    )
    setup = _m(
        daily_return_pct=1.2, return_1w_pct=3.5, return_1m_pct=6.0,
        return_3m_pct=10.0, return_6m_pct=18.0, rvol_20=3.5,
        dist_from_20d_high_pct=-2.4, dist_from_60d_high_pct=-3.0,
        last_close=10.0, sma_20=9.6, sma_50=9.3, realized_vol_20d_ann_pct=35.0,
    )
    legacy_e = audit_legacy_contributions(extreme)
    assert legacy_e["return_6m"] > 100  # uncapped linear term
    lh = long_horizon_context_points(extreme, classify_history_integrity(extreme))
    assert lh["points"] <= LONG_HORIZON_CAP
    assert lh["points"] < 2.0  # NOT_VERIFIED weight 0.35
    cal_e = calibrate_candidate(extreme)
    cal_s = calibrate_candidate(setup)
    assert cal_s["candidate_score_calibrated"] > cal_e["candidate_score_calibrated"]
    assert prescreen_score(extreme) > prescreen_score(setup)


def test_three_and_six_month_contribution_is_bounded():
    modest = _m(return_3m_pct=40, return_6m_pct=80)
    huge = _m(return_3m_pct=400, return_6m_pct=800)
    integrity = classify_history_integrity(modest)
    a = long_horizon_context_points(modest, integrity)["points"]
    b = long_horizon_context_points(huge, integrity)["points"]
    assert a <= LONG_HORIZON_CAP * 0.35 + 1e-9
    assert b <= LONG_HORIZON_CAP * 0.35 + 1e-9
    # Linear 3M/6M terms would scale ~10x; saturating+cap must not.
    assert b / max(a, 1e-9) < 3.0
    assert b <= LONG_HORIZON_CAP


def test_move_already_realized_classification_multi_factor():
    extreme = classify_move_already_realized(_m(
        return_1m_pct=40, return_3m_pct=154, return_6m_pct=478,
        last_close=20, sma_50=10, realized_vol_20d_ann_pct=90,
    ))
    assert extreme["MOVE_ALREADY_REALIZED"] == "EXTREME"
    assert any("return_3m" in r for r in extreme["reasons"])
    assert any("return_6m" in r for r in extreme["reasons"])
    low = classify_move_already_realized(_m(
        return_1m_pct=3, return_3m_pct=6, return_6m_pct=10, last_close=10, sma_50=9.8,
    ))
    assert low["MOVE_ALREADY_REALIZED"] == "LOW"
    missing = classify_move_already_realized({
        "available": True, "return_1m_pct": None, "return_3m_pct": None, "return_6m_pct": None,
    })
    assert missing["MOVE_ALREADY_REALIZED"] == "NOT_RELIABLE"


def test_extreme_move_does_not_automatically_exclude():
    m = _m(
        return_3m_pct=140, return_6m_pct=227, rvol_20=2.2,
        dist_from_20d_high_pct=0.1, breakout_20d=True, last_close=12, sma_20=10,
    )
    cal = calibrate_candidate(m)
    assert cal["MOVE_ALREADY_REALIZED"] in {"HIGH", "EXTREME"}
    assert cal["candidate_score_calibrated"] > 0
    assert "CONTINUATION" in cal["candidate_families"] or "HIGH_BASE_SECOND_LEG" in cal["candidate_families"]


def test_forward_setup_can_outrank_extreme_historical_winner():
    winner = {
        "ticker": "HUGE",
        "metrics": _m(
            daily_return_pct=-0.8, return_1w_pct=-3.0, return_1m_pct=2.0,
            return_3m_pct=160, return_6m_pct=420, rvol_20=0.8,
            dist_from_20d_high_pct=-16.0, last_close=8, sma_20=10, sma_50=11,
            realized_vol_20d_ann_pct=100,
        ),
    }
    fresh = {
        "ticker": "SETUP",
        "metrics": _m(
            daily_return_pct=0.8, return_1w_pct=2.5, return_1m_pct=5.0,
            return_3m_pct=9.0, return_6m_pct=14.0, rvol_20=3.4,
            dist_from_20d_high_pct=-1.8, last_close=10, sma_20=9.7, sma_50=9.4,
            realized_vol_20d_ann_pct=33, breakout_20d=False,
        ),
    }
    top = select_handoff_candidates([winner, fresh], max_handoff=2)
    assert top[0]["ticker"] == "SETUP"
    assert top[0]["candidate_score_calibrated"] > top[1]["candidate_score_calibrated"]
    assert top[0]["candidate_score_legacy"] is not None
    assert top[1]["candidate_score_legacy"] > top[0]["candidate_score_legacy"]


def test_clean_correction_requires_actual_pullback():
    good = _m(
        daily_return_pct=-2.4, return_1w_pct=-1.0, return_1m_pct=8.0, return_3m_pct=12.0,
        rvol_20=1.8, dist_from_20d_high_pct=-5.0, last_close=10, sma_20=9.8, sma_50=9.5,
    )
    assert "CLEAN_CORRECTION" in classify_candidate_families(good)
    near_high = _m(return_1m_pct=8.0, dist_from_20d_high_pct=-0.4)
    assert "CLEAN_CORRECTION" not in classify_candidate_families(near_high)
    collapse = _m(
        return_1m_pct=-12.0, return_3m_pct=-4.0, dist_from_20d_high_pct=-10.0,
        last_close=8.0, sma_20=10.0, sma_50=10.5,
    )
    assert "CLEAN_CORRECTION" not in classify_candidate_families(collapse)


def test_pre_breakout_requires_proximity_to_reference():
    near = _m(
        dist_from_20d_high_pct=-1.2, breakout_20d=False, return_1w_pct=1.0,
        last_close=10, sma_20=9.7, daily_return_pct=0.4,
    )
    fams = classify_candidate_families(near)
    assert "PRE_BREAKOUT" in fams
    far = _m(dist_from_20d_high_pct=-9.0, breakout_20d=False, return_1w_pct=2.0)
    assert "PRE_BREAKOUT" not in classify_candidate_families(far)
    already = _m(dist_from_20d_high_pct=1.2, breakout_20d=False)
    assert "PRE_BREAKOUT" not in classify_candidate_families(already)


def test_early_reversal_requires_prior_weakness_and_reclaim():
    reclaim = _m(
        dist_from_20d_high_pct=-11.0, return_1m_pct=-6.0, return_1w_pct=2.0,
        daily_return_pct=1.0, last_close=10, sma_20=9.8,
    )
    assert "EARLY_REVERSAL" in classify_candidate_families(reclaim)
    ordinary = _m(dist_from_20d_high_pct=-3.0, return_1m_pct=4.0, return_1w_pct=0.5)
    assert "EARLY_REVERSAL" not in classify_candidate_families(ordinary)


def test_false_breakout_remains_false():
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
    assert m["breakout_flag_20d"] is False


def test_high_rvol_is_not_automatically_bullish():
    down = _m(rvol_20=3.6, daily_return_pct=-5.5, dist_from_20d_high_pct=-14.0)
    fams = classify_candidate_families(down)
    assert "HIGH_RELATIVE_VOLUME" in fams
    ctx = rvol_context(down)
    assert ctx["constructive_volume_structure"] is False
    assert ctx["breakdown_event_risk"] is True
    assert "not automatically bullish" in ctx["note"]
    up = _m(rvol_20=3.6, daily_return_pct=2.0, dist_from_20d_high_pct=-0.5)
    ctx_up = rvol_context(up)
    assert ctx_up["constructive_volume_structure"] is True


def test_possible_discontinuity_neutralizes_long_horizon_points():
    candles = []
    for i in range(40):
        close = 10.0 if i < 20 else 20.0  # 100% one-session jump
        day = 1 + i
        month = 1 + (day - 1) // 28
        d = (day - 1) % 28 + 1
        ts = f"2026-{month:02d}-{d:02d}T00:00:00+00:00"
        candles.append({
            "close": close, "high": close, "volume": 1000,
            "normalized_utc_timestamp": ts, "timestamp": ts,
        })
    m = _m(return_3m_pct=120, return_6m_pct=400)
    hi = classify_history_integrity(m, candles)
    assert hi["TECHNICAL_HISTORY_INTEGRITY"] == "POSSIBLE_DISCONTINUITY"
    assert hi["long_horizon_weight"] == 0.0
    pts = long_horizon_context_points(m, hi)["points"]
    assert pts == 0.0
    cal = calibrate_candidate(m, candles=candles)
    assert cal["candidate_score_calibrated"] is not None  # still ranked; recent data usable


def test_not_reliable_history_excludes_long_horizon_contribution():
    m = {
        "available": True, "bars": 12, "days_of_history": 12,
        "return_1m_pct": None, "return_3m_pct": None, "return_6m_pct": None,
        "rvol_20": 1.5, "dist_from_20d_high_pct": -2.0, "last_close": 10, "sma_20": 9.8,
        "daily_return_pct": 1.0, "return_1w_pct": 2.0, "breakout_20d": False, "breakout_60d": False,
        "realized_vol_20d_ann_pct": 30,
    }
    hi = classify_history_integrity(m)
    assert hi["TECHNICAL_HISTORY_INTEGRITY"] == "NOT_RELIABLE"
    assert long_horizon_context_points(m, hi)["points"] == 0.0


def test_candidate_lanes_diversify_shortlist():
    rows = []
    for i in range(12):
        rows.append({
            "ticker": f"EXT{i}",
            "metrics": _m(
                return_3m_pct=140 + i, return_6m_pct=400 + i * 5,
                rvol_20=0.6, dist_from_20d_high_pct=-20.0,
                last_close=8, sma_20=11, sma_50=12, realized_vol_20d_ann_pct=95,
                daily_return_pct=-1.0, return_1w_pct=-2.0, return_1m_pct=3.0,
            ),
        })
    for i in range(5):
        rows.append({
            "ticker": f"EARLY{i}",
            "metrics": _m(
                daily_return_pct=1.0 + i * 0.1, return_1w_pct=2.5, return_1m_pct=5.0,
                return_3m_pct=8.0, return_6m_pct=12.0, rvol_20=2.8,
                dist_from_20d_high_pct=-1.5, last_close=10, sma_20=9.7, sma_50=9.4,
                realized_vol_20d_ann_pct=30, breakout_20d=False,
            ),
        })
    selected = select_handoff_candidates(rows, max_handoff=12)
    tickers = [r["ticker"] for r in selected]
    assert any(t.startswith("EARLY") for t in tickers)
    assert sum(1 for t in tickers if t.startswith("EARLY")) >= 4
    lanes = {r["candidate_lane"] for r in selected}
    assert len(lanes) >= 2


def test_legacy_and_calibrated_scores_both_exported():
    row = select_handoff_candidates([{"ticker": "X", "metrics": _m()}], max_handoff=1)[0]
    assert row["candidate_score_legacy"] == prescreen_score(_m())
    assert row["candidate_score_calibrated"] is not None
    assert row["candidate_score"] == row["candidate_score_calibrated"]
    assert row["score_kind"] == SCORE_KIND
    assert row["not_a_probability"] is True


def test_fair_value_not_used_in_tactical_score_and_not_modified():
    m = _m()
    a = calibrate_candidate(m, funnel_ctx={"funnel_status": "CURRENT", "Fair Value Range": "99–120"})
    b = calibrate_candidate(m, funnel_ctx={"funnel_status": "NOT_FOUND", "Fair Value Range": None})
    assert a["candidate_score_calibrated"] == b["candidate_score_calibrated"]
    assert a["fair_value_used_in_tactical_score"] is False
    row = build_candidate_row(
        "KIMA", m, {"funnel_status": "CURRENT", "Fair Value Range": "11.0"},
        extra={"MOVE_ALREADY_REALIZED": "EXTREME"},
    )
    assert row["fair_value_from_funnel_only"] is not None
    assert row["fair_value_manufactured"] is False
    assert row["MOVE_ALREADY_REALIZED"] == "EXTREME"


def test_no_probability_claim_generated():
    cal = calibrate_candidate(_m())
    blob = str(cal)
    assert cal["not_a_probability"] is True
    assert cal["score_kind"] == SCORE_KIND
    assert "probability" not in blob.lower() or "not_a_probability" in blob
    assert "chance" not in blob.lower()
    assert "P(profit)" not in blob


def test_no_paid_ai_api_required():
    root = Path(__file__).resolve().parents[1] / "egxbridge"
    banned = ("import openai", "import anthropic", "google.generativeai", "from openai", "from anthropic")
    for p in root.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        low = text.lower()
        for token in banned:
            assert token not in low, f"{p} contains {token}"
    assert AI_CHATGPT_HANDOFF == "CHATGPT_HANDOFF"


def test_intraday_selection_prefers_setup_families_not_legacy_score():
    rows = [
        {
            "ticker": "LEGACY",
            "candidate_families": ["CLEAN_CORRECTION"],
            "candidate_score_calibrated": 40.0,
            "candidate_score_legacy": 200.0,
        },
        {
            "ticker": "PRE",
            "candidate_families": ["PRE_BREAKOUT"],
            "candidate_score_calibrated": 55.0,
            "candidate_score_legacy": 30.0,
        },
    ]
    assert select_intraday_tickers(rows, 1) == ["PRE"]


def test_volatility_cross_section_and_fixed_bands():
    xs = [20.0] * 10 + [40.0] * 10 + [90.0] * 5
    hi = classify_volatility_risk({"realized_vol_20d_ann_pct": 95.0}, cross_section_vols=xs)
    assert hi["VOLATILITY_RISK"] == "EXTREME"
    assert hi["basis"] == "cross_sectional_percentiles"
    band = classify_volatility_risk({"realized_vol_20d_ann_pct": 100.0})
    assert band["VOLATILITY_RISK"] == "EXTREME"
    assert band["realized_vol_20d_ann_pct"] == 100.0


def test_handoff_exports_both_scores_without_fv_mutation(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite")
    db = Database(tmp_path / "m.sqlite")
    for i, close in enumerate([10 + (i % 5) * 0.1 for i in range(60)]):
        day = 1 + i
        month = 1 + (day - 1) // 28
        d = (day - 1) % 28 + 1
        ts = f"2026-{month:02d}-{d:02d}T00:00:00+00:00"
        db.upsert_candle({
            "symbol": "COMI", "interval": "1d", "timestamp": ts,
            "normalized_utc_timestamp": ts,
            "open": close, "high": close + 0.2, "low": close - 0.2, "close": close,
            "volume": 4000 + i, "provider": "yahoo",
            "capture_timestamp": "2026-09-05T00:00:00+00:00",
            "session_date": ts[:10],
        })
    store.set_key_value("COMI", "Fair Value", "8.5")
    before = store.get_key_value("COMI", "Fair Value")
    funnel = FunnelRegistry(workspace_root=tmp_path / "funnels", store=store, db=db)
    out = tmp_path / "exp"
    res = prepare_explorer_handoff(
        ExplorerRunConfig(universe=["COMI"], enrich_intraday=False),
        db=db, store=store, funnel_registry=funnel, output_root=out,
    )
    after = store.get_key_value("COMI", "Fair Value")
    assert before == after == "8.5"
    payload = (out / "explorer_handoff.json").read_text(encoding="utf-8")
    assert "HEURISTIC_UNCALIBRATED" in payload
    assert '"not_a_probability": true' in payload.lower() or '"not_a_probability": True' in payload
    assert "80% chance" not in payload.lower()
    md = (out / "explorer_handoff.md").read_text(encoding="utf-8")
    assert "MOVE_ALREADY_REALIZED" in md
    assert "FORWARD_SETUP_QUALITY" in md
    assert (out / "legacy_vs_calibrated_ranking.csv").exists()
    assert (out / "calibration_snapshots.jsonl").exists()
    snap = (out / "calibration_snapshots.jsonl").read_text(encoding="utf-8")
    assert "next_session_return" in snap
    assert "null" in snap
    assert res["orders_generated"] is False
    store.close()
    db.close()


def test_diversify_does_not_force_empty_lane():
    rows = []
    for i in range(6):
        rows.append({
            "ticker": f"A{i}",
            "candidate_lane": "LANE_A_EARLY_PRE_IGNITION",
            "candidate_score_calibrated": 80 - i,
        })
    out = diversify_by_lane(rows, max_handoff=5)
    assert len(out) == 5
    assert all(r["ticker"].startswith("A") for r in out)
