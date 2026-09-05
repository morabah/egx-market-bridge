"""v0.6.4 Daily Operator workflow state, version labels, and session safety."""
from __future__ import annotations

from pathlib import Path
import json

from egxbridge import DATA_LAYER_VERSION, __version__ as APP_VERSION
from egxbridge.analysis import SCORING_VERSION, WORKFLOW_VERSION
from egxbridge.analysis.explorer.calibration import SCORE_KIND, calibrate_candidate
from egxbridge.analysis.schedule.identity import canonical_signal_id, market_state_fingerprint
from egxbridge.analysis.schedule.outcomes import compute_outcomes
from egxbridge.ui import ALL_PAGES, DEFAULT_PAGE, OPERATE_PAGES, TECHNICAL_PAGES
from egxbridge.ui.candidates import candidate_preview_rows, filter_candidates
from egxbridge.ui.snapshot import gather_operator_snapshot, resolve_explorer_package
from egxbridge.ui.versions import version_caption, version_labels
from egxbridge.ui.theme import chip_tone
from egxbridge.ui.workflow_state import (
    ACTION_CTA,
    ACTION_EXPORT_OR_IMPORT,
    ACTION_IMPORT_CHATGPT,
    ACTION_FUNNEL,
    ACTION_INTRADAY,
    ACTION_PREPARE_NEXT_SESSION,
    ACTION_REFRESH_MARKET_DATA,
    ACTION_REVIEW_CANDIDATES,
    ACTION_RUN_EXPLORER,
    ACTION_UPDATE_OUTCOMES,
    ACTION_WAIT,
    ACTION_WEEKLY,
    action_hint,
    explorer_status,
    explorer_should_enrich_intraday,
    focus_steps,
    funnel_buttons_for_status,
    freshness_state,
    intraday_card_state,
    next_recommended_action,
    recommended_jobs,
    should_skip_market_refresh,
    workflow_stage,
)


WEEKEND_META = {
    "session_phase": "POST_CLOSE",
    "analysis_timestamp_utc": "2026-09-05T13:00:00+00:00",
    "analysis_timestamp_cairo": "2026-09-05T16:00:00+03:00",
}
PREOPEN_META = {
    "session_phase": "PRE_OPEN",
    "analysis_timestamp_utc": "2026-09-03T06:30:00+00:00",
    "analysis_timestamp_cairo": "2026-09-03T09:30:00+03:00",
}
LIVE_META = {
    "session_phase": "CONTINUOUS_TRADING",
    "analysis_timestamp_utc": "2026-09-03T08:20:00+00:00",
    "analysis_timestamp_cairo": "2026-09-03T11:20:00+03:00",
}


def _cand(**kwargs):
    row = {
        "ticker": "RAYA",
        "last_close": 2.62,
        "FORWARD_SETUP_QUALITY": "STRONG",
        "MOVE_ALREADY_REALIZED": "LOW",
        "candidate_lane": "LANE_A_EARLY_PRE_IGNITION",
        "candidate_score_calibrated": 80.0,
        "calibrated_rank": 1,
        "rvol_20": 1.4,
        "VOLATILITY_RISK": "LOW",
        "funnel_status": "NOT_FOUND",
        "intraday_available": True,
    }
    row.update(kwargs)
    return row


def _snap(**kw):
    base = {
        "data_usable": True,
        "explorer_status": "READY",
        "schedules_prepared": False,
        "recommended_imported_n": 0,
        "recommended_jobs_n": 3,
        "funnel_action_required": False,
        "intraday": {"live": False, "actionable": False, "status": "NOT_LIVE"},
        "outcomes_pending_n": 20,
        "outcomes_update_recommended": False,
        "weekend": True,
        "weekly_recommended": False,
        "weekly_imported": False,
        "candidate_count": 20,
    }
    base.update(kw)
    return base


def test_default_page_is_daily_operator():
    assert DEFAULT_PAGE == "Daily Operator"
    assert ALL_PAGES[0] == "Daily Operator"
    assert ALL_PAGES[1] == "Explorer Candidates"
    assert "System Overview" in ALL_PAGES
    assert "Overview" not in ALL_PAGES
    assert OPERATE_PAGES[-1] == "Signal Outcomes"
    assert TECHNICAL_PAGES[0] == "Whole Market"


