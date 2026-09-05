"""v0.6.2 calibration integrity: breadth, fingerprint identity, counts, envelopes."""
from __future__ import annotations

from pathlib import Path
import json

from egxbridge.analysis.common.environment import UNIT_TEST
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.calibration import calibrate_candidate, SCORING_VERSION, SCORE_KIND
from egxbridge.analysis.explorer.intraday_select import LANE_A
from egxbridge.analysis.schedule.handoff import prepare_schedule_handoffs
from egxbridge.analysis.schedule.identity import (
    resolve_signal_identity, explorer_canonical_id, quantize, ORIGIN_INTRADAY,
    market_state_fingerprint,
)
from egxbridge.analysis.schedule.importer import import_schedule_result, resolve_import_linkage
from egxbridge.analysis.schedule.market_summary import (
    compute_breadth, build_market_summary, MARKET_BREADTH_SCOPE, SHORTLIST_BREADTH_LABEL,
)
from egxbridge.analysis.schedule.metrics import observation_counts, is_evaluable_observation
from egxbridge.analysis.schedule.outcomes import update_outcomes_for_store
from egxbridge.analysis.schedule.types import (
    ANALYSIS_TYPES, ANALYSIS_MACRO, ANALYSIS_PREMARKET, ANALYSIS_INTRADAY,
    ANALYSIS_VALUE, ANALYSIS_WEEKLY, ANALYSIS_EXPLORER, RESULT_ENVELOPE_VERSION,
    LINKAGE_EXPLICIT, LINKAGE_FALLBACK, LINKAGE_AMBIGUOUS, LINKAGE_INVALID,
)
from egxbridge.db import Database


def _eq_row(ticker, daily, **kwargs):
    row = {
        "ticker": ticker,
        "security_type": "EQUITY",
        "available": True,
        "daily_return_pct": daily,
        "rvol_20": kwargs.pop("rvol", 1.1),
        "last_close": kwargs.pop("close", 10.0),
        "sma_20": kwargs.pop("sma20", 9.5),
        "sma_50": kwargs.pop("sma50", 9.0),
        "dist_from_20d_high_pct": kwargs.pop("d20", -1.0),
        "dist_from_60d_high_pct": kwargs.pop("d60", -3.0),
        "breakout_20d": kwargs.pop("b20", False),
        "breakout_60d": kwargs.pop("b60", False),
        "realized_vol_20d_ann_pct": kwargs.pop("vol", 30.0),
    }
    row.update(kwargs)
    return row


def _cand(ticker, **kwargs):
    row = {
        "ticker": ticker,
        "candidate_lane": kwargs.pop("lane", LANE_A),
        "FORWARD_SETUP_QUALITY": kwargs.pop("quality", "STRONG"),
        "MOVE_ALREADY_REALIZED": kwargs.pop("realized", "LOW"),
        "candidate_score_calibrated": kwargs.pop("score", 80.0),
        "calibrated_rank": kwargs.pop("rank", 1),
        "last_close": kwargs.pop("last_close", 10.0),
        "daily_return_pct": kwargs.pop("daily_return_pct", 1.0),
        "rvol_20": kwargs.pop("rvol_20", 1.2),
        "available": True,
    }
    row.update(kwargs)
    return row


def _payload(n=20, explorer_run_id="xr_a", session="2026-09-03"):
    tickers = ["EGCH", "RAYA", "ALCN", "MASR"] + [f"T{i:02d}" for i in range(n - 4)]
    return {
        "explorer_run_id": explorer_run_id,
        "generated_at": f"pack-{explorer_run_id}",
        "latest_completed_market_session": session,
        "counts": {
            "EQUITY_UNIVERSE_TOTAL": 135, "HANDOFF_CANDIDATES": n,
            "SCANNER_ELIGIBLE_SYMBOLS": 110,
            "funnel_coverage_n": 135, "funnel_coverage_denominator": 135,
        },
        "coverage": {"EXPLORER_COVERAGE": "HIGH", "selection_basis": "BROAD_UNIVERSE"},
        "candidates": [_cand(t, rank=i + 1, score=90 - i) for i, t in enumerate(tickers[:n])],
    }


