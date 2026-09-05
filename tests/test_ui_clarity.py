"""UI regression checks for navigation, display units and guided workflows."""
from pathlib import Path
import json

from streamlit.testing.v1 import AppTest

from egxbridge.ui.candidates import candidate_preview_rows, sort_candidates
from egxbridge.ui.forward_validation import _rows
from egxbridge.ui.workflow_state import is_weekend, recommended_jobs


def test_sunday_is_a_possible_session_not_a_weekend_review():
    assert is_weekend(4) and is_weekend(5)
    assert not is_weekend(6)
    assert not recommended_jobs(session_phase="PRE_OPEN", cairo_weekday=6)["weekly_recommended"]


def test_candidate_table_preserves_the_requested_sort_order():
    candidates = [{"ticker": "ZZZ", "calibrated_rank": 1}, {"ticker": "AAA", "calibrated_rank": 2}]
    ordered = sort_candidates(candidates, "Ticker")
    assert [r["Ticker"] for r in candidate_preview_rows(ordered, sort_by_rank=False)] == ["AAA", "ZZZ"]
    assert [r["Ticker"] for r in candidate_preview_rows(candidates)] == ["ZZZ", "AAA"]


def test_report_horizon_rates_and_missing_values_keep_their_meaning():
    groups = [{"N": 3, "horizons": {
        "5": {"N": 2, "independent_signal_n": 2, "median_return": 4.5, "empirical_positive_return_rate": .5},
        "20": {"N": 0, "independent_signal_n": 0, "median_return": None, "empirical_positive_return_rate": None}}}]
    five, twenty = _rows(groups, 5)[0], _rows(groups, 20)[0]
    assert five["Empirical positive-return rate (%)"] == 50
    assert five["Median return · +5 (%)"] == 4.5
    assert five["Ready outcomes (N)"] == 2
    assert twenty["Empirical positive-return rate (%)"] is None
    assert twenty["Net return after costs (%)"] is None
    assert "Median return · +5 (%)" not in twenty


def test_first_run_explains_next_action_and_keeps_advanced_steps_collapsed(tmp_path):
    script = f'''
from pathlib import Path
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.funnel.registry import FunnelRegistry
from egxbridge.ui.daily_operator import render_daily_operator
root = Path({str(tmp_path)!r})
store = AnalysisStore(root / "analysis.sqlite", environment="UNIT_TEST")
funnel = FunnelRegistry(workspace_root=root / "funnels", store=store)
render_daily_operator(store=store, funnel_reg=funnel, root=root)
store.close()
'''
    app = AppTest.from_string(script).run(timeout=20)
    assert not app.exception
    content = " ".join(m.value for m in app.markdown)
    assert "Next: Scan the market" in content
    assert "In this app" in content
    assert "1. Scan the market" in content
    assert any(b.key == "cta_primary" and not b.disabled for b in app.button)
    assert [t.label for t in app.tabs] == ["Candidate shortlist", "Imported analysis", "Outcome tracking"]
    assert any(e.label == "Full workflow · step details and manual actions" for e in app.expander)
    assert any("shortlist will appear" in i.value for i in app.info)


def test_import_form_defaults_to_next_missing_reply():
    script = '''
from egxbridge.ui.daily_operator import _import_result_form
_import_result_form({"schedule": {"included_jobs": ["MACRO_HOLDINGS", "PREMARKET_CATALYSTS", "VALUE_QUALITY"]},
    "imports": {"MACRO_HOLDINGS": {"status": "IMPORTED"}}}, None)
'''
    app = AppTest.from_string(script).run()
    assert not app.exception
    assert app.selectbox(key="do_imp_type").value == "PREMARKET_CATALYSTS"
    assert app.button(key="do_imp_go").disabled
    first_upload_id = app.get("file_uploader")[0].proto.id
    app.session_state["do_imp_type"] = "MACRO_HOLDINGS"
    app.session_state["op_import_advance"] = True
    app.run()
    assert not app.exception
    assert app.selectbox(key="do_imp_type").value == "PREMARKET_CATALYSTS"
    assert app.get("file_uploader")[0].proto.id != first_upload_id
    assert app.button(key="do_imp_go").disabled


def test_candidate_search_and_company_navigation(tmp_path):
    folder = tmp_path / "output" / "explorer_handoff"
    folder.mkdir(parents=True)
    (folder / "explorer_handoff.json").write_text(json.dumps({
        "generated_at": "2026-09-03T15:00:00+00:00", "latest_completed_market_session": "2026-09-03",
        "candidates": [{"ticker": "ZZZ", "calibrated_rank": 1}, {"ticker": "AAA", "calibrated_rank": 2}]}))
    script = f'''
from pathlib import Path
from egxbridge.ui.explorer_candidates import render_explorer_candidates
render_explorer_candidates(root=Path({str(tmp_path)!r}))
'''
    app = AppTest.from_string(script).run(timeout=20)
    assert not app.exception
    app.text_input(key="candidates_query").input("aaa").run()
    assert not app.exception
    assert app.selectbox(key="candidate_inspect").options == ["AAA"]
    app.button(key="candidate_open_funnel").click().run()
    assert app.session_state["funnel_ticker"] == "AAA"
    assert app.session_state["op_nav"] == "Analysis Workflows"
    app.text_input(key="candidates_query").input("no-match").run()
    assert not app.exception
    assert any("No candidates match" in i.value for i in app.info)
