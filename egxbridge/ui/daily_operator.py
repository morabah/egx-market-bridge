"""Daily Operator Streamlit page — workflow orchestration only."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from egxbridge.ui import actions
from egxbridge.ui.actions import CHATGPT_HANDOFF_ZIP_NAME
from egxbridge.ui.candidates import (
    SOURCE_FUNNEL,
    SOURCE_LOCAL_HEURISTIC,
    candidate_preview_rows,
    chatgpt_status_by_ticker,
    intraday_panel_rows,
)
from egxbridge.ui.components import (
    audit_expander,
    candidate_table,
    do_now_panel,
    display_label,
    download_zip,
    flash_from_state,
    format_age,
    job_status_label,
    operator_hero,
    plan_panel,
    readiness_strip,
    set_flash,
)
from egxbridge.ui.snapshot import gather_operator_snapshot
from egxbridge.ui.workflow_state import (
    ACTION_LABELS,
    ACTION_CTA,
    ACTION_EXPORT_OR_IMPORT,
    ACTION_FUNNEL,
    ACTION_IMPORT_CHATGPT,
    ACTION_INTRADAY,
    ACTION_PREPARE_NEXT_SESSION,
    ACTION_REFRESH_MARKET_DATA,
    ACTION_REVIEW_CANDIDATES,
    ACTION_RUN_EXPLORER,
    ACTION_UPDATE_OUTCOMES,
    ACTION_WAIT,
    ACTION_WEEKLY,
    ALL_JOBS,
    JOB_LABELS,
    NEXT_SESSION_JOBS,
    action_steps,
    explorer_should_enrich_intraday,
    focus_steps,
    funnel_buttons_for_status,
    next_recommended_action,
    should_skip_market_refresh,
)


HERE = Path(__file__).resolve().parents[2]
OUT = HERE / "output"


def _go(page: str):
    st.session_state["op_nav"] = page
    st.rerun()


def _run(result: dict[str, Any], *, rerun: bool = True):
    set_flash(result)
    if rerun:
        st.rerun()


def _handles():
    from egxbridge.analysis.common.persistence import AnalysisStore
    from egxbridge.analysis.common.environment import PRODUCTION
    from egxbridge.analysis.funnel.registry import FunnelRegistry
    from egxbridge.db import Database
    db_path = OUT / "egx_bridge.sqlite"
    db = Database(db_path) if db_path.exists() else None
    store = AnalysisStore(OUT / "analysis.sqlite", environment=PRODUCTION)
    funnel = FunnelRegistry(store=store, db=db, environment=PRODUCTION)
    return store, funnel, db


def render_daily_operator(*, store=None, funnel_reg=None, db=None, root: Path | None = None):
    flash_from_state()
    own = store is None
    if own:
        store, funnel_reg, db = _handles()
    root = root or HERE
    age_override = st.session_state.get("intraday_age_override")
    snap = gather_operator_snapshot(root=root, store=store, db=db, intraday_age_seconds=age_override)
    combined = (snap.get("schedule") or {}).get("combined_zip")
    if combined:
        actions.publish_chatgpt_handoff_zip(combined, root=root)
    nxt = next_recommended_action({
        **snap,
        "ready_to_import": bool(st.session_state.get("op_ready_to_import")),
    })
    code = nxt.get("code")
    focus = focus_steps(code)

    live = snap.get("session_phase") == "CONTINUOUS_TRADING"
    if "enrich_tv_now" not in st.session_state:
        st.session_state["enrich_tv_now"] = live

    operator_hero(
        title="Daily Operator",
        session=snap.get("latest_completed_market_session"),
        phase=snap.get("session_phase"),
        cairo=snap.get("cairo_time"),
        caption="Start here. Follow the next action, then return after ChatGPT replies or new market data arrives.",
    )
    _primary_cta(code, snap, store, funnel_reg, db)
    readiness_strip(_readiness_items(snap, code))
    st.markdown('<ol class="op-workflow" aria-label="Workflow overview">'
        '<li><b>1. Scan the market</b><span>App · data and shortlist</span></li>'
        '<li><b>2. Analyze in ChatGPT</b><span>You · send files and import replies</span></li>'
        '<li><b>3. Review companies</b><span>ChatGPT · selective Funnel analysis</span></li>'
        '<li><b>4. Track what happens</b><span>App · outcomes and weekly evidence</span></li></ol>', unsafe_allow_html=True)
    preview, results, tracking = st.tabs(["Candidate shortlist", "Imported analysis", "Outcome tracking"])
    with preview:
        if snap.get("candidate_count"):
            st.write(f"**{snap['candidate_count']} candidates** from the latest scan. Review the shortlist before sending it to ChatGPT.")
            rows = candidate_preview_rows(snap.get("candidates") or [], limit=5)
            candidate_table([{k: row.get(k) for k in ("Rank", "Ticker", "Close", "Forward Setup", "RVOL20")} for row in rows], key="home_candidates")
            if st.button("Review all candidates", key="home_review_candidates"):
                _go("Explorer Candidates")
        else:
            st.info("Your shortlist will appear here after the first market scan. Use the next action above to get started.")
    with results:
        if snap.get("plan"):
            plan_panel(snap["plan"])
        else:
            st.info("No imported analysis yet. Prepare a package, send it to ChatGPT, then import each saved reply.")
        if st.button("Open ChatGPT analysis center", key="home_analysis_center"):
            _go("Schedule Analysis Center")
    with tracking:
        from egxbridge.ui.forward_validation import render_forward_status
        render_forward_status(store)
        if st.button("Open Forward Validation Lab", key="home_forward_lab"):
            _go("Forward Validation Lab")

    with st.expander("Quick tools and data options", expanded=False):
        st.caption("Run an individual task or adjust optional intraday data collection.")
        st.checkbox(
            "Include TradingView (slow)",
            key="enrich_tv_now",
            help=(
                "Candidate ranks are computed from daily bars first. TradingView only attaches "
                "confirmation candles afterwards. Skip it when the market is closed."
            ),
        )
        if not live:
            st.caption("Market is closed — leave TradingView off.")
        q1, q2, q3, q4 = st.columns(4)
        with q1:
            if st.button("Refresh + Run Explorer", key="qa_refresh_explorer"):
                _refresh_and_explorer(snap, store, funnel_reg, db)
        with q2:
            if st.button("Prepare Next-Session Package", key="qa_next_session"):
                _prepare_next_session(snap, store, db)
        with q3:
            if st.button("Refresh Intraday", key="qa_intraday"):
                _refresh_intraday(snap)
        with q4:
            if st.button("Update Outcomes", key="qa_outcomes"):
                with st.spinner("Updating outcomes..."):
                    _run(actions.update_outcomes(store=store, db=db))

    with st.expander("Full workflow · step details and manual actions", expanded=False):
        st.caption("Use this checklist to revisit a completed step or open a specific tool.")
        _step1_refresh(snap, focus, code)
        _step2_explorer(snap, store, funnel_reg, db, focus, code)
        _step3_candidates(snap, focus, code)
        _step4_schedules(snap, store, db, focus, code)
        _step5_export(snap, focus, code)
        _step6_import(snap, store, focus, code)
        _step7_funnel(snap, funnel_reg, store, focus, code)
        _step8_intraday(snap, store, db, focus, code)
        _step9_outcomes(snap, store, db, focus, code)
        _step10_weekly(snap, store, db, focus, code)
    st.caption("The app prepares evidence and tracks results. You make the final capital decision.")
    if own:
        try:
            store.close()
        except Exception:
            pass
        if db:
            try:
                db.close()
            except Exception:
                pass


def _readiness_items(snap: dict[str, Any], *rest: Any) -> list[dict[str, Any]]:
    code = None
    for item in rest:
        if item is None or isinstance(item, str):
            code = item
    keep = {"market_data", "explorer", "schedules", "chatgpt"}
    if code in {ACTION_FUNNEL}:
        keep.add("funnel")
    if code in {ACTION_UPDATE_OUTCOMES, ACTION_WAIT}:
        keep.add("outcomes")
    return [
        item
        for item in (snap.get("readiness") or [])
        if item.get("id") in keep
    ]


def _import_result_form(snap: dict[str, Any], store):
    jobs = (snap.get("schedule") or {}).get("included_jobs") or list(NEXT_SESSION_JOBS)
    pending = [job for job in jobs if not ((snap.get("imports") or {}).get(job) or {}).get("status", "").startswith("IMPORTED")]
    default_job = (pending or jobs or list(ALL_JOBS))[0]
    if st.session_state.pop("op_import_advance", False):
        st.session_state["do_imp_type"] = default_job
        # A new reply must be chosen when advancing to the next analysis job.
        st.session_state["op_import_upload_version"] = st.session_state.get("op_import_upload_version", 0) + 1
    options = list(ALL_JOBS)
    st.caption("Import one saved ChatGPT reply at a time. Do not upload the ZIP.")
    up = st.file_uploader(
        "Saved ChatGPT reply (.md / .txt / .json)",
        type=["md", "txt", "json"],
        key=f"do_imp_any_{st.session_state.get('op_import_upload_version', 0)}",
    )
    job = st.selectbox(
        "Which job is this file for?",
        options,
        index=options.index(default_job) if default_job in options else 0,
        format_func=lambda j: JOB_LABELS.get(j, j),
        key="do_imp_type",
    )
    go = st.button(ACTION_CTA[ACTION_IMPORT_CHATGPT], type="primary", key="do_imp_go", disabled=not up)
    if go and up:
        dest = actions.save_upload(up, dest_dir=OUT / "imports")
        with st.spinner("Importing ChatGPT result..."):
            r = actions.import_chatgpt_result(
                dest, analysis_type=job, store=store, run_id=(snap.get("schedule") or {}).get("run_id"),
            )
        res = r.get("result") or {}
        if r.get("ok"):
            st.session_state["op_import_advance"] = True
            st.success(r.get("message"))
            warn = res.get("structured_parse_status")
            if warn in {"INVALID_SCHEMA", "INVALID_CANONICAL_ID", "AMBIGUOUS_REJECTED"}:
                st.warning(str(warn))
            if res.get("session_phase_validation") in {"MISMATCH", "SESSION_PHASE_MISMATCH"}:
                st.warning("SESSION_PHASE_MISMATCH")
            issues = res.get("schema_issues") or []
            if issues:
                st.warning("; ".join(str(x) for x in issues[:6]))
            st.session_state["op_flash"] = {"ok": True, "message": r.get("message")}
            st.rerun()
        else:
            _run(r)


def _primary_cta(code: str | None, snap, store, funnel_reg, db):
    owner = "In ChatGPT · download the evidence here, then continue in ChatGPT" if code == ACTION_EXPORT_OR_IMPORT else "Waiting for market data" if code == ACTION_WAIT else "In this app"
    title = ACTION_LABELS.get(code or "", "Review your workflow")
    do_now_panel(title=title if code == ACTION_WAIT else f"Next: {title}", steps=action_steps(code, snap), owner=owner)
    label = ACTION_CTA.get(code or "")
    if code == ACTION_WAIT or not label:
        return
    if code == ACTION_REFRESH_MARKET_DATA:
        if st.button(label, type="primary", key="cta_primary"):
            _refresh_and_explorer(snap, store, funnel_reg, db)
        return
    if code == ACTION_RUN_EXPLORER:
        if st.button(label, type="primary", key="cta_primary", disabled=not snap.get("data_usable")):
            _run_explorer(snap, store, funnel_reg, db)
        return
    if code == ACTION_REVIEW_CANDIDATES:
        if st.button(label, type="primary", key="cta_primary"):
            _go("Explorer Candidates")
        return
    if code == ACTION_PREPARE_NEXT_SESSION:
        if st.button(label, type="primary", key="cta_primary"):
            _prepare_next_session(snap, store, db)
        return
    if code == ACTION_EXPORT_OR_IMPORT:
        zip_path = (snap.get("schedule") or {}).get("combined_zip")
        if not download_zip(
            zip_path,
            label=label,
            key="cta_dl_combined",
            primary=True,
            download_name=CHATGPT_HANDOFF_ZIP_NAME,
        ):
            if st.button("Prepare next-session package", type="primary", key="cta_prep_for_export"):
                _prepare_next_session(snap, store, db)
        if st.button("I have ChatGPT replies · import them", key="cta_goto_import"):
            st.session_state["op_ready_to_import"] = True
            st.rerun()
        return
    if code == ACTION_IMPORT_CHATGPT:
        _import_result_form(snap, store)
        if st.button("Back to download the ZIP", key="cta_back_export"):
            st.session_state["op_ready_to_import"] = False
            st.rerun()
        return
    if code == ACTION_FUNNEL:
        rows = snap.get("funnel_rows") or []
        t = (rows[0].get("ticker") if rows else None)
        if t:
            if st.button(f"Open company analysis for {t}", type="primary", key="cta_primary"):
                st.session_state["funnel_ticker"] = t
                _go("Analysis Workflows")
        else:
            st.caption("Open STEP 7 below if you need a Funnel for another ticker.")
        return
    if code == ACTION_INTRADAY:
        if st.button(label, type="primary", key="cta_primary"):
            _refresh_intraday(snap)
        return
    if code == ACTION_UPDATE_OUTCOMES:
        if st.button(label, type="primary", key="cta_primary", disabled=not snap.get("canonical_n")):
            with st.spinner("Updating outcomes..."):
                _run(actions.update_outcomes(store=store, db=db))
        return
    if code == ACTION_WEEKLY:
        if st.button(label, type="primary", key="cta_primary"):
            pkg = (snap.get("explorer") or {}).get("package_dir")
            with st.spinner("Preparing Weekly X-Ray..."):
                _run(actions.prepare_schedule_jobs(
                    ["WEEKLY_XRAY"], store=store, db=db, explorer_package_dir=pkg, session_meta=snap.get("session_meta"),
                ))


def _refresh_and_explorer(snap, store, funnel_reg, db):
    skip_yahoo = should_skip_market_refresh(snap)
    use_tv = explorer_should_enrich_intraday(
        snap.get("session_phase"), force=bool(st.session_state.get("enrich_tv_now")),
    )
    with st.status("Refresh + Run Explorer", expanded=True) as status:
        if skip_yahoo:
            st.write("Using cached daily bars (market closed).")
        else:
            st.write("Refreshing market data from Yahoo.")
        if use_tv:
            st.write("Scanning Explorer, then querying TradingView for 15 names (this can take several minutes).")
        else:
            st.write("Scanning Explorer from daily bars (TradingView skipped).")
        r = actions.refresh_and_run_explorer(
            snapshot=snap,
            store=store,
            db=db,
            funnel_registry=funnel_reg,
            root=HERE,
            force_tv=bool(st.session_state.get("enrich_tv_now")),
        )
        status.update(
            label="Completed" if r.get("ok") else "Did not complete",
            state="complete" if r.get("ok") else "error",
        )
    _run(r)


def _run_explorer(snap, store, funnel_reg, db):
    use_tv = explorer_should_enrich_intraday(
        snap.get("session_phase"), force=bool(st.session_state.get("enrich_tv_now")),
    )
    label = (
        "Scanning Explorer, then querying TradingView (this can take several minutes)..."
        if use_tv else
        "Scanning Explorer from daily bars (TradingView skipped)..."
    )
    with st.spinner(label):
        _run(actions.run_broad_explorer(
            store=store, db=db, funnel_registry=funnel_reg, enrich_intraday=use_tv,
        ))


def _prepare_next_session(snap, store, db):
    if not snap.get("explorer", {}).get("package_dir"):
        _run({"ok": False, "message": "Explorer has not been run yet. Run Broad Explorer before preparing schedules."})
        return
    with st.spinner("Preparing next-session ChatGPT handoffs..."):
        _run(actions.prepare_next_session_package(
            store=store, db=db,
            explorer_package_dir=snap.get("explorer", {}).get("package_dir"),
            session_meta=snap.get("session_meta"),
        ))


def _refresh_intraday(snap):
    with st.spinner("Refreshing Intraday evidence..."):
        r = actions.refresh_intraday(explorer_payload=snap.get("explorer", {}).get("payload"), root=HERE)
    if r.get("ok") and r.get("age_seconds") is not None:
        st.session_state["intraday_age_override"] = r.get("age_seconds")
    _run(r)


def _step_box(n: int, title: str, status: str, focus: set[int]):
    mark = " · now" if n in focus else ""
    return st.expander(f"{n}. {title} · {display_label(status)}{mark}", expanded=n in focus)


def _step1_refresh(snap: dict[str, Any], focus: set[int], code: str | None):
    with _step_box(1, "Refresh Market Data", snap.get("market_data_status") or "NOT RUN", focus):
        st.caption("Yahoo-only collect. Not required unless the next action calls for new data.")
        st.caption(f"Last run: {snap.get('latest_collection_at') or snap.get('handoff_generated_at') or '—'}")
        if snap.get("freshness") == "STALE_EXPECTED":
            st.info(snap.get("freshness_note") or "")
        elif snap.get("freshness") == "UNEXPECTED_STALE":
            st.warning(snap.get("freshness_note") or "")
        st.write(
            f"Daily data: **{snap.get('daily_data_available') or 0}** / **{snap.get('equity_universe') or 0}**  ·  "
            f"Scanner eligible: **{snap.get('scanner_eligible') or 0}**  ·  "
            f"TradingView Intraday: **{snap.get('intraday_enriched') or 0}** / **{snap.get('intraday_requested') or 0}** requested  ·  "
            f"Freshness: **{snap.get('freshness')}**"
        )
        if snap.get("provider_summary"):
            st.caption("Providers: " + ", ".join(
                f"{p.get('name')}={p.get('state')}" for p in snap.get("provider_summary") if p.get("name")
            ))
        if code == ACTION_REFRESH_MARKET_DATA:
            st.caption("Use the next action at the top of this page. It refreshes and scans Explorer together.")
        else:
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Refresh Market Data", key="do_refresh"):
                    with st.spinner("Refreshing market data..."):
                        _run(actions.refresh_market_data(root=HERE))
            with b2:
                if st.button("View Provider Status", key="do_providers"):
                    _go("Provider Status")
        audit_expander("Advanced / Audit — market data", {
            "latest_completed_market_session": snap.get("latest_completed_market_session"),
            "handoff_status": snap.get("handoff_status"),
            "market_data_status": snap.get("market_data_status"),
            "provider_status": snap.get("provider_status"),
            "handoff_path": str(OUT / "chatgpt_handoff.json"),
            "application_version": (snap.get("versions") or {}).get("application_version"),
            "market_data_schema_version": (snap.get("versions") or {}).get("market_data_schema_version"),
        })


def _step2_explorer(snap, store, funnel_reg, db, focus: set[int], code: str | None):
    exp = snap.get("explorer") or {}
    with _step_box(2, "Scan the EGX Market", snap.get("explorer_status") or "NOT_RUN", focus):
        st.caption("Scan the eligible equity universe and narrow it to the strongest forward setups.")
        st.caption(f"Last run: {exp.get('generated_at') or '—'}")
        if not snap.get("data_usable"):
            st.warning("Explorer needs usable daily data. Refresh Market Data first.")
        disabled = not snap.get("data_usable")
        live = snap.get("session_phase") == "CONTINUOUS_TRADING"
        st.write(
            f"{snap.get('equity_universe') or 0} Equity Universe  ·  "
            f"{snap.get('scanner_eligible') or 0} Scanner Eligible  ·  "
            f"{snap.get('prescreen') or 0} Prescreen  ·  "
            f"{snap.get('handoff_candidates') or snap.get('candidate_count') or 0} Final Candidates  ·  "
            f"{snap.get('intraday_requested') or 0} Intraday Requested  ·  "
            f"{snap.get('intraday_enriched') or 0} Intraday Enriched"
        )
        st.caption(
            f"Explorer run_id: `{exp.get('explorer_run_id') or '—'}`  ·  "
            f"generated_at: {exp.get('generated_at') or '—'}  ·  scoring_version: {snap.get('scoring_version')}"
        )
        if not live and st.session_state.get("enrich_tv_now"):
            st.caption("TradingView on a closed market is not live confirmation and can take several minutes.")
        if code != ACTION_RUN_EXPLORER:
            if st.button("Run Broad Explorer", key="do_explorer", disabled=disabled):
                _run_explorer(snap, store, funnel_reg, db)
        else:
            st.caption("Use the next action at the top of this page to run Explorer.")
        audit_expander("Advanced / Audit — Explorer", {
            "package_dir": exp.get("package_dir"),
            "explorer_run_id": exp.get("explorer_run_id"),
            "coverage": snap.get("coverage"),
            "zip_path": exp.get("zip_path"),
        })


def _step3_candidates(snap, focus: set[int], code: str | None):
    with _step_box(3, "Review candidates", "READY" if snap.get("candidate_count") else "NOT RUN", focus):
        st.caption("Rank is a screening priority, not a buy recommendation.")
        st.caption(f"Last run: {(snap.get('explorer') or {}).get('generated_at') or '—'}")
        if code != ACTION_REVIEW_CANDIDATES:
            if st.button("View Candidates", key="do_view_cands"):
                _go("Explorer Candidates")
        else:
            st.caption("Use the next action at the top of this page to open the full list.")
        rows = candidate_preview_rows(snap.get("candidates") or [], limit=5)
        candidate_table(
            rows,
            key="do_preview_cands",
            help_text="Top 5 preview. Candidate Score is HEURISTIC_UNCALIBRATED — not a probability.",
        )


def _job_row(job: str, snap: dict[str, Any], store, db, *, expanded: bool, tools: bool):
    recs = snap.get("job_recommendations") or {}
    recommended = job in (recs.get("recommended") or [])
    imports = snap.get("imports") or {}
    status = job_status_label(job, imports, bool(snap.get("schedules_prepared")))
    imp = imports.get(job) or {}
    rec_note = "Recommended now" if recommended else (
        "NOT LIVE" if job == "INTRADAY_OPPORTUNITY" and not recs.get("intraday_live") else "Manual OK"
    )
    with st.expander(f"{JOB_LABELS.get(job, job)} · {status} · {rec_note}", expanded=expanded):
        st.caption(f"Imported: {imp.get('imported_at') or '—'}")
        if not tools:
            return
        pkg = (snap.get("explorer") or {}).get("package_dir")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Prepare", key=f"prep_{job}"):
                with st.spinner(f"Preparing {JOB_LABELS.get(job, job)}..."):
                    _run(actions.prepare_schedule_jobs(
                        [job], store=store, db=db, explorer_package_dir=pkg, session_meta=snap.get("session_meta"),
                    ))
        with b2:
            download_zip((snap.get("schedule") or {}).get("individual_zips", {}).get(job), label="Export", key=f"dl_{job}")
        up = st.file_uploader("Import result", type=["md", "txt", "json"], key=f"up_{job}")
        if up and st.button("Import Result", key=f"imp_{job}"):
            dest = actions.save_upload(up, dest_dir=OUT / "imports")
            with st.spinner("Importing ChatGPT result..."):
                r = actions.import_chatgpt_result(dest, analysis_type=job, store=store, run_id=(snap.get("schedule") or {}).get("run_id"))
            _run(r)
        if st.button("History", key=f"hist_{job}"):
            st.json(imp or {"status": "none"})


def _prepare_package_buttons(snap, store, db, recs):
    a1, a2, a3 = st.columns(3)
    pkg = (snap.get("explorer") or {}).get("package_dir")
    with a1:
        if st.button("Prepare Next-Session Package", key="do_next_pkg"):
            st.caption("Will run: Macro / Holdings, Pre-Market Catalysts, Value & Quality.")
            with st.spinner("Preparing next-session ChatGPT handoffs..."):
                _run(actions.prepare_next_session_package(
                    store=store, db=db, explorer_package_dir=pkg, session_meta=snap.get("session_meta"),
                ))
    with a2:
        if st.button("Prepare Recommended Jobs", key="do_rec_jobs"):
            with st.spinner("Preparing recommended ChatGPT handoffs..."):
                _run(actions.prepare_recommended_jobs(
                    recs.get("recommended") or list(NEXT_SESSION_JOBS),
                    store=store, db=db, explorer_package_dir=pkg, session_meta=snap.get("session_meta"),
                ))
    with a3:
        if st.button("Prepare All 5 Jobs", key="do_all5"):
            st.caption("Will run all five jobs: " + ", ".join(JOB_LABELS[j] for j in ALL_JOBS))
            with st.spinner("Preparing five ChatGPT handoffs..."):
                _run(actions.prepare_all_jobs(
                    store=store, db=db, explorer_package_dir=pkg, session_meta=snap.get("session_meta"),
                ))


def _step4_schedules(snap, store, db, focus: set[int], code: str | None):
    with _step_box(4, "Prepare ChatGPT Analysis", "READY" if snap.get("schedules_prepared") else "NOT PREPARED", focus):
        st.caption("Builds Macro, Pre-Market, and Value/Quality into one ChatGPT ZIP.")
        st.caption(f"Last run: {(snap.get('schedule') or {}).get('generated_at') or '—'}")
        if not snap.get("explorer", {}).get("package_dir"):
            st.warning("Explorer has not been run yet. Run Broad Explorer before preparing schedules.")
        recs = snap.get("job_recommendations") or {}
        st.caption("Recommended now: " + ", ".join(JOB_LABELS.get(j, j) for j in (recs.get("recommended") or [])))
        if recs.get("intraday_note"):
            st.caption(recs.get("intraday_note"))
        current_prepare = code == ACTION_PREPARE_NEXT_SESSION
        if current_prepare:
            st.caption("Use the next action at the top of this page. Do not use the extra prepare buttons.")
        elif code in {ACTION_EXPORT_OR_IMPORT, ACTION_IMPORT_CHATGPT}:
            st.caption("Package is already built. Use the next action above to continue.")
            with st.expander("Rebuild package — not the current task"):
                _prepare_package_buttons(snap, store, db, recs)
        else:
            _prepare_package_buttons(snap, store, db, recs)
        recommended = set(recs.get("recommended") or [])
        for job in ALL_JOBS:
            _job_row(
                job, snap, store, db,
                expanded=job in recommended and 4 in focus and current_prepare,
                tools=code not in {ACTION_PREPARE_NEXT_SESSION, ACTION_EXPORT_OR_IMPORT, ACTION_IMPORT_CHATGPT},
            )


def _step5_export(snap, focus: set[int], code: str | None):
    sched = snap.get("schedule") or {}
    jobs = sched.get("included_jobs") or []
    job_txt = ", ".join(JOB_LABELS.get(j, j) for j in jobs) or "—"
    with _step_box(5, "Send one ZIP to ChatGPT", "READY" if sched.get("combined_zip") else "NOT PREPARED", focus):
        st.write(
            f"Session {sched.get('latest_session') or snap.get('latest_completed_market_session') or '—'}  ·  "
            f"{job_txt}  ·  "
            f"{sched.get('candidate_count') or snap.get('candidate_count') or '—'} candidates"
        )
        if code == ACTION_EXPORT_OR_IMPORT:
            st.caption("Use the download in the next-action panel. That is the only file ChatGPT needs.")
        elif code == ACTION_IMPORT_CHATGPT:
            st.caption("The ZIP is already for ChatGPT. Import saved replies with the form at the top. Do not download again.")
        else:
            st.caption("ChatGPT needs one file: EGX_CHATGPT_HANDOFF.zip. The app does not call ChatGPT.")
            download_zip(
                sched.get("combined_zip"),
                label="Download EGX_CHATGPT_HANDOFF.zip",
                key="do_dl_combined",
                primary=False,
                download_name=CHATGPT_HANDOFF_ZIP_NAME,
            )
        if code not in {ACTION_EXPORT_OR_IMPORT, ACTION_IMPORT_CHATGPT}:
            with st.expander("Per-job ZIPs (optional — not required)"):
                st.caption("Only if you want a single job in a separate ChatGPT chat.")
                zips = sched.get("individual_zips") or {}
                labels = {
                    "MACRO_HOLDINGS": "Macro ZIP",
                    "PREMARKET_CATALYSTS": "Pre-Market ZIP",
                    "INTRADAY_OPPORTUNITY": "Intraday ZIP",
                    "VALUE_QUALITY": "Value & Quality ZIP",
                    "WEEKLY_XRAY": "Weekly ZIP",
                }
                for job, title in labels.items():
                    download_zip(zips.get(job), label=title, key=f"do_dl_{job}")
        audit_expander("Advanced / Audit — export", {
            "combined_zip": sched.get("combined_zip"),
            "chatgpt_alias": str(HERE / "output" / CHATGPT_HANDOFF_ZIP_NAME),
            "package_dir": sched.get("package_dir"),
            "run_id": sched.get("run_id"),
            "included_jobs": jobs,
        })


def _step6_import(snap, store, focus: set[int], code: str | None):
    rec_n = int(snap.get("recommended_jobs_n") or 0) or 5
    rec_imp = int(snap.get("recommended_imported_n") or 0)
    with _step_box(6, "Import ChatGPT Results", f"{rec_imp}/{rec_n} IMPORTED", focus):
        st.caption("Import saved ChatGPT replies. The handoff ZIP is not a completed analysis.")
        cols = st.columns(5)
        for col, job in zip(cols, ALL_JOBS):
            with col:
                st.write(JOB_LABELS.get(job, job))
                st.write(job_status_label(job, snap.get("imports") or {}, bool(snap.get("schedules_prepared"))))
        if code == ACTION_IMPORT_CHATGPT:
            st.caption("Use the import form in the next-action panel. Repeat once per saved ChatGPT file.")
        elif code == ACTION_EXPORT_OR_IMPORT:
            st.caption("Do not import yet. Download the ZIP first, then return after ChatGPT replies.")
        else:
            _import_result_form(snap, store)
        last = None
        for job_name in ALL_JOBS:
            rec = (snap.get("imports") or {}).get(job_name) or {}
            if rec.get("imported_at"):
                last = rec
                break
        if last:
            audit_expander("Advanced / Audit — last import", {
                "run_id": last.get("run_id"),
                "imported_at": last.get("imported_at"),
                "raw_path": last.get("raw_path"),
                "status": last.get("status"),
            })


def _step7_funnel(snap, funnel_reg, store, focus: set[int], code: str | None):
    status = f"ACTION REQUIRED: {snap.get('funnel_action_n') or 0}" if snap.get("funnel_action_required") else "NO ACTION"
    with _step_box(7, "Company Valuation / Full Funnel", status, focus):
        st.caption("Driven by Value & Quality results plus Funnel state. Fair Value is never calculated here.")
        if code == ACTION_FUNNEL:
            st.caption("Use the next action at the top of this page for the named ticker. Other tickers stay in this step.")
        rows = snap.get("funnel_rows") or []
        if not rows:
            st.caption("Import Value & Quality results to see Funnel actions, or continue a partial Funnel below.")
        for row in rows:
            t = row.get("ticker")
            st.write(f"**{t}**  ·  Funnel status: `{row.get('funnel_status')}`  ·  Recommended: `{row.get('recommended_action')}`")
            st.caption(f"Source: {row.get('source') or SOURCE_LOCAL_HEURISTIC}")
            buttons = funnel_buttons_for_status(row.get("funnel_status"), row.get("recommended_action"))
            cols = st.columns(max(len(buttons), 1))
            for col, btn in zip(cols, buttons):
                with col:
                    if btn == "VIEW_FUNNEL":
                        if st.button("View Funnel", key=f"fv_{t}"):
                            st.session_state["funnel_ticker"] = t
                            _go("Analysis Workflows")
                    elif st.button(btn.replace("_", " ").title().replace("Funnel", "Funnel"), key=f"{btn}_{t}"):
                        with st.spinner(f"Preparing Funnel for {t}..."):
                            _run(actions.prepare_funnel(funnel_registry=funnel_reg, ticker=t, mode=btn))
            with st.expander(f"Manual override / Funnel files — {t}"):
                st.caption("COMPLETE Funnel stays view-only unless you override.")
                if st.button("Prepare Full Funnel anyway", key=f"ff_over_{t}"):
                    with st.spinner(f"Preparing full Funnel for {t}..."):
                        _run(actions.prepare_funnel(funnel_registry=funnel_reg, ticker=t, mode="PREPARE_FULL_FUNNEL"))
                up = st.file_uploader("Import Funnel result", type=["md", "txt", "json"], key=f"fu_{t}")
                if up and st.button("Import Funnel Result", key=f"fi_{t}"):
                    dest = actions.save_upload(up, dest_dir=OUT / "imports")
                    with st.spinner("Importing Funnel result..."):
                        _run(actions.import_funnel_result(funnel_registry=funnel_reg, ticker=t, source=dest))
        st.markdown("**Export / import Funnel (any ticker)**")
        ft = st.text_input("Ticker", value=st.session_state.get("funnel_ticker") or "", key="do_funnel_t").upper().strip()
        f1, f2, f3 = st.columns(3)
        with f1:
            if st.button("Export Funnel Handoff", key="do_funnel_export") and ft:
                with st.spinner("Preparing Funnel handoff..."):
                    r = actions.prepare_funnel(funnel_registry=funnel_reg, ticker=ft, mode="PREPARE_FULL_FUNNEL")
                if r.get("ok") and r.get("zip_path"):
                    download_zip(r.get("zip_path"), label="Download Funnel ZIP", key="do_funnel_zip")
                _run(r, rerun=False)
        with f2:
            upf = st.file_uploader("Import Funnel result", type=["md", "txt", "json"], key=f"do_funnel_up")
            if upf and st.button("Import Funnel Result", key=f"do_funnel_imp") and ft:
                dest = actions.save_upload(upf, dest_dir=OUT / "imports")
                with st.spinner("Importing Funnel result..."):
                    _run(actions.import_funnel_result(funnel_registry=funnel_reg, ticker=ft, source=dest))
        with f3:
            if ft:
                ctx = funnel_reg.context_fields(ft)
                st.caption(f"Source: {SOURCE_FUNNEL}" if ctx.get("Fair Value Range") else f"Source: {SOURCE_LOCAL_HEURISTIC}")
                st.write({"funnel_status": ctx.get("funnel_status"), "Fair Value Range": ctx.get("Fair Value Range")})


def _step8_intraday(snap, store, db, focus: set[int], code: str | None):
    intra = snap.get("intraday") or {}
    with _step_box(8, "During the EGX Session", intra.get("status") or "NOT_LIVE", focus):
        st.caption("Live confirmation is only available in continuous trading, and only with fresh bars.")
        st.info(intra.get("headline") or "")
        st.caption(
            "EGX Market Bridge does not execute orders and currently does not provide broker-grade bid/ask/depth. "
            "Use your broker for live execution information."
        )
        live = bool(intra.get("live"))
        age = snap.get("intraday_age_seconds")
        st.write(
            f"Latest Intraday age: **{format_age(age)}**  ·  "
            f"Freshness: **{intra.get('status')}**  ·  "
            f"ACTIONABLE: **{'YES' if intra.get('actionable') else 'NO'}**  ·  "
            f"Enriched: {snap.get('intraday_enriched') or 0} / {snap.get('intraday_requested') or 0}"
        )
        if live and not intra.get("actionable"):
            st.error("Intraday evidence is too stale for actionable confirmation. ACTIONABLE = NO.")
        b1, b2 = st.columns(2)
        with b1:
            if code == ACTION_INTRADAY:
                st.caption("Use the next action at the top of this page.")
            elif st.button("Refresh Intraday Data", key="do_intra_ref"):
                _refresh_intraday(snap)
        with b2:
            disable_prep = not snap.get("has_intraday_selected")
            if disable_prep:
                st.caption("Prepare Intraday requires Intraday-selected candidates.")
            if st.button("Prepare Intraday Handoff", key="do_intra_prep", disabled=disable_prep):
                with st.spinner("Preparing Intraday ChatGPT handoff..."):
                    _run(actions.prepare_schedule_jobs(
                        ["INTRADAY_OPPORTUNITY"],
                        store=store, db=db,
                        explorer_package_dir=(snap.get("explorer") or {}).get("package_dir"),
                        session_meta=snap.get("session_meta"),
                    ))
        if live:
            panel = intraday_panel_rows(snap.get("candidates") or [], imports=snap.get("imports"))
            if panel:
                st.dataframe(pd.DataFrame(panel), use_container_width=True, hide_index=True)
                st.caption("ChatGPT states such as CONFIRMED are analysis labels, not automatic orders. Never CONFIRMED BUY.")
        else:
            with st.expander("Historical Intraday review"):
                panel = intraday_panel_rows(snap.get("candidates") or [], imports=snap.get("imports"))
                if panel:
                    st.dataframe(pd.DataFrame(panel), use_container_width=True, hide_index=True)
                else:
                    st.caption("No enriched Intraday rows in the current Explorer package.")
        pre = chatgpt_status_by_ticker(snap.get("imports"), "PREMARKET_CATALYSTS")
        if pre:
            st.caption("Pre-market ChatGPT statuses are analysis labels (PRIORITY WATCH / WAIT / AVOID CHASE), not orders.")


def _step9_outcomes(snap, store, db, focus: set[int], code: str | None):
    with _step_box(9, "Update Signal Outcomes", f"{snap.get('outcomes_pending_n') or 0} PENDING", focus):
        st.caption("The app calculates returns after 1, 2, 5, 10 and 20 trading sessions from saved market data.")
        st.write(
            f"Canonical scanner signals: **{snap.get('canonical_n') or 0}**  ·  "
            f"Pending: **{snap.get('outcomes_pending_n') or 0}**  ·  "
            f"1-session mature: **{snap.get('outcomes_1s_n') or 0}**  ·  "
            f"3-session mature: **{snap.get('outcomes_3s_n') or 0}**  ·  "
            f"5-session mature: **{snap.get('outcomes_5s_n') or 0}**  ·  "
            f"Not evaluable: **{snap.get('outcomes_not_evaluable_n') or 0}**"
        )
        st.caption("MFE is the best price move; MAE is the worst price move during the measured period. Future sessions remain pending.")
        if not snap.get("canonical_n"):
            st.warning("Update Outcomes requires canonical signals. Prepare Explorer and schedules first.")
        b1, b2 = st.columns(2)
        with b1:
            if code != ACTION_UPDATE_OUTCOMES:
                if st.button("Update Outcomes", key="do_upd_out", disabled=not snap.get("canonical_n")):
                    with st.spinner("Updating outcomes..."):
                        _run(actions.update_outcomes(store=store, db=db))
            else:
                st.caption("Use the next action at the top of this page.")
        with b2:
            if st.button("View Signal Outcomes", key="do_view_out"):
                _go("Signal Outcomes")


def _step10_weekly(snap, store, db, focus: set[int], code: str | None):
    with _step_box(10, "Weekly Review", "RECOMMENDED" if snap.get("weekly_recommended") else "AVAILABLE", focus):
        st.caption("Historical review of scanner samples and imported analyses. Do not auto-tune scores.")
        st.write(
            f"scanner_sample_n: **{snap.get('canonical_n') or 0}**  ·  "
            f"analysis_observations_imported_n: **{snap.get('chatgpt_imported_n') or 0}**  ·  "
            f"analysis_observations_evaluable_n: **{snap.get('evaluable_n') or 0}**  ·  "
            f"mature 5-session: **{snap.get('outcomes_5s_n') or 0}**  ·  "
            f"calibration status: **{snap.get('calibration_status') or 'INSUFFICIENT_SAMPLE'}**"
        )
        pkg = (snap.get("explorer") or {}).get("package_dir")
        zips = (snap.get("schedule") or {}).get("individual_zips") or {}
        if code == ACTION_WEEKLY:
            st.caption("Use the next action at the top of this page.")
        elif st.button("Prepare Weekly Review", key="do_weekly"):
            with st.spinner("Preparing Weekly X-Ray..."):
                _run(actions.prepare_schedule_jobs(
                    ["WEEKLY_XRAY"], store=store, db=db, explorer_package_dir=pkg, session_meta=snap.get("session_meta"),
                ))
        download_zip(zips.get("WEEKLY_XRAY"), label="Export Weekly ZIP", key="do_weekly_dl")
        up = st.file_uploader("Import Weekly result", type=["md", "txt", "json"], key="do_weekly_up")
        if up and st.button("Import Weekly Result", key="do_weekly_imp"):
            dest = actions.save_upload(up, dest_dir=OUT / "imports")
            with st.spinner("Importing Weekly result..."):
                _run(actions.import_chatgpt_result(
                    dest, analysis_type="WEEKLY_XRAY", store=store, run_id=(snap.get("schedule") or {}).get("run_id"),
                ))
        st.caption("Do not treat this as a score-tuning instruction. Scoring remains frozen at 0.5.1 / HEURISTIC_UNCALIBRATED.")
