"""Job-specific ChatGPT instructions. Prose is primary; JSON envelope is optional."""
from __future__ import annotations

from typing import Any
import json

from egxbridge.analysis.schedule.types import (
    ANALYSIS_MACRO, ANALYSIS_PREMARKET, ANALYSIS_INTRADAY, ANALYSIS_VALUE, ANALYSIS_WEEKLY,
    SCORING_VERSION, RESULT_ENVELOPE_VERSION, NOT_LIVE_CONFIRMATION_TEXT,
    STALE_EVIDENCE_PHASES, ANALYSIS_OBSERVATIONS_N_SEMANTICS,
)
from egxbridge.analysis.schedule.result_schemas import (
    build_example_envelope, enum_line,
    CATALYST_STATUS_VALUES, NEXT_SESSION_STATUS_VALUES, SETUP_STATE_VALUES,
    FUNNEL_ACTION_VALUES, MARKET_REGIME_VALUES, PORTFOLIO_POSTURE_VALUES,
    CALIBRATION_STATUS_VALUES, COPY_FROM_INPUT,
)


def _envelope_request(analysis_type: str, ctx: dict[str, Any] | None = None) -> str:
    example = build_example_envelope(analysis_type, ctx)
    return f"""
## Funnel v2.8 responsibility boundary

Use prior v2.8 fields only when imported and attributed to their source/cutoffs.
Missing expectations are NOT_ANALYZED. Price momentum cannot determine expectations,
revision outlook, Fair Value, Fresh Capital Test or the final capital decision.
Pre-market: which price-implied expectation can new evidence revise?
Intraday: timing/reaction only; no intrinsic Fair Value recalculation.
Value & Quality: START_FULL_FUNNEL / CONTINUE_FUNNEL / RUN_DELTA / NO_ACTION routing only.
Weekly X-Ray owns validation interpretation and may return rule_change_proposals
with action KEEP_RULE / INVESTIGATE_RULE / PROPOSE_CHANGE, rule_name, old_definition,
proposed_definition, reason, sample_window, independent_N, group_statistics,
friction_included, regime_splits, known_limitations, expected_effect.
The app stores proposals; external human approval and versioned developer implementation
are required. The motivating sample is DISCOVERY_FOR_NEW_RULE, never independent validation
of the changed rule. Return later_event_review separately from T0 classifications.
Declare analysis_started_at, declared_research_cutoff, market_data_cutoff.
Per-candidate funnel_v28 may contain supported partial structured fields; use
NOT_AVAILABLE/NOT_ANALYZED when a selective full Funnel has not been performed.

## Optional JSON result envelope (result_envelope_version={RESULT_ENVELOPE_VERSION})

After your prose conclusion, append a fenced JSON block matching this job's schema.
Prose remains the primary reasoning record. Do not answer JSON-only.
This block is a TEMPLATE (example_kind=TEMPLATE_NOT_ACTUAL_OUTPUT).
Copy canonical_signal_id and session_phase from the package. Do not invent ids.
Do not hard-code CONTINUOUS_TRADING. session_phase must match the package header.

analysis_type MUST be {analysis_type}.

```json
{json.dumps(example, indent=2)}
```
"""