def test_market_breadth_uses_full_scanner_eligible_not_shortlist():
    eligible = []
    for i in range(45):
        eligible.append(_eq_row(f"UP{i:03d}", 1.0 + i * 0.01))
    for i in range(65):
        eligible.append(_eq_row(f"DN{i:03d}", -1.0 - i * 0.01, close=8.0, sma20=9.0, sma50=9.5, d20=-8.0))
    shortlist = eligible[:16] + eligible[45:49]  # 16 up + 4 down
    market = build_market_summary(
        coverage={"EXPLORER_COVERAGE": "HIGH"},
        counts={"EQUITY_UNIVERSE_TOTAL": 135, "SCANNER_ELIGIBLE_SYMBOLS": 110, "HANDOFF_CANDIDATES": 20},
        scanner_rows=shortlist,
        latest_session="2026-09-03",
        session_meta={"session_phase": "POST_CLOSE"},
        breadth_rows=eligible,
    )
    mb = market["market_breadth"]
    assert mb["breadth_scope"] == MARKET_BREADTH_SCOPE
    assert mb["breadth_n"] == 110
    assert mb["advancers"] == 45
    assert mb["decliners"] == 65
    assert mb["is_market_breadth"] is True
    sb = market["shortlist_breadth"]
    assert sb["label"] == SHORTLIST_BREADTH_LABEL
    assert sb["advancers"] == 16
    assert sb["decliners"] == 4
    assert sb["is_market_breadth"] is False
    assert "market_participation" in market
    assert market["market_participation"]["breadth_n"] == 110
    assert "CANDIDATE" in json.dumps(sb["note"]).upper() or "shortlist" in sb["note"].lower()


def test_indices_and_funds_excluded_from_market_breadth():
    rows = [
        _eq_row("COMI", 1.0),
        {**_eq_row("EGX30", 2.0), "security_type": "INDEX"},
        {**_eq_row("KASABF", -1.0), "security_type": "FUND"},
        {**_eq_row("XYZW", 3.0), "security_type": "WARRANT"},
    ]
    b = compute_breadth(rows, scope=MARKET_BREADTH_SCOPE)
    assert b["breadth_n"] == 1
    assert b["advancers"] == 1


def test_build_market_summary_never_uses_shortlist_as_market_when_eligible_missing():
    short = [_eq_row("RAYA", 5.0) for _ in range(20)]
    market = build_market_summary(
        coverage={}, counts={"HANDOFF_CANDIDATES": 20},
        scanner_rows=short, latest_session="2026-09-03", session_meta={},
        breadth_rows=[],
    )
    assert market["market_breadth"]["breadth_n"] == 0
    assert market["shortlist_breadth"]["breadth_n"] == 20
    assert market["market_breadth"].get("missing_eligible_metrics") is True


