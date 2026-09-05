"""Small Streamlit widgets for Daily Operator. No backend math."""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from egxbridge.ui.candidates import SOURCE_CHATGPT
from egxbridge.ui.theme import chip_tone
from egxbridge.ui.versions import version_caption, version_labels


def _esc(value: Any) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def display_label(value: Any) -> str:
    """Readable UI labels; stored classifications and codes stay unchanged."""
    labels = {
        "NOT_RUN": "Not scanned yet", "NOT_STARTED": "Not started", "NOT_FOUND": "Not analyzed",
        "NOT_ANALYZED": "Not analyzed", "NOT_AVAILABLE": "Not available", "NOT_RELIABLE": "Not reliable",
        "READY_WITH_LIMITATIONS": "Ready · limited coverage", "STALE_EXPECTED": "Latest closed session",
        "PREPARED / NOT IMPORTED": "Ready for ChatGPT", "NOT_LIVE": "No live confirmation",
        "CONTINUOUS_TRADING": "Market open", "POST_CLOSE": "Outside trading hours", "PRE_OPEN": "Before market open",
        "DESCRIPTIVE_ONLY": "Descriptive only", "HEURISTIC_UNCALIBRATED": "Heuristic · under validation",
        "INSUFFICIENT_SAMPLE": "More evidence needed", "CALIBRATION_REVIEW_ELIGIBLE": "Ready for calibration review",
        "NO ACTION": "No action needed", "NONE": "None yet", "PENDING": "Waiting for future data",
        "MATURE": "Ready", "NOT IMPORTED": "Awaiting ChatGPT", "NOT PREPARED": "Not prepared",
        "burden_revision": "Price-implied expectations × revision outlook",
        "gap_revision": "Expectations gap × revision outlook", "premium_to_fv": "Price above fair value",
        "discount_to_fv": "Price below fair value", "market_tape_regime_local_input": "Market tape regime",
        "volume_ratio_bin": "Relative volume", "CLV_bin": "Position within daily price range (CLV)",
        "RS_state": "Relative strength", "RS_direction_5": "Relative strength over 5 sessions",
    }
    if value is None or value == "":
        return "Not available"
    text = str(value)
    return labels.get(text, text.replace("_", " ").capitalize())


def flash_from_state():
    flash = st.session_state.pop("op_flash", None)
    if not flash:
        return
    if flash.get("ok"):
        st.success(flash.get("message") or "Completed")
    else:
        st.error(flash.get("message") or "Action could not complete")
    extra = flash.get("detail")
    if extra:
        st.caption(str(extra))


def set_flash(result: dict[str, Any]):
    st.session_state["op_flash"] = {
        "ok": bool(result.get("ok")),
        "message": result.get("message"),
        "detail": result.get("warning"),
    }


def version_header(*, environment: str = "PRODUCTION"):
    lab = version_labels(environment=environment)
    st.title(lab["title"])
    st.caption(version_caption(lab))
    return lab


def operator_hero(*, title: str, session: str | None, phase: str | None, cairo: str | None, caption: str | None = None):
    cairo_short = (cairo or "—")
    if "T" in cairo_short:
        cairo_short = cairo_short.replace("T", " ")[:19]
    extra = f"<p>{_esc(caption)}</p>" if caption else ""
    st.markdown(
        f"""
<div class="op-hero">
  <h1 class="op-hero-title">{_esc(title)}</h1>
  {extra}
  <p class="op-meta">Latest data: {_esc(session or "not collected yet")} · {_esc(display_label(phase))} · Cairo {_esc(cairo_short)}</p>
</div>
        """.strip(),
        unsafe_allow_html=True,
    )


def do_now_panel(*, title: str, steps: list[str] | None = None, owner: str = "In this app"):
    items = ""
    if steps:
        lis = "".join(f"<li>{_esc(step)}</li>" for step in steps)
        items = f'<ul class="op-cta-steps">{lis}</ul>'
    st.markdown(
        f'<section class="op-cta" aria-label="Your next action"><h2 class="op-cta-title">{_esc(title)}</h2>'
        f'<p class="op-owner">{_esc(owner)}</p>{items}</section>',
        unsafe_allow_html=True,
    )


