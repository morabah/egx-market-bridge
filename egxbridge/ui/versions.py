"""User-facing version labels. Do not collapse these into a generic 'Version'."""
from __future__ import annotations

from egxbridge import __version__ as APP_VERSION, DATA_LAYER_VERSION
from egxbridge.analysis import WORKFLOW_VERSION, SCORING_VERSION, FUNNEL_PROMPT_VERSION
from egxbridge.analysis.common.ai_mode import AI_CHATGPT_HANDOFF, active_ai_mode
from egxbridge.analysis.common.environment import PRODUCTION
from egxbridge.analysis.explorer.calibration import SCORE_KIND
from egxbridge.analysis.schedule.types import HANDOFF_SCHEMA_VERSION


def version_labels(*, environment: str = PRODUCTION) -> dict[str, str]:
    return {
        "application_version": APP_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "funnel_prompt_version": FUNNEL_PROMPT_VERSION,
        "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
        "market_data_schema_version": DATA_LAYER_VERSION,
        "scoring_version": SCORING_VERSION,
        "score_kind": SCORE_KIND,
        "ai_mode": active_ai_mode() or AI_CHATGPT_HANDOFF,
        "environment": environment,
        "title": f"EGX Market Bridge v{APP_VERSION}",
    }


def version_caption(labels: dict[str, str] | None = None) -> str:
    lab = labels or version_labels()
    return (
        f"Application: {lab['application_version']}  ·  "
        f"Funnel Framework: {lab['funnel_prompt_version']}  ·  "
        f"Market Data Schema: {lab['market_data_schema_version']}  ·  "
        f"Scoring: {lab['scoring_version']} / {lab['score_kind']}  ·  "
        f"Handoff Schema: {lab['handoff_schema_version']}  ·  AI Mode: {lab['ai_mode']}"
    )