def test_version_labels_are_not_ambiguous():
    lab = version_labels()
    assert lab["application_version"] == APP_VERSION == "0.7.0"
    assert lab["market_data_schema_version"] == DATA_LAYER_VERSION == "0.3.1"
    assert lab["scoring_version"] == SCORING_VERSION == "0.5.1"
    assert lab["workflow_version"] == WORKFLOW_VERSION == "0.7.0"
    assert lab["score_kind"] == SCORE_KIND == "HEURISTIC_UNCALIBRATED"
    caption = version_caption(lab)
    assert "Application: 0.7.0" in caption
    assert "Market Data Schema: 0.3.1" in caption
    assert "Scoring: 0.5.1" in caption
    assert "Version:" not in caption
    assert lab["title"] == "EGX Market Bridge v0.7.0"


def test_next_action_no_market_data():
    nxt = next_recommended_action(_snap(data_usable=False, explorer_status="NOT_RUN"))
    assert nxt["code"] == ACTION_REFRESH_MARKET_DATA
    assert workflow_stage(_snap(data_usable=False)) == "DATA_NOT_READY"


def test_next_action_data_ready_no_explorer():
    nxt = next_recommended_action(_snap(explorer_status="NOT_RUN"))
    assert nxt["code"] == ACTION_RUN_EXPLORER


def test_next_action_explorer_ready_no_schedules():
    nxt = next_recommended_action(_snap(explorer_status="READY", schedules_prepared=False))
    assert nxt["code"] == ACTION_PREPARE_NEXT_SESSION


def test_next_action_schedules_ready_imports_missing():
    nxt = next_recommended_action(_snap(
        explorer_status="READY", schedules_prepared=True,
        recommended_imported_n=0, recommended_jobs_n=3,
    ))
    assert nxt["code"] == ACTION_EXPORT_OR_IMPORT
    nxt_partial = next_recommended_action(_snap(
        explorer_status="READY", schedules_prepared=True,
        recommended_imported_n=1, recommended_jobs_n=3,
    ))
    assert nxt_partial["code"] == ACTION_IMPORT_CHATGPT
    nxt_ready = next_recommended_action(_snap(
        explorer_status="READY", schedules_prepared=True,
        recommended_imported_n=0, recommended_jobs_n=3,
        ready_to_import=True,
    ))
    assert nxt_ready["code"] == ACTION_IMPORT_CHATGPT


def test_next_action_funnel_required_after_imports():
    nxt = next_recommended_action(_snap(
        explorer_status="READY", schedules_prepared=True,
        recommended_imported_n=3, recommended_jobs_n=3,
        funnel_action_required=True,
    ))
    assert nxt["code"] == ACTION_FUNNEL


def test_next_action_live_intraday():
    nxt = next_recommended_action(_snap(
        explorer_status="READY", schedules_prepared=True,
        recommended_imported_n=1, recommended_jobs_n=1, weekend=False,
        funnel_action_required=False,
        intraday={"live": True, "actionable": True, "status": "READY"},
    ))
    assert nxt["code"] == ACTION_INTRADAY


def test_next_action_outcomes_when_recommended():
    nxt = next_recommended_action(_snap(
        explorer_status="READY", schedules_prepared=True,
        recommended_imported_n=3, recommended_jobs_n=3,
        weekend=False, outcomes_update_recommended=True, outcomes_pending_n=20,
        weekly_recommended=False,
        intraday={"live": False, "actionable": False, "status": "NOT_LIVE"},
    ))
    assert nxt["code"] == ACTION_UPDATE_OUTCOMES


def test_next_action_weekly_when_recommended():
    nxt = next_recommended_action(_snap(
        explorer_status="READY", schedules_prepared=True,
        recommended_imported_n=3, recommended_jobs_n=3,
        weekly_recommended=True, weekly_imported=False,
        outcomes_update_recommended=False,
        weekend=False,
        intraday={"live": False, "actionable": False, "status": "NOT_LIVE"},
    ))
    assert nxt["code"] == ACTION_WEEKLY