def test_new_explorer_run_id_same_market_state_reuses_canonical(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    a = _payload(20, explorer_run_id="xr_run_A")
    b = _payload(20, explorer_run_id="xr_run_B")
    prepare_schedule_handoffs(explorer_payload=a, store=store, output_root=tmp_path / "a", environment=UNIT_TEST)
    n1 = len(store.list_canonical_signals())
    ids1 = {s["canonical_signal_id"] for s in store.list_canonical_signals()}
    prepare_schedule_handoffs(explorer_payload=b, store=store, output_root=tmp_path / "b", environment=UNIT_TEST)
    n2 = len(store.list_canonical_signals())
    ids2 = {s["canonical_signal_id"] for s in store.list_canonical_signals()}
    assert n1 == 20 and n2 == 20
    assert ids1 == ids2
    raya = next(s for s in store.list_canonical_signals() if s["ticker"] == "RAYA")
    assert raya.get("latest_seen_explorer_run_id") == "xr_run_B"
    store.close()


def test_same_market_state_different_package_timestamp_reuses(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(5, explorer_run_id="xr_same")
    prepare_schedule_handoffs(explorer_payload=payload, store=store, output_root=tmp_path / "p1", environment=UNIT_TEST)
    prepare_schedule_handoffs(explorer_payload=payload, store=store, output_root=tmp_path / "p2", environment=UNIT_TEST)
    assert len(store.list_canonical_signals()) == 5
    store.close()


def test_new_session_creates_new_canonical():
    a = resolve_signal_identity(
        _cand("RAYA", last_close=10.0),
        environment=UNIT_TEST, explorer_run_id="xr1", latest_session="2026-09-03",
        analysis_type=ANALYSIS_EXPLORER,
    )
    b = resolve_signal_identity(
        _cand("RAYA", last_close=10.0),
        environment=UNIT_TEST, explorer_run_id="xr1", latest_session="2026-09-04",
        analysis_type=ANALYSIS_EXPLORER,
    )
    assert a["canonical_signal_id"] != b["canonical_signal_id"]
    assert a["market_state_fingerprint"] != b["market_state_fingerprint"]


def test_material_intraday_creates_child_with_parent_and_family():
    parent = resolve_signal_identity(
        _cand("RAYA", last_close=2.5),
        environment=UNIT_TEST, explorer_run_id="xr_lin", latest_session="2026-09-03",
        analysis_type=ANALYSIS_EXPLORER, price_basis="OFFICIAL_CLOSE",
    )
    child = resolve_signal_identity(
        {**_cand("RAYA", last_close=2.5), "current_session_price": 2.62,
         "intraday": {"current_session_price": 2.62, "current_session": True}},
        environment=UNIT_TEST, explorer_run_id="xr_other", latest_session="2026-09-03",
        analysis_type=ANALYSIS_INTRADAY, price_basis="CURRENT_INTRADAY_PRICE",
        session_meta={
            "session_phase": "CONTINUOUS_TRADING",
            "analysis_timestamp_cairo": "2026-09-03T11:20:00+03:00",
            "analysis_timestamp_utc": "2026-09-03T08:20:00+00:00",
        },
    )
    later_bucket_same_px = resolve_signal_identity(
        {**_cand("RAYA", last_close=2.5), "current_session_price": 2.62,
         "intraday": {"current_session_price": 2.62, "current_session": True}},
        environment=UNIT_TEST, explorer_run_id="xr_other", latest_session="2026-09-03",
        analysis_type=ANALYSIS_INTRADAY, price_basis="CURRENT_INTRADAY_PRICE",
        session_meta={
            "session_phase": "CONTINUOUS_TRADING",
            "analysis_timestamp_cairo": "2026-09-03T13:25:00+03:00",
            "analysis_timestamp_utc": "2026-09-03T10:25:00+00:00",
        },
    )
    child2 = resolve_signal_identity(
        {**_cand("RAYA", last_close=2.5), "current_session_price": 2.70,
         "intraday": {"current_session_price": 2.70, "current_session": True}},
        environment=UNIT_TEST, explorer_run_id="xr_other", latest_session="2026-09-03",
        analysis_type=ANALYSIS_INTRADAY, price_basis="CURRENT_INTRADAY_PRICE",
        session_meta={
            "session_phase": "CONTINUOUS_TRADING",
            "analysis_timestamp_cairo": "2026-09-03T13:20:00+03:00",
            "analysis_timestamp_utc": "2026-09-03T10:20:00+00:00",
        },
    )
    assert child["signal_origin"] == ORIGIN_INTRADAY
    assert child["canonical_signal_id"] != parent["canonical_signal_id"]
    assert child["parent_signal_id"] == parent["canonical_signal_id"]
    assert child["signal_family_id"] == parent["signal_family_id"] == child2["signal_family_id"]
    assert later_bucket_same_px["canonical_signal_id"] == child["canonical_signal_id"]
    assert child2["canonical_signal_id"] != child["canonical_signal_id"]
    assert child2["parent_signal_id"] == parent["canonical_signal_id"]


def test_float_normalization_prevents_hash_churn():
    assert quantize(2.6200001) == quantize(2.62) == "2.6200"
    a = market_state_fingerprint(
        {"ticker": "RAYA", "last_close": 2.6200001, "FORWARD_SETUP_QUALITY": "STRONG"},
        environment=UNIT_TEST, ticker="RAYA", market_session_basis="2026-09-03",
        scoring_version="0.5.1", signal_origin="EXPLORER",
    )
    b = market_state_fingerprint(
        {"ticker": "RAYA", "last_close": 2.62, "FORWARD_SETUP_QUALITY": "STRONG"},
        environment=UNIT_TEST, ticker="RAYA", market_session_basis="2026-09-03",
        scoring_version="0.5.1", signal_origin="EXPLORER",
    )
    assert a == b
    id1 = explorer_canonical_id(
        environment=UNIT_TEST, ticker="RAYA", market_session_basis="2026-09-03",
        explorer_run_id="xr1", candidate={"last_close": 2.6200001},
    )
    id2 = explorer_canonical_id(
        environment=UNIT_TEST, ticker="RAYA", market_session_basis="2026-09-03",
        explorer_run_id="xr2", candidate={"last_close": 2.62},
    )
    assert id1 == id2


def test_generated_imported_evaluable_counts(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(20)
    res = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "s",
        environment=UNIT_TEST, jobs=list(ANALYSIS_TYPES),
    )
    oc = observation_counts(store.list_analysis_observations())
    assert res["canonical_signals_n"] == 20
    assert oc["analysis_observations_generated_n"] == 100
    assert oc["analysis_observations_imported_n"] == 0
    assert oc["analysis_observations_evaluable_n"] == 0
    weekly = json.loads((Path(res["package_dir"]) / "optional" / "calibration_history_summary.json").read_text())
    assert weekly["scanner_sample_n"] == 20
    assert weekly["analysis_observations_generated_n"] == 100
    assert weekly["analysis_observations_imported_n"] == 0
    assert weekly["analysis_observations_evaluable_n"] == 0
    no_import = {"generated_by": "CHATGPT_HANDOFF", "chatgpt_status": "NO_IMPORT", "canonical_signal_id": "x"}
    assert not is_evaluable_observation(no_import)
    store.close()


def test_repeated_packaging_does_not_inflate_scanner_n(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(20)
    prepare_schedule_handoffs(explorer_payload=payload, store=store, output_root=tmp_path / "a", environment=UNIT_TEST)
    prepare_schedule_handoffs(explorer_payload=payload, store=store, output_root=tmp_path / "b", environment=UNIT_TEST)
    oc = observation_counts(store.list_analysis_observations())
    assert len(store.list_canonical_signals()) == 20
    assert oc["analysis_observations_generated_n"] == 200
    store.close()


def test_envelope_contains_canonical_signal_id(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(4)
    res = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "e",
        environment=UNIT_TEST, jobs=list(ANALYSIS_TYPES),
    )
    pkg = Path(res["package_dir"])
    schema = json.loads((pkg / "common" / "chatgpt_result_schema.json").read_text())
    assert schema["result_envelope_version"] == RESULT_ENVELOPE_VERSION
    man = json.loads((pkg / "manifest.json").read_text())
    assert man["result_envelope_version"] == RESULT_ENVELOPE_VERSION
    for job, fname in {
        ANALYSIS_MACRO: "macro_holdings.md",
        ANALYSIS_PREMARKET: "premarket_catalysts.md",
        ANALYSIS_INTRADAY: "intraday_opportunity.md",
        ANALYSIS_VALUE: "value_quality.md",
        ANALYSIS_WEEKLY: "weekly_xray.md",
    }.items():
        text = (pkg / "jobs" / fname).read_text(encoding="utf-8")
        assert "canonical_signal_id" in text
        assert RESULT_ENVELOPE_VERSION in text
        if job != ANALYSIS_WEEKLY:
            assert "RAYA" in text or "EGCH" in text
    cands = json.loads((pkg / "common" / "explorer_snapshot.json").read_text())["candidates"]
    for c in cands:
        assert c.get("canonical_signal_id")
        assert c.get("market_state_fingerprint")
        assert c.get("explorer_run_id")
        assert c.get("schedule_run_id")
    store.close()


def test_explicit_canonical_import_links(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(2, explorer_run_id="xr_env")
    res = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "i",
        environment=UNIT_TEST, jobs=[ANALYSIS_PREMARKET],
    )
    raya = next(s for s in store.list_canonical_signals() if s["ticker"] == "RAYA")
    raw = json.dumps({
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "analysis_type": ANALYSIS_PREMARKET,
        "run_id": res["run_id"],
        "candidates": [{
            "ticker": "RAYA",
            "canonical_signal_id": raya["canonical_signal_id"],
            "signal_family_id": raya.get("signal_family_id"),
            "parent_signal_id": raya.get("parent_signal_id"),
            "status": "PROMOTE",
            "catalyst_status": "POSITIVE_CONFIRMED",
        }],
    })
    src = tmp_path / "in.md"
    src.write_text("prose\n```json\n" + raw + "\n```\n", encoding="utf-8")
    out = import_schedule_result(src, analysis_type=ANALYSIS_PREMARKET, run_id=res["run_id"], store=store)
    assert out["candidate_linkages"][0]["linkage_method"] == LINKAGE_EXPLICIT
    oc = observation_counts(store.list_analysis_observations())
    assert oc["analysis_observations_generated_n"] == 2
    assert oc["analysis_observations_imported_n"] == 1
    assert oc["analysis_observations_evaluable_n"] == 1
    store.close()


def test_ticker_mismatch_rejected(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(2)
    res = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "i",
        environment=UNIT_TEST, jobs=[ANALYSIS_PREMARKET],
    )
    raya = next(s for s in store.list_canonical_signals() if s["ticker"] == "RAYA")
    raw = json.dumps({
        "analysis_type": ANALYSIS_PREMARKET, "run_id": res["run_id"],
        "candidates": [{"ticker": "EGCH", "canonical_signal_id": raya["canonical_signal_id"], "status": "KEEP"}],
    })
    src = tmp_path / "bad.md"
    src.write_text("```json\n" + raw + "\n```", encoding="utf-8")
    out = import_schedule_result(src, analysis_type=ANALYSIS_PREMARKET, run_id=res["run_id"], store=store)
    assert out["candidate_linkages"][0]["linkage_method"] == LINKAGE_INVALID
    assert out["candidate_linkages"][0]["reason"] == "ticker_mismatch"
    oc = observation_counts(store.list_analysis_observations())
    assert oc["analysis_observations_imported_n"] == 0
    store.close()


def test_invalid_canonical_id_rejected(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(2)
    res = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "i",
        environment=UNIT_TEST, jobs=[ANALYSIS_PREMARKET],
    )
    raw = json.dumps({
        "analysis_type": ANALYSIS_PREMARKET, "run_id": res["run_id"],
        "candidates": [{"ticker": "RAYA", "canonical_signal_id": "does-not-exist", "status": "KEEP"}],
    })
    src = tmp_path / "bad.md"
    src.write_text("```json\n" + raw + "\n```", encoding="utf-8")
    out = import_schedule_result(src, analysis_type=ANALYSIS_PREMARKET, run_id=res["run_id"], store=store)
    assert out["candidate_linkages"][0]["linkage_method"] == LINKAGE_INVALID
    store.close()


def test_ambiguous_fallback_rejected(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    # Two sessions → two canonicals for RAYA
    prepare_schedule_handoffs(
        explorer_payload=_payload(1, explorer_run_id="xr_s1", session="2026-09-03"),
        store=store, output_root=tmp_path / "s1", environment=UNIT_TEST, jobs=[ANALYSIS_PREMARKET],
    )
    prepare_schedule_handoffs(
        explorer_payload=_payload(1, explorer_run_id="xr_s2", session="2026-09-04"),
        store=store, output_root=tmp_path / "s2", environment=UNIT_TEST, jobs=[ANALYSIS_PREMARKET],
    )
    link = resolve_import_linkage(
        store, {"ticker": "EGCH"}, analysis_type=ANALYSIS_PREMARKET, schedule_run_id=None,
    )
    assert link["linkage_method"] == LINKAGE_AMBIGUOUS
    store.close()


def test_unambiguous_fallback_labeled(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(2)
    res = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "i",
        environment=UNIT_TEST, jobs=[ANALYSIS_PREMARKET],
    )
    raw = json.dumps({
        "analysis_type": ANALYSIS_PREMARKET, "run_id": res["run_id"],
        "candidates": [{"ticker": "RAYA", "status": "KEEP", "catalyst_status": "NEUTRAL"}],
    })
    src = tmp_path / "fb.md"
    src.write_text("```json\n" + raw + "\n```", encoding="utf-8")
    out = import_schedule_result(src, analysis_type=ANALYSIS_PREMARKET, run_id=res["run_id"], store=store)
    assert out["candidate_linkages"][0]["linkage_method"] == LINKAGE_FALLBACK
    store.close()


def test_outcomes_one_per_canonical_not_per_observation(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    db = Database(tmp_path / "m.sqlite")
    payload = _payload(3, explorer_run_id="xr_out")
    prepare_schedule_handoffs(explorer_payload=payload, store=store, output_root=tmp_path / "s", environment=UNIT_TEST)
    for t in ("EGCH", "RAYA", "ALCN"):
        for i, close in enumerate([10, 11, 10.5, 12, 11.8, 13]):
            day = 3 + i
            ts = f"2026-09-{day:02d}T00:00:00+00:00"
            db.upsert_candle({
                "symbol": t, "interval": "1d", "timestamp": ts,
                "normalized_utc_timestamp": ts, "open": close, "high": close + 0.4,
                "low": close - 0.2, "close": close, "volume": 1000,
                "provider": "yahoo", "capture_timestamp": "2026-09-10T00:00:00+00:00",
                "session_date": ts[:10],
            })
    res = update_outcomes_for_store(store, db, pending_only=True)
    assert res["scanner_sample_n"] == 3
    assert len(store.list_canonical_outcomes()) == 3
    assert observation_counts(store.list_analysis_observations())["analysis_observations_generated_n"] >= 15
    store.close()
    db.close()


def test_v051_calibrated_scores_unchanged_for_fixed_fixture():
    assert SCORING_VERSION == "0.5.1"
    assert SCORE_KIND == "HEURISTIC_UNCALIBRATED"
    metrics = {
        "available": True, "daily_return_pct": 1, "return_1w_pct": 2, "return_1m_pct": 4,
        "return_3m_pct": 8, "return_6m_pct": 12, "rvol_20": 1.4, "dist_from_20d_high_pct": -3,
        "last_close": 10, "sma_20": 9.7, "sma_50": 9.4, "breakout_20d": False, "breakout_60d": False,
        "realized_vol_20d_ann_pct": 32, "bars": 80,
    }
    a = calibrate_candidate(dict(metrics))
    b = calibrate_candidate(dict(metrics))
    assert a["candidate_score_calibrated"] == b["candidate_score_calibrated"]
    assert a["FORWARD_SETUP_QUALITY"] == b["FORWARD_SETUP_QUALITY"]
    assert a["MOVE_ALREADY_REALIZED"] == b["MOVE_ALREADY_REALIZED"]
