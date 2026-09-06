from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys

import pandas as pd
import streamlit as st

import importlib

from egxbridge.ui import DEFAULT_PAGE, OPERATE_PAGES, TECHNICAL_PAGES
from egxbridge.ui.theme import inject_operator_theme
from egxbridge.ui.versions import version_caption, version_labels
from egxbridge.ui.components import display_label, download_zip

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
DB_PATH = OUT / "egx_bridge.sqlite"

_labels = version_labels()
st.set_page_config(page_title=_labels["title"], layout="wide")

# Streamlit caches imported UI modules; reload so Daily Operator copy stays current.
from egxbridge.ui import actions as _ui_actions
from egxbridge.ui import components as _ui_components
from egxbridge.ui import daily_operator as _ui_daily_operator
from egxbridge.ui import explorer_candidates as _ui_explorer_candidates
from egxbridge.ui import snapshot as _ui_snapshot
from egxbridge.ui import theme as _ui_theme
from egxbridge.ui import workflow_state as _ui_workflow_state
for _mod in (
    _ui_theme,
    _ui_workflow_state,
    _ui_actions,
    _ui_snapshot,
    _ui_components,
    _ui_daily_operator,
    _ui_explorer_candidates,
):
    importlib.reload(_mod)
inject_operator_theme()

if "op_nav" not in st.session_state:
    st.session_state["op_nav"] = DEFAULT_PAGE

st.sidebar.markdown("### EGX Market Bridge")
st.sidebar.caption("Market research, one step at a time.")
st.sidebar.markdown('<div class="nav-group">Daily workflow</div>', unsafe_allow_html=True)
for _label in OPERATE_PAGES:
    if st.session_state["op_nav"] == _label:
        st.sidebar.markdown(f'<div class="nav-current">{_label}</div>', unsafe_allow_html=True)
    elif st.sidebar.button(_label, key=f"nav_{_label}", type="secondary", use_container_width=True):
        st.session_state["op_nav"] = _label
        st.rerun()
with st.sidebar.expander("Market data and diagnostics", expanded=st.session_state["op_nav"] in TECHNICAL_PAGES):
    for _label in TECHNICAL_PAGES:
        if st.session_state["op_nav"] == _label:
            st.markdown(f'<div class="nav-current">{_label}</div>', unsafe_allow_html=True)
        elif st.button(_label, key=f"nav_{_label}", type="secondary", use_container_width=True):
            st.session_state["op_nav"] = _label
            st.rerun()
st.sidebar.caption("Start with Daily Operator whenever you need the next step.")
with st.sidebar.expander("Versions and responsibilities"):
    st.caption(version_caption(_labels))
    st.write("The app collects evidence. ChatGPT analyzes it. You make the final capital decision.")
    st.caption("Files are transferred manually to ChatGPT. No orders are placed by this app.")

page = st.session_state["op_nav"]
if page != "Daily Operator":
    if page not in {"Explorer Candidates", "Forward Validation Lab"}:
        st.title(page)


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_db():
    if not DB_PATH.exists():
        return None
    try:
        from egxbridge.db import Database
        return Database(DB_PATH)
    except Exception as e:
        st.warning(f"DB open failed: {e}")
        return None


handoff = load_json(OUT / "chatgpt_handoff.json")
scanner = load_json(OUT / "scanner_handoff.json")
probe = load_json(OUT / "probe.json")
universe = load_json(OUT / "universe.json")
db = load_db()

ANALYSIS_DB = OUT / "analysis.sqlite"


def analysis_handles():
    from egxbridge.analysis.common.persistence import AnalysisStore
    from egxbridge.analysis.common.environment import PRODUCTION
    from egxbridge.analysis.funnel.registry import FunnelRegistry
    from egxbridge.analysis.explorer.registry import ExplorerRegistry
    store = AnalysisStore(ANALYSIS_DB, environment=PRODUCTION)
    funnel = FunnelRegistry(store=store, db=db, environment=PRODUCTION)
    explorer = ExplorerRegistry(store=store, db=db, funnel_registry=funnel, environment=PRODUCTION)
    return store, funnel, explorer


if page == "Daily Operator":
    from egxbridge.ui.daily_operator import render_daily_operator
    store, funnel_reg, _explorer = analysis_handles()
    render_daily_operator(store=store, funnel_reg=funnel_reg, db=db, root=HERE)
    store.close()

