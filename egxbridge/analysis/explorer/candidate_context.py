from __future__ import annotations

from typing import Any

from egxbridge.analysis.explorer.prescreen import normalize_scanner_metrics
from egxbridge.analysis.funnel.completion import sanitize_fair_value


def recommend_deep_analysis(funnel_status: str, *, high_interest: bool = False) -> str | None:
    """Explorer → Funnel request flags only. Does not modify Fair Value."""
    if funnel_status in {"PARTIAL", "REQUIRES_CONTINUATION"}:
        return "CONTINUE_FUNNEL"
    if funnel_status == "NOT_FOUND":
        return "NEEDS_FULL_FUNNEL"
    if funnel_status in {"NEEDS_DELTA", "STALE"}:
        return "NEEDS_FUNNEL_DELTA"
    if funnel_status == "NOT_RELIABLE":
        return "NEEDS_FULL_FUNNEL"
    if funnel_status == "CURRENT":
        return "NO_FUNNEL_ACTION"
    return "NO_FUNNEL_ACTION"


def build_candidate_row(
    ticker: str,
    metrics: dict[str, Any],
    funnel_ctx: dict[str, Any],
    *,
    selection_basis: str = "BROAD_UNIVERSE",
    selection_bias_risk: str = "MEDIUM",
    candidate_reasons: list[str] | None = None,
    candidate_families: list[str] | None = None,
    candidate_warnings: list[str] | None = None,
    data_status: str | None = None,
    candidate_score: float | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    m = normalize_scanner_metrics(metrics)
    status = funnel_ctx.get("funnel_status") or "NOT_FOUND"
    high = bool(m.get("available")) and (
        (m.get("rvol_20") or 0) >= 1.5 or (m.get("breakout_20d") is True)
        or bool(candidate_families)
    )
    rec = recommend_deep_analysis(status, high_interest=high)
    fv = sanitize_fair_value(funnel_ctx.get("Fair Value Range"))
    row = {
        "ticker": ticker.upper(),
        **{k: m.get(k) for k in (
            "last_close", "latest_close", "daily_return_pct", "return_1w_pct", "return_1m_pct",
            "return_3m_pct", "return_6m_pct", "rvol_20", "volume_sma_20", "volume_sma_60",
            "atr_14", "realized_vol_20d_ann_pct", "dist_from_20d_high_pct",
            "dist_from_60d_high_pct", "sma_20", "sma_50", "breakout_20d", "breakout_60d",
            "breakout_flag_20d", "breakout_flag_60d",
            "bars", "days_of_history", "latest_session", "available",
            "daily_provider", "daily_provider_note", "daily_bars_lagging", "expected_session",
        )},
        "daily_provider": m.get("daily_provider"),
        "daily_provider_note": m.get("daily_provider_note"),
        "session_date": m.get("latest_session") or m.get("session_date"),
        "data_status": data_status or ("DATA_AVAILABLE" if m.get("available") else "DATA_UNAVAILABLE"),
        "funnel_status": status,
        "funnel_completion_status": funnel_ctx.get("funnel_completion_status"),
        "delta_eligible": funnel_ctx.get("delta_eligible"),
        "funnel_context": {
            "structured_fields": funnel_ctx.get("structured_fields") or {},
            "structured_provenance": funnel_ctx.get("structured_provenance") or {},
            "funnel_version": funnel_ctx.get("funnel_version"),
            "decision_kind": funnel_ctx.get("decision_kind"),
            "Business Quality": funnel_ctx.get("Business Quality"),
            "Earnings Quality": funnel_ctx.get("Earnings Quality"),
            "Financial Strength": funnel_ctx.get("Financial Strength"),
            "Growth": funnel_ctx.get("Growth"),
            "Economic Valuation": funnel_ctx.get("Economic Valuation"),
            "Fair Value Range": fv,
            "Investment Classification": funnel_ctx.get("Investment Classification"),
            "Integrated Risk": funnel_ctx.get("Integrated Risk"),
            "Valuation Date": funnel_ctx.get("Valuation Date"),
            "Final Decision Domain": funnel_ctx.get("Final Decision Domain") or funnel_ctx.get("Final Decision"),
        },
        "fair_value_from_funnel_only": fv,
        "fair_value_manufactured": False,
        "recommended_deep_analysis": rec,
        "candidate_score": candidate_score,
        "candidate_families": candidate_families or [],
        "candidate_reasons": candidate_reasons or [],
        "candidate_warnings": candidate_warnings or [],
        "selection_basis": selection_basis,
        "selection_bias_risk": selection_bias_risk,
        "microstructure_claims": None,
        "microstructure_note": "No absorption/order-flow/Level-2 claims without depth/trades",
        "intraday_must_not_redefine_funnel": True,
        "orders_generated": False,
        "score_kind": "HEURISTIC_UNCALIBRATED",
        "not_a_probability": True,
        "fair_value_used_in_tactical_score": False,
        "daily_return": m.get("daily_return_pct"),
        "return_1w": m.get("return_1w_pct"),
        "return_1m": m.get("return_1m_pct"),
        "return_3m": m.get("return_3m_pct"),
        "return_6m": m.get("return_6m_pct"),
        "RVOL20": m.get("rvol_20"),
        "distance_20d_high": m.get("dist_from_20d_high_pct"),
        "distance_60d_high": m.get("dist_from_60d_high_pct"),
    }
    if extra:
        for k, v in extra.items():
            if k not in {"funnel_context", "candles", "metrics", "funnel_ctx"}:
                row[k] = v
    return row
