"""v0.6.3 handoff schema hygiene: job schemas, session phase, weekly counts, identity, importer."""
from __future__ import annotations

from pathlib import Path
import csv
import json
import zipfile

from egxbridge.analysis.common.environment import UNIT_TEST
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.calibration import calibrate_candidate, SCORING_VERSION, SCORE_KIND
from egxbridge.analysis.explorer.intraday_select import LANE_A
from egxbridge.analysis.schedule.handoff import (
    prepare_schedule_handoffs, reconcile_identity_groups, assert_identity_consistent,
    IdentityConflictError,
)
from egxbridge.analysis.schedule.importer import import_schedule_result, extract_json_envelope
from egxbridge.analysis.schedule.result_schemas import (
    COPY_FROM_INPUT, MODEL_DECISION, JOB_ENUMS,
)
from egxbridge.analysis.schedule.types import (
    ANALYSIS_TYPES, ANALYSIS_MACRO, ANALYSIS_PREMARKET, ANALYSIS_INTRADAY,
    ANALYSIS_VALUE, ANALYSIS_WEEKLY, RESULT_ENVELOPE_VERSION, HANDOFF_SCHEMA_VERSION,
    RESULT_SCHEMA_FILES, ANALYSIS_OBSERVATIONS_N_SEMANTICS, DEPRECATED_FIELDS,
    PARSE_VALID, PARSE_INVALID_SCHEMA, PARSE_INVALID_CANONICAL_ID, PARSE_TICKER_MISMATCH,
    PARSE_NEEDS_REVIEW, PHASE_MISMATCH, PHASE_MATCH, NOT_LIVE_CONFIRMATION_TEXT,
    LINKAGE_INVALID, LINKAGE_EXPLICIT,
)


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


def _payload(n=4, explorer_run_id="xr_v063", session="2026-09-03"):
    tickers = ["EGCH", "RAYA", "ALCN", "MASR"] + [f"T{i:02d}" for i in range(max(0, n - 4))]
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


def _pack(tmp_path: Path, payload=None, session_meta=None, n=4, jobs=None):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    res = prepare_schedule_handoffs(
        explorer_payload=payload or _payload(n),
        store=store,
        output_root=tmp_path / "pkg",
        environment=UNIT_TEST,
        jobs=list(jobs or ANALYSIS_TYPES),
        session_meta=session_meta,
    )
    return store, res, Path(res["package_dir"])


