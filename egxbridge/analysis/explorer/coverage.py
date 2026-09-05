"""Explorer coverage classification — honest about thin daily data."""
from __future__ import annotations

from typing import Any


DEFAULT_THRESHOLDS = {
    "HIGH": 80.0,
    "MEDIUM": 60.0,
    "LOW": 30.0,
}


def _pct(num: float, den: float) -> float:
    if not den:
        return 0.0
    return round(100.0 * float(num) / float(den), 2)


def classify_explorer_coverage(
    *,
    equity_universe_total: int,
    mapped_symbols: int,
    daily_data_available: int,
    scanner_eligible: int,
    thresholds: dict[str, float] | None = None,
    broad_universe_min_eligible_pct: float = 60.0,
) -> dict[str, Any]:
    th = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        th.update({k.upper(): float(v) for k, v in thresholds.items()})

    eq = max(int(equity_universe_total or 0), 0)
    mapped_coverage_pct = _pct(mapped_symbols, eq)
    daily_data_coverage_pct = _pct(daily_data_available, eq)
    scanner_eligible_coverage_pct = _pct(scanner_eligible, eq)
    eligible_coverage_pct = scanner_eligible_coverage_pct

    if eligible_coverage_pct >= th["HIGH"]:
        coverage = "HIGH"
    elif eligible_coverage_pct >= th["MEDIUM"]:
        coverage = "MEDIUM"
    elif eligible_coverage_pct >= th["LOW"]:
        coverage = "LOW"
    else:
        coverage = "INSUFFICIENT"

    # BROAD_UNIVERSE only when eligible coverage is actually broad.
    if coverage in {"HIGH", "MEDIUM"} and eligible_coverage_pct >= broad_universe_min_eligible_pct:
        selection_basis = "BROAD_UNIVERSE"
    else:
        selection_basis = "PARTIAL_UNIVERSE"

    if eligible_coverage_pct >= th["HIGH"]:
        bias = "LOW"
    elif eligible_coverage_pct >= th["MEDIUM"]:
        bias = "MEDIUM"
    else:
        bias = "HIGH"

    market_wide_confidence = coverage != "INSUFFICIENT"
    return {
        "mapped_coverage_pct": mapped_coverage_pct,
        "daily_data_coverage_pct": daily_data_coverage_pct,
        "scanner_eligible_coverage_pct": scanner_eligible_coverage_pct,
        "eligible_coverage_pct": eligible_coverage_pct,
        "EXPLORER_COVERAGE": coverage,
        "selection_basis": selection_basis,
        "selection_bias_risk": bias,
        "market_wide_confidence_allowed": market_wide_confidence,
        "coverage_thresholds": th,
        "equity_universe_total": eq,
        "mapped_symbols": int(mapped_symbols or 0),
        "daily_data_available": int(daily_data_available or 0),
        "scanner_eligible": int(scanner_eligible or 0),
        "note": (
            "Do not present market-wide conclusions when EXPLORER_COVERAGE=INSUFFICIENT"
            if not market_wide_confidence
            else "Coverage supports universe-level Explorer interpretation with stated bias risk"
        ),
    }
