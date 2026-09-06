"""Operational integrity fixtures. SYNTHETIC_ACCEPTANCE_NOT_PRODUCTION."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.common.environment import UNIT_TEST
from egxbridge.analysis.funnel.registry import FunnelRegistry
from egxbridge.analysis.funnel.state import workspace_dir, save_project
from egxbridge.analysis.funnel.schema import extract_summary, normalize_fields
from egxbridge.analysis.schedule.session import CAIRO, classify_session_phase, session_context
from egxbridge.analysis.schedule.outcomes import completed_through
from egxbridge.freshness import egx_session_open_at, EGX_SESSION_CLOSE
from egxbridge.ui.versions import version_labels

ROOT = Path(__file__).resolve().parents[1]
OLD_AUDIT = "EGX_STAGE12_AUDIT_FINAL_PACK_v1.1_v2.7_COMPATIBLE.md"
ARCHIVED_AUDIT = "prompts/archive/" + OLD_AUDIT
CURRENT_AUDIT = "EGX_STAGE12_AUDIT_FINAL_PACK_v1.2_v2.8_COMPATIBLE.md"
BOUNDARIES = [
    ("09:59:59", "PRE_OPEN"), ("10:00:00", "CONTINUOUS_TRADING"),
    ("14:14:59", "CONTINUOUS_TRADING"), ("14:15:00", "CLOSING_AUCTION"),
    ("14:24:59", "CLOSING_AUCTION"), ("14:25:00", "TRADING_AT_LAST"),
    ("14:29:59", "TRADING_AT_LAST"), ("14:30:00", "POST_CLOSE"),
    ("14:45:00", "POST_CLOSE"),
]
VALUATION = {"central_fv": 37.0, "highest_credible_bull_fv": 44.0,
    "valuation_date": "2026-09-06", "price_implied_expectations": "REASONABLE",
    "expectations_revision_outlook": "UPWARD"}


def cairo_at(clock, day="2026-09-06"):
    return datetime.fromisoformat(day + "T" + clock).replace(tzinfo=CAIRO)


def reply(fields, prose="", version="2.8"):
    envelope = {"funnel_version": version, "final_decision_summary": fields,
        "analysis_started_at": "2026-09-06T09:00:00+03:00",
        "declared_research_cutoff": "2026-09-06T08:00:00+03:00",
        "market_data_cutoff": "2026-09-03T14:30:00+03:00"}
    return "SYNTHETIC_ACCEPTANCE_NOT_PRODUCTION\n" + prose + "\n```json\n" + json.dumps(envelope, indent=2) + "\n```\n"


def valuation_case(root, fields, prose="", *, version="2.8", environment=UNIT_TEST):
    root.mkdir(parents=True, exist_ok=True)
    store = AnalysisStore(root / "analysis.sqlite", environment=environment)
    registry = FunnelRegistry(workspace_root=root / "funnels", store=store)
    project = registry.create("SYNTH")
    project.funnel_version = version
    save_project(project, root=registry.workspace_root, store=store)
    raw = reply(fields, prose, version)
    result = registry.import_result("SYNTH", raw, stage_id="6")
    history = json.loads((workspace_dir("SYNTH", registry.workspace_root) / "results/valuation_history.json").read_text())
    report = {"evidence_kind": "SYNTHETIC_ACCEPTANCE_NOT_PRODUCTION", "environment": store.environment,
        "result": result, "history": history, "persisted_keys": store.all_key_values("SYNTH"),
        "raw_preserved": Path(result["saved_path"]).read_text() == raw and store.get_stage_result("SYNTH", "6")["content_text"] == raw,
        "stage_metadata": store.get_stage_result("SYNTH", "6")["meta"],
        "forward_signal_n": len(store.validation_records("forward_signal_snapshots"))}
    store.close()
    return report


@pytest.mark.parametrize("clock,phase", BOUNDARIES)
def test_exact_cairo_session_boundaries(clock, phase):
    at = cairo_at(clock)  # Sunday is a possible normal session day.
    assert classify_session_phase(at) == phase
    assert classify_session_phase(at.astimezone(timezone.utc)) == phase
    assert egx_session_open_at(at) == (phase not in {"PRE_OPEN", "POST_CLOSE"})


@pytest.mark.parametrize("day", ["2026-09-04", "2026-09-05"])
def test_weekends_are_post_close(day):
    assert classify_session_phase(cairo_at("12:00:00", day)) == "POST_CLOSE"
    assert not egx_session_open_at(cairo_at("12:00:00", day))


@pytest.mark.parametrize("clock,expected", [("14:29:59", "2026-09-05"), ("14:30:00", "2026-09-06")])
def test_completed_session_boundary_uses_cairo(clock, expected):
    at = cairo_at(clock)
    assert completed_through(at) == expected
    assert completed_through(at.astimezone(timezone.utc)) == expected


def test_session_context_matches_freshness_band():
    from egxbridge.analysis.schedule.session import TRADING_AT_LAST_END
    assert (EGX_SESSION_CLOSE.hour, EGX_SESSION_CLOSE.minute) == TRADING_AT_LAST_END
    bands = session_context(cairo_at("14:30:00"))["egx_bands_cairo"]
    assert bands["CONTINUOUS_TRADING"] == "10:00–14:15"
    assert bands["CLOSING_AUCTION"] == "14:15–14:25"
    assert bands["TRADING_AT_LAST"] == "14:25–14:30"


def test_structured_only_valuation_is_persisted_without_completing_funnel(tmp_path):
    data = valuation_case(tmp_path, VALUATION)
    project = data["result"]["project"]
    assert project["structured_fields"]["central_fv"] == 37.0
    assert project["last_valuation_date"] == "2026-09-06"
    assert project["valuation_status"] == "UPDATED"
    assert data["persisted_keys"]["Fair Value"] == "37.0"
    assert data["history"][0]["central_fv"] == 37.0
    assert data["history"][0]["highest_credible_bull_fv"] == 44.0
    assert data["history"][0]["source_kind"] == "STRUCTURED_FUNNEL_V28"
    assert project["funnel_completion_status"] == "PARTIAL"
    assert project["delta_eligible"] == "NO"
    assert project["verified_completed_stages"] == ["6"]
    assert data["raw_preserved"] and data["forward_signal_n"] == 0
    assert data["result"]["schema_issues"] == []


@pytest.mark.parametrize("version", ["2.7", "2.8"])
def test_legacy_only_response_still_persists(tmp_path, version):
    data = valuation_case(tmp_path, {}, "Fair Value: 35\nValuation date: 2026-09-06", version=version)
    assert data["persisted_keys"]["Fair Value"] == "35"
    assert "central_fv" not in data["result"]["project"]["structured_fields"]
    assert data["result"]["project"]["valuation_status"] == "UPDATED"
    assert data["history"][0]["fair_value"] == "35"
    assert data["history"][0]["source_kind"] == "LEGACY_TEXT_EXTRACTION"
    assert data["raw_preserved"]


def test_structured_prose_conflict_is_exposed_and_preserved(tmp_path):
    data = valuation_case(tmp_path, VALUATION, "Fair Value: 40\nBlended Fair Value: 41")
    assert data["persisted_keys"]["Fair Value"] == data["persisted_keys"]["Blended Fair Value"] == "37.0"
    conflict = data["result"]["valuation_diagnostics"][0]
    assert conflict["code"] == "VALUATION_SOURCE_CONFLICT"
    assert conflict["structured_value"] == 37.0
    assert conflict["legacy_text_value"] == 40.0
    assert conflict["chosen_source"] == "STRUCTURED_FUNNEL_V28"
    assert conflict["content_hash"] == data["result"]["content_hash"]
    assert data["history"][0]["diagnostics"][0] == conflict
    assert data["stage_metadata"]["valuation_diagnostics"][0] == conflict
    assert data["result"]["optional_extracted_keys"]["Fair Value"] == "40"
    assert data["raw_preserved"]


def test_expected_price_and_all_valuation_fields_stay_separate(tmp_path):
    fields = {**VALUATION, "expected_horizon_market_price": 43, "economic_terminal_value": 47,
        "robust_fv_range": "32–41", "expected_return_spread": "POSITIVE"}
    data = valuation_case(tmp_path, fields)
    for key, value in fields.items():
        assert data["result"]["project"]["structured_fields"][key] == value
        if key not in {"price_implied_expectations", "expectations_revision_outlook"}:
            assert data["history"][0][key] == value
    assert data["persisted_keys"]["Fair Value"] == "37.0"


@pytest.mark.parametrize("fields", [
    {"central_fv": 37}, {"central_fv": 37, "valuation_date": "2026-02-30"},
    {"expected_horizon_market_price": 43}, {"valuation_date": "2026-09-06"},
])
def test_partial_valuation_does_not_invent_missing_values_or_completion(tmp_path, fields):
    data = valuation_case(tmp_path, fields)
    project = data["result"]["project"]
    assert project["valuation_status"] != "UPDATED"
    assert project["funnel_completion_status"] != "COMPLETE"
    assert project["delta_eligible"] == "NO"
    if "central_fv" not in fields:
        assert "central_fv" not in project["structured_fields"]
        assert "Fair Value" not in data["persisted_keys"]
    if fields.get("valuation_date") != "2026-09-06":
        assert project["last_valuation_date"] is None


def test_later_partial_fields_preserve_history_and_field_availability(tmp_path, monkeypatch):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    registry = FunnelRegistry(workspace_root=tmp_path / "funnels", store=store)
    registry.create("SYNTH")
    path = workspace_dir("SYNTH", registry.workspace_root) / "results/valuation_history.json"
    old = {"recorded_at": "2025-01-01", "fair_value": "30", "stage": "5"}
    path.write_text(json.dumps([old]))
    monkeypatch.setattr("egxbridge.analysis.funnel.importer.utc_now", lambda: "2026-09-06T07:00:00+00:00")
    first = registry.import_result("SYNTH", reply({"central_fv": 37}), stage_id="6")
    provenance = first["project"]["structured_provenance"]["field_provenance"]["central_fv"]
    monkeypatch.setattr("egxbridge.analysis.funnel.importer.utc_now", lambda: "2026-09-07T07:00:00+00:00")
    second = registry.import_result("SYNTH", reply({"valuation_date": "2026-09-06", "expected_horizon_market_price": 43}), stage_id="7")
    assert second["project"]["valuation_status"] == "UPDATED"
    assert second["project"]["structured_provenance"]["field_provenance"]["central_fv"] == provenance
    saved_source = store._conn.execute("SELECT source_stage FROM funnel_key_values WHERE key_name='Fair Value'").fetchone()
    assert saved_source["source_stage"] == "6"
    assert second["project"]["structured_provenance"]["field_provenance"]["expected_horizon_market_price"]["analysis_imported_at"] == "2026-09-07T07:00:00+00:00"
    third = registry.import_result("SYNTH", "Fair Value: 40\nUnrelated partial stage", stage_id="8")
    assert third["project"]["structured_fields"]["central_fv"] == 37
    assert store.get_key_value("SYNTH", "Fair Value") == "37.0"
    assert third["valuation_diagnostics"]
    history = json.loads(path.read_text())
    assert history[0] == old and len(history) == 4
    assert history[2]["field_provenance"]["central_fv"] == provenance
    assert provenance["analysis_started_at"] and provenance["declared_research_cutoff"] and provenance["market_data_cutoff"]
    assert third["project"]["funnel_completion_status"] != "COMPLETE"
    store.close()


def test_valid_structured_alias_wins_and_invalid_structured_value_falls_back(tmp_path):
    fields, _ = extract_summary("Central Fair Value: 40", {"structured_fields": {"central_fv": 37}})
    assert fields["central_fv"] == 37
    fields, issues = extract_summary("Central Fair Value: 40", {"structured_fields": {"central_fv": "bad"}})
    assert fields["central_fv"] == 40 and issues
    data = valuation_case(tmp_path, {"central_fv": "bad"}, "Fair Value: 35\nValuation date: 2026-09-06")
    assert data["persisted_keys"]["Fair Value"] == "35"
    assert data["result"]["schema_issues"]
    assert normalize_fields({"valuation_date": "tomorrow"})[1]


def test_release_versions_and_frozen_sources():
    labels = version_labels()
    assert labels["application_version"] == labels["workflow_version"] == "0.7.1"
    assert labels["funnel_prompt_version"] == "2.8"
    assert labels["scoring_version"] == "0.5.1"
    assert labels["score_kind"] == "HEURISTIC_UNCALIBRATED"
    assert labels["market_data_schema_version"] == "0.3.1"
    assert labels["ai_mode"] == "CHATGPT_HANDOFF"
    for name, expected in json.loads((ROOT / "tests/fixtures/v071_frozen_sources.json").read_text()).items():
        path = ARCHIVED_AUDIT if name == OLD_AUDIT else name
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, name
    assert not (ROOT / OLD_AUDIT).exists()
    assert (ROOT / CURRENT_AUDIT).is_file()