def render_macro(ctx: dict[str, Any]) -> str:
    run_id = ctx["run_id"]
    session = ctx.get("latest_session")
    summary = json.dumps(ctx.get("market_summary") or {}, indent=2, default=str)
    top = json.dumps(ctx.get("top_candidates_compact") or [], indent=2, default=str)
    phase = (ctx.get("session_meta") or {}).get("session_phase")
    return f"""# A) MACRO / HOLDINGS — next session regime

Run ID: {run_id}
schedule_run_id: {run_id}
Scoring version (frozen): {SCORING_VERSION}
AI MODE: CHATGPT_HANDOFF — no paid API.
Horizon: NEXT_WORKING_DAY planning (not live execution).
latest_completed_market_session: {session or 'UNKNOWN'}
target_next_working_day: UNKNOWN (do not guess holidays)
session_phase at package generation: {phase}

## Purpose

What macro, market-regime and portfolio conditions matter for the **next session**?

This job must NOT rank 20 stocks in deep technical detail.
Do not manufacture macro or news locally — research externally.

Per-candidate records are OPTIONAL. This job is valid without candidate identities.
If you include candidate notes, echo ticker + canonical_signal_id + signal_family_id + parent_signal_id + market_state_fingerprint. Ticker alone is not the identity key.

## A. BROAD MARKET EVIDENCE (primary)

Scope = SCANNER_ELIGIBLE_EQUITY_UNIVERSE.

Use `market_participation` / `market_breadth` below.
Do **not** infer market regime from candidate shortlist breadth.
Use broad-market breadth first.

```json
{summary}
```

## B. CANDIDATE SHORTLIST CONTEXT (secondary)

These names are a biased attractive-setup shortlist. Their internal
advancer/decliner mix is CANDIDATE_BREADTH, not market breadth.

```json
{top}
```

## Required output (JSON fields)

{enum_line("market_regime", MARKET_REGIME_VALUES)}

{enum_line("portfolio_posture", PORTFOLIO_POSTURE_VALUES)}

Also: macro_drivers, market_breadth_interpretation, risk_factors, {enum_line("confidence", ("LOW", "MEDIUM", "HIGH"))}

Do not place orders. Do not change Funnel Fair Value.
{_envelope_request(ANALYSIS_MACRO, ctx)}
"""


def render_premarket(ctx: dict[str, Any]) -> str:
    run_id = ctx["run_id"]
    session = ctx.get("latest_session")
    phase = (ctx.get("session_meta") or {}).get("session_phase")
    cands = json.dumps(ctx.get("handoff_candidates_compact") or [], indent=2, default=str)
    return f"""# B) PRE-MARKET CATALYSTS & STRUCTURE

Run ID: {run_id}
schedule_run_id: {run_id}
Scoring version (frozen): {SCORING_VERSION}
Horizon: NEXT_WORKING_DAY planning using the **latest completed session** + external news.
latest_completed_market_session: {session or 'UNKNOWN'}
target_next_working_day: UNKNOWN
session_phase at package generation: {phase}

## Purpose

What changed since the latest completed session that may change tomorrow's candidate ranking?

The local pre-screen is NOT a recommendation.

## Candidates (Explorer evidence)

Each row includes canonical_signal_id, signal_family_id, parent_signal_id, and market_state_fingerprint.
Echo those identity fields in your result envelope. Ticker alone is not the identity key.

```json
{cands}
```

## For each candidate research externally

official disclosure, company news, regulatory event, corporate action,
ownership activity, reliable financial media, material macro sensitivity.

Missing news in this package is expected. Do not fabricate.

An unverified rumor must NOT automatically promote a candidate.

## Required per-name JSON fields

ticker, canonical_signal_id, signal_family_id, parent_signal_id, market_state_fingerprint

{enum_line("catalyst_status", CATALYST_STATUS_VALUES)}

catalyst_status is NOT mandatory if no evidence exists.

{enum_line("next_session_status", NEXT_SESSION_STATUS_VALUES)}

{enum_line("confidence", ("LOW", "MEDIUM", "HIGH"))}

Also: catalyst_summary, source_summary, risk_notes

Also distinguish: MOVE_ALREADY_REALIZED vs FORWARD_SETUP_QUALITY vs catalyst vs Funnel vs chase risk.

Do not place orders. Do not change Fair Value. Scores are HEURISTIC_UNCALIBRATED, not probabilities.
{_envelope_request(ANALYSIS_PREMARKET, ctx)}
"""