def test_weekend_pending_outcomes_wait():
    nxt = next_recommended_action(_snap(
        explorer_status="READY", schedules_prepared=True,
        recommended_imported_n=3, recommended_jobs_n=3,
        weekend=True, outcomes_pending_n=20, outcomes_update_recommended=False,
        weekly_recommended=False,
    ))
    assert nxt["code"] == ACTION_WAIT


def test_explorer_not_stale_just_because_weekend_passed():
    status = explorer_status(
        has_explorer=True, candidate_count=20,
        explorer_session="2026-09-03", market_session="2026-09-03",
    )
    assert status == "READY"
    stale = explorer_status(
        has_explorer=True, candidate_count=20,
        explorer_session="2026-07-28", market_session="2026-09-03",
    )
    assert stale == "STALE"


def test_freshness_stale_expected_is_normal_when_closed():
    assert freshness_state(session_phase="POST_CLOSE") == "STALE_EXPECTED"
    assert freshness_state(session_phase="PRE_OPEN") == "STALE_EXPECTED"
    assert freshness_state(session_phase="CONTINUOUS_TRADING", unexpected_stale=True) == "UNEXPECTED_STALE"
    assert freshness_state(session_phase="CONTINUOUS_TRADING") == "LIVE"


def test_intraday_session_safety():
    post = intraday_card_state(session_phase="POST_CLOSE", age_seconds=120)
    assert post["live"] is False and post["actionable"] is False and post["status"] == "NOT_LIVE"
    pre = intraday_card_state(session_phase="PRE_OPEN", age_seconds=60)
    assert pre["status"] == "NOT_LIVE"
    live = intraday_card_state(session_phase="CONTINUOUS_TRADING", age_seconds=120)
    assert live["status"] == "READY" and live["actionable"] is True
    stale = intraday_card_state(session_phase="CONTINUOUS_TRADING", age_seconds=480)
    assert stale["status"] == "STALE" and stale["actionable"] is False


def test_recommended_jobs_post_close_and_live():
    post = recommended_jobs(session_phase="POST_CLOSE", cairo_weekday=5)
    assert post["recommended"] == ["MACRO_HOLDINGS", "PREMARKET_CATALYSTS", "VALUE_QUALITY"]
    assert post["intraday_live"] is False
    assert post["weekly_recommended"] is True
    live = recommended_jobs(session_phase="CONTINUOUS_TRADING", cairo_weekday=2)
    assert live["recommended"] == ["INTRADAY_OPPORTUNITY"]
    assert live["intraday_live"] is True
    pre = recommended_jobs(session_phase="PRE_OPEN", cairo_weekday=2)
    assert "MACRO_HOLDINGS" in pre["recommended"]
    assert pre["intraday_live"] is False


def test_focus_steps_follow_next_action():
    assert focus_steps(ACTION_REFRESH_MARKET_DATA) == {1}
    assert focus_steps(ACTION_RUN_EXPLORER) == {2}
    assert focus_steps(ACTION_REVIEW_CANDIDATES) == {3}
    assert focus_steps(ACTION_PREPARE_NEXT_SESSION) == {4}
    assert focus_steps(ACTION_EXPORT_OR_IMPORT) == {5}
    assert focus_steps(ACTION_IMPORT_CHATGPT) == {6}
    assert focus_steps(ACTION_FUNNEL) == {7}
    assert focus_steps(ACTION_INTRADAY) == {8}
    assert focus_steps(ACTION_UPDATE_OUTCOMES) == {9}
    assert focus_steps(ACTION_WAIT) == {9}
    assert focus_steps(ACTION_WEEKLY) == {10}
    assert focus_steps(None) == {1}
    assert ACTION_CTA[ACTION_WAIT] is None
    closed = _snap(
        data_usable=True,
        scanner_eligible=110,
        daily_data_available=111,
        freshness="STALE_EXPECTED",
        session_phase="POST_CLOSE",
    )
    hint = action_hint(ACTION_REFRESH_MARKET_DATA, closed)
    assert "Yahoo" in hint
    assert chip_tone("PREPARED / NOT IMPORTED") == "mute"
    assert chip_tone("READY") == "ok"
    assert chip_tone("ACTION REQUIRED: 2") == "warn"
    assert chip_tone("FAILED") == "bad"
    assert chip_tone("0/5 IMPORTED") == "mute"
    assert chip_tone("2/5 IMPORTED") == "warn"
    assert chip_tone("5/5 IMPORTED") == "ok"


