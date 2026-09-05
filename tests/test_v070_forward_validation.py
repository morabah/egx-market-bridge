"""v0.7.0 chronological acceptance: synthetic evidence, isolated from production."""
from datetime import datetime, timedelta
from pathlib import Path
import json
import sqlite3

import pytest

from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.common.environment import UNIT_TEST
from egxbridge.analysis.forward_validation import (
    HORIZONS, DEFAULT_CONFIG, freeze_explorer_run, validation_report, append_classification,
    start_validation, store_change_proposal, append_later_review, round_encounters, local_evidence,
    eligible_sample, sample_statistics, joined_signals,
)
from egxbridge.analysis.schedule.outcomes import compute_outcomes, update_outcomes_for_store, friction_outcome, target_stop_outcome
from egxbridge.analysis.funnel.schema import normalize_fields
from egxbridge.db import Database

T0 = "2026-01-01T15:00:00+00:00"
SESSION = "2026-01-01"


def dates(n=60):
    # Friday/Saturday weekends and one synthetic holiday are absent from observed bars.
    day = datetime(2026, 1, 2)
    result = []
    while len(result) < n:
        if day.weekday() not in (4, 5) and day.date().isoformat() != "2026-01-06":
            result.append(day.date().isoformat())
        day += timedelta(days=1)
    return result


def candidate(ticker="AAA", price=100.0, **extra):
    return {"ticker": ticker, "last_close": price, "candidate_score_calibrated": 75,
            "FORWARD_SETUP_QUALITY": "STRONG", "MOVE_ALREADY_REALIZED": "LOW",
            "candidate_lane": "LANE_A", "TECHNICAL_HISTORY_INTEGRITY": "VERIFIED",
            "rvol_20": 1.8, "RS20": 2, "sector": "SYNTHETIC", **extra}


def freeze(store, candidates=None, *, selected=None, run="run1", **kwargs):
    candidates = candidates or [candidate()]
    chosen = selected if selected is not None else {c["ticker"] for c in candidates}
    return freeze_explorer_run(store, run_id=run, generated_at=T0, market_session=SESSION,
        all_candidates=candidates, prescreen_tickers=chosen, final_tickers=chosen,
        intraday_tickers=set(), **kwargs)


def seed(db, ticker, n, *, growth=1, high_extra=1, low_extra=1):
    for i, day in enumerate(dates(n), 1):
        close = 100 + growth*i
        db.upsert_candle({"symbol": ticker, "interval": "1d", "timestamp": day+"T00:00:00+00:00",
            "session_date": day, "open": close, "high": close+high_extra, "low": close-low_extra,
            "close": close, "volume": 1000, "provider": "synthetic", "capture_timestamp": day+"T15:00:00+00:00"})


@pytest.fixture
def stores(tmp_path):
    a = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    m = Database(tmp_path / "m.sqlite")
    yield a, m
    a.close(); m.close()


def test_no_future_data_and_trading_session_maturity(stores):
    store, db = stores
    freeze(store)
    update_outcomes_for_store(store, db, forward_validation_only=True)
    row = validation_report(store)["signals"][0]
    for h in HORIZONS:
        assert row[f"return_{h}"] is None
        assert row[f"mfe_{h}"] is None and row[f"mae_{h}"] is None
        assert row[f"maturity_{h}"] == "PENDING"
    seed(db,"AAA",2)
    update_outcomes_for_store(store,db,forward_validation_only=True)
    row=validation_report(store)["signals"][0]
    assert row["return_1"] == 1 and row["return_2"] == 2
    assert row["mfe_2"] == 3 and row["mae_2"] == 0
    for h in (5,10,20):
        assert row[f"return_{h}"] is None and row[f"mfe_{h}"] is None
    seed(db,"AAA",20)
    update_outcomes_for_store(store,db,through_session=dates(5)[-1],forward_validation_only=True)
    row=validation_report(store)["signals"][0]
    assert row["return_5"] == 5 and row["session_dates"][4] == "2026-01-11"
    assert row["return_10"] is None and row["return_20"] is None
    update_outcomes_for_store(store,db,forward_validation_only=True)
    row=validation_report(store)["signals"][0]
    assert row["return_20"] == 20 and row["mfe_20"] == 21


