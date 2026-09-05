"""Canonical signal identity — no double-counting for calibration. scoring_version frozen."""
from __future__ import annotations

from pathlib import Path

from egxbridge.analysis.common.environment import UNIT_TEST
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.intraday_select import LANE_A, LANE_C
from egxbridge.analysis.schedule.handoff import prepare_schedule_handoffs
from egxbridge.analysis.schedule.identity import (
    make_explorer_run_id, explorer_canonical_id, resolve_signal_identity,
    ORIGIN_INTRADAY,
)
from egxbridge.analysis.schedule.importer import import_schedule_result
from egxbridge.analysis.schedule.outcomes import compute_outcomes, update_outcomes_for_store
from egxbridge.analysis.schedule.snapshots import build_signal_snapshot, persist_snapshots
from egxbridge.analysis.schedule.types import (
    ANALYSIS_PREMARKET, ANALYSIS_VALUE, ANALYSIS_INTRADAY, ANALYSIS_EXPLORER, ANALYSIS_TYPES,
)
from egxbridge.db import Database


def _cand(ticker, lane=LANE_A, quality="STRONG", score=80.0, **kwargs):
    row = {
        "ticker": ticker,
        "candidate_lane": lane,
        "FORWARD_SETUP_QUALITY": quality,
        "MOVE_ALREADY_REALIZED": "LOW",
        "candidate_score_calibrated": score,
        "calibrated_rank": kwargs.pop("rank", 1),
        "last_close": kwargs.pop("last_close", 10.0),
        "available": True,
    }
    row.update(kwargs)
    return row


def _payload(n=20, explorer_run_id="xr_fixed_test", session="2026-09-03"):
    tickers = ["EGCH", "RAYA", "ALCN", "MASR"] + [f"T{i:02d}" for i in range(n - 4)]
    return {
        "explorer_run_id": explorer_run_id,
        "generated_at": "2026-09-03T16:00:00+00:00",
        "latest_completed_market_session": session,
        "counts": {
            "EQUITY_UNIVERSE_TOTAL": 135, "HANDOFF_CANDIDATES": n,
            "funnel_coverage_n": 135, "funnel_coverage_denominator": 135,
        },
        "coverage": {"EXPLORER_COVERAGE": "HIGH", "selection_basis": "BROAD_UNIVERSE"},
        "candidates": [_cand(t, rank=i + 1, score=90 - i) for i, t in enumerate(tickers[:n])],
    }


def test_multiple_jobs_reuse_canonical_signal(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(20)
    res = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "s1",
        environment=UNIT_TEST, jobs=list(ANALYSIS_TYPES),
    )
    canonical = store.list_canonical_signals()
    obs = store.list_analysis_observations()
    assert res["canonical_signals_n"] == 20
    assert len(canonical) == 20
    assert len(obs) > 20
    assert len(obs) == 20 * 5
    raya = [c for c in canonical if c["ticker"] == "RAYA"]
    egch = [c for c in canonical if c["ticker"] == "EGCH"]
    assert len(raya) == 1 and len(egch) == 1
    raya_obs = store.list_analysis_observations(canonical_signal_id=raya[0]["canonical_signal_id"])
    types = {o["analysis_type"] for o in raya_obs}
    assert ANALYSIS_PREMARKET in types
    assert ANALYSIS_VALUE in types
    assert raya_obs[0]["canonical_signal_id"] == raya[0]["canonical_signal_id"]
    store.close()


def test_repeated_packaging_does_not_inflate_scanner_n(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(20)
    prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "a", environment=UNIT_TEST,
    )
    n1 = len(store.list_canonical_signals())
    o1 = len(store.list_analysis_observations())
    prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "b", environment=UNIT_TEST,
    )
    n2 = len(store.list_canonical_signals())
    o2 = len(store.list_analysis_observations())
    assert n1 == 20 and n2 == 20
    assert o2 > o1
    store.close()


def test_premarket_and_value_share_canonical(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(4, explorer_run_id="xr_share")
    prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "p",
        environment=UNIT_TEST, jobs=[ANALYSIS_PREMARKET],
    )
    prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "v",
        environment=UNIT_TEST, jobs=[ANALYSIS_VALUE],
    )
    assert len(store.list_canonical_signals()) == 4
    raya = next(c for c in store.list_canonical_signals() if c["ticker"] == "RAYA")
    cid = raya["canonical_signal_id"]
    obs = store.list_analysis_observations(canonical_signal_id=cid)
    assert {o["analysis_type"] for o in obs} >= {ANALYSIS_PREMARKET, ANALYSIS_VALUE}
    store.close()