def test_export_and_import_copy_do_not_compete():
    from egxbridge.ui.workflow_state import action_steps
    export = " ".join(action_steps(ACTION_EXPORT_OR_IMPORT)).lower()
    assert "egx_chatgpt_handoff.zip" in export
    assert "do not import the zip" in export
    assert "funnel" in export
    assert ACTION_CTA[ACTION_EXPORT_OR_IMPORT] == "Download EGX_CHATGPT_HANDOFF.zip"
    imported = " ".join(action_steps(ACTION_IMPORT_CHATGPT)).lower()
    assert "do not upload egx_chatgpt_handoff.zip" in imported
    assert ACTION_CTA[ACTION_IMPORT_CHATGPT] == "Import this ChatGPT file"
    assert focus_steps(ACTION_EXPORT_OR_IMPORT) == {5}
    assert focus_steps(ACTION_IMPORT_CHATGPT) == {6}


def test_closed_market_skips_yahoo_and_tradingview():
    closed = _snap(
        data_usable=True,
        scanner_eligible=110,
        daily_data_available=111,
        freshness="STALE_EXPECTED",
        session_phase="POST_CLOSE",
    )
    assert should_skip_market_refresh(closed) is True
    assert explorer_should_enrich_intraday("POST_CLOSE") is False
    assert explorer_should_enrich_intraday("PRE_OPEN") is False
    assert explorer_should_enrich_intraday("CONTINUOUS_TRADING") is True
    assert explorer_should_enrich_intraday("POST_CLOSE", force=True) is True
    empty = _snap(data_usable=False, scanner_eligible=0, daily_data_available=0, freshness="STALE_EXPECTED")
    assert should_skip_market_refresh(empty) is False


def test_funnel_buttons_guards():
    assert funnel_buttons_for_status("NOT_FOUND")[0] == "PREPARE_FULL_FUNNEL"
    assert "CONTINUE_FUNNEL" in funnel_buttons_for_status("PARTIAL")
    assert "PREPARE_DELTA" in funnel_buttons_for_status("NEEDS_DELTA")
    complete = funnel_buttons_for_status("COMPLETE")
    assert complete == ["VIEW_FUNNEL"]
    current = funnel_buttons_for_status("CURRENT")
    assert current == ["VIEW_FUNNEL"]


def test_candidate_preview_does_not_imply_probability():
    rows = candidate_preview_rows([_cand(), _cand(ticker="EGCH", calibrated_rank=2)])
    assert rows[0]["Ticker"] == "RAYA"
    assert "Probability" not in rows[0]
    filtered = filter_candidates([_cand(), _cand(ticker="MASR", candidate_lane="LANE_B")], lane="LANE_A_EARLY_PRE_IGNITION")
    assert [c["ticker"] for c in filtered] == ["RAYA"]


def test_gather_empty_root_next_action_is_refresh(tmp_path: Path):
    snap = gather_operator_snapshot(root=tmp_path, session_meta=WEEKEND_META)
    assert snap["versions"]["application_version"] == "0.7.0"
    assert snap["versions"]["market_data_schema_version"] == "0.3.1"
    assert snap["next_action"]["code"] == ACTION_REFRESH_MARKET_DATA
    assert snap["intraday"]["status"] == "NOT_LIVE"
    assert snap["freshness"] == "STALE_EXPECTED"


