from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from egxbridge.analysis.common.ai_mode import AI_CHATGPT_HANDOFF
from egxbridge.analysis.common.models import utc_now
from egxbridge.analysis import WORKFLOW_VERSION


EXPLORER_HORIZONS = {
    "NEXT_WORKING_DAY",
    "1_TO_3_SESSIONS",
    "1_WEEK",
    "TACTICAL_20_SESSIONS",
}

CANDIDATE_QUALITY = {
    "INVESTMENT_QUALITY",
    "HYBRID",
    "SPECULATIVE",
    "HIGHLY_SPECULATIVE",
}

NEXT_DAY_ACTIONS = {
    "WATCH",
    "WAIT_FOR_CONFIRMATION",
    "CLEAN_CORRECTION_BUY_CANDIDATE",
    "BREAKOUT_CONFIRMATION_CANDIDATE",
    "SPECULATION_CANDIDATE",
    "AVOID_CHASE",
    "NO_TRADE",
}

SELECTION_BASIS = {
    "BROAD_UNIVERSE",
    "PARTIAL_UNIVERSE",
    "MOMENTUM_SCREEN",
    "FUNDAMENTAL_SCREEN",
    "CATALYST_SCREEN",
    "TOP_GAINER",
    "USER_SELECTED",
}

CANDIDATE_FAMILIES = {
    "EARLY_MOMENTUM",
    "PRE_BREAKOUT",
    "CLEAN_CORRECTION",
    "CONTINUATION",
    "EARLY_REVERSAL",
    "DELAYED_REPRICING",
    "HIGH_RELATIVE_VOLUME",
    "NEAR_HIGH_STRENGTH",
    "USER_WATCHLIST",
    "FRESH_CONTINUATION",
    "MATURE_CONTINUATION",
    "DELAYED_REPRICING_TECHNICAL_HYPOTHESIS",
    "HIGH_BASE_SECOND_LEG",
}


@dataclass
class ExplorerRunConfig:
    horizon: str = "NEXT_WORKING_DAY"
    universe: list[str] = field(default_factory=list)
    target_date: str | None = None
    portfolio_context: str = ""
    selection_basis: str = "BROAD_UNIVERSE"
    selection_bias_risk: str = "MEDIUM"
    ai_mode: str = AI_CHATGPT_HANDOFF
    workflow_version: str = WORKFLOW_VERSION
    created_at: str = ""
    environment: str = "PRODUCTION"
    prescreen_limit: int = 30
    intraday_limit: int = 15
    handoff_limit: int = 20
    enrich_intraday: bool = False
    min_scanner_bars: int = 20
    coverage_high: float = 80.0
    coverage_medium: float = 60.0
    coverage_low: float = 30.0
    watchlist: list[str] = field(default_factory=list)
    lane_a_slots: int = 8
    lane_b_slots: int = 6
    lane_c_slots: int = 8
    lane_d_slots: int = 4
    lane_e_slots: int = 4
    recovery_limit: int = 10
    # Intraday enrichment representation (does not change ranking scores).
    intraday_lane_a_slots: int = 8
    intraday_lane_b_slots: int = 2
    intraday_lane_c_slots: int = 4
    intraday_lane_d_slots: int = 1

    def __post_init__(self):
        if not self.created_at:
            self.created_at = utc_now()
        if self.horizon not in EXPLORER_HORIZONS:
            raise ValueError(f"Invalid horizon: {self.horizon}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExplorerCandidateTemplate:
    """Labels ChatGPT may assign — Bridge does not place orders."""
    ticker: str
    funnel_status: str = "NOT_FOUND"
    investment_quality: str | None = None
    next_day_action: str | None = None
    recommended_deep_analysis: str | None = None  # FULL_FUNNEL | DELTA_FUNNEL | None
    selection_basis: str = "BROAD_UNIVERSE"
    selection_bias_risk: str = "MEDIUM"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
