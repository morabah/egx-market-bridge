"""Explorer Candidates page — display and filter only. No orders, no rescoring."""
from __future__ import annotations

import streamlit as st

from egxbridge.ui.candidates import (
    candidate_audit, candidate_detail, candidate_preview_rows,
    filter_candidates, sort_candidates, unique_values,
)
from egxbridge.ui.components import candidate_table, display_label
from egxbridge.ui.snapshot import gather_operator_snapshot, resolve_explorer_package


def render_explorer_candidates(*, root, store=None, db=None):
    snap = gather_operator_snapshot(root=root, store=store, db=db)
    st.title("Explorer Candidates")
    st.write("Review the scanner shortlist, inspect the evidence for a company, then return to Daily Operator to prepare ChatGPT analysis.")
    st.caption(f"Latest data: {snap.get('latest_completed_market_session') or 'not collected yet'} · {display_label(snap.get('explorer_status'))}")
    if st.button("Continue on Daily Operator", key="cands_back"):
        st.session_state["op_nav"] = "Daily Operator"
        st.rerun()
    candidates = list(snap.get("candidates") or [])
    if not candidates:
        candidates = list(resolve_explorer_package(root).get("candidates") or [])
    if not candidates:
        st.info("Your shortlist is empty. Open Daily Operator and run a market scan to find candidates.")
        return

    search, sorting = st.columns([2, 1])
    query = search.text_input("Find a ticker", placeholder="For example: COMI", key="candidates_query").strip().upper()
    sort_by = sorting.selectbox("Sort by", ["Rank", "Ticker", "Candidate Score", "RVOL20", "Forward Setup", "Lane"])
    with st.expander("Filter candidates and table options"):
        f1, f2, f3 = st.columns(3)
        lane = f1.selectbox("Setup group (lane)", ["(all)"] + unique_values(candidates, "candidate_lane"), format_func=display_label)
        setup = f2.selectbox("Setup quality", ["(all)"] + unique_values(candidates, "FORWARD_SETUP_QUALITY"), format_func=display_label)
        realized = f3.selectbox("Move already made", ["(all)"] + unique_values(candidates, "MOVE_ALREADY_REALIZED"), format_func=display_label)
        f4, f5, f6 = st.columns(3)
        vol = f4.selectbox("Volatility risk", ["(all)"] + unique_values(candidates, "VOLATILITY_RISK"), format_func=display_label)
        funnel = f5.selectbox("Company analysis status", ["(all)"] + unique_values(candidates, "funnel_status"), format_func=display_label)
        intra = f6.selectbox("Intraday data available", ["(all)", "Yes", "No"])
        descending = st.checkbox("Reverse sort order", value=False)
        all_metrics = st.checkbox("Show all table metrics", value=False)

    filtered = filter_candidates(candidates, lane=lane, setup=setup, realized=realized, vol=vol, funnel=funnel, intraday=intra)
    filtered = [c for c in filtered if not query or query in str(c.get("ticker") or "").upper()]
    filtered = sort_candidates(filtered, sort_by, descending=descending)
    st.caption(f"Showing {len(filtered)} of {len(candidates)} candidates")
    rows = candidate_preview_rows(filtered, sort_by_rank=False)
    if not all_metrics:
        visible = ("Rank", "Ticker", "Close", "Forward Setup", "Move Already Realized", "RVOL20", "Candidate Score")
        rows = [{k: row.get(k) for k in visible} for row in rows]
    candidate_table(rows, key="all_cands")
    with st.expander("How to read this shortlist"):
        st.markdown("- **Rank / scanner score:** screening priority from a fixed heuristic.\n- **Setup quality:** the strength of the local market setup.\n- **Move already made:** how much of the move may have happened already.\n- **Relative volume:** current volume compared with the 20-session average; 1× is average.\n- **Funnel:** company economics, expectations and valuation analyzed in ChatGPT.")
        st.caption("These are research inputs. A strong setup is not an investment decision.")
    if not filtered:
        return
    st.subheader("Inspect a company")
    ticker = st.selectbox("Company ticker", [c["ticker"] for c in filtered], key="candidate_inspect")
    candidate = next(c for c in filtered if c["ticker"] == ticker)
    detail = candidate_detail(candidate)
    market_tab, funnel_tab, source_tab = st.tabs(["Market evidence", "Imported Funnel analysis", "Source details"])
    with market_tab:
        st.caption("Calculated from market data. Missing values mean the evidence is unavailable.")
        st.dataframe([{"Period": period, "Price return (%)": detail.get(key)}
            for key, period in (("1D", "1 session"), ("1W", "1 week"), ("1M", "1 month"), ("3M", "3 months"), ("6M", "6 months"))], hide_index=True, use_container_width=True)
        st.dataframe([{"Measure": key, "Value": str(value) if value is not None else "Not available"}
            for key, value in detail.items() if key not in {"1D", "1W", "1M", "3M", "6M"}], hide_index=True, use_container_width=True)
    with funnel_tab:
        context = candidate.get("funnel_context") or {}
        fields = context.get("structured_fields") or {}
        if fields:
            st.caption("Imported ChatGPT judgments · Funnel " + str(context.get("funnel_version") or "version not recorded"))
            st.dataframe([{"Field": display_label(k), "Imported value": str(v)} for k, v in fields.items()], hide_index=True, use_container_width=True)
        else:
            st.info("No structured Funnel analysis is available for this company yet. You can prepare a company analysis when needed.")
        if st.button(f"Open Funnel for {ticker}", key="candidate_open_funnel"):
            st.session_state["funnel_ticker"] = ticker
            st.session_state["op_nav"] = "Analysis Workflows"
            st.rerun()
        with st.expander("Funnel source and cutoffs"):
            st.json(context)
    with source_tab:
        st.json(candidate_audit(candidate))
        st.json({k: candidate.get(k) for k in ("canonical_signal_id", "market_state_fingerprint", "history_integrity", "TECHNICAL_HISTORY_INTEGRITY", "funnel_status", "intraday_available")})