def test_outcome_attaches_once_to_canonical(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    db = Database(tmp_path / "m.sqlite")
    payload = _payload(3, explorer_run_id="xr_out")
    prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "s", environment=UNIT_TEST,
    )
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
    outs = store.list_canonical_outcomes()
    assert len(outs) == 3
    raya = next(o for o in outs if o["ticker"] == "RAYA")
    assert raya["next_session_return"] == 10.0
    assert raya["canonical_signal_id"]
    # Five jobs did not mint five outcome rows.
    assert len(store.list_analysis_observations(ticker="RAYA")) >= 5
    store.close()
    db.close()


def test_intraday_material_state_creates_child_with_parent(tmp_path: Path):
    parent = resolve_signal_identity(
        {"ticker": "RAYA", "last_close": 2.5},
        environment=UNIT_TEST, explorer_run_id="xr_lin", latest_session="2026-09-03",
        analysis_type=ANALYSIS_EXPLORER, price_basis="OFFICIAL_CLOSE",
    )
    child = resolve_signal_identity(
        {"ticker": "RAYA", "last_close": 2.5, "current_session_price": 2.62,
         "intraday": {"current_session_price": 2.62, "current_session": True}},
        environment=UNIT_TEST, explorer_run_id="xr_lin", latest_session="2026-09-03",
        analysis_type=ANALYSIS_INTRADAY, price_basis="CURRENT_INTRADAY_PRICE",
        session_meta={
            "session_phase": "CONTINUOUS_TRADING",
            "analysis_timestamp_cairo": "2026-09-03T11:20:00+03:00",
            "analysis_timestamp_utc": "2026-09-03T08:20:00+00:00",
        },
    )
    child2 = resolve_signal_identity(
        {"ticker": "RAYA", "last_close": 2.5, "current_session_price": 2.70,
         "intraday": {"current_session_price": 2.70, "current_session": True}},
        environment=UNIT_TEST, explorer_run_id="xr_lin", latest_session="2026-09-03",
        analysis_type=ANALYSIS_INTRADAY, price_basis="CURRENT_INTRADAY_PRICE",
        session_meta={
            "session_phase": "CONTINUOUS_TRADING",
            "analysis_timestamp_cairo": "2026-09-03T13:20:00+03:00",
            "analysis_timestamp_utc": "2026-09-03T10:20:00+00:00",
        },
    )
    assert parent["signal_origin"] != ORIGIN_INTRADAY or parent["canonical_signal_id"] != child["canonical_signal_id"]
    assert child["canonical_signal_id"] != parent["canonical_signal_id"]
    assert child["canonical_signal_id"] != child2["canonical_signal_id"]
    assert child["parent_signal_id"] == parent["canonical_signal_id"]
    assert child["signal_family_id"] == parent["signal_family_id"] == child2["signal_family_id"]
    assert child["signal_origin"] == ORIGIN_INTRADAY
    later_same = resolve_signal_identity(
        {"ticker": "RAYA", "last_close": 2.5, "current_session_price": 2.62,
         "intraday": {"current_session_price": 2.62, "current_session": True}},
        environment=UNIT_TEST, explorer_run_id="xr_lin", latest_session="2026-09-03",
        analysis_type=ANALYSIS_INTRADAY, price_basis="CURRENT_INTRADAY_PRICE",
        session_meta={
            "session_phase": "CONTINUOUS_TRADING",
            "analysis_timestamp_cairo": "2026-09-03T11:25:00+03:00",
            "analysis_timestamp_utc": "2026-09-03T08:25:00+00:00",
        },
    )
    # 11:25 still in the 11:20 bucket with same price → same canonical (not wall-clock seconds).
    assert later_same["canonical_signal_id"] == child["canonical_signal_id"]