def render_intraday(ctx: dict[str, Any]) -> str:
    run_id = ctx["run_id"]
    session = ctx.get("latest_session")
    phase = (ctx.get("session_meta") or {}).get("session_phase")
    live = bool(ctx.get("live_session_evidence_available"))
    rows = json.dumps(ctx.get("intraday_candidates") or [], indent=2, default=str)
    limits = json.dumps(ctx.get("data_limitations") or [], indent=2)
    if (phase in STALE_EVIDENCE_PHASES) or not live:
        horizon = (
            "Job purpose: LIVE SESSION confirmation analysis when live evidence exists. "
            f"This package's bars are from the latest completed session only — "
            f"**{NOT_LIVE_CONFIRMATION_TEXT}**"
        )
        live_note = (
            f"{NOT_LIVE_CONFIRMATION_TEXT}\n"
            f"live_session_evidence_available = false\n"
            "Do not imply current live confirmation."
        )
    else:
        horizon = "Horizon: **LIVE SESSION** analysis (not next-working-day planning)."
        live_note = "live_session_evidence_available = true"
    return f"""# C) INTRADAY OPPORTUNITY SCANNER

Run ID: {run_id}
schedule_run_id: {run_id}
Scoring version (frozen): {SCORING_VERSION}
{horizon}
latest_completed_market_session: {session or 'UNKNOWN'}
session_phase at package generation: {phase}
{live_note}
Any execution-oriented conclusion MUST state which session_phase it belongs to.
Copy session_phase from this package. Do not hard-code CONTINUOUS_TRADING.

## Purpose

Which previously identified setups are confirming or failing during the current EGX session?

Use only current-session evidence that actually exists.
Primary JSON field is setup_state — not catalyst_status.

## Intraday-enriched / selected candidates

Each row includes canonical_signal_id, signal_family_id, parent_signal_id, and market_state_fingerprint
(and parent_signal_id when this is an intraday child).
Echo those identity fields. Ticker alone is not the identity key.

```json
{rows}
```

## Data limitations

```json
{limits}
```

Do NOT infer bid/ask pressure, absorption, distribution, queue dominance,
order-book imbalance, or fillability without depth/trades.

## setup_state labels (analysis only — no orders)

{enum_line("setup_state", SETUP_STATE_VALUES)}

{enum_line("confidence", ("LOW", "MEDIUM", "HIGH"))}

Also: confirmation_notes, risk_notes, live_session_evidence_available

This package does not invent live execution capability.
Do not change Funnel Fair Value. Do not ask this job to produce next-day macro regime.
{_envelope_request(ANALYSIS_INTRADAY, ctx)}
"""


def render_value(ctx: dict[str, Any]) -> str:
    run_id = ctx["run_id"]
    session = ctx.get("latest_session")
    phase = (ctx.get("session_meta") or {}).get("session_phase")
    rows = json.dumps(ctx.get("value_candidates") or [], indent=2, default=str)
    funnel = json.dumps(ctx.get("funnel_coverage_meta") or {}, indent=2, default=str)
    return f"""# D) VALUE & QUALITY SCAN

Run ID: {run_id}
schedule_run_id: {run_id}
Scoring version (frozen): {SCORING_VERSION}
Horizon: company-value follow-up — NOT next-minute timing, NOT Full Funnel itself.
latest_completed_market_session: {session or 'UNKNOWN'}
session_phase at package generation: {phase}

## Purpose

Which Explorer candidates deserve deeper company-value work?

Do **not** calculate a new Fair Value in this schedule analysis.
Do **not** overwrite Funnel valuation.
MOVE_ALREADY_REALIZED = EXTREME does not downgrade Fair Value.
A high Fair Value is not a tactical Explorer bonus.

## Funnel coverage (equities only)

```json
{funnel}
```

## Candidates + Funnel status

Each row includes canonical_signal_id, signal_family_id, parent_signal_id, and market_state_fingerprint.
Echo those identity fields. Ticker alone is not the identity key.

```json
{rows}
```

## funnel_action

{enum_line("funnel_action", FUNNEL_ACTION_VALUES)}

{enum_line("confidence", ("LOW", "MEDIUM", "HIGH"))}

Also: reason, material_new_evidence

Context (ChatGPT confirms):
- NOT_FOUND + materially interesting Explorer candidate → candidate for START_FULL_FUNNEL
- PARTIAL / REQUIRES_CONTINUATION → CONTINUE_FUNNEL
- COMPLETE + materially new company evidence → RUN_DELTA
- CURRENT + no material change → NO_ACTION

Do not place orders.
{_envelope_request(ANALYSIS_VALUE, ctx)}
"""


