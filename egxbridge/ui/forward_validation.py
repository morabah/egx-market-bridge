"""Forward Validation Lab: evidence display and explicit operator actions only."""
from __future__ import annotations

import json
from pathlib import Path
import streamlit as st

from egxbridge.analysis.forward_validation import validation_report, weekly_package, start_validation, validation_run, HORIZONS
from egxbridge.analysis.schedule.outcomes import update_outcomes_for_store
from egxbridge.ui.components import display_label


def _rows(groups: list[dict], horizon: int = 5) -> list[dict]:
    """Show one horizon at a time; the download retains all horizons and metadata."""
    rows = []
    metadata = {"N", "unit", "independent_signal_n", "unique_ticker_n", "unique_sector_n", "market_regime_n",
                "date_span", "sample_diversity_status", "largest_ticker_share", "interpretation", "rate_label",
                "horizons", "signal_calibration_status"}
    for group in groups:
        stats = group.get("horizons", {}).get(str(horizon), {})
        row = {display_label(k): display_label(v) for k, v in group.items() if k not in metadata}
        rate = stats.get("empirical_positive_return_rate")
        row.update({"Signals / observations": group.get("N"), "Ready outcomes (N)": stats.get("N", 0),
            "Independent signals": stats.get("independent_signal_n", 0),
            f"Median return · +{horizon} (%)": stats.get("median_return"),
            "Empirical positive-return rate (%)": None if rate is None else round(rate * 100, 1),
            "Best move · median MFE (%)": stats.get("median_mfe"),
            "Worst move · median MAE (%)": stats.get("median_mae"),
            "Net return after costs (%)": stats.get("median_net_return_after_friction"),
            "Evidence status": display_label(stats.get("group_evidence") or stats.get("interpretation"))})
        if "round_encounter_n" in stats:
            row["Round-level encounters"] = stats["round_encounter_n"]
            for key in ("touch", "rejection", "breakout", "close_above"):
                value = stats.get(f"empirical_{key}_rate")
                row[f"{display_label(key)} (%)"] = None if value is None else round(value * 100, 1)
        rows.append(row)
    return rows


def _cases(rows: list[dict], horizon: int) -> list[dict]:
    return [{"Ticker": r.get("ticker"), "Signal date": r.get("market_session"),
        "Scanner rank": r.get("scanner_rank") or r.get("selection_rank"),
        "Setup quality": display_label(r.get("forward_setup_quality")),
        f"Return · +{horizon} (%)": r.get(f"return_{horizon}"),
        f"Worst move · +{horizon} (%)": r.get(f"mae_{horizon}"),
        "Review reason": display_label(r.get("MISSED_REASON") or "POOR_FORWARD_OUTCOME")} for r in rows]


def _table(rows):
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No eligible evidence for this view yet. Wait for future market sessions and import dated LLM classifications where applicable.")


def render_forward_status(store):
    from egxbridge.analysis.forward_validation import joined_signals, sample_statistics
    run = validation_run(store) or {}
    rows, _ = joined_signals(store)
    summary = sample_statistics(rows, cfg=run.get("config"))
    report = {"status": run.get("status", "NOT_STARTED"), "FORWARD_VALIDATION_START": run.get("FORWARD_VALIDATION_START")}
    st.markdown("**Forward test status**")
    if not run:
        st.caption("Not started. The next Explorer scan automatically saves the starting evidence for each candidate.")
    else:
        st.caption(f"{display_label(report['status'])} · Started {report['FORWARD_VALIDATION_START'][:10]} · {summary['independent_signal_n']} independent signals")
        st.write(f"**{summary['horizons']['5']['N']}** ready after 5 sessions · **{summary['horizons']['10']['N']}** after 10 · **{summary['horizons']['20']['N']}** after 20")
    st.caption("Outcomes need future trading sessions. Open the Lab to compare results and prepare the weekly review.")