def test_weekly_scanner_n_uses_canonical(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(20)
    res = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "w", environment=UNIT_TEST,
    )
    hist = (res.get("manifest") or {})
    # weekly file
    import json
    weekly = json.loads((Path(res["package_dir"]) / "optional" / "calibration_history_summary.json").read_text())
    assert weekly["canonical_signals_n"] == 20
    assert weekly["scanner_sample_n"] == 20
    assert weekly["analysis_observations_n"] > 20
    assert weekly["scanner_performance"]["canonical_signals_n"] == 20
    assert weekly["analysis_value_add"]["evaluation"] == "ANALYSIS_VALUE_ADD"
    assert "analysis_observations_n" in weekly["analysis_value_add"]
    store.close()


def test_chatgpt_value_add_uses_observations(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    payload = _payload(2, explorer_run_id="xr_imp")
    res = prepare_schedule_handoffs(
        explorer_payload=payload, store=store, output_root=tmp_path / "i",
        environment=UNIT_TEST, jobs=[ANALYSIS_PREMARKET],
    )
    before = len(store.list_analysis_observations())
    raw = """prose
```json
{"analysis_type":"PREMARKET_CATALYSTS","run_id":"%s","candidates":[
  {"ticker":"RAYA","status":"PROMOTE","catalyst_status":"POSITIVE_CONFIRMED"},
  {"ticker":"EGCH","status":"DOWNGRADE","catalyst_status":"NEUTRAL"}
]}
```
""" % res["run_id"]
    src = tmp_path / "premarket.md"
    src.write_text(raw, encoding="utf-8")
    import_schedule_result(src, analysis_type=ANALYSIS_PREMARKET, run_id=res["run_id"], store=store)
    after = store.list_analysis_observations()
    assert len(after) >= before
    chat = [o for o in after if o.get("generated_by") == "CHATGPT_HANDOFF"]
    assert chat
    raya_chat = next(o for o in chat if o["ticker"] == "RAYA")
    stored = next(c for c in store.list_canonical_signals() if c["ticker"] == "RAYA")
    assert raya_chat["canonical_signal_id"] == stored["canonical_signal_id"]
    assert raya_chat.get("linkage_method") in {None, "FALLBACK_UNAMBIGUOUS", "EXPLICIT_CANONICAL_ID"} or (
        (raya_chat.get("payload") or {}).get("linkage_method") in {"FALLBACK_UNAMBIGUOUS", "EXPLICIT_CANONICAL_ID"}
    )
    assert raya_chat["chatgpt_status"] == "PROMOTE"
    canon_n = len(store.list_canonical_signals())
    assert canon_n == 2
    store.close()


def test_old_snapshots_remain_immutable(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    snap = build_signal_snapshot(
        {"ticker": "MASR", "candidate_score_calibrated": 70.5, "last_close": 4.2},
        run_id="r0", environment=UNIT_TEST, generated_at="t0",
        latest_session="2026-09-03",
        session_meta={"analysis_timestamp_utc": "t0", "analysis_timestamp_cairo": "t0", "session_phase": "POST_CLOSE"},
        explorer_run_id="xr_imm",
    )
    persist_snapshots(store, [snap])
    original = store.get_signal_snapshot(snap["snapshot_id"])["payload"]
    mutated = dict(snap)
    mutated["candidate_score_calibrated"] = 1
    persist_snapshots(store, [mutated])
    again = store.get_signal_snapshot(snap["snapshot_id"])["payload"]
    assert again["candidate_score_calibrated"] == original["candidate_score_calibrated"]
    canon = store.get_canonical_signal(snap["canonical_signal_id"])
    assert canon["payload"]["candidate_score_calibrated"] == 70.5
    store.close()


def test_wall_clock_seconds_do_not_mint_new_explorer_signal():
    a = make_explorer_run_id(environment=UNIT_TEST, latest_session="2026-09-03", generated_at="pack-A")
    b = make_explorer_run_id(environment=UNIT_TEST, latest_session="2026-09-03", generated_at="pack-A")
    assert a == b
    id1 = explorer_canonical_id(environment=UNIT_TEST, ticker="EGCH", market_session_basis="2026-09-03", explorer_run_id=a)
    id2 = explorer_canonical_id(environment=UNIT_TEST, ticker="EGCH", market_session_basis="2026-09-03", explorer_run_id=a)
    assert id1 == id2
    later_session = explorer_canonical_id(
        environment=UNIT_TEST, ticker="EGCH", market_session_basis="2026-09-04", explorer_run_id=a,
    )
    assert later_session != id1
