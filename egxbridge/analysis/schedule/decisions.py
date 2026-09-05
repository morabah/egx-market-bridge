"""Unified daily decision record after imported analyses. Never emits BUY."""
from __future__ import annotations

from typing import Any
from pathlib import Path
import json

from egxbridge.analysis.common.packaging import write_json
from egxbridge.analysis.schedule.types import SCORING_VERSION


HERE = Path(__file__).resolve().parents[3]


def suggested_funnel_action(funnel_status: str | None) -> str:
    st = funnel_status or "NOT_FOUND"
    if st in {"PARTIAL", "REQUIRES_CONTINUATION"}:
        return "CONTINUE_FUNNEL"
    if st == "NOT_FOUND":
        return "START_FULL_FUNNEL"
    if st in {"NEEDS_DELTA", "STALE"}:
        return "RUN_DELTA"
    if st == "CURRENT":
        return "NO_ACTION"
    return "REVIEW_EXISTING_FUNNEL"


def build_daily_decision(
    *,
    run_id: str,
    latest_session: str | None,
    market_regime: str | None,
    portfolio_posture: str | None,
    candidates: list[dict[str, Any]],
    imports_by_type: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = []
    for c in candidates:
        env = ((imports_by_type or {}).get("PREMARKET_CATALYSTS") or {}).get("by_ticker") or {}
        intra = ((imports_by_type or {}).get("INTRADAY_OPPORTUNITY") or {}).get("by_ticker") or {}
        val = ((imports_by_type or {}).get("VALUE_QUALITY") or {}).get("by_ticker") or {}
        t = c.get("ticker")
        pre = env.get(t) or {}
        intra_row = intra.get(t) or {}
        val_row = val.get(t) or {}
        rows.append({
            "ticker": t,
            "explorer_rank": c.get("calibrated_rank"),
            "lane": c.get("candidate_lane"),
            "FORWARD_SETUP_QUALITY": c.get("FORWARD_SETUP_QUALITY"),
            "MOVE_ALREADY_REALIZED": c.get("MOVE_ALREADY_REALIZED"),
            "premarket_status": pre.get("status") or pre.get("next_session_status"),
            "catalyst_status": pre.get("catalyst_status"),
            "intraday_setup_state": intra_row.get("SETUP_STATE") or intra_row.get("setup_state"),
            "funnel_action": val_row.get("FUNNEL_ACTION") or suggested_funnel_action(c.get("funnel_status")),
            "funnel_action_source": "CHATGPT" if val_row.get("FUNNEL_ACTION") else "BRIDGE_HEURISTIC_CONTEXT",
        "FINAL_TACTICAL_STATUS": None,  # ChatGPT / user; never auto BUY
        "BUY_not_emitted": True,
        })
    rec = {
        "run_id": run_id,
        "latest_completed_market_session": latest_session,
        "target_next_working_day": "UNKNOWN",
        "market_regime": market_regime or "NOT_RELIABLE",
        "portfolio_posture": portfolio_posture or "NOT_RELIABLE",
        "candidates": rows,
        "scoring_version": SCORING_VERSION,
        "orders_generated": False,
        "no_automatic_buy": True,
    }
    return rec


def persist_daily_decision(
    store,
    rec: dict[str, Any],
    *,
    date_tag: str,
    dest_dir: Path | None = None,
    write_workspace_file: bool = True,
) -> Path | None:
    path = None
    if write_workspace_file:
        dest = Path(dest_dir) if dest_dir else HERE / "output" / "daily_decision"
        dest.mkdir(parents=True, exist_ok=True)
        path = dest / f"{date_tag}.json"
        write_json(path, rec)
    if store:
        store.upsert_daily_decision(date_tag, rec.get("run_id") or "", rec)
    return path


def imports_by_type_from_store(store) -> dict[str, Any]:
    from egxbridge.analysis.schedule.types import ANALYSIS_TYPES
    out: dict[str, Any] = {}
    if store is None:
        return out
    for at in ANALYSIS_TYPES:
        imp = store.latest_schedule_import(at)
        env = (imp or {}).get("envelope") or {}
        by_ticker = {}
        for c in env.get("candidates") or []:
            if isinstance(c, dict) and c.get("ticker"):
                by_ticker[str(c["ticker"]).upper()] = c
                by_ticker[c["ticker"]] = c
        out[at] = {
            "envelope": env,
            "by_ticker": by_ticker,
            "imported_at": (imp or {}).get("imported_at"),
        }
    return out


def refresh_daily_decision_from_store(store, *, date_tag: str, run_id: str, latest_session: str | None, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = imports_by_type_from_store(store)
    macro = ((grouped.get("MACRO_HOLDINGS") or {}).get("envelope") or {})
    rec = build_daily_decision(
        run_id=run_id,
        latest_session=latest_session,
        market_regime=macro.get("MARKET_REGIME") or macro.get("market_regime"),
        portfolio_posture=macro.get("PORTFOLIO_POSTURE") or macro.get("portfolio_posture"),
        candidates=candidates,
        imports_by_type=grouped,
    )
    persist_daily_decision(
        store, rec, date_tag=date_tag,
        write_workspace_file=getattr(store, "environment", "") == "PRODUCTION",
    )
    return rec