def next_action_banner(next_action: dict[str, Any] | None):
    if not next_action:
        return
    st.info(f"Next: **{next_action.get('label') or next_action.get('code')}**")


def readiness_strip(items: list[dict[str, Any]]):
    if not items:
        return
    parts = ['<div class="op-chips">']
    for item in items:
        status = item.get("status") or "—"
        tone = chip_tone(str(status))
        label = item.get("label") or ""
        parts.append(
            f'<span class="op-chip" data-tone="{_esc(tone)}">{_esc(label)} <b>{_esc(display_label(status))}</b></span>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def source_caption(source: str):
    st.caption(f"Source: {source}")


def download_zip(path: str | Path | None, *, label: str, key: str, primary: bool = False, download_name: str | None = None):
    if not path:
        st.caption(f"{label}: not prepared yet.")
        return False
    p = Path(path)
    if not p.exists():
        st.caption(f"{label}: file is no longer on disk.")
        return False
    data = p.read_bytes()
    st.download_button(
        label,
        data=data,
        file_name=download_name or p.name,
        mime="application/zip",
        key=key,
        type="primary" if primary else "secondary",
    )
    return True


def audit_expander(title: str, payload: dict[str, Any]):
    with st.expander(title):
        st.json(payload)


def candidate_table(rows: list[dict[str, Any]], *, key: str, help_text: str | None = None):
    if help_text:
        st.caption(help_text)
    if not rows:
        st.info("No candidates match this view. Clear the filters, or run a market scan from Daily Operator if you have not scanned yet.")
        return
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True, key=key, column_config={
        "Close": st.column_config.NumberColumn("Close (EGP)", format="%.2f"),
        "RVOL20": st.column_config.NumberColumn("Relative volume", format="%.2fx", help="Volume divided by its 20-session average. 1× means average volume."),
        "Candidate Score": st.column_config.NumberColumn("Scanner score", format="%.1f", help="Heuristic screening score. This is not a probability or investment decision."),
        "Distance 20D High": st.column_config.NumberColumn("From 20-session high (%)", format="%.2f"),
        "Move Already Realized": st.column_config.TextColumn("Move already made", help="How much of the setup's price move may already have occurred."),
        "Forward Setup": st.column_config.TextColumn("Setup quality", help="Local heuristic based on market evidence; not a ChatGPT conclusion."),
    })
    st.caption("Local scanner evidence · Rank is a review priority. Scores are heuristic, not a probability of profit.")


def job_status_label(job: str, imports: dict[str, Any], prepared: bool) -> str:
    rec = (imports or {}).get(job) or {}
    if rec.get("status") == "IMPORTED":
        return "IMPORTED"
    if rec.get("status", "").startswith("IMPORTED"):
        return rec["status"]
    if prepared:
        return "PREPARED / NOT IMPORTED"
    return "NOT PREPARED"


def format_age(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    return f"{seconds / 3600:.1f}h"


def plan_panel(plan: dict[str, Any] | None):
    if not plan:
        return
    watch = ", ".join(str(x) for x in (plan.get("priority_watch") or [])) or "—"
    wait = ", ".join(str(x) for x in (plan.get("wait_for_confirmation") or [])) or "—"
    avoid = ", ".join(str(x) for x in (plan.get("avoid_chase") or [])) or "—"
    funnel = plan.get("funnel_action") or []
    funnel_txt = (
        "; ".join(f"{r.get('ticker')} {r.get('action')}" for r in funnel) if funnel else "—"
    )
    source = plan.get("source") or SOURCE_CHATGPT
    st.markdown(
        f"""
<div class="op-plan">
  <div class="op-plan-title">Next session plan</div>
  <p class="op-meta">Source: {_esc(source)} — not a local scanner order</p>
  <p><b>Regime</b> {_esc(plan.get("market_regime") or "—")} · <b>Posture</b> {_esc(plan.get("portfolio_posture") or "—")}</p>
  <p><b>Priority watch</b> {_esc(watch)}<br>
  <b>Wait for confirmation</b> {_esc(wait)}<br>
  <b>Avoid chase</b> {_esc(avoid)}<br>
  <b>Funnel</b> {_esc(funnel_txt)}</p>
</div>
        """.strip(),
        unsafe_allow_html=True,
    )
