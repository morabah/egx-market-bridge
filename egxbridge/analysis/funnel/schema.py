"""Funnel 2.8 import contract. These are LLM judgments, never scanner inputs."""
from __future__ import annotations

import math
import re
from typing import Any

FUNNEL_SCHEMA_VERSION = "2.8.0"
MISSING_VALUES = {"NOT_AVAILABLE", "NOT_ANALYZED", "NOT_RELIABLE"}
ENUMS = {
    "intrinsic_value_position": "DEEP_DISCOUNT DISCOUNT NEAR_CENTRAL_VALUE PREMIUM_TO_CENTRAL_VALUE BEYOND_CREDIBLE_ECONOMIC_RANGE UNRELIABLE",
    "price_implied_expectations": "UNDEMANDING REASONABLE DEMANDING VERY_DEMANDING ECONOMICALLY_IMPLAUSIBLE NOT_RELIABLE",
    "expectations_burden": "UNDEMANDING REASONABLE DEMANDING VERY_DEMANDING ECONOMICALLY_IMPLAUSIBLE NOT_RELIABLE",
    "expectations_gap": "STRONGLY_POSITIVE POSITIVE NEUTRAL NEGATIVE STRONGLY_NEGATIVE NOT_RELIABLE",
    "expectations_revision_outlook": "STRONG_UPWARD UPWARD STABLE DOWNWARD STRONG_DOWNWARD UNCERTAIN",
    "expectations_revision_confidence": "HIGH MEDIUM LOW NOT_RELIABLE",
    "catalyst_revision_potential": "HIGH_POSITIVE MODERATE_POSITIVE NEUTRAL MODERATE_NEGATIVE HIGH_NEGATIVE TWO_SIDED NOT_RELIABLE",
    "information_reaction_regime": "UNDERREACTION CONTINUATION OVERREACTION REVERSAL MIXED INCONCLUSIVE NOT_APPLICABLE",
    "rerating_attribution": "EARNINGS_LED RATE_LED QUALITY_LED FLOW_LED BEHAVIORAL_LED MIXED NOT_RELIABLE",
    "fresh_capital_test": "YES BORDERLINE NO",
    "timing_quality": "GOOD NEUTRAL POOR",
    "realized_expectations_revision": "UP UNCHANGED DOWN MIXED NOT_OBSERVABLE NOT_RELIABLE",
    "catalyst_confirmed_outcome": "CONFIRMED PARTIALLY_CONFIRMED FAILED DELAYED CANCELLED UNRESOLVED NOT_APPLICABLE",
}
NUMERIC_FIELDS = set("central_fv highest_credible_bull_fv expected_horizon_market_price economic_terminal_value implied_revenue_cagr implied_margin implied_roic implied_growth_duration expected_total_return expected_annualized_total_return target_price_t0 stop_or_invalidation_t0".split())
TEXT_FIELDS = set("eps_reconciliation robust_fv_range expected_return_spread economic_valuation_summary value_creating_growth opportunity_cost overall_risk business_quality earnings_quality financial_strength economic_quality expectations_revision_edge risk_adjusted_return speculation_classification final_decision final_decision_domain valuation_date financial_cutoff news_cutoff capital_basis target_source stop_source catalyst_type catalyst_status event_description material_event_occurred".split())
STRUCTURED_FIELDS = {"psychological_levels", "fresh_capital_pillars", "eps_reconciliation_detail"}
FRESH_CAPITAL_PILLARS = {"economic_quality", "expectations_burden", "expectations_revision_edge", "risk_adjusted_return"}
LATER_FIELDS = {"realized_expectations_revision", "catalyst_confirmed_outcome", "event_description", "material_event_occurred"}
JUDGMENT_FIELDS = (set(ENUMS) | NUMERIC_FIELDS | TEXT_FIELDS | STRUCTURED_FIELDS) - LATER_FIELDS
ALIASES = {
    "central_pw_intrinsic_fv": "central_fv", "central_pw_fv": "central_fv",
    "central_fair_value": "central_fv", "capital_structure_basis": "capital_basis",
    "economic_terminal_value_horizon": "economic_terminal_value",
    "expected_horizon_market_price_horizon": "expected_horizon_market_price",
}


def field_name(value: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return ALIASES.get(key, key)


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def normalize_fields(data: dict[str, Any], *, later: bool = False) -> tuple[dict, list[str]]:
    """Partial records are valid. Invalid fields stay in raw import, not report groups."""
    fields, issues = {}, []
    if not isinstance(data, dict):
        return {}, ["structured fields: expected an object"]
    for raw_key, value in data.items():
        key = field_name(raw_key)
        if key not in (LATER_FIELDS if later else JUDGMENT_FIELDS) or value is None:
            continue
        if key in ENUMS:
            enum = re.sub(r"[\s-]+", "_", str(value).strip().upper())
            if enum not in set(ENUMS[key].split()) | MISSING_VALUES:
                issues.append(f"{key}: invalid enum")
                continue
            fields[key] = enum
        elif key in NUMERIC_FIELDS:
            n = finite_number(value)
            if n is None:
                issues.append(f"{key}: expected finite number")
            else:
                fields[key] = n
        elif key == "fresh_capital_pillars":
            if not isinstance(value, dict):
                issues.append(f"{key}: expected an object with four named pillars")
                continue
            # Map explicitly imported pillar values to the canonical display fields.
            # No pillar or overall YES/NO judgment is calculated locally.
            pillars, pillar_issues = normalize_fields({field_name(k): v for k, v in value.items()
                if field_name(k) in FRESH_CAPITAL_PILLARS})
            fields.update(pillars)
            issues.extend(pillar_issues)
        elif key == "psychological_levels":
            if isinstance(value, list) and all(isinstance(level, dict) for level in value):
                fields[key] = value
            else:
                issues.append(f"{key}: expected a list of level evidence objects")
        elif key in STRUCTURED_FIELDS:
            if isinstance(value, (list, dict)):
                fields[key] = value
            else:
                issues.append(f"{key}: expected structured evidence")
        elif isinstance(value, (str, int, float, bool)):
            fields[key] = value
    return fields, issues


def extract_summary(content: str, envelope: dict | None) -> tuple[dict, list[str]]:
    raw = {}
    for line in content.splitlines():
        cleaned = line.strip().strip("|").replace("**", "").strip()
        match = re.match(r"([^:=|]+)\s*[:=]\s*(.+)", cleaned)
        if match:
            raw[match[1].strip()] = match[2].strip().strip("|").strip()
    issues = []
    if envelope:
        section = envelope.get("final_decision_summary") or envelope.get("structured_fields") or envelope
        if isinstance(section, dict):
            raw.update(section)
        else:
            issues.append("final_decision_summary: expected an object")
    fields, field_issues = normalize_fields(raw)
    return fields, issues + field_issues


def result_schema() -> dict:
    return {
        "schema_version": FUNNEL_SCHEMA_VERSION, "partial_results_allowed": True,
        "classification_source": "FUNNEL_LLM",
        "enums": {k: sorted(set(v.split()) | MISSING_VALUES) for k, v in ENUMS.items()},
        "numeric_fields": sorted(NUMERIC_FIELDS), "text_fields": sorted(TEXT_FIELDS),
        "structured_fields": sorted(STRUCTURED_FIELDS),
        "fresh_capital_pillars": sorted(FRESH_CAPITAL_PILLARS),
        "linkage": ["canonical_signal_id", "ticker"],
        "cutoffs": ["analysis_started_at", "declared_research_cutoff", "market_data_cutoff"],
        "completion": "Existing verified stages / tagged full-result checks apply; fields alone never prove completion.",
    }
