"""Descriptive calibration summaries. v0.6 collects evidence — no parameter search."""
from __future__ import annotations

from typing import Any
from collections import defaultdict

from egxbridge.analysis.schedule.types import CALIBRATION_STATUS, NEXT_SESSION_STATUS, FUNNEL_ACTION
from egxbridge.analysis.schedule.outcomes import TACTICAL_SUCCESS_THRESHOLD_PCT


NOT_EVALUABLE_STATUSES = {"NO_IMPORT", "PENDING_IMPORT", "INVALID_PARSE", "", "NONE", "NOT_RELIABLE"}
EVALUABLE_DECISIONS = set(NEXT_SESSION_STATUS) | {
    "CONFIRMED", "PARTIAL_CONFIRMATION", "FAILED", "REJECTED_BREAKOUT", "NO_TRADE",
    "EARLY_CONFIRMATION", "RECLAIM", "OVEREXTENDED",
} | set(FUNNEL_ACTION)


def _decision_fields(row: dict[str, Any]) -> list[str]:
    p = row.get("payload") or {}
    return [
        row.get("chatgpt_status") or p.get("chatgpt_status"),
        row.get("next_session_status") or p.get("next_session_status"),
        row.get("status") or p.get("status"),
        row.get("setup_state") or p.get("setup_state") or row.get("SETUP_STATE") or p.get("SETUP_STATE"),
        row.get("funnel_action") or p.get("funnel_action") or row.get("FUNNEL_ACTION") or p.get("FUNNEL_ACTION"),
    ]


def is_evaluable_observation(row: dict[str, Any]) -> bool:
    """Imported ChatGPT observation with a decision-bearing structured status."""
    if (row.get("generated_by") or "") != "CHATGPT_HANDOFF" and (row.get("import_status") or "") != "IMPORTED":
        if (row.get("generated_by") or "") == "LOCAL":
            return False
        if (row.get("import_status") or "GENERATED") == "GENERATED":
            return False
    method = row.get("linkage_method") or (row.get("payload") or {}).get("linkage_method")
    if method in {"AMBIGUOUS_REJECTED", "INVALID_ID", "NOT_LINKED"}:
        return False
    if not row.get("canonical_signal_id"):
        return False
    values = [str(v or "").strip().upper() for v in _decision_fields(row)]
    if any(v in NOT_EVALUABLE_STATUSES for v in values if v):
        # A row may mix NEUTRAL catalyst with PROMOTE status; only reject if ALL
        # decision fields are non-evaluable placeholders.
        pass
    if any(v in EVALUABLE_DECISIONS for v in values):
        return True
    return False


def observation_counts(observations: list[dict[str, Any]]) -> dict[str, Any]:
    generated = [
        o for o in observations
        if (o.get("generated_by") or "LOCAL") in {"LOCAL", "LEGACY_SNAPSHOT"}
    ]
    imported = [
        o for o in observations
        if (o.get("generated_by") or "") == "CHATGPT_HANDOFF"
    ]
    evaluable = [o for o in imported if is_evaluable_observation(o)]
    return {
        "analysis_observations_generated_n": len(generated),
        "analysis_observations_imported_n": len(imported),
        "analysis_observations_evaluable_n": len(evaluable),
        "analysis_observations_n": len(generated),
        "analysis_observations_n_semantics": "DEPRECATED_ALIAS_OF_GENERATED",
        "note": (
            "generated = schedule/job looks; imported = ChatGPT results; "
            "evaluable = imported with a decision-bearing status. "
            "Do not use generated_n as ChatGPT value-add n or as scanner n."
        ),
        "evaluable_ids": [o.get("analysis_observation_id") for o in evaluable],
    }


def calibration_status_for_n(n: int) -> str:
    if n < 10:
        return "INSUFFICIENT_SAMPLE"
    if n < 30:
        return "EARLY_SAMPLE"
    if n < 80:
        return "DEVELOPING"
    return "USABLE"


def _mean(xs: list[float]) -> float | None:
    if not xs:
        return None
    return round(sum(xs) / len(xs), 4)


def _median(xs: list[float]) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2:
        return round(s[mid], 4)
    return round((s[mid - 1] + s[mid]) / 2.0, 4)