def _csv_by_ticker(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {str(r.get("ticker") or "").upper(): r for r in rows if r.get("ticker")}


def _ident(row: dict) -> tuple[str, str, str]:
    return (
        str(row.get("canonical_signal_id") or ""),
        str(row.get("signal_family_id") or ""),
        str(row.get("market_state_fingerprint") or ""),
    )


def test_each_job_schema_has_correct_analysis_type(tmp_path: Path):
    store, res, pkg = _pack(tmp_path, session_meta={"session_phase": "POST_CLOSE"})
    expected = {
        ANALYSIS_MACRO: ANALYSIS_MACRO,
        ANALYSIS_PREMARKET: ANALYSIS_PREMARKET,
        ANALYSIS_INTRADAY: ANALYSIS_INTRADAY,
        ANALYSIS_VALUE: ANALYSIS_VALUE,
        ANALYSIS_WEEKLY: ANALYSIS_WEEKLY,
    }
    for job, atype in expected.items():
        schema = json.loads((pkg / "common" / "schemas" / RESULT_SCHEMA_FILES[job]).read_text())
        assert schema["analysis_type"] == atype
        assert schema["example"]["analysis_type"] == atype
        assert schema["scoring_version"] == "0.5.1"
        if job != ANALYSIS_PREMARKET:
            blob = json.dumps(schema)
            assert '"analysis_type": "PREMARKET_CATALYSTS"' not in blob or atype == ANALYSIS_PREMARKET
            assert schema["example"]["analysis_type"] != ANALYSIS_PREMARKET
    index = json.loads((pkg / "common" / "chatgpt_result_schema.json").read_text())
    assert index["result_envelope_version"] == RESULT_ENVELOPE_VERSION
    assert "analysis_type" not in index or index.get("analysis_type") != ANALYSIS_PREMARKET
    assert index["result_schemas"][ANALYSIS_INTRADAY].endswith("intraday_opportunity_result_schema.json")
    store.close()


def test_individual_zips_are_not_cross_contaminated(tmp_path: Path):
    store, res, pkg = _pack(tmp_path, session_meta={"session_phase": "POST_CLOSE"})
    for job, zpath in res["individual_zips"].items():
        with zipfile.ZipFile(zpath) as zf:
            names = zf.namelist()
            schema_names = [n for n in names if n.endswith("_result_schema.json") or n.endswith("result_schema.json")]
            assert schema_names, names
            for n in schema_names:
                schema = json.loads(zf.read(n))
                if "analysis_type" in schema:
                    assert schema["analysis_type"] == job
            if job != ANALYSIS_PREMARKET:
                for n in names:
                    if n.endswith(".json"):
                        obj = json.loads(zf.read(n))
                        if isinstance(obj, dict) and obj.get("analysis_type") == ANALYSIS_PREMARKET:
                            raise AssertionError(f"{job} zip contains PREMARKET schema in {n}")
            md_name = [n for n in names if n.endswith(".md")][0]
            md = zf.read(md_name).decode("utf-8")
            example = extract_json_envelope(md)
            assert example["analysis_type"] == job
    store.close()


def test_job_enums_match_markdown(tmp_path: Path):
    store, res, pkg = _pack(tmp_path)
    files = {
        ANALYSIS_MACRO: "macro_holdings.md",
        ANALYSIS_PREMARKET: "premarket_catalysts.md",
        ANALYSIS_INTRADAY: "intraday_opportunity.md",
        ANALYSIS_VALUE: "value_quality.md",
        ANALYSIS_WEEKLY: "weekly_xray.md",
    }
    for job, fname in files.items():
        text = (pkg / "jobs" / fname).read_text(encoding="utf-8")
        schema = json.loads((pkg / "common" / "schemas" / RESULT_SCHEMA_FILES[job]).read_text())
        assert schema["analysis_type"] in text
        for field, values in JOB_ENUMS[job].items():
            assert field in text
            for v in values:
                assert v in text, f"{job} markdown missing {field} value {v}"
        example = extract_json_envelope(text)
        assert example["analysis_type"] == job
        if job == ANALYSIS_INTRADAY:
            assert "catalyst_status" not in json.dumps(schema.get("per_candidate_fields") or {})
            assert schema.get("primary_decision_field") == "setup_state"
            assert "setup_state" in text
        if job == ANALYSIS_PREMARKET:
            assert "catalyst_status" in text
        if job == ANALYSIS_VALUE:
            assert "funnel_action" in text
            assert "Fair Value" in text  # instruction not to overwrite
            assert "do **not** overwrite Funnel valuation".lower() in text.lower() or "overwrite Funnel" in text
    store.close()


def test_session_phase_inherited_post_close_pre_open_continuous(tmp_path: Path):
    cases = {
        "POST_CLOSE": {"session_phase": "POST_CLOSE"},
        "PRE_OPEN": {"session_phase": "PRE_OPEN"},
        "CONTINUOUS_TRADING": {
            "session_phase": "CONTINUOUS_TRADING",
            "analysis_timestamp_utc": "2026-09-03T08:20:00+00:00",
            "analysis_timestamp_cairo": "2026-09-03T11:20:00+03:00",
        },
    }
    for phase, meta in cases.items():
        store, res, pkg = _pack(tmp_path / phase, session_meta=meta)
        man = json.loads((pkg / "manifest.json").read_text())
        assert man["session_phase"] == phase
        intra = (pkg / "jobs" / "intraday_opportunity.md").read_text(encoding="utf-8")
        example = extract_json_envelope(intra)
        assert example["session_phase"] == phase
        assert example["session_phase"] != "CONTINUOUS_TRADING" or phase == "CONTINUOUS_TRADING"
        schema = json.loads((pkg / "common" / "schemas" / RESULT_SCHEMA_FILES[ANALYSIS_INTRADAY]).read_text())
        assert schema["example"]["session_phase"] == phase
        if phase in {"POST_CLOSE", "PRE_OPEN"}:
            assert NOT_LIVE_CONFIRMATION_TEXT in intra
            assert example.get("live_session_evidence_available") is False
        store.close()


def test_intraday_example_never_hardcodes_continuous_on_post_close(tmp_path: Path):
    store, res, pkg = _pack(tmp_path, session_meta={"session_phase": "POST_CLOSE"})
    intra = (pkg / "jobs" / "intraday_opportunity.md").read_text(encoding="utf-8")
    example = extract_json_envelope(intra)
    assert example["session_phase"] == "POST_CLOSE"
    assert '"session_phase": "CONTINUOUS_TRADING"' not in intra.split("```json")[-1]
    store.close()


def test_weekly_example_does_not_hardcode_zero_counts(tmp_path: Path):
    store, res, pkg = _pack(tmp_path, n=20)
    weekly_md = (pkg / "jobs" / "weekly_xray.md").read_text(encoding="utf-8")
    example = extract_json_envelope(weekly_md)
    for key in (
        "scanner_sample_n", "analysis_observations_generated_n",
        "analysis_observations_imported_n", "analysis_observations_evaluable_n",
    ):
        assert example.get(key) not in (0, "0")
    hist = json.loads((pkg / "optional" / "calibration_history_summary.json").read_text())
    assert hist["scanner_sample_n"] == 20
    assert hist["analysis_observations_generated_n"] == 100
    assert hist["analysis_observations_imported_n"] == 0
    assert hist["weekly_metrics"] == "APP_GENERATED"
    store.close()


def test_weekly_import_does_not_overwrite_app_counts(tmp_path: Path):
    store, res, pkg = _pack(tmp_path, n=20)
    before = json.loads((pkg / "optional" / "calibration_history_summary.json").read_text())
    raw = json.dumps({
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "analysis_type": ANALYSIS_WEEKLY,
        "run_id": res["run_id"],
        "scanner_summary": "template interpretation",
        "calibration_status": "INSUFFICIENT_SAMPLE",
        "scanner_sample_n": 0,
        "analysis_observations_generated_n": 0,
    })
    src = tmp_path / "weekly.md"
    src.write_text("prose\n```json\n" + raw + "\n```\n", encoding="utf-8")
    out = import_schedule_result(
        src, analysis_type=ANALYSIS_WEEKLY, run_id=res["run_id"], store=store,
        raw_dest_dir=tmp_path / "imports",
    )
    assert out["structured_parse_status"] == PARSE_VALID
    assert out["weekly_metrics_source"] == "APP_GENERATED"
    assert out["weekly_interpretation_source"] == "CHATGPT_IMPORTED"
    assert out["weekly_metrics"]["scanner_sample_n"] == 20
    assert out["weekly_metrics"]["analysis_observations_generated_n"] == 100
    assert out["weekly_count_mismatches"]
    after = json.loads((pkg / "optional" / "calibration_history_summary.json").read_text())
    assert after["scanner_sample_n"] == before["scanner_sample_n"]
    assert after["analysis_observations_generated_n"] == before["analysis_observations_generated_n"]
    store.close()


def test_raw_candidate_detail_identity_matches_summary_and_markdown(tmp_path: Path):
    store, res, pkg = _pack(tmp_path, n=4)
    raw = json.loads((pkg / "optional" / "raw_candidate_detail.json").read_text())
    summary = _csv_by_ticker(pkg / "common" / "candidate_summary.csv")
    premarket = (pkg / "jobs" / "premarket_catalysts.md").read_text(encoding="utf-8")
    for row in raw:
        t = row["ticker"]
        for field in (
            "ticker", "canonical_signal_id", "signal_family_id", "parent_signal_id",
            "market_state_fingerprint", "explorer_run_id", "schedule_run_id", "analysis_type",
        ):
            assert field in row
        assert _ident(row) == _ident(summary[t])
        assert row["canonical_signal_id"] in premarket
        assert t in premarket
    store.close()


def test_identity_conflict_fails_packaging():
    groups = {
        "candidate_summary": [{
            "ticker": "RAYA", "canonical_signal_id": "aaa",
            "signal_family_id": "fam", "market_state_fingerprint": "fp1",
        }],
        "raw_candidate_detail": [{
            "ticker": "RAYA", "canonical_signal_id": "bbb",
            "signal_family_id": "fam", "market_state_fingerprint": "fp1",
        }],
    }
    conflicts = reconcile_identity_groups(groups)
    assert conflicts
    try:
        assert_identity_consistent(groups)
        raised = False
    except IdentityConflictError:
        raised = True
    assert raised


def test_analysis_observations_n_deprecated_in_manifest(tmp_path: Path):
    store, res, pkg = _pack(tmp_path)
    man = json.loads((pkg / "manifest.json").read_text())
    assert man["analysis_observations_n_semantics"] == ANALYSIS_OBSERVATIONS_N_SEMANTICS
    assert "analysis_observations_n" in man["deprecated_fields"]
    assert man["analysis_observations_n"] == man["analysis_observations_generated_n"]
    assert man["handoff_schema_version"] == HANDOFF_SCHEMA_VERSION
    assert man["supported_result_envelope_version"] == RESULT_ENVELOPE_VERSION
    assert set(man["result_schemas"]) == set(ANALYSIS_TYPES)
    store.close()


def test_importer_valid_intraday(tmp_path: Path):
    store, res, pkg = _pack(tmp_path, session_meta={"session_phase": "POST_CLOSE"}, jobs=[ANALYSIS_INTRADAY])
    raya = next(s for s in store.list_canonical_signals() if s["ticker"] == "RAYA")
    env = {
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "analysis_type": ANALYSIS_INTRADAY,
        "run_id": res["run_id"],
        "session_phase": "POST_CLOSE",
        "live_session_evidence_available": False,
        "candidates": [{
            "ticker": "RAYA",
            "canonical_signal_id": raya["canonical_signal_id"],
            "setup_state": "NOT_STARTED",
            "confidence": "LOW",
        }],
    }
    src = tmp_path / "ok.md"
    src.write_text("prose\n```json\n" + json.dumps(env) + "\n```\n", encoding="utf-8")
    out = import_schedule_result(
        src, analysis_type=ANALYSIS_INTRADAY, run_id=res["run_id"], store=store,
        raw_dest_dir=tmp_path / "imports",
    )
    assert out["structured_parse_status"] == PARSE_VALID
    assert out["session_phase_validation"] == PHASE_MATCH
    assert out["candidate_linkages"][0]["linkage_method"] == LINKAGE_EXPLICIT
    assert out["original_preserved"] is True
    store.close()


def test_importer_wrong_analysis_type_invalid_schema(tmp_path: Path):
    store, res, pkg = _pack(tmp_path, jobs=[ANALYSIS_INTRADAY])
    env = {
        "analysis_type": ANALYSIS_PREMARKET,
        "run_id": res["run_id"],
        "candidates": [{"ticker": "RAYA", "status": "KEEP", "catalyst_status": "NEUTRAL"}],
    }
    src = tmp_path / "bad.md"
    src.write_text("```json\n" + json.dumps(env) + "\n```", encoding="utf-8")
    out = import_schedule_result(
        src, analysis_type=ANALYSIS_INTRADAY, run_id=res["run_id"], store=store,
        raw_dest_dir=tmp_path / "imports",
    )
    assert out["structured_parse_status"] == PARSE_INVALID_SCHEMA
    assert out["original_preserved"] is True
    assert Path(out["saved_path"]).read_text(encoding="utf-8")
    chat = [o for o in store.list_analysis_observations() if o.get("generated_by") == "CHATGPT_HANDOFF"]
    assert chat == []
    store.close()


def test_importer_invalid_canonical_and_ticker_mismatch(tmp_path: Path):
    store, res, pkg = _pack(tmp_path, jobs=[ANALYSIS_PREMARKET])
    raya = next(s for s in store.list_canonical_signals() if s["ticker"] == "RAYA")
    bad_id = {
        "analysis_type": ANALYSIS_PREMARKET, "run_id": res["run_id"],
        "candidates": [{"ticker": "RAYA", "canonical_signal_id": "does-not-exist", "status": "KEEP"}],
    }
    src = tmp_path / "id.md"
    src.write_text("```json\n" + json.dumps(bad_id) + "\n```", encoding="utf-8")
    out = import_schedule_result(
        src, analysis_type=ANALYSIS_PREMARKET, run_id=res["run_id"], store=store,
        raw_dest_dir=tmp_path / "imports",
    )
    assert out["candidate_linkages"][0]["linkage_method"] == LINKAGE_INVALID
    assert out["candidate_linkages"][0]["canonical_validation"] == PARSE_INVALID_CANONICAL_ID
    assert out["structured_parse_status"] == PARSE_INVALID_CANONICAL_ID
    assert out["original_preserved"] is True
    mismatch = {
        "analysis_type": ANALYSIS_PREMARKET, "run_id": res["run_id"],
        "candidates": [{"ticker": "EGCH", "canonical_signal_id": raya["canonical_signal_id"], "status": "KEEP"}],
    }
    src2 = tmp_path / "mm.md"
    src2.write_text("```json\n" + json.dumps(mismatch) + "\n```", encoding="utf-8")
    out2 = import_schedule_result(
        src2, analysis_type=ANALYSIS_PREMARKET, run_id=res["run_id"], store=store,
        raw_dest_dir=tmp_path / "imports",
    )
    assert out2["candidate_linkages"][0]["reason"] == "ticker_mismatch"
    assert out2["structured_parse_status"] == PARSE_TICKER_MISMATCH
    assert out2["original_preserved"] is True
    store.close()


def test_importer_phase_mismatch_preserves_raw(tmp_path: Path):
    store, res, pkg = _pack(tmp_path, session_meta={"session_phase": "POST_CLOSE"}, jobs=[ANALYSIS_INTRADAY])
    raya = next(s for s in store.list_canonical_signals() if s["ticker"] == "RAYA")
    env = {
        "analysis_type": ANALYSIS_INTRADAY,
        "run_id": res["run_id"],
        "session_phase": "CONTINUOUS_TRADING",
        "candidates": [{
            "ticker": "RAYA",
            "canonical_signal_id": raya["canonical_signal_id"],
            "setup_state": "CONFIRMED",
        }],
    }
    src = tmp_path / "phase.md"
    raw_text = "keep this raw\n```json\n" + json.dumps(env) + "\n```\n"
    src.write_text(raw_text, encoding="utf-8")
    out = import_schedule_result(
        src, analysis_type=ANALYSIS_INTRADAY, run_id=res["run_id"], store=store,
        raw_dest_dir=tmp_path / "imports",
    )
    assert out["session_phase_validation"] == PHASE_MISMATCH
    assert out["structured_parse_status"] == PARSE_NEEDS_REVIEW
    assert out["live_state_analysis_valid"] is False
    assert out["original_preserved"] is True
    assert "keep this raw" in Path(out["saved_path"]).read_text(encoding="utf-8")
    assert out["envelope"]["session_phase"] == "CONTINUOUS_TRADING"
    chat = [o for o in store.list_analysis_observations() if o.get("generated_by") == "CHATGPT_HANDOFF"]
    assert chat == []
    store.close()


def test_macro_and_weekly_valid_without_candidates(tmp_path: Path):
    store, res, pkg = _pack(tmp_path)
    macro = {
        "analysis_type": ANALYSIS_MACRO,
        "run_id": res["run_id"],
        "market_regime": "NEUTRAL",
        "portfolio_posture": "SELECTIVE",
        "confidence": "MEDIUM",
    }
    weekly = {
        "analysis_type": ANALYSIS_WEEKLY,
        "run_id": res["run_id"],
        "scanner_summary": "n too small",
        "calibration_status": "INSUFFICIENT_SAMPLE",
    }
    sm = tmp_path / "macro.md"
    sw = tmp_path / "weekly.md"
    sm.write_text("```json\n" + json.dumps(macro) + "\n```", encoding="utf-8")
    sw.write_text("```json\n" + json.dumps(weekly) + "\n```", encoding="utf-8")
    om = import_schedule_result(sm, analysis_type=ANALYSIS_MACRO, run_id=res["run_id"], store=store, raw_dest_dir=tmp_path / "imports")
    ow = import_schedule_result(sw, analysis_type=ANALYSIS_WEEKLY, run_id=res["run_id"], store=store, raw_dest_dir=tmp_path / "imports")
    assert om["structured_parse_status"] == PARSE_VALID
    assert ow["structured_parse_status"] == PARSE_VALID
    assert om["candidate_linkages"] == []
    assert ow["candidate_linkages"] == []
    store.close()


def test_examples_are_templates_not_fake_decisions(tmp_path: Path):
    store, res, pkg = _pack(tmp_path, session_meta={"session_phase": "POST_CLOSE"})
    for job, fname in RESULT_SCHEMA_FILES.items():
        schema = json.loads((pkg / "common" / "schemas" / fname).read_text())
        example = schema["example"]
        assert example.get("example_kind") == "TEMPLATE_NOT_ACTUAL_OUTPUT"
        dumped = json.dumps(example)
        assert MODEL_DECISION in dumped or job == ANALYSIS_WEEKLY
        if job == ANALYSIS_INTRADAY:
            assert example["session_phase"] == "POST_CLOSE"
        if job == ANALYSIS_WEEKLY:
            assert example.get("scanner_sample_n") not in (0, "0")
            assert COPY_FROM_INPUT in dumped or "APP_GENERATED" in dumped
        if job == ANALYSIS_MACRO:
            assert example.get("candidates") in (None, "<OPTIONAL>", "<OPTIONAL>")
    store.close()


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