def render_weekly(ctx: dict[str, Any]) -> str:
    run_id = ctx["run_id"]
    session = ctx.get("latest_session")
    phase = (ctx.get("session_meta") or {}).get("session_phase")
    hist = json.dumps(ctx.get("weekly_history") or {}, indent=2, default=str)
    return f"""# E) WEEKLY X-RAY / SIGNAL AUDIT

Run ID: {run_id}
schedule_run_id: {run_id}
Scoring version (frozen): {SCORING_VERSION}
Horizon: historical point-in-time signals + realized outcomes.
Do not mix this with live-session timing or next-working-day promotion lists.
session_phase at package generation: {phase}

## Purpose

What did the system say, and what actually happened?

Keep three layers separate:
1. LOCAL_SIGNAL (FORWARD_SETUP_QUALITY, MOVE_ALREADY_REALIZED, scores)
2. CHATGPT_ANALYSIS (PROMOTE / setup_state / funnel_action)
3. ACTUAL_OUTCOME (session returns, MFE, MAE)

A good signal can be untradeable. A bad fill does not make the signal bad.
Do NOT retune v0.5.1 weights from this sample.

Per-candidate audit records are OPTIONAL. Aggregate interpretation is valid without canonical ids.
If you include per-candidate audit rows, echo identity fields. Ticker alone is not the identity key.

## Calibration counts — APP owns these numbers

The app is authoritative for:

scanner_sample_n
canonical_signals_n
analysis_observations_generated_n
analysis_observations_imported_n
analysis_observations_evaluable_n
outcomes_complete_n
outcomes_pending_n

ChatGPT may interpret these values. ChatGPT is not the authoritative source.
Do not recreate deterministic counts unless a field is explicitly {COPY_FROM_INPUT}.
Do not return fake zeros.

analysis_observations_n is deprecated.
analysis_observations_n_semantics = {ANALYSIS_OBSERVATIONS_N_SEMANTICS}

Use generated / imported / evaluable instead.

weekly_metrics = APP_GENERATED
weekly_interpretation = CHATGPT_IMPORTED

## Calibration count definitions

scanner_sample_n = distinct canonical_signal_id eligible for outcome evaluation

analysis_observations_generated_n = schedule/job looks created
analysis_observations_imported_n = ChatGPT results successfully imported
analysis_observations_evaluable_n = imported rows with a decision-bearing status

outcomes_complete_n / outcomes_pending_n = scanner outcomes, one per canonical signal

Do **not** summarize generated looks as "analysis n" without that label.
Do **not** display generated_n as scanner n.
Do **not** combine SCANNER PERFORMANCE with ANALYSIS VALUE-ADD.
Do **not** count NO_IMPORT / PENDING_IMPORT / INVALID_PARSE as evaluable.

## FORWARD VALIDATION AUDIT

Use FORWARD_VALIDATION_AUDIT for predictive calibration. Other historical counts are descriptive only.
Report EMPIRICAL POSITIVE-RETURN RATE with N, date range, maturity, friction and regime coverage.
Do not equate N >= 50 with VALIDATED.

## Outcome / snapshot history (app-generated metrics)

```json
{hist}
```

Hit-rate definitions (if you cite them, show n):
- POSITIVE_CLOSE = future close return > 0
- TACTICAL_SUCCESS = future close return >= 1.0%

{enum_line("calibration_status", CALIBRATION_STATUS_VALUES)}

Job-level interpretation fields:
scanner_summary
analysis_value_add_summary
false_positive_notes
missed_opportunity_notes
calibration_status

Do not write "STRONG setups work 70% of the time" without n, date range, horizon, and selection method.

Do not place orders. Do not change Fair Value. Do not optimize parameters.
{_envelope_request(ANALYSIS_WEEKLY, ctx)}
"""


RENDERERS = {
    ANALYSIS_MACRO: render_macro,
    ANALYSIS_PREMARKET: render_premarket,
    ANALYSIS_INTRADAY: render_intraday,
    ANALYSIS_VALUE: render_value,
    ANALYSIS_WEEKLY: render_weekly,
}
