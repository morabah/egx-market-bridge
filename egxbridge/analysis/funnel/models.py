from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from egxbridge.analysis import FUNNEL_PROMPT_VERSION, WORKFLOW_VERSION
from egxbridge.analysis.common.models import utc_now
from egxbridge.analysis.common.ai_mode import AI_CHATGPT_HANDOFF


ANALYSIS_OBJECTIVES = {
    "LONG_TERM_INVESTMENT",
    "SWING_POSITION_TRADE",
    "SHORT_TERM_SPECULATION",
    "OWNED_POSITION_REVIEW",
    "FULL_HYBRID_REVIEW",
}

OWNERSHIP_STATES = {
    "NOT_OWNED",
    "OWNED",
    "OWNED_OVERWEIGHT",
    "OWNED_UNDERWEIGHT",
}

RUN_MODES = {
    "INTERACTIVE_STAGE_BY_STAGE",
    "FULL_AUTOMATED_RUN",
    "DELTA_ONLY",
}

# Ordered Funnel stages (labels only — reasoning stays in the prompt)
FUNNEL_STAGES = [
    "-1", "0", "0.5", "1", "2", "3", "4", "5", "6", "7", "8", "9", "9.5", "10", "11",
]

CRITICAL_KEYS = [
    "Fair Value",
    "Bear Valuation",
    "Base Valuation",
    "Bull Valuation",
    "Blended Fair Value",
    "Sustainable Earnings",
    "EPS",
    "Share count",
    "Fully diluted share count",
    "Required Earnings",
    "Capital-action assumptions",
    "Valuation date",
    "News cutoff",
    "Business Quality",
    "Earnings Quality",
    "Financial Strength",
    "Growth",
    "Economic Valuation",
    "Investment Classification",
    "Integrated Risk",
]


@dataclass
class FunnelProject:
    ticker: str
    company_name_if_known: str = ""
    funnel_version: str = FUNNEL_PROMPT_VERSION
    workflow_version: str = WORKFLOW_VERSION
    created_at: str = ""
    updated_at: str = ""
    analysis_objective: str = "FULL_HYBRID_REVIEW"
    ownership_state: str = "NOT_OWNED"
    intended_horizon: str = ""
    personal_required_return: str = ""
    proposed_capital: str = ""
    primary_benchmark: str = "EGX30"
    run_mode: str = "INTERACTIVE_STAGE_BY_STAGE"
    current_stage: str = "-1"
    completed_stages: list[str] = field(default_factory=list)
    last_data_cutoff: str | None = None
    last_news_cutoff: str | None = None
    last_valuation_date: str | None = None
    valuation_status: str = "NOT_STARTED"
    funnel_completion_status: str = "NOT_STARTED"  # NOT_STARTED | PARTIAL | COMPLETE
    delta_eligible: str = "NO"  # YES | NO
    completion_basis: str = "NONE"  # INTERACTIVE_VERIFIED | FULL_AUTOMATED_VERIFIED | PARTIAL | NONE
    claimed_completed_stages: list[str] = field(default_factory=list)  # metadata only
    verified_completed_stages: list[str] = field(default_factory=list)
    skipped_stages: list[str] = field(default_factory=list)  # explicit recorded skips
    current_operation: str = "STAGE"  # STAGE | DELTA | FULL_AUTOMATED_RUN — distinct from current_stage
    ai_mode: str = AI_CHATGPT_HANDOFF
    execution_grade_at_last_handoff: str | None = None
    research_data_quality_at_last_handoff: str | None = None
    # Numeric DQ preserved at handoff boundary (optional)
    research_data_quality_score_at_last_handoff: float | None = None
    execution_data_quality_score_at_last_handoff: float | None = None
    run_started_at: str | None = None
    archived_funnel_workspace: str | None = None
    previous_funnel_context: dict[str, Any] = field(default_factory=dict)
    structured_fields: dict[str, Any] = field(default_factory=dict)
    structured_provenance: dict[str, Any] = field(default_factory=dict)
    environment: str = "PRODUCTION"  # PRODUCTION | ACCEPTANCE_TEST | UNIT_TEST

    def __post_init__(self):
        now = utc_now()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        self.ticker = self.ticker.upper()
        if self.analysis_objective not in ANALYSIS_OBJECTIVES:
            raise ValueError(f"Invalid analysis_objective: {self.analysis_objective}")
        if self.ownership_state not in OWNERSHIP_STATES:
            raise ValueError(f"Invalid ownership_state: {self.ownership_state}")
        if self.run_mode not in RUN_MODES:
            raise ValueError(f"Invalid run_mode: {self.run_mode}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FunnelProject":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