def test_mfe_missing_ohlc_not_imputed_and_same_session_ambiguous():
    path=[{"session_date":"2026-01-04","close":101,"high":110,"low":90}]
    o=compute_outcomes(baseline_price=100,baseline_timestamp=T0,baseline_type="OFFICIAL_CLOSE",signal_session=SESSION,future_bars=path)
    assert o["mfe_5"] is None and o["mae_5"] is None
    out=target_stop_outcome({"target_price_t0":105,"stop_or_invalidation_t0":95},path)
    assert out["target_before_stop"] == "SAME_SESSION_AMBIGUOUS"
    assert target_stop_outcome({},path)["target_before_stop"] == "NOT_APPLICABLE"
    path[0].pop("high")
    o=compute_outcomes(baseline_price=100,baseline_timestamp=T0,baseline_type="OFFICIAL_CLOSE",signal_session=SESSION,future_bars=path)
    assert o["return_1"] == 1 and o["mfe_1"] is None and o["mae_1"] is None


def test_friction_known_partial_absent():
    assert friction_outcome(5,None)["net_return_after_friction"] is None
    partial=friction_outcome(5,{"components_pct":{"brokerage":.2}})
    assert partial["friction_status"] == "PARTIAL" and partial["estimated_total_friction"] is None
    model={"friction_model_version":"synthetic-1","friction_inputs_source":"SYNTHETIC_ACCEPTANCE",
        "components_pct":{"brokerage":.2,"exchange_regulatory":.1,"taxes":0,"spread":.3,"slippage":.4}}
    assert friction_outcome(5,model)["net_return_after_friction"] == 4
    assert friction_outcome(5,model)["friction_status"] == "ESTIMATED"


def classify(store,cid,ticker,fields,source_id="x",stamp="2026-01-02T12:00:00+00:00",**kw):
    return append_classification(store,cid,ticker=ticker,fields=fields,source="FUNNEL_LLM",source_id=source_id,
        source_cutoff=T0,imported_at=stamp,funnel_version="2.8",**kw)


def test_fv_revision_groups_no_app_judgment(stores):
    store,db=stores
    freeze(store,[candidate(t) for t in ("A","B","C","D")])
    for snap in store.validation_records("forward_signal_snapshots"):
        t=snap["ticker"]
        classify(store,snap["canonical_signal_id"],t,{
            "central_fv":80 if t in {"A","B"} else 120,
            "price_implied_expectations":"REASONABLE" if t in {"A","C"} else "DEMANDING",
            "expectations_revision_outlook":"UPWARD" if t in {"A","C"} else "DOWNWARD",
            "expectations_gap":"POSITIVE", "information_reaction_regime":"UNDERREACTION",
            "catalyst_revision_potential":"HIGH_POSITIVE"})
        seed(db,t,20,growth=1 if t in {"A","C"} else -1)
    update_outcomes_for_store(store,db,forward_validation_only=True)
    r=validation_report(store)
    assert {g["premium_fv_group"] for g in r["expectations"]["premium_to_fv"]} == {"A_REASONABLE_UPWARD","B_DEMANDING_DOWNWARD"}
    assert {g["discount_fv_group"] for g in r["expectations"]["discount_to_fv"]} == {"DISCOUNT_UPWARD","DISCOUNT_DOWNWARD"}
    assert len(r["expectations"]["burden_revision"]) == 2
    for row in r["signals"]:
        assert "final_decision" not in row and "fresh_capital_test" not in row
    assert r["summary"]["interpretation"] == "DESCRIPTIVE_ONLY"


def test_late_classification_never_rewrites_t0(stores):
    store,db=stores
    freeze(store)
    s=store.validation_records("forward_signal_snapshots")[0]
    cid=s["canonical_signal_id"]
    classify(store,cid,"AAA",{"expectations_revision_outlook":"UPWARD"},source_id="early")
    classify(store,cid,"AAA",{"expectations_revision_outlook":"DOWNWARD"},source_id="late",stamp="2026-01-07T15:00:00+00:00")
    seed(db,"AAA",10)
    update_outcomes_for_store(store,db,forward_validation_only=True)
    r=validation_report(store)
    assert r["signals"][0]["expectations_revision_outlook"] == "UPWARD"
    assert r["sample_integrity"]["excluded_late_classifications"] == 1
    append_later_review(store,cid,ticker="AAA",fields={"realized_expectations_revision":"DOWN","catalyst_confirmed_outcome":"FAILED"},source_id="weekly",cutoff=dates(10)[-1])
    assert store.validation_records("forward_signal_snapshots")[0] == s
    assert len(store.validation_records("forward_signal_classifications")) == 2
    with pytest.raises(sqlite3.IntegrityError):
        store._conn.execute("UPDATE forward_signal_snapshots SET payload_json='{}'")
    with pytest.raises(sqlite3.IntegrityError):
        store._conn.execute("DELETE FROM forward_signal_classifications")