elif page == "Explorer Candidates":
    from egxbridge.ui.explorer_candidates import render_explorer_candidates
    store, _funnel, _explorer = analysis_handles()
    render_explorer_candidates(root=HERE, store=store, db=db)
    store.close()

elif page == "System Overview":
    from egxbridge.ui.snapshot import gather_operator_snapshot
    store, _funnel, _explorer = analysis_handles()
    snap = gather_operator_snapshot(root=HERE, store=store, db=db)
    store.close()
    st.subheader("System Overview")
    st.caption("Diagnostics for collectors and providers. Daily work starts on Daily Operator.")
    st.write({
        "Application Version": _labels["application_version"],
        "Market Data Schema": _labels["market_data_schema_version"],
        "Scoring Version": _labels["scoring_version"],
        "Market Data Status": snap.get("market_data_status"),
        "Provider Coverage Status": snap.get("provider_status"),
        "Explorer Status": snap.get("explorer_status"),
        "Schedules": "READY" if snap.get("schedules_prepared") else "NOT_PREPARED",
        "Freshness": snap.get("freshness"),
        "Session phase": snap.get("session_phase"),
        "Latest completed session": snap.get("latest_completed_market_session"),
    })
    if snap.get("handoff_status") == "PARTIAL":
        st.caption(
            "chatgpt_handoff.json status PARTIAL means the focus snapshot has limited provider coverage. "
            "It is not a generic app status — see Market Data / Providers / Explorer separately."
        )
    if not handoff:
        st.info("No focus snapshot yet. Use Daily Operator → Refresh Market Data.")
    else:
        st.subheader("Latest sample observations")
        st.caption("Focus-snapshot quotes only — not the Explorer universe and not whole-market state.")
        rows = []
        for s in handoff.get("symbols", []):
            q = s.get("quote") or {}
            rows.append({
                "Ticker": s.get("symbol"),
                "Last": s.get("price") or q.get("last"),
                "Source": s.get("price_source") or q.get("provider"),
                "Freshness": s.get("freshness") or q.get("freshness_class"),
                "Volume": s.get("volume") or q.get("volume"),
                "Research DQ": s.get("research_data_quality"),
                "Execution DQ": s.get("execution_data_quality"),
                "Warnings": " | ".join((s.get("warnings") or [])[:3]),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        with st.expander("Handoff files"):
            st.code(str(OUT / "chatgpt_handoff.json"))
            st.code(str(OUT / "scanner_handoff.json"))
            st.caption(f"Market Data Schema in this file: {handoff.get('version')} (not the application version)")

elif page == "Analysis Workflows":
    st.write("Prepare company analysis for ChatGPT, then import its findings to keep your Funnel up to date.")
    store, funnel_reg, explorer_reg = analysis_handles()

    col_a, col_b = st.tabs(["Company analysis · Funnel", "Custom Explorer scan"])

    with col_a:
        st.subheader("Analyze a company")
        st.caption("1. Choose a ticker and analysis mode. 2. Download the evidence for ChatGPT. 3. Import the saved reply below.")
        if "funnel_ticker" not in st.session_state:
            st.session_state["funnel_ticker"] = "MASR"
        fticker = st.text_input("Ticker", key="funnel_ticker").upper().strip()
        with st.expander("Analysis preferences · optional", expanded=False):
            fobj = st.selectbox(
                "Analysis Objective",
                [
                    "FULL_HYBRID_REVIEW",
                    "LONG_TERM_INVESTMENT",
                    "SWING_POSITION_TRADE",
                    "SHORT_TERM_SPECULATION",
                    "OWNED_POSITION_REVIEW",
                ],
                key="funnel_obj",
                format_func=display_label,
            )
            fmode = st.selectbox(
                "Run Mode",
                ["INTERACTIVE_STAGE_BY_STAGE", "FULL_AUTOMATED_RUN", "DELTA_ONLY"],
                key="funnel_mode",
                format_func=lambda mode: {"INTERACTIVE_STAGE_BY_STAGE": "Step by step · one Funnel stage", "FULL_AUTOMATED_RUN": "Full analysis · all stages in ChatGPT", "DELTA_ONLY": "Update an existing complete analysis"}[mode],
            )
            fown = st.selectbox(
                "Ownership State",
                ["NOT_OWNED", "OWNED", "OWNED_OVERWEIGHT", "OWNED_UNDERWEIGHT"],
                key="funnel_own",
                format_func=display_label,
            )
            fhorizon = st.text_input("Investment horizon (optional)", value="", placeholder="For example: 12 months", key="funnel_horizon")
            freq = st.text_input("Required return (optional)", value="", placeholder="For example: 20% per year", key="funnel_req")
            fcap = st.text_input("Proposed capital (optional)", value="", placeholder="Amount and currency", key="funnel_cap")
            fbench = st.text_input("Benchmark", value="EGX30", key="funnel_bench")

        proj = funnel_reg.get(fticker)
        if proj:
            from egxbridge.analysis.funnel.completion import sync_completion_fields
            sync_completion_fields(proj, store=store, workspace_root=HERE / "workspace" / "funnels")
            st.caption(f"Funnel {proj.funnel_version} · Stage {proj.current_stage} · {display_label(proj.funnel_completion_status)}")
            with st.expander("Company analysis state and source details"):
                st.write({
                    "Funnel version": proj.funnel_version,
                    "Current stage": proj.current_stage,
                    "Completed": proj.completed_stages,
                    "Funnel completion": proj.funnel_completion_status,
                    "Delta eligible": proj.delta_eligible,
                    "Valuation status": proj.valuation_status,
                    "Valuation date": proj.last_valuation_date,
                    "Exec grade (last handoff)": proj.execution_grade_at_last_handoff,
                    "Research DQ (last handoff)": proj.research_data_quality_at_last_handoff,
                })
            kv = store.all_key_values(fticker)
            if kv.get("Fair Value") or kv.get("Blended Fair Value"):
                st.write("Fair Value summary (imported only):", kv.get("Fair Value") or kv.get("Blended Fair Value"))
        else:
            st.caption("No Funnel project yet for this ticker.")

        if st.button("Prepare Funnel handoff", type="primary", disabled=not fticker):
            p = funnel_reg.get(fticker) or funnel_reg.create(
                fticker, analysis_objective=fobj, ownership_state=fown, run_mode=fmode,
                intended_horizon=fhorizon, personal_required_return=freq,
                proposed_capital=fcap, primary_benchmark=fbench,
            )
            if fmode == "DELTA_ONLY":
                res = funnel_reg.prepare_delta(fticker)
            elif fmode == "FULL_AUTOMATED_RUN":
                res = funnel_reg.prepare_full(fticker)
            else:
                res = funnel_reg.prepare_stage(fticker)
            if res.get("status") == "DELTA_NOT_AVAILABLE":
                st.warning(res.get("message") or "DELTA_NOT_AVAILABLE — REQUIRES_FULL_BUILD")
                st.json(res)
            else:
                st.success("Funnel evidence is ready. Download it below and attach it in ChatGPT.")
                st.session_state["funnel_download_" + fticker] = res.get("zip_path")
                st.json({
                    "execution_grade": res.get("execution_grade"),
                    "blocked": res.get("blocked_by_execution_grade"),
                    "session_date": res.get("session_date"),
                    "funnel_completion_status": res.get("funnel_completion_status"),
                    "delta_eligible": res.get("delta_eligible"),
                    "valuation_status": res.get("valuation_status"),
                })

        download_zip(st.session_state.get("funnel_download_" + fticker), label="Download Funnel evidence for ChatGPT", key="funnel_download")

        st.markdown("**Bring the ChatGPT analysis back**")
        st.caption("Save the company reply as .md, .txt or .json. Importing a stage preserves the original text and updates the saved Funnel state.")
        uploaded = st.file_uploader("Import ChatGPT Funnel result (.md/.txt/.json)", type=["md", "txt", "json"], key="funnel_up")
        if uploaded and st.button("Import Funnel result"):
            dest = OUT / "imports" / uploaded.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(uploaded.getvalue())
            imp = funnel_reg.import_result(fticker, dest)
            st.success(f"Imported stage {imp.get('stage_id')} — original preserved")
            if imp.get("valuation_diagnostics"):
                st.warning("VALUATION_SOURCE_CONFLICT: the structured valuation is authoritative. Conflicting prose is retained for review.")
                st.json(imp["valuation_diagnostics"])
            st.json({k: imp[k] for k in ("content_hash", "optional_extracted_keys", "saved_path") if k in imp})

        with st.expander("Funnel history and saved values"):
            st.json(store.list_corrections(fticker))
            st.json(store.all_key_values(fticker))

    with col_b:
        st.subheader("Next-day Explorer")
        st.caption("Discover what to watch, invest in, or tactically trade next EGX working day.")
        ehorizon = st.selectbox(
            "Explorer Horizon",
            ["NEXT_WORKING_DAY", "1_TO_3_SESSIONS", "1_WEEK", "TACTICAL_20_SESSIONS"],
            key="exp_horizon",
        )
        etarget = st.text_input("Target Date (optional YYYY-MM-DD)", value="", key="exp_date")
        euni = st.text_area("Universe (optional, comma-separated)", value="", key="exp_uni")
        eport = st.text_area("Optional portfolio context", value="", key="exp_port")

        if st.button("Prepare Explorer handoff"):
            from egxbridge.analysis.explorer.models import ExplorerRunConfig
            symbols = [x.strip().upper() for x in euni.split(",") if x.strip()] or None
            cfg = ExplorerRunConfig(
                horizon=ehorizon,
                universe=symbols or [],
                target_date=etarget or None,
                portfolio_context=eport,
                enrich_intraday=True,
            )
            res = explorer_reg.prepare(cfg)
            st.success(f"Explorer ZIP: {res.get('zip_path')}")
            st.write("Candidates:", res.get("candidate_count"), "| Funnel coverage:", res.get("funnel_coverage"))
            st.caption("No orders generated. Fair Value not manufactured.")

        exp_up = st.file_uploader("Import Explorer result", type=["md", "txt", "json"], key="exp_up")
        if exp_up and st.button("Import Explorer result"):
            dest = OUT / "imports" / exp_up.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(exp_up.getvalue())
            imp = explorer_reg.import_result(dest)
            st.success(imp.get("saved_path"))

        req_t = st.text_input("Request Funnel for candidate", value="", key="req_funnel")
        if req_t and st.button("Request Funnel for candidate"):
            st.json(explorer_reg.request_funnel_for_candidate(req_t))

        cand_path = OUT / "explorer_handoff" / "candidate_metrics.csv"
        last_run_path = HERE / "workspace" / "explorer" / "last_run.json"
        last_run = {}
        if last_run_path.exists():
            try:
                last_run = json.loads(last_run_path.read_text(encoding="utf-8"))
            except Exception:
                last_run = {}
        counts = last_run.get("counts") or {}
        coverage = last_run.get("coverage") or {}
        if counts:
            st.subheader("Universe coverage")
            st.caption("Production Explorer reads Funnel context from environment=PRODUCTION only.")
            st.write({
                "Universe total": counts.get("UNIVERSE_TOTAL"),
                "Equity universe": counts.get("EQUITY_UNIVERSE_TOTAL"),
                "Mapped": counts.get("MAPPED_SYMBOLS"),
                "Daily data coverage %": counts.get("daily_data_coverage_pct"),
                "Scanner eligible": counts.get("SCANNER_ELIGIBLE_SYMBOLS"),
                "Coverage %": counts.get("scanner_eligible_coverage_pct"),
                "Explorer coverage": coverage.get("EXPLORER_COVERAGE") or counts.get("EXPLORER_COVERAGE"),
                "Pre-screen": counts.get("PRESCREEN_SELECTED"),
                "Intraday enriched": counts.get("INTRADAY_ENRICHED"),
                "Final handoff": counts.get("HANDOFF_CANDIDATES"),
            })
            if (coverage.get("EXPLORER_COVERAGE") or counts.get("EXPLORER_COVERAGE")) == "INSUFFICIENT":
                st.warning("EXPLORER_COVERAGE=INSUFFICIENT — do not treat this as a market-wide screen.")

        table_path = OUT / "explorer_handoff" / "universe.csv"
        if table_path.exists():
            st.subheader("Universe status")
            udf = pd.read_csv(table_path)
            keep = [c for c in (
                "canonical_symbol", "data_status", "exclusion_reason",
            ) if c in udf.columns]
            st.dataframe(udf[keep] if keep else udf, use_container_width=True, hide_index=True)

        if cand_path.exists():
            st.subheader("Candidates")
            cdf = pd.read_csv(cand_path)
            cols = [c for c in (
                "ticker", "data_status", "candidate_families", "candidate_lane",
                "candidate_score", "candidate_score_calibrated", "candidate_score_legacy",
                "prescreen_score", "MOVE_ALREADY_REALIZED", "FORWARD_SETUP_QUALITY",
                "funnel_status", "intraday_available",
            ) if c in cdf.columns]
            st.dataframe(cdf[cols] if cols else cdf, use_container_width=True, hide_index=True)

    store.close()

elif page == "Schedule Analysis Center":
    from egxbridge.ui.daily_operator import _prepare_package_buttons, _import_result_form
    from egxbridge.ui.snapshot import gather_operator_snapshot
    from egxbridge.ui.workflow_state import ALL_JOBS, JOB_LABELS
    from egxbridge.ui.components import job_status_label
    store, funnel_reg, explorer_reg = analysis_handles()
    snap = gather_operator_snapshot(root=HERE, store=store, db=db)
    schedule = snap.get("schedule") or {}
    st.write("Send market evidence to ChatGPT and bring its analysis back. Each job has a separate purpose and saved reply.")
    purposes = {
        "MACRO_HOLDINGS": "Market context and portfolio implications",
        "PREMARKET_CATALYSTS": "News and catalysts for the next session",
        "INTRADAY_OPPORTUNITY": "Timing and confirmation during trading",
        "VALUE_QUALITY": "Which companies need a full Funnel or an update",
        "WEEKLY_XRAY": "Forward outcomes, missed candidates and rule proposals",
    }
    st.dataframe([{"Analysis": JOB_LABELS[j], "Purpose": purposes[j],
        "Status": display_label(job_status_label(j, snap.get("imports") or {}, j in (schedule.get("included_jobs") or [])))}
        for j in ALL_JOBS], use_container_width=True, hide_index=True)
    prepare_tab, import_tab, history_tab = st.tabs(["1. Prepare & download", "2. Import replies", "History"])
    with prepare_tab:
        if not snap.get("candidate_count"):
            st.info("Start with a market scan on Daily Operator. Its candidate list supplies the evidence for these analyses.")
        else:
            st.caption("The next-session package includes Macro / Holdings, Pre-Market Catalysts, and Value & Quality. Intraday and Weekly X-Ray can run separately.")
            _prepare_package_buttons(snap, store, db, snap.get("job_recommendations") or {})
        st.markdown("**Send the evidence to ChatGPT**")
        ready = download_zip(schedule.get("combined_zip"), label="Download ChatGPT evidence package", key="center_combined_zip")
        if ready:
            st.write("Attach the ZIP in ChatGPT. Ask it to run the included jobs, then save each reply as .md, .txt or .json.")
        with st.expander("Download a single analysis"):
            for job, path in (schedule.get("individual_zips") or {}).items():
                download_zip(path, label=f"Download {JOB_LABELS.get(job, job)}", key=f"center_zip_{job}")
    with import_tab:
        st.caption("Return here after ChatGPT finishes. Company Funnel replies belong on Analysis Workflows.")
        _import_result_form(snap, store)
    with history_tab:
        for job in ALL_JOBS:
            record = store.latest_schedule_import(job)
            with st.expander(JOB_LABELS[job]):
                if record:
                    st.caption(f"Imported: {record.get('imported_at') or 'Unknown date'}")
                    st.json(record)
                else:
                    st.info("No saved reply for this analysis yet.")
    store.close()

elif page == "Forward Validation Lab":
    from egxbridge.ui.forward_validation import render_forward_validation
    store, _, _ = analysis_handles()
    render_forward_validation(store=store, db=db, root=HERE)
    store.close()

elif page == "Signal Outcomes":
    st.write("Track price changes after the original signal. Choose a trading-session horizon to see its return and best / worst price moves.")
    st.caption("A pending outcome needs more future data. Missing values are not zero returns. Starting prices are reference prices, not confirmed trade fills.")
    outcome_horizon = st.selectbox("Outcome horizon", [1, 2, 5, 10, 20], index=2, format_func=lambda h: f"{h} trading session{'s' if h != 1 else ''}")
    store, _, _ = analysis_handles()
    try:
        from egxbridge.analysis.schedule.identity import backfill_canonical_from_legacy_snapshots
        backfill_canonical_from_legacy_snapshots(store)
    except Exception:
        pass
    canonical = store.list_canonical_signals(limit=400)
    observations = store.list_analysis_observations(limit=2000)
    outcomes = {o.get("canonical_signal_id"): {**o, **json.loads(o.get("payload_json") or "{}")} for o in store.list_canonical_outcomes(limit=400)}
    from egxbridge.analysis.schedule.metrics import observation_counts
    oc = observation_counts(observations)
    complete_n = sum(
        1 for o in outcomes.values()
        if o.get("maturity_20") == "MATURE"
    )
    stat1, stat2, stat3 = st.columns(3)
    stat1.metric("Signals shown", len(canonical))
    stat2.metric("Ready after 20 sessions", complete_n)
    stat3.metric("Waiting for 20 sessions", max(0, len(canonical) - complete_n))
    with st.expander("Signal counts and analysis observations"):
        st.caption("This view shows up to 400 recent signals. Imported analyses are separate observations; they do not add scanner signals.")
        st.json(oc)
    rows = []
    for s in canonical:
        p = s.get("payload") or {}
        o = outcomes.get(s.get("canonical_signal_id")) or {}
        rows.append({
            "Date": (s.get("market_session_basis") or p.get("market_session_basis") or "")[:10],
            "Ticker": s.get("ticker"),
            "Analysis Type": s.get("signal_origin"),
            "Lane": s.get("candidate_lane") or p.get("candidate_lane"),
            "Forward Setup": s.get("FORWARD_SETUP_QUALITY") or p.get("FORWARD_SETUP_QUALITY"),
            "Move Realized": s.get("MOVE_ALREADY_REALIZED") or p.get("MOVE_ALREADY_REALIZED"),
            "Signal Price": s.get("price_at_signal") or p.get("price_at_signal"),
            f"Return · +{outcome_horizon} (%)": o.get(f"return_{outcome_horizon}"),
            "Best move · MFE (%)": o.get(f"mfe_{outcome_horizon}"),
            "Worst move · MAE (%)": o.get(f"mae_{outcome_horizon}"),
            "Net return after costs (%)": o.get(f"net_return_after_friction_{outcome_horizon}"),
            "Outcome status": display_label(o.get(f"maturity_{outcome_horizon}") or "PENDING"),
            "canonical_signal_id": (s.get("canonical_signal_id") or "")[:12],
        })
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No saved signals yet. Run a market scan on Daily Operator; starting evidence is saved automatically.")
    else:
        f1, f2, f3, f4, f5 = st.columns(5)
        tickers = ["(all)"] + sorted({str(x) for x in df["Ticker"].dropna()})
        lanes = ["(all)"] + sorted({str(x) for x in df["Lane"].dropna()})
        setups = ["(all)"] + sorted({str(x) for x in df["Forward Setup"].dropna()})
        types = ["(all)"] + sorted({str(x) for x in df["Analysis Type"].dropna()})
        dates = ["(all)"] + sorted({str(x) for x in df["Date"].dropna() if x}, reverse=True)
        tsel = f1.selectbox("Ticker", tickers)
        lsel = f2.selectbox("Lane", lanes)
        ssel = f3.selectbox("Setup quality", setups)
        ysel = f4.selectbox("Analysis type", types)
        dsel = f5.selectbox("Date", dates)
        view = df
        if tsel != "(all)":
            view = view[view["Ticker"] == tsel]
        if lsel != "(all)":
            view = view[view["Lane"] == lsel]
        if ssel != "(all)":
            view = view[view["Forward Setup"] == ssel]
        if ysel != "(all)":
            view = view[view["Analysis Type"] == ysel]
        if dsel != "(all)":
            view = view[view["Date"] == dsel]
        st.dataframe(view, use_container_width=True, hide_index=True)
    with st.expander("Optional USER_ACTION (never inferred, never sent to Thndr)"):
        ua_t = st.text_input("Ticker", key="ua_ticker")
        ua_a = st.selectbox("USER_ACTION", ["NO_ACTION", "WATCHED", "BOUGHT", "SOLD", "ADDED", "TRIMMED", "OTHER"], key="ua_act")
        ua_e = st.text_input("user_entry_price", key="ua_entry")
        ua_x = st.text_input("user_exit_price", key="ua_exit")
        ua_s = st.text_input("user_position_size", key="ua_size")
        if st.button("Record user action") and ua_t:
            store.insert_user_action({
                "ticker": ua_t,
                "user_action": ua_a,
                "user_entry_price": float(ua_e) if ua_e else None,
                "user_exit_price": float(ua_x) if ua_x else None,
                "user_position_size": ua_s or None,
            })
            st.success("Recorded locally. No order was placed.")
    store.close()

elif page == "Provider Status":
    from egxbridge.provider_health import serialize_status_for_display

    rows = []
    if db:
        rows = db.fetch_provider_status()
    elif handoff and handoff.get("providers"):
        rows = handoff["providers"]
    elif probe and probe.get("providers"):
        for name, p in probe["providers"].items():
            health = p.get("health") or {}
            rows.append({
                "name": name,
                "provider": name,
                "enabled": p.get("enabled", health.get("enabled", True)),
                "health_state": health.get("health_state") or p.get("status"),
                "auth_status": health.get("auth_status"),
                "reachable": health.get("reachable"),
                "authenticated": health.get("authenticated"),
                "main_role": health.get("main_role"),
                "mode": p.get("mode") or health.get("mode"),
                "notes": p.get("note") or health.get("notes") or p.get("status"),
                "last_error": p.get("error") or health.get("last_error"),
                "last_http_status": p.get("HTTP") or health.get("last_http_status"),
                "latency_ms": health.get("latency_ms"),
                "capabilities": health.get("capabilities") or {},
                "provider_type": health.get("provider_type"),
            })
    if not rows:
        st.info("No provider status yet. Run probe or collect.")
    else:
        display = [serialize_status_for_display(r) for r in rows]
        table = [{
            "Provider": d["provider"],
            "State": d["state"],
            "Auth": d["auth"],
            "Reachable": d["reachable"],
            "Main Role": d["main_role"],
            "Mode": d.get("mode"),
            "Latency ms": d.get("latency_ms"),
            "Last HTTP": d.get("last_http_status"),
            "Notes": d.get("notes") or d.get("last_error") or "",
        } for d in display]
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)

        with st.expander("Raw provider health JSON"):
            clean = []
            for r in rows:
                clean.append({
                    "name": r.get("name") or r.get("provider"),
                    "enabled": r.get("enabled"),
                    "provider_type": r.get("provider_type"),
                    "health_state": r.get("health_state"),
                    "auth_status": r.get("auth_status"),
                    "reachable": r.get("reachable"),
                    "authenticated": r.get("authenticated"),
                    "mode": r.get("mode"),
                    "capabilities": r.get("capabilities"),
                    "last_success": r.get("last_success"),
                    "last_error": r.get("last_error"),
                    "last_http_status": r.get("last_http_status"),
                    "latency_ms": r.get("latency_ms"),
                    "notes": r.get("notes"),
                    "main_role": r.get("main_role"),
                })
            st.json(clean)

        st.caption(
            "Auth false/null is not always a failure — see Auth column "
            "(Anonymous / Not required / N/A / License required)."
        )

        # Capability vs current-run data availability
        st.subheader("Capability vs current data")
        st.caption(
            "Supported Capability describes what the provider can do. "
            "Current Data Available is for the latest collection/probe run only."
        )
        cap_rows = []
        sym_list = []
        if handoff:
            raw_syms = handoff.get("symbols") or []
            if isinstance(raw_syms, dict):
                sym_list = list(raw_syms.values())
            else:
                sym_list = list(raw_syms)
        for r in rows:
            name = r.get("name") or r.get("provider")
            caps = r.get("capabilities") or {}
            if isinstance(caps, str):
                try:
                    caps = json.loads(caps)
                except Exception:
                    caps = {}
            for cap, supported in (caps or {}).items():
                if not supported:
                    continue
                current = None
                if sym_list:
                    if cap == "fundamentals":
                        current = any(bool(sp.get("fundamentals_available")) for sp in sym_list)
                    elif cap in ("quote", "daily_ohlcv", "intraday_ohlcv", "volume"):
                        used = any(name in (sp.get("providers_used") or []) for sp in sym_list)
                        if used:
                            current = True
                        elif any(sp.get("price_source") == name for sp in sym_list):
                            current = True
                        else:
                            current = False
                cap_rows.append({
                    "Provider": name,
                    "Capability": cap,
                    "Supported Capability": "YES",
                    "Current Data Available": (
                        "YES" if current is True else ("NO" if current is False else "—")
                    ),
                })
        if cap_rows:
            st.dataframe(pd.DataFrame(cap_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Capability details appear after collect/probe writes provider status.")

        if probe and "egid" in (probe.get("providers") or {}):
            eg = probe["providers"]["egid"]
            health = eg.get("health") or {}
            if (
                eg.get("status") == "AUTH_REQUIRED"
                or eg.get("HTTP") == 401
                or health.get("health_state") in {"AUTH_REQUIRED", "LICENSE_REQUIRED"}
            ):
                st.warning(
                    "EGID: LICENSE/AUTH REQUIRED (HTTP 401) — server reachable; "
                    "token/license missing. Not a network-down failure."
                )

elif page == "Whole Market":
    mw = OUT / "market_watch.csv"
    if mw.exists():
        st.dataframe(pd.read_csv(mw), use_container_width=True, hide_index=True)
    elif universe:
        st.write(universe)
    else:
        st.info("No whole-market snapshot. EGID market watch needs auth; use universe refresh for discovery.")
        if st.button("Refresh universe"):
            r = subprocess.run(
                [sys.executable, str(HERE / "collect.py"), "--refresh-universe"],
                cwd=str(HERE), capture_output=True, text=True,
            )
            st.code(r.stdout or r.stderr)

elif page == "Symbol Explorer":
    symbols = []
    if handoff:
        symbols = [s.get("symbol") for s in handoff.get("symbols", [])]
    choice = st.selectbox("Symbol", symbols or ["MASR", "COMI", "RAYA", "LUTS"])
    if handoff:
        for s in handoff.get("symbols", []):
            if s.get("symbol") == choice:
                st.json(s)
                break
    for fname in ("quote.json", "fundamentals.json", "depth.csv", "trades.csv"):
        p = OUT / choice / fname
        if p.exists():
            st.subheader(fname)
            if fname.endswith(".json"):
                st.json(load_json(p))
            else:
                try:
                    st.dataframe(pd.read_csv(p).tail(100), use_container_width=True, hide_index=True)
                except Exception as e:
                    st.warning(str(e))

elif page == "Candles":
    symbols = [s.get("symbol") for s in (handoff or {}).get("symbols", [])] or ["MASR"]
    choice = st.selectbox("Symbol", symbols, key="candle_sym")
    interval = st.selectbox("Interval", ["1d", "5m", "15m", "30m", "1h", "1m"])
    path = OUT / choice / f"candles_{interval}.csv"
    legacy = OUT / choice / "candles.csv"
    use = path if path.exists() else (legacy if interval == "1d" and legacy.exists() else None)
    if use:
        df = pd.read_csv(use)
        st.dataframe(df.tail(200), use_container_width=True, hide_index=True)
        if "close" in df.columns:
            st.line_chart(df.set_index(df.columns[1] if "time" in df.columns[1].lower() or "timestamp" in df.columns[1].lower() else df.columns[0])["close"].tail(200))
    elif db:
        rows = db.fetch_candles(choice, interval)
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No candles stored for this symbol/interval.")
    else:
        st.info("No candle files yet.")

elif page == "Data Quality":
    if not handoff:
        st.info("No handoff yet.")
    else:
        rows = []
        for s in handoff.get("symbols", []):
            rows.append({
                "Symbol": s.get("symbol"),
                "Research DQ": s.get("research_data_quality"),
                "Execution DQ": s.get("execution_data_quality"),
                "Freshness": s.get("freshness"),
                "Missing exec": ", ".join(s.get("missing_execution_fields") or []),
            })
            with st.expander(s.get("symbol")):
                st.write(s.get("availability"))
                st.write(s.get("quality_components"))
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

elif page == "Source Conflicts":
    rows = db.fetch_conflicts() if db else []
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No recorded conflicts yet. Conflicts appear when providers disagree on price/volume.")

elif page == "Collection Health":
    st.caption("Technical collector diagnostics. The daily starting point is Daily Operator.")
    if st.button("Refresh Market Data", key="health_refresh"):
        from egxbridge.ui import actions
        with st.spinner("Refreshing market data..."):
            r = actions.refresh_market_data(root=HERE)
        if r.get("ok"):
            st.success(r.get("message"))
        else:
            st.error(r.get("message"))
    if db:
        st.subheader("Recent runs")
        st.dataframe(pd.DataFrame(db.fetch_runs()), use_container_width=True, hide_index=True)
        st.subheader("Provider status")
        st.dataframe(pd.DataFrame(db.fetch_provider_status()), use_container_width=True, hide_index=True)
    else:
        st.info("SQLite DB not found yet.")

if db:
    db.close()
