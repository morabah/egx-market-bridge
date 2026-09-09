"""Operator console theme. Injected once per Streamlit run. No scoring."""
from __future__ import annotations

import streamlit as st

# Institutional ops console: one sans, dark room-light, teal only on the live action.
_CSS = """
@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap");

html, body, [class*="css"], [data-testid="stAppViewContainer"], .stMarkdown, .stText, .stCaption {
  font-family: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
}
code, pre, kbd, samp, [data-testid="stCode"], .stDataFrame {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
::selection {
  background: rgba(61, 155, 143, 0.35);
  color: #F4F7FA;
}
:focus-visible {
  outline: 2px solid #3D9B8F;
  outline-offset: 2px;
}
* {
  scrollbar-width: thin;
  scrollbar-color: #3A4553 #0E1116;
}

[data-testid="stHeader"] { background: transparent; }

[data-testid="stSidebar"] {
  background: #0B0E13;
  border-right: 1px solid rgba(230, 237, 243, 0.06);
}
[data-testid="stSidebar"] {
  font-family: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
}
[data-testid="stSidebarNav"] { display: none; }

.block-container {
  padding-top: 2.25rem;
  padding-bottom: 3rem;
  max-width: 1180px;
}

h1, h2, h3 {
  letter-spacing: -0.02em;
  font-weight: 600;
}
[data-testid="stAppViewContainer"] h1 { font-size: 1.8rem; line-height: 1.25; }
[data-testid="stCaption"] {
  color: #A8B4C0 !important;
}

div[data-testid="stMetric"] {
  background: #161B22;
  padding: 0.7rem 0.85rem;
  border: 1px solid rgba(230, 237, 243, 0.06);
}
div[data-testid="stMetric"] label { color: #A8B4C0; font-size: 0.75rem; }
div[data-testid="stMetricValue"] { font-size: 1.05rem; font-weight: 600; }

[data-testid="stHeaderActionElements"] {
  display: none;
}
div[data-testid="stExpander"] {
  background: #12171F;
  border: 1px solid rgba(230, 237, 243, 0.08);
  margin-bottom: 0.28rem;
}
div[data-testid="stExpander"] summary {
  font-weight: 500;
  font-size: 0.95rem;
}

.stButton > button {
  border-radius: 2px;
  font-weight: 500;
  border-color: rgba(230, 237, 243, 0.14);
}
.stButton > button[kind="primary"] {
  background: #3D9B8F;
  color: #061014;
  border: none;
  font-weight: 600;
}
.stButton > button[kind="primary"]:hover {
  background: #4DB0A3;
  color: #061014;
}
.stButton > button:disabled {
  opacity: 0.45;
}

[data-testid="stSidebar"] .nav-group {
  margin: 1.1rem 0 0.4rem 0;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #8B9AAB;
  font-weight: 600;
}
[data-testid="stSidebar"] .stButton > button {
  justify-content: flex-start;
  font-weight: 400;
  background: transparent;
  color: #C5D0DA;
  border: 1px solid transparent;
  padding: 0.38rem 0.55rem;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: #161B22;
  color: #F4F7FA;
  border-color: rgba(230, 237, 243, 0.06);
}
[data-testid="stSidebar"] .nav-current {
  padding: 0.38rem 0.55rem;
  font-weight: 600;
  color: #F4F7FA;
  background: #161B22;
  border: 1px solid rgba(230, 237, 243, 0.08);
  margin-bottom: 0.15rem;
}
[data-testid="stDownloadButton"] > button[kind="primary"] {
  background: #3D9B8F;
  color: #061014;
  border: none;
  font-weight: 600;
  border-radius: 2px;
}
[data-testid="stDownloadButton"] > button[kind="primary"]:hover {
  background: #4DB0A3;
  color: #061014;
}

.op-hero {
  margin: 0 0 0.35rem 0;
}
.op-hero .op-hero-title {
  font-size: 1.8rem;
  line-height: 1.2;
  margin: 0 0 0.35rem 0;
  color: #F4F7FA;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.op-hero p {
  margin: 0;
  color: #A8B4C0;
  font-size: 0.95rem;
}
.op-meta {
  margin: 0.55rem 0 0 0;
  color: #8B9AAB;
  font-size: 0.82rem;
  font-variant-numeric: tabular-nums;
}
.op-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0.85rem 0 1rem 0;
}
.op-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 0.4rem;
  padding: 0.28rem 0.55rem;
  background: #161B22;
  border: 1px solid rgba(230, 237, 243, 0.08);
  font-size: 0.78rem;
  color: #C5D0DA;
  font-variant-numeric: tabular-nums;
}
.op-chip b {
  font-weight: 600;
  color: #F4F7FA;
}
.op-chip[data-tone="ok"] b { color: #8FCBB8; }
.op-chip[data-tone="warn"] b { color: #E0C07A; }
.op-chip[data-tone="bad"] b { color: #E08A7A; }
.op-chip[data-tone="mute"] b { color: #A8B4C0; }

.op-cta {
  background: #12171F;
  border: 1px solid rgba(61, 155, 143, 0.35);
  padding: 0.95rem 1rem 0.7rem;
  margin: 1.1rem 0 0.45rem 0;
}
.op-shortcut-label {
  margin: 0.85rem 0 0.35rem 0;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #8A96A3;
  font-weight: 600;
}
.op-cta .op-cta-title {
  font-size: 1.2rem;
  margin: 0 0 0.35rem 0;
  color: #F4F7FA;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.op-cta-steps {
  margin: 0.2rem 0 0;
  padding-left: 1.15rem;
  color: #C5D0DA;
  font-size: 0.9rem;
  line-height: 1.45;
}
.op-cta-steps li {
  margin: 0.18rem 0;
}
.op-plan {
  background: #12171F;
  border: 1px solid rgba(230, 237, 243, 0.08);
  padding: 0.9rem 1rem 0.75rem;
  margin: 0 0 1rem 0;
}
.op-plan-title {
  font-size: 0.95rem;
  margin: 0 0 0.45rem 0;
  color: #F4F7FA;
  font-weight: 600;
}
.op-plan p {
  color: #C5D0DA;
  font-size: 0.9rem;
  line-height: 1.45;
}
.op-owner { color: #A8B4C0; font-size: 0.85rem; margin: 0.2rem 0 0.6rem; }
.op-workflow { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); list-style: none; padding: 0; margin: 1rem 0 1.4rem; gap: 1rem; }
.op-workflow li { border-top: 1px solid #34424C; padding-top: 0.7rem; }
.op-workflow b { display: block; color: #E6EDF3; font-size: 0.9rem; font-weight: 500; }
.op-workflow span { display: block; color: #A8B4C0; font-size: 0.8rem; line-height: 1.5; margin-top: 0.2rem; }
[data-testid="stTabs"] [role="tablist"] { gap: 1.2rem; }
[data-testid="stTabs"] [role="tab"] { font-size: 0.95rem; min-height: 44px; }
input, textarea { caret-color: #8FCBB8; }
a { text-underline-offset: 0.2em; }
@media (max-width: 700px) {
  .block-container { padding: 2.5rem 1rem 2rem; }
  [data-testid="stAppViewContainer"] h1, .op-hero .op-hero-title { font-size: 1.5rem; }
  .op-workflow { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.8rem; }
  .op-cta { padding: 0.85rem; }
  .stButton > button, [data-testid="stDownloadButton"] > button { min-height: 44px; }
  [data-testid="stTabs"] [role="tablist"] { gap: 0.7rem; }
}
"""


def inject_operator_theme() -> None:
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


def chip_tone(status: str | None) -> str:
    s = (status or "").upper()
    if any(
        token in s
        for token in (
            "NOT IMPORTED",
            "NOT PREPARED",
            "NOT RUN",
            "NOT_RUN",
            "NOT_LIVE",
            "NOT LIVE",
        )
    ) or s in {"NONE"}:
        return "mute"
    if "FAIL" in s or "ERROR" in s or "UNEXPECTED" in s:
        return "bad"
    frac = s.split(" ", 1)[0]
    if "/" in frac and "IMPORTED" in s:
        try:
            done, total = (int(x) for x in frac.split("/", 1))
            if total and done >= total:
                return "ok"
            if done == 0:
                return "mute"
            return "warn"
        except ValueError:
            pass
    if "ACTION REQUIRED" in s or "PENDING" in s or "PARTIAL" in s or "STALE" in s or "LIMITATION" in s:
        return "warn"
    if "READY" in s or "IMPORTED" in s or "OK" in s or "NO ACTION" in s:
        return "ok"
    return "mute"