def test_full_universe_100_with_missed_winner(stores):
    store,db=stores
    c=[candidate(f"S{i:03}") for i in range(100)]
    selected={row["ticker"] for row in c[:20]}
    freeze(store,c,selected=selected)
    for row in c:
        seed(db,row["ticker"],20,growth=2 if row["ticker"] == "S099" else .1)
    update_outcomes_for_store(store,db,forward_validation_only=True)
    report=validation_report(store)
    assert len(store.validation_records("universe_snapshot_members")) == 100
    assert report["summary"]["N"] == 20
    missed=report["false_negatives"]["10"]
    winner=next(r for r in missed["cases"] if r["ticker"] == "S099")
    assert winner["forward_rank"] == 1 and not winner["selected_for_final_handoff"]
    assert missed["coverage"][0]["mature_n"] == 100
    assert winner["MISSED_REASON"] == "UNEXPLAINED"  # A top-20 cap is not proof of a weak-RS reason.


def test_discovery_and_untrusted_reconstructions_excluded(stores):
    store,db=stores
    freeze(store,sample_role="DISCOVERY")
    seed(db,"AAA",20)
    update_outcomes_for_store(store,db)
    r=validation_report(store)
    assert r["summary"]["N"] == 0 and r["sample_integrity"]["forward_validation_n"] == 0
    assert r["false_negatives"]["10"]["cases"] == []
    assert not eligible_sample({"sample_role":"FORWARD_VALIDATION","point_in_time_kind":"RECONSTRUCTED_POINT_IN_TIME","enrolled_after_start":True},include_reconstructed=True)


def proposal():
    return {"action":"PROPOSE_CHANGE","rule_name":"pullback_rule","old_definition":{"min":3},"proposed_definition":{"min":4},
            "reason":"SYNTHETIC_TEST_ONLY","sample_window":[SESSION,dates(20)[-1]],"independent_N":100,
            "group_statistics":{},"friction_included":False,"regime_splits":{},"known_limitations":["synthetic"],"expected_effect":"unknown"}


def test_proposal_has_no_mutation_or_self_confirmation(stores):
    store,_=stores
    start_validation(store,at=T0)
    before=store.validation_records("rule_definitions")
    rec=store_change_proposal(store,proposal(),source="WEEKLY_LLM",source_id="xray")
    assert rec["auto_applied"] is False and rec["requires_forward_confirmation"] == "YES"
    assert rec["discovery_for_new_rule"] == proposal()["sample_window"]
    assert store.validation_records("rule_definitions") == before
    with pytest.raises(ValueError):
        store_change_proposal(store,proposal(),source="SCANNER",source_id="bad")


def test_plss_missing_is_not_negative_and_round_increments():
    fields,issues=normalize_fields({"psychological_levels":[{"PLSS_raw":3,"PLSS_available_max":5,"PLSS_evidence_coverage":.5,"volume_at_price_component":None}]})
    assert not issues and fields["psychological_levels"][0]["volume_at_price_component"] is None
    assert "PLSS_normalized_if_allowed" not in fields["psychological_levels"][0]
    assert round_encounters(250,DEFAULT_CONFIG)[0]["round_level"] == 250
    assert round_encounters(2.5,DEFAULT_CONFIG)[0]["round_level"] == 2.5
    evidence=local_evidence(candidate(),session=SESSION,cutoff=T0,cfg=DEFAULT_CONFIG)
    assert evidence["PLSS_status"] == "HEURISTIC" and evidence["depth_available"] is False


def test_repeated_identity_and_dry_run_are_idempotent(stores):
    store,db=stores
    freeze(store)
    before=store.validation_records("forward_signal_snapshots")
    freeze(store,run="run2")
    assert store.validation_records("forward_signal_snapshots") == before
    assert len(store.list_canonical_signals()) == 1
    seed(db,"AAA",20)
    db_before=store._conn.total_changes
    update_outcomes_for_store(store,db,dry_run=True,forward_validation_only=True)
    assert store._conn.total_changes == db_before
    update_outcomes_for_store(store,db,forward_validation_only=True)
    old=store.list_canonical_outcomes()[0]["payload_json"]
    update_outcomes_for_store(store,db,pending_only=False,through_session=dates(2)[-1],forward_validation_only=True)
    new=json.loads(store.list_canonical_outcomes()[0]["payload_json"])
    assert new["return_20"] == json.loads(old)["return_20"] == 20
    assert new["maturity_20"] == "MATURE"