def test_gather_handoff_only_next_is_explorer(tmp_path: Path):
    out = tmp_path / "output"
    out.mkdir()
    (out / "chatgpt_handoff.json").write_text(json.dumps({
        "generated_at": "2026-09-05T12:00:00+00:00",
        "version": "0.3.1",
        "status": "PARTIAL",
        "symbols": [{"symbol": "MASR", "quote": {"session_date": "2026-09-03", "freshness_class": "STALE_EXPECTED"}}],
    }), encoding="utf-8")
    snap = gather_operator_snapshot(root=tmp_path, session_meta=WEEKEND_META)
    assert snap["market_data_status"] == "READY_WITH_LIMITATIONS"
    assert snap["provider_status"] == "PARTIAL"
    assert snap["next_action"]["code"] == ACTION_RUN_EXPLORER
    assert snap["handoff_status"] == "PARTIAL"


def test_gather_explorer_ready_prepare_schedules(tmp_path: Path):
    pkg = tmp_path / "output" / "explorer_handoff"
    pkg.mkdir(parents=True)
    (pkg / "explorer_handoff.json").write_text(json.dumps({
        "explorer_run_id": "xr_test",
        "generated_at": "2026-09-05T11:00:00+00:00",
        "latest_completed_market_session": "2026-09-03",
        "scoring_version": "0.5.1",
        "counts": {
            "EQUITY_UNIVERSE_TOTAL": 135,
            "DAILY_DATA_AVAILABLE": 111,
            "SCANNER_ELIGIBLE_SYMBOLS": 110,
            "PRESCREEN_SELECTED": 30,
            "HANDOFF_CANDIDATES": 20,
            "INTRADAY_ENRICHED": 12,
        },
        "coverage": {"EXPLORER_COVERAGE": "HIGH"},
        "candidates": [_cand(ticker=f"T{i:02d}", calibrated_rank=i + 1) for i in range(20)],
    }), encoding="utf-8")
    snap = gather_operator_snapshot(root=tmp_path, session_meta=WEEKEND_META)
    assert snap["explorer_status"] == "READY"
    assert snap["candidate_count"] == 20
    assert snap["next_action"]["code"] == ACTION_PREPARE_NEXT_SESSION
    assert snap["intraday"]["status"] == "NOT_LIVE"
    assert "MACRO_HOLDINGS" in snap["recommended_jobs"]


def test_ignores_pytest_last_run_leftovers(tmp_path: Path):
    pytest_pkg = tmp_path / "pytest-of-agent" / "exp"
    pytest_pkg.mkdir(parents=True)
    (pytest_pkg / "explorer_handoff.json").write_text(json.dumps({
        "candidates": [{"ticker": "X"}],
        "latest_completed_market_session": "2026-07-28",
    }), encoding="utf-8")
    ws = tmp_path / "workspace" / "explorer"
    ws.mkdir(parents=True)
    (ws / "last_run.json").write_text(json.dumps({
        "package_dir": str(pytest_pkg),
        "explorer_run_id": "xr_pytest",
        "counts": {"HANDOFF_CANDIDATES": 1, "EQUITY_UNIVERSE_TOTAL": 1},
    }), encoding="utf-8")
    v06 = tmp_path / "output" / "acceptance" / "v06" / "explorer_handoff"
    v06.mkdir(parents=True, exist_ok=True)
    (v06 / "explorer_handoff.json").write_text(json.dumps({
        "latest_completed_market_session": "2026-09-03",
        "candidates": [{"ticker": f"T{i}"} for i in range(20)],
        "counts": {"HANDOFF_CANDIDATES": 20, "EQUITY_UNIVERSE_TOTAL": 135, "SCANNER_ELIGIBLE_SYMBOLS": 110},
    }), encoding="utf-8")
    exp = resolve_explorer_package(tmp_path)
    assert len(exp["candidates"]) == 20
    assert exp["latest_session"] == "2026-09-03"
    assert exp.get("explorer_run_id") != "xr_pytest"
    alias = tmp_path / "output" / "explorer_handoff"
    alias.mkdir(parents=True)
    (alias / "explorer_handoff.json").write_text(json.dumps({
        "candidates": [{"ticker": "MASR"}],
        "handoff_candidate_count": 1,
    }), encoding="utf-8")
    v06 = tmp_path / "output" / "acceptance" / "v06" / "explorer_handoff"
    v06.mkdir(parents=True, exist_ok=True)
    (v06 / "explorer_handoff.json").write_text(json.dumps({
        "latest_completed_market_session": "2026-09-03",
        "candidates": [{"ticker": f"T{i}"} for i in range(20)],
        "counts": {"HANDOFF_CANDIDATES": 20},
    }), encoding="utf-8")
    exp = resolve_explorer_package(tmp_path)
    assert len(exp["candidates"]) == 20
    assert exp["package_dir"] == str(v06)