def render_forward_validation(*, store, db=None, root: Path):
    st.title("Forward Validation Lab")
    st.write("See what happened after each signal, compare the evidence, and prepare a weekly review. Results are descriptive until enough independent evidence accumulates.")
    if not validation_run(store):
        st.info("Validation starts automatically when the next Explorer run freezes its eligible universe. Historical discoveries are excluded.")
        with st.expander("Configure forward test before starting"):
            with st.form("forward_test_start"):
                low = st.number_input("Descriptive below independent N", min_value=1, value=20)
                high = st.number_input("Calibration review eligible at N", min_value=2, value=50)
                top = st.number_input("False-negative audit: top performers", min_value=1, value=20)
                st.caption("Friction components are round-trip percentage points. Leave unknown components blank; explicitly enter 0 only when the component is known to be zero.")
                costs = {k: st.text_input(k.replace("_", " ").title() + " (%)", key="friction_"+k)
                         for k in ("brokerage", "exchange_regulatory", "taxes", "spread", "slippage")}
                source = st.text_input("Friction inputs source")
                if st.form_submit_button("Start forward validation with these settings"):
                    try:
                        components = {k: float(v) for k, v in costs.items() if v.strip()}
                        start_validation(store, config={"descriptive_below": low, "review_eligible_at": high,
                            "false_negative_top_n": top, "friction_model": {"friction_model_version": "1",
                            "components_pct": components, "friction_inputs_source": source or None}})
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
    a, b = st.columns(2)
    if a.button("Update forward outcomes", disabled=db is None, key="lab_update"):
        with st.spinner("Reading completed trading sessions..."):
            result = update_outcomes_for_store(store, db, forward_validation_only=True)
            st.success(f"Outcome check complete. Checked {result.get('updated', 0)} signals against available completed sessions.")
    if b.button("Prepare Weekly Validation X-Ray", key="lab_weekly"):
        weekly_package(store, root / "output" / "forward_validation" / store.environment.lower())
        st.success("Weekly evidence package prepared. Import the Weekly X-Ray result through Schedule Analysis Center.")
    report = validation_report(store)
    summary = report["summary"]
    st.caption(f"Forward Test Start: {report['FORWARD_VALIDATION_START'] or 'NOT_STARTED'}")
    metrics = st.columns(5)
    for col, label, value in zip(metrics, ["Canonical signals", "Independent signals", "+5 mature", "+10 mature", "+20 mature"],
            [summary["N"], summary["independent_signal_n"], *[summary["horizons"][str(h)]["N"] for h in (5,10,20)]]):
        col.metric(label, value)
    st.caption(f"{summary['unique_ticker_n']} companies · {summary['unique_sector_n']} known sectors · {summary['market_regime_n']} market regimes · {display_label(summary['interpretation'])}")
    if not summary["N"]:
        st.info("No forward-test signals yet. Run Explorer from Daily Operator to save the starting evidence automatically.")
        if st.button("Go to Daily Operator", key="lab_start_scan"):
            st.session_state["op_nav"] = "Daily Operator"
            st.rerun()
    elif not summary["horizons"]["1"]["N"]:
        st.info("Signals are saved; future outcomes are not ready yet. After a new trading session, refresh market data on Daily Operator and choose Update forward outcomes here.")
    st.caption("Scanner evidence comes from the app. Expectations and valuation judgments come from imported ChatGPT analysis.")
    horizon = st.selectbox("Compare returns after", HORIZONS, index=2,
        format_func=lambda h: f"{h} trading session{'s' if h != 1 else ''}", key="lab_report_horizon",
        help="A trading session is a market day with completed data. Pending outcomes are excluded from rates. N shows how many outcomes are ready.")
    with st.expander("How to read these results"):
        st.markdown("""- **Ready outcomes (N):** observations with a completed, reliable horizon.
- **Independent signals:** signal-family count; repeated companies can still concentrate the sample.
- **Median return:** the middle price return in the group.
- **MFE / MAE:** best / worst price moves during the period.
- **Positive-return rate:** the observed share of positive results, not a forecast.
- **Net return:** shown only when the required transaction-cost inputs are available.""")
        st.json({k: summary[k] for k in ("date_span", "sample_diversity_status", "largest_ticker_share")})
    st.download_button("Download full validation audit (JSON)", json.dumps(report, indent=2, default=str),
                       file_name="forward_validation_audit.json", mime="application/json")
    names = ["Overview", "Expectations", "Breakouts", "Pullbacks", "Psychology / PLSS", "Regimes", "False Positives", "False Negatives", "Rule Versions", "Change Proposals"]
    tabs = st.tabs(names)
    with tabs[0]:
        st.markdown("**Scanner performance · one canonical signal per sample**")
        _table(_rows([summary], horizon))
        st.markdown("**Cohorts and LLM value-add · denominators shown separately**")
        _table(_rows([{ "cohort": k, **v} for k,v in report["cohorts"].items()], horizon))
        with st.expander("Sample integrity and excluded evidence"):
            st.json(report["sample_integrity"])
        ticker = st.selectbox("Inspect a saved signal", ["Choose a ticker"] + sorted({r["ticker"] for r in report["signals"]}))
        for row in report["signals"]:
            if row["ticker"] != ticker:
                continue
            with st.expander(f"{row['ticker']} · {row['market_session']} · {row['canonical_signal_id'][:12]}"):
                with st.expander("Original evidence and source cutoffs"):
                    st.json(row)
                if row.get("final_decision"):
                    st.write("IMPORTED_LLM_DECISION", row["final_decision"])
                    st.json(row["llm_provenance"].get("final_decision") or {})
                st.write("Fresh Capital Test pillars · imported LLM only")
                _table([{"Pillar": display_label(key), "Imported judgment": display_label(row.get(key))} for key in ("economic_quality", "expectations_burden", "expectations_revision_edge", "risk_adjusted_return")])
                _table([{ "horizon": h, "maturity": row.get(f"maturity_{h}", "PENDING"), "gross_return": row.get(f"return_{h}"),
                    "estimated_friction": row.get("estimated_total_friction"), "net_return": row.get(f"net_return_after_friction_{h}"),
                    "MFE": row.get(f"mfe_{h}"), "MAE": row.get(f"mae_{h}")} for h in HORIZONS])
    with tabs[1]:
        view = st.selectbox("Expectations test", list(report["expectations"]), format_func=display_label)
        st.caption("LLM FUNNEL / SCHEDULE classifications · EMPIRICAL POSITIVE-RETURN RATE · N shown for every horizon")
        if view == "premium_to_fv":
            st.write("PREMIUM-TO-FV FORWARD TEST: Does rejecting stocks above Central Fair Value cause us to miss winners?")
        if view == "discount_to_fv":
            st.write("DISCOUNT-TO-FV FORWARD TEST: compare upward and downward revision groups.")
        _table(_rows(report["expectations"][view], horizon))
    for tab, key in ((tabs[2], "breakouts"), (tabs[3], "pullbacks"), (tabs[5], "regimes")):
        with tab:
            st.caption("Initial analysis bins are heuristic. Small groups are descriptive and require more evidence.")
            fields = [k for k,v in report[key].items() if isinstance(v,list)]
            view = st.selectbox("Split by", fields, key="split_"+key, format_func=display_label)
            _table(_rows(report[key][view], horizon))
    with tabs[4]:
        st.caption("PLSS status: HEURISTIC. Missing components remain unavailable; round levels imply no resistance assumption.")
        _table(_rows(report["psychology"]["coverage_groups"], horizon))
        _table(_rows(report["psychology"]["round_groups"], horizon))
        with st.expander("Raw psychological evidence and future encounters"):
            st.json(report["psychology"])
    with tabs[6]:
        st.caption("Poor future outcomes flag cases for Weekly review; they do not automatically establish a bad rule.")
        _table(_cases(report["false_positives"], 10))
    with tabs[7]:
        missed_horizon = st.selectbox("Missed-candidate horizon", [5,10,20], format_func=lambda h: f"{h} trading sessions")
        fn = report["false_negatives"][str(missed_horizon)]
        st.caption(fn["note"])
        _table(_cases(fn["cases"], missed_horizon))
        with st.expander("Universe coverage and original evidence"):
            st.json(fn)
    with tabs[8]:
        st.caption("These definitions stay fixed for each signal. Outcome reports never change the scanner rules.")
        for rule in report["rule_versions"]:
            with st.expander(f"{display_label(rule.get('rule_name'))} · {rule.get('rule_version')}"):
                st.json(rule)
    with tabs[9]:
        st.caption("Weekly LLM → stored proposal → external human review → developer implements a new version → later forward sample. No automatic activation.")
        if not report["change_proposals"]:
            st.info("No rule changes proposed. Import a Weekly X-Ray reply to save its proposals for review.")
        else:
            st.json(report["change_proposals"])
        st.markdown("**Later event reviews · separate from T0**")
        st.json(report["later_event_reviews"])
    with st.expander("Data and interpretation limitations"):
        for text in report["limitations"][4:]:
            st.write(text)