def test_concentrated_n_never_becomes_validated():
    rows=[{"canonical_signal_id":str(i),"signal_family_id":str(i//2),"ticker":"AAA","market_session":SESSION,
           "return_20":1,"maturity_20":"MATURE"} for i in range(100)]
    s=sample_statistics(rows)
    assert s["independent_signal_n"] == 50 and s["sample_diversity_status"] == "HIGHLY_CONCENTRATED"
    assert s["signal_calibration_status"] == "CALIBRATION_REVIEW_ELIGIBLE"
    assert s["signal_calibration_status"] not in {"VALIDATED","PROVISIONALLY_CALIBRATED"}


def test_import_identity_and_local_judgment_boundary(stores):
    store,_=stores
    freeze(store)
    cid=store.validation_records("forward_signal_snapshots")[0]["canonical_signal_id"]
    with pytest.raises(ValueError):
        append_classification(store,cid,ticker="AAA",fields={"fresh_capital_test":"YES"},source="LOCAL_HEURISTIC",source_id="bad")
    with pytest.raises(ValueError):
        classify(store,cid,"OTHER",{"expectations_gap":"POSITIVE"})
    with pytest.raises(ValueError):
        classify(store,"invalid","AAA",{"expectations_gap":"POSITIVE"})


def test_new_prompt_and_historical_prompt_preserved(tmp_path):
    from egxbridge.analysis.funnel.state import create_project,save_project
    from egxbridge.analysis.funnel.handoff import prepare_funnel_handoff
    from egxbridge.analysis.funnel.importer import import_funnel_result
    store=AnalysisStore(tmp_path/"f.sqlite",environment=UNIT_TEST)
    ws=tmp_path/"funnels"
    p=create_project("AAA",root=ws,store=store)
    assert p.funnel_version == "2.8"
    root=Path(__file__).resolve().parents[1]
    assert (ws/"AAA/source/master_funnel_v2.8.md").read_bytes() == (root/"EGX_STOCK_ANALYSIS_FUNNEL_v2.8.md").read_bytes()
    old=create_project("OLD",root=ws,store=store)
    old.funnel_version="EGX_STOCK_ANALYSIS_FUNNEL_v2.7"
    save_project(old,root=ws,store=store)
    res=prepare_funnel_handoff(old,store=store,workspace_root=ws,output_root=tmp_path/"out")
    assert (Path(res["package_dir"])/"MASTER_FUNNEL_v2.7.md").read_bytes() == (root/"prompts/EGX_STOCK_ANALYSIS_FUNNEL_v2.7.md").read_bytes()
    data={"funnel_version":"2.8","declared_research_cutoff":T0,"final_decision_summary":{"Central / PW Intrinsic FV":80,"Price-Implied Expectations":"REASONABLE","Expectations Revision Outlook":"UPWARD","Fresh Capital Test":"YES","Final Decision":"ACCUMULATE"}}
    imported=import_funnel_result("AAA",json.dumps(data),store=store,workspace_root=ws,advance_stage=False)
    assert imported["structured_fields"]["central_fv"] == 80
    assert imported["structured_fields"]["expectations_revision_outlook"] == "UPWARD"
    assert Path(imported["saved_path"]).read_text() == json.dumps(data)
    assert imported["project"]["funnel_completion_status"] != "COMPLETE"
    assert imported["project"]["delta_eligible"] == "NO"
    blocked=prepare_funnel_handoff(p,store=store,workspace_root=ws,output_root=tmp_path/"blocked",run_mode="DELTA_ONLY")
    assert blocked.get("status") != "OK"
    store.close()


def test_real_explorer_auto_freezes_history_and_reuses_schedule_identity(tmp_path):
    from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
    from egxbridge.analysis.explorer.models import ExplorerRunConfig
    from egxbridge.analysis.funnel.registry import FunnelRegistry
    from egxbridge.analysis.schedule.handoff import prepare_schedule_handoffs
    from test_v05_explorer import _seed_daily
    store=AnalysisStore(tmp_path/"a.sqlite",environment=UNIT_TEST)
    db=Database(tmp_path/"m.sqlite")
    for t in ("COMI","MASR","ALCN"):
        _seed_daily(db,t,n=80)
    registry=FunnelRegistry(workspace_root=tmp_path/"funnels",store=store,db=db)
    config=ExplorerRunConfig(universe=["COMI","MASR","ALCN"],enrich_intraday=False,environment=UNIT_TEST)
    prepare_explorer_handoff(config,db=db,store=store,funnel_registry=registry,output_root=tmp_path/"explorer")
    payload=json.loads((tmp_path/"explorer/explorer_handoff.json").read_text())
    snaps=store.validation_records("forward_signal_snapshots")
    assert len(snaps) == len(payload["candidates"]) == 3
    assert all(s["CLV"] is not None and s["return_20d_trailing"] is not None for s in snaps)
    assert all(s["scanner_metrics"]["return_6m_pct"] is None for s in snaps)
    ids={s["canonical_signal_id"] for s in snaps}
    before={s["canonical_signal_id"] for s in store.list_canonical_signals()}
    assert before == ids
    prepared=prepare_schedule_handoffs(explorer_payload=payload,store=store,output_root=tmp_path/"schedules",environment=UNIT_TEST)
    after={s["canonical_signal_id"] for s in store.list_canonical_signals()}
    assert after == before
    from egxbridge.analysis.schedule.types import JOB_FILE, ANALYSIS_WEEKLY
    assert "FORWARD VALIDATION AUDIT" in (tmp_path/"schedules"/"jobs"/JOB_FILE[ANALYSIS_WEEKLY]).read_text()
    assert len(prepared["jobs"]) == 5
    store.close();db.close()


def test_target_definition_import_and_sunday_session(stores):
    store,db=stores
    freeze(store)
    cid=store.validation_records("forward_signal_snapshots")[0]["canonical_signal_id"]
    classify(store,cid,"AAA",{"target_price_t0":102,"stop_or_invalidation_t0":100})
    seed(db,"AAA",1,high_extra=2,low_extra=2)
    update_outcomes_for_store(store,db,forward_validation_only=True)
    row=validation_report(store)["signals"][0]
    assert row["target_stop_1"]["target_before_stop"] == "SAME_SESSION_AMBIGUOUS"
    assert row["target_stop_definition"]["target_source"] == "FUNNEL_LLM"
    assert row["day_of_week"] == "Thursday"


def test_lab_renders_with_and_without_data(tmp_path):
    from streamlit.testing.v1 import AppTest
    path=tmp_path/"ui.sqlite"
    store=AnalysisStore(path,environment=UNIT_TEST)
    freeze(store)
    store.close()
    script=f'''from pathlib import Path
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.ui.forward_validation import render_forward_validation
store=AnalysisStore({str(path)!r},environment="UNIT_TEST")
render_forward_validation(store=store,root=Path({str(tmp_path)!r}))
store.close()
'''
    app=AppTest.from_string(script).run(timeout=20)
    assert not app.exception
    assert len(app.tabs) == 10
    assert app.tabs[1].label == "Expectations"
    assert any(m.label == "Canonical signals" and m.value == "1" for m in app.metric)
    app.selectbox(key="split_regimes").select("sector").run()
    assert not app.exception


def test_schedule_v28_import_and_weekly_proposal_flow(tmp_path,monkeypatch):
    import egxbridge.analysis.schedule.importer as importer
    from egxbridge.analysis.schedule.handoff import prepare_schedule_handoffs
    from egxbridge.analysis.schedule.types import ANALYSIS_PREMARKET,ANALYSIS_WEEKLY,RESULT_ENVELOPE_VERSION
    store=AnalysisStore(tmp_path/"a.sqlite",environment=UNIT_TEST)
    db=Database(tmp_path/"m.sqlite")
    freeze(store)
    snap=store.validation_records("forward_signal_snapshots")[0]
    cid=snap["canonical_signal_id"]
    monkeypatch.setattr(importer,"utc_now",lambda:"2026-01-02T12:00:00+00:00")
    # Use explicit canonical linkage; schedule import never infers identity from outcome winners.
    data={"result_envelope_version":RESULT_ENVELOPE_VERSION,"analysis_type":ANALYSIS_PREMARKET,
          "schedule_run_id":"test-pre","session_phase":"POST_CLOSE","declared_research_cutoff":T0,
          "candidates":[{"ticker":"AAA","canonical_signal_id":cid,"next_session_status":"PROMOTE",
                         "confidence":"HIGH","funnel_v28":{"expectations_revision_outlook":"UPWARD"}}]}
    result=importer.import_schedule_result(json.dumps(data),analysis_type=ANALYSIS_PREMARKET,store=store,
        raw_dest_dir=tmp_path/"raw",package_session_phase="POST_CLOSE",package_live_session_evidence_available=False)
    assert result["original_preserved"] and result["candidate_linkages"][0]["canonical_signal_id"] == cid
    assert len(store.validation_records("forward_signal_classifications")) == 1
    # Re-importing one observation must not inflate its value-add denominator.
    importer.import_schedule_result(json.dumps(data),analysis_type=ANALYSIS_PREMARKET,store=store,
        raw_dest_dir=tmp_path/"raw",package_session_phase="POST_CLOSE",package_live_session_evidence_available=False)
    seed(db,"AAA",20)
    update_outcomes_for_store(store,db,forward_validation_only=True)
    assert validation_report(store)["cohorts"]["LLM_PROMOTED"]["N"] == 1
    definitions=store.validation_records("rule_definitions")
    weekly={"result_envelope_version":RESULT_ENVELOPE_VERSION,"analysis_type":ANALYSIS_WEEKLY,
        "session_phase":"POST_CLOSE","schedule_run_id":"weekly","scanner_summary":"synthetic",
        "analysis_value_add_summary":"synthetic", "calibration_status":"INSUFFICIENT_SAMPLE",
        "rule_change_proposals":[proposal()]}
    result=importer.import_schedule_result(json.dumps(weekly),analysis_type=ANALYSIS_WEEKLY,store=store,
        raw_dest_dir=tmp_path/"raw",package_session_phase="POST_CLOSE")
    assert len(store.validation_records("rule_change_proposals")) == 1
    assert store.validation_records("rule_definitions") == definitions
    store.close();db.close()


def test_breakout_pullback_clv_and_future_history_cutoff():
    from egxbridge.analysis.forward_validation import pullback_evidence
    bars=[]
    for i in range(70):
        price=50+i
        bars.append({"session_date":(datetime(2025,9,1)+timedelta(days=i)).date().isoformat(),
                     "close":price,"high":price+.2,"low":price-.2,"volume":2000})
    for i,px in enumerate([117,115,114,112,113]):
        bars.append({"session_date":(datetime(2025,9,1)+timedelta(days=70+i)).date().isoformat(),
                     "close":px,"high":px+.2,"low":px-.2,"volume":1000})
    result=pullback_evidence(bars,DEFAULT_CONFIG)
    assert result["prior_uptrend"] is True and result["pullback_mechanical_match"] is True
    assert result["volume_contraction_ratio"] == .5
    day=bars[-1]["session_date"]
    c=candidate(candles=bars,last_close=113)
    before=local_evidence(c,session=day,cutoff=T0,cfg=DEFAULT_CONFIG)
    future={"session_date":"2026-02-01","close":1000,"high":2000,"low":1,"volume":1e9}
    after=local_evidence({**c,"candles":bars+[future]},session=day,cutoff=T0,cfg=DEFAULT_CONFIG)
    assert before == after
    assert abs(before["CLV"]) < 1e-8


def test_missing_outcomes_do_not_count_as_losses_and_legacy_outcomes_excluded(stores):
    store,db=stores
    freeze(store)
    cid=store.validation_records("forward_signal_snapshots")[0]["canonical_signal_id"]
    store.upsert_canonical_outcome({"canonical_signal_id":cid,"ticker":"AAA","return_20":99,"maturity_20":"MATURE"})
    assert validation_report(store)["summary"]["horizons"]["20"]["N"] == 0
    seed(db,"AAA",2)
    update_outcomes_for_store(store,db,forward_validation_only=True)
    summary=validation_report(store)["summary"]
    assert summary["horizons"]["1"]["N"] == 1
    assert summary["horizons"]["20"]["N"] == 0
    assert summary["horizons"]["20"]["empirical_positive_return_rate"] is None


def test_new_full_run_archives_v27_without_inheriting_completion(tmp_path,monkeypatch):
    from egxbridge.analysis.funnel.registry import FunnelRegistry
    from egxbridge.analysis.funnel.state import save_project,load_project
    from egxbridge.analysis.funnel.importer import import_funnel_result
    from egxbridge.analysis.funnel.handoff import prepare_funnel_handoff
    import egxbridge.analysis.funnel.registry as registry_module
    store=AnalysisStore(tmp_path/"a.sqlite",environment=UNIT_TEST)
    registry=FunnelRegistry(workspace_root=tmp_path/"funnels",store=store)
    old=registry.create("AAA")
    old.funnel_version="EGX_STOCK_ANALYSIS_FUNNEL_v2.7"
    save_project(old,root=registry.workspace_root,store=store)
    original="analysis_scope: FULL_FUNNEL\nrun_mode: FULL_AUTOMATED_RUN\nresult_type: COMPLETE_FUNNEL_RESULT\nFair Value: 120\nFinal Decision: WATCH\nComplete economic valuation with verified supporting evidence."
    import_funnel_result("AAA",original,store=store,workspace_root=registry.workspace_root,advance_stage=False)
    old=registry.get("AAA")
    assert old.funnel_completion_status == "COMPLETE"
    monkeypatch.setattr(registry_module,"prepare_funnel_handoff",lambda p,**kw: prepare_funnel_handoff(p,output_root=tmp_path/"out",**kw))
    res=registry.prepare_full("AAA")
    current=registry.get("AAA")
    assert current.funnel_version == "2.8"
    assert current.funnel_completion_status != "COMPLETE" and current.delta_eligible == "NO"
    archived=Path(current.archived_funnel_workspace)
    assert json.loads((archived/"project.json").read_text())["funnel_version"].endswith("2.7")
    assert (archived/"results/latest_funnel_result.md").read_text() == original
    assert store.list_stage_results("AAA")[0]["content_text"] == original
    assert (Path(res["package_dir"])/"MASTER_FUNNEL_v2.8.md").exists()
    with pytest.raises(ValueError):
        import_funnel_result("AAA",json.dumps({"funnel_version":"2.7","final_decision_summary":{"central_fv":200}}),store=store,workspace_root=registry.workspace_root)
    assert registry.get("AAA").funnel_completion_status != "COMPLETE"
    store.close()


def test_cairo_friday_saturday_weekend_sunday_continuous():
    from egxbridge.analysis.schedule.session import classify_session_phase
    assert classify_session_phase("2026-01-02T12:00:00+02:00") == "POST_CLOSE"
    assert classify_session_phase("2026-01-03T12:00:00+02:00") == "POST_CLOSE"
    assert classify_session_phase("2026-01-04T12:00:00+02:00") == "CONTINUOUS_TRADING"


def test_partial_import_schema_errors_and_missing_labels_are_not_judgments(stores):
    from egxbridge.analysis.funnel.schema import extract_summary
    assert normalize_fields("malformed")[1]
    assert extract_summary("",{"final_decision_summary":[1,2]})[1]
    store,db=stores
    freeze(store)
    cid=store.validation_records("forward_signal_snapshots")[0]["canonical_signal_id"]
    classify(store,cid,"AAA",{"expectations_revision_outlook":"NOT_ANALYZED"},source_id="missing")
    classify(store,cid,"AAA",{"expectations_revision_outlook":"UPWARD"},source_id="known",stamp="2026-01-02T13:00:00+00:00")
    seed(db,"AAA",1)
    update_outcomes_for_store(store,db,forward_validation_only=True)
    assert validation_report(store)["signals"][0]["expectations_revision_outlook"] == "UPWARD"
    invalid=compute_outcomes(baseline_price="NOT_AVAILABLE",baseline_timestamp=T0,baseline_type="UNKNOWN",signal_session=SESSION,future_bars=[])
    assert invalid["outcome_status"] == "NOT_EVALUABLE"


def test_missing_first_future_bars_cannot_admit_late_classifications(stores):
    store, db = stores
    freeze(store)
    cid = store.validation_records("forward_signal_snapshots")[0]["canonical_signal_id"]
    classify(store, cid, "AAA", {"expectations_revision_outlook": "UPWARD"},
             stamp="2026-01-05T15:00:00+00:00")
    # The provider only has a bar from Jan 7. Its absence on Jan 4/5 must
    # not create permission to call the Jan 5 opinion a pre-outcome judgment.
    db.upsert_candle({"symbol": "AAA", "interval": "1d", "timestamp": "2026-01-07T00:00:00+00:00",
        "session_date": "2026-01-07", "open": 109, "high": 111, "low": 108,
        "close": 110, "volume": 1000, "provider": "synthetic",
        "capture_timestamp": "2026-01-07T15:00:00+00:00"})
    before = validation_report(store)
    update_outcomes_for_store(store, db, forward_validation_only=True)
    after = validation_report(store)
    for report in (before, after):
        assert report["sample_integrity"]["excluded_late_classifications"] == 1
        assert "expectations_revision_outlook" not in report["signals"][0]
    assert after["signals"][0]["return_1"] == 10


def test_cutoff_metadata_and_timezone_ordering(stores):
    store, db = stores
    freeze(store)
    cid = store.validation_records("forward_signal_snapshots")[0]["canonical_signal_id"]
    classify(store, cid, "AAA", {"expectations_gap": "POSITIVE"}, source_id="future-market",
             market_data_cutoff="2026-02-01")
    classify(store, cid, "AAA", {"expectations_revision_outlook": "DOWNWARD"}, source_id="later",
             stamp="2026-01-02T08:30:00+00:00")
    classify(store, cid, "AAA", {"expectations_revision_outlook": "UPWARD"}, source_id="earlier",
             stamp="2026-01-02T10:00:00+02:00")
    seed(db, "AAA", 1)
    update_outcomes_for_store(store, db, forward_validation_only=True)
    signal = validation_report(store)["signals"][0]
    assert signal["expectations_revision_outlook"] == "UPWARD"
    assert "expectations_gap" not in signal


def test_partial_funnel_import_preserves_each_fields_original_provenance(tmp_path, monkeypatch):
    from egxbridge.analysis.funnel.registry import FunnelRegistry
    import egxbridge.analysis.funnel.importer as importer

    store = AnalysisStore(tmp_path / "analysis.sqlite", environment=UNIT_TEST)
    registry = FunnelRegistry(workspace_root=tmp_path / "funnels", store=store)
    registry.create("AAA")
    first_at = "2025-12-29T15:00:00+00:00"
    second_at = "2025-12-31T15:00:00+00:00"
    for at, fields in ((first_at, {"central_fv": 80, "price_implied_expectations": "REASONABLE"}),
                       (second_at, {"expectations_revision_outlook": "UPWARD"})):
        monkeypatch.setattr(importer, "utc_now", lambda: at)
        importer.import_funnel_result("AAA", json.dumps({"funnel_version": "2.8",
            "declared_research_cutoff": at, "market_data_cutoff": at[:10],
            "final_decision_summary": fields}), store=store, workspace_root=registry.workspace_root,
            advance_stage=False)
    project = registry.get("AAA")
    provenance = project.structured_provenance["field_provenance"]
    assert provenance["central_fv"]["analysis_imported_at"] == first_at
    assert provenance["expectations_revision_outlook"]["analysis_imported_at"] == second_at
    freeze(store, [candidate(funnel_ctx={"funnel_version": project.funnel_version,
        "structured_fields": project.structured_fields, "structured_provenance": project.structured_provenance})])
    records = store.validation_records("forward_signal_classifications")
    assert len(records) == 2
    by_field = {key: row for row in records for key in row["fields"]}
    assert by_field["central_fv"]["analysis_imported_at"] == first_at
    assert by_field["central_fv"]["source_cutoff"] == first_at
    assert by_field["central_fv"]["market_data_cutoff"] == first_at[:10]
    assert by_field["expectations_revision_outlook"]["analysis_imported_at"] == second_at
    store.close()


def test_fresh_capital_pillars_remain_separate_imported_values():
    fields, issues = normalize_fields({"fresh_capital_pillars": {
        "Economic Quality": "STRONG", "Expectations Burden": "DEMANDING",
        "Expectations Revision Edge": "UPWARD", "Risk Adjusted Return": "NOT_RELIABLE"}})
    assert not issues
    assert fields == {"economic_quality": "STRONG", "expectations_burden": "DEMANDING",
                      "expectations_revision_edge": "UPWARD", "risk_adjusted_return": "NOT_RELIABLE"}
    assert "fresh_capital_test" not in fields
    assert normalize_fields({"psychological_levels": {"PLSS_raw": 3}})[1]


@pytest.mark.parametrize("config", [
    {"false_negative_top_fraction": 2}, {"false_negative_top_n": -1},
    {"pullback_min_pct": 8, "pullback_max_pct": 3}, {"round_increment_mantissas": [0]},
    {"friction_model": {"components_pct": {"spread": -1}}},
])
def test_invalid_initial_rules_are_rejected_before_freezing(stores, config):
    store, _ = stores
    with pytest.raises(ValueError):
        start_validation(store, at=T0, config=config)
    assert not store.validation_records("forward_test_runs")
    assert not store.validation_records("rule_definitions")


def test_round_breakout_requires_a_crossing_and_reliable_ohlc():
    from egxbridge.analysis.schedule.outcomes import outcome_for_snapshot
    snapshot = {"ticker": "AAA", "price_t0": 101, "market_session": SESSION,
                "round_number_encounters": [{"round_level": 100}]}
    bar = {"session_date": "2026-01-04", "close": 102, "high": 103, "low": 101}
    def event(row, baseline=101):
        out = outcome_for_snapshot({**snapshot, "price_t0": baseline}, [row],
            horizons=(1,), through_session="2026-01-04")
        return out["round_number_outcomes_1"][0]
    assert event(bar)["close_above"] is True
    assert event(bar)["breakout"] is False
    assert event(bar, baseline=99)["breakout"] is True
    assert event({**bar, "low": 104})["status"] == "NOT_RELIABLE"


def test_subset_outcome_update_preserves_complete_evidence_for_mature_horizons(stores):
    store, db = stores
    model = {"friction_inputs_source": "SYNTHETIC", "components_pct": {
        "brokerage": .2, "exchange_regulatory": .1, "taxes": 0, "spread": .3, "slippage": .4}}
    start_validation(store, at=T0, config={"friction_model": model})
    freeze(store, [candidate(target_price_t0=105, target_source="SYNTHETIC")])
    seed(db, "AAA", 20)
    update_outcomes_for_store(store, db, horizons=(1,), forward_validation_only=True)
    update_outcomes_for_store(store, db, forward_validation_only=True)
    row = validation_report(store)["signals"][0]
    assert len(row["session_dates"]) == 20
    assert row["return_20"] == 20
    assert row["net_return_after_friction_20"] == 19
    assert row["target_stop_20"]["target_hit"] is True