def test_chatgpt_handoff_zip_alias(tmp_path: Path):
    from egxbridge.ui.actions import CHATGPT_HANDOFF_ZIP_NAME, publish_chatgpt_handoff_zip
    src = tmp_path / "schedule.zip"
    src.write_bytes(b"zip-bytes")
    dest = publish_chatgpt_handoff_zip(src, root=tmp_path)
    assert dest == tmp_path / "output" / CHATGPT_HANDOFF_ZIP_NAME
    assert dest.read_bytes() == b"zip-bytes"
    assert publish_chatgpt_handoff_zip(None, root=tmp_path) is None


def test_scoring_identity_outcomes_untouched():
    assert SCORING_VERSION == "0.5.1"
    assert SCORE_KIND == "HEURISTIC_UNCALIBRATED"
    metrics = {
        "available": True, "last_close": 10.0, "daily_return_pct": 1.0,
        "return_1w_pct": 2.0, "return_1m_pct": 3.0, "return_3m_pct": 4.0,
        "return_6m_pct": 5.0, "rvol_20": 1.5, "dist_from_20d_high_pct": -1.0,
        "dist_from_60d_high_pct": -2.0, "sma_20": 9.8, "sma_50": 9.5,
        "breakout_20d": False, "breakout_60d": False, "bars": 80,
        "atr_14": 0.2, "realized_vol_20d_ann_pct": 20.0,
    }
    a = calibrate_candidate(metrics)
    b = calibrate_candidate(metrics)
    assert a["candidate_score_calibrated"] == b["candidate_score_calibrated"]
    assert a.get("scoring_version") == "0.5.1" or SCORING_VERSION == "0.5.1"
    cand = _cand(last_close=2.62, daily_return_pct=1.0)
    fp1 = market_state_fingerprint(
        cand, environment="UNIT_TEST", ticker="RAYA",
        market_session_basis="2026-09-03", scoring_version="0.5.1",
        signal_origin="EXPLORER",
    )
    fp2 = market_state_fingerprint(
        cand, environment="UNIT_TEST", ticker="RAYA",
        market_session_basis="2026-09-03", scoring_version="0.5.1",
        signal_origin="EXPLORER",
    )
    assert fp1 == fp2
    id1 = canonical_signal_id(
        environment="UNIT_TEST", ticker="RAYA", market_session_basis="2026-09-03",
        scoring_version="0.5.1", signal_origin="EXPLORER",
        market_state_fingerprint_value=fp1, candidate=cand,
    )
    id2 = canonical_signal_id(
        environment="UNIT_TEST", ticker="RAYA", market_session_basis="2026-09-03",
        scoring_version="0.5.1", signal_origin="EXPLORER",
        market_state_fingerprint_value=fp2, candidate=cand,
    )
    assert id1 == id2
    future = [
        {"session_date": "2026-01-02", "close": 10, "high": 10.2, "low": 9.9},
        {"session_date": "2026-01-05", "close": 11, "high": 11.5, "low": 9.8},
        {"session_date": "2026-01-06", "close": 10.5, "high": 12.0, "low": 10.2},
        {"session_date": "2026-01-07", "close": 12.0, "high": 12.2, "low": 10.4},
        {"session_date": "2026-01-08", "close": 11.8, "high": 12.1, "low": 11.0},
        {"session_date": "2026-01-09", "close": 13.0, "high": 13.2, "low": 11.7},
    ]
    pos = compute_outcomes(
        baseline_price=10, baseline_timestamp="2026-01-02", baseline_type="OFFICIAL_CLOSE",
        signal_session="2026-01-02", future_bars=future,
    )
    assert pos["next_session_return"] == 10.0
    assert pos["return_3_sessions"] == 20.0
    assert pos["return_5_sessions"] == 30.0
    assert pos["scoring_version_untouched"] == "0.5.1"