def summarize_outcomes(rows: list[dict[str, Any]], *, grouping: str = "all", unit: str = "canonical_signal_id") -> dict[str, Any]:
    rets_1 = [float(r["next_session_return"]) for r in rows if r.get("next_session_return") is not None]
    rets_3 = [float(r["return_3_sessions"]) for r in rows if r.get("return_3_sessions") is not None]
    rets_5 = [float(r["return_5_sessions"]) for r in rows if r.get("return_5_sessions") is not None]
    mfe = [float(r["mfe_3"]) for r in rows if r.get("mfe_3") is not None]
    mae = [float(r["mae_3"]) for r in rows if r.get("mae_3") is not None]
    n = len(rows)
    status = calibration_status_for_n(len(rets_1))
    if status not in CALIBRATION_STATUS:
        status = "NOT_RELIABLE"
    hit_1 = [x > 0 for x in rets_1]
    tac_1 = [x >= TACTICAL_SUCCESS_THRESHOLD_PCT for x in rets_1]
    return {
        "grouping": grouping,
        "n": n,
        "unit_of_observation": unit,
        "n_with_1_session_outcome": len(rets_1),
        "n_with_3_session_outcome": len(rets_3),
        "n_with_5_session_outcome": len(rets_5),
        "CALIBRATION_STATUS": status,
        "mean_return_1": _mean(rets_1),
        "median_return_1": _median(rets_1),
        "mean_return_3": _mean(rets_3),
        "median_return_3": _median(rets_3),
        "mean_return_5": _mean(rets_5),
        "hit_rate_positive_close_1": _mean([1.0 if h else 0.0 for h in hit_1]) if hit_1 else None,
        "hit_rate_tactical_success_1": _mean([1.0 if h else 0.0 for h in tac_1]) if tac_1 else None,
        "positive_close_definition": "future return > 0",
        "tactical_success_definition": f"future return >= {TACTICAL_SUCCESS_THRESHOLD_PCT}%",
        "best_mfe_3": max(mfe) if mfe else None,
        "worst_mae_3": min(mae) if mae else None,
        "do_not_claim_economic_significance": True,
        "no_parameter_optimization": True,
        "scoring_version_frozen": "0.5.1",
    }


def group_summaries(joined: list[dict[str, Any]]) -> dict[str, Any]:
    """joined rows contain both snapshot payload fields and outcome fields."""
    groups = {
        "FORWARD_SETUP_QUALITY": defaultdict(list),
        "MOVE_ALREADY_REALIZED": defaultdict(list),
        "candidate_lane": defaultdict(list),
        "VOLATILITY_RISK": defaultdict(list),
        "TECHNICAL_HISTORY_INTEGRITY": defaultdict(list),
    }
    for row in joined:
        p = row.get("payload") or row
        for key in groups:
            groups[key][str(p.get(key) or row.get(key) or "UNKNOWN")].append(row)
    out = {"all": summarize_outcomes(joined, grouping="all")}
    for key, buckets in groups.items():
        out[key] = {
            k: summarize_outcomes(v, grouping=f"{key}={k}")
            for k, v in buckets.items()
        }
    return out


def false_positive_cases(joined: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases = []
    for row in joined:
        p = row.get("payload") or row
        r3 = row.get("return_3_sessions")
        if p.get("FORWARD_SETUP_QUALITY") == "STRONG" and r3 is not None and float(r3) < 0:
            cases.append({
                "ticker": p.get("ticker") or row.get("ticker"),
                "kind": "STRONG_FORWARD_NEGATIVE_3S",
                "return_3_sessions": r3,
                "note": "Calibration example — not automatic proof the algorithm is wrong",
            })
        if row.get("chatgpt_status") == "PROMOTE" and row.get("setup_state") in {"FAILED", "REJECTED_BREAKOUT"}:
            cases.append({
                "ticker": p.get("ticker") or row.get("ticker"),
                "kind": "PROMOTED_THEN_INTRADAY_FAILED",
                "note": "Calibration example",
            })
    return cases


def scanner_performance(canonical_joined: list[dict[str, Any]]) -> dict[str, Any]:
    """Unit = canonical_signal_id. Do not pass analysis observations here."""
    summary = summarize_outcomes(canonical_joined, grouping="scanner", unit="canonical_signal_id")
    summary["evaluation"] = "SCANNER_PERFORMANCE"
    summary["canonical_signals_n"] = len(canonical_joined)
    summary["do_not_use_analysis_observations_as_n"] = True
    return summary


def analysis_value_add(observation_joined: list[dict[str, Any]]) -> dict[str, Any]:
    """Unit = canonical_signal_id + evaluable analysis observation (e.g. PROMOTE vs DOWNGRADE)."""
    counts = observation_counts(observation_joined)
    evaluable = [o for o in observation_joined if is_evaluable_observation(o)]
    by_status: dict[str, list] = {}
    for row in evaluable:
        st = str(
            row.get("chatgpt_status")
            or row.get("next_session_status")
            or row.get("setup_state")
            or row.get("funnel_action")
            or "UNKNOWN"
        )
        by_status.setdefault(st, []).append(row)
    out = {
        "evaluation": "ANALYSIS_VALUE_ADD",
        "unit_of_observation": "canonical_signal_id + analysis_observation",
        "analysis_observations_n": counts["analysis_observations_generated_n"],
        "analysis_observations_n_semantics": "DEPRECATED_ALIAS_OF_GENERATED",
        "analysis_observations_generated_n": counts["analysis_observations_generated_n"],
        "analysis_observations_imported_n": counts["analysis_observations_imported_n"],
        "analysis_observations_evaluable_n": counts["analysis_observations_evaluable_n"],
        "sample_n": counts["analysis_observations_evaluable_n"],
        "note": "Value-add n = analysis_observations_evaluable_n. Generated handoffs are not ChatGPT decisions.",
        "by_chatgpt_status": {
            k: summarize_outcomes(v, grouping=f"chatgpt_status={k}", unit="canonical_signal_id + analysis_observation")
            for k, v in by_status.items()
        },
        "do_not_combine_with_scanner_performance": True,
        "do_not_count_generated_as_chatgpt": True,
    }
    return out
