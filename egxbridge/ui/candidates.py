"""Candidate table mapping for Daily Operator / Explorer Candidates. No scoring."""
from __future__ import annotations

from typing import Any


SOURCE_LOCAL_DATA = "LOCAL DATA"
SOURCE_LOCAL_HEURISTIC = "LOCAL HEURISTIC"
SOURCE_CHATGPT = "CHATGPT ANALYSIS"
SOURCE_FUNNEL = "FUNNEL RESULT"
SOURCE_USER = "USER ACTION"
SOURCE_OUTCOME = "ACTUAL OUTCOME"


def _num(value: Any):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        return value


def candidate_preview_rows(candidates: list[dict[str, Any]], *, limit: int | None = None, sort_by_rank: bool = True) -> list[dict[str, Any]]:
    rows = []
    for c in candidates or []:
        m = c.get("metrics") if isinstance(c.get("metrics"), dict) else {}
        sess = (
            c.get("latest_session")
            or c.get("session_date")
            or m.get("latest_session")
            or m.get("session_date")
            or ""
        )
        intra = c.get("intraday") if isinstance(c.get("intraday"), dict) else {}
        today_px = _num(
            intra.get("current_session_price")
            or (intra.get("last_price") if intra.get("current_session") else None)
        )
        rows.append({
            "Rank": c.get("calibrated_rank") or c.get("legacy_rank"),
            "Ticker": c.get("ticker"),
            "Session close": _num(c.get("last_close") or c.get("latest_close") or m.get("last_close")),
            "Session": str(sess)[:10] if sess else None,
            "Today": today_px,
            "Price source": c.get("daily_provider") or m.get("daily_provider") or None,
            "Forward Setup": c.get("FORWARD_SETUP_QUALITY"),
            "Move Already Realized": c.get("MOVE_ALREADY_REALIZED"),
            "Lane": c.get("candidate_lane"),
            "RVOL20": _num(c.get("RVOL20") or c.get("rvol_20") or m.get("rvol_20")),
            "Distance 20D High": _num(
                c.get("distance_20d_high") or c.get("dist_from_20d_high_pct") or m.get("dist_from_20d_high_pct")
            ),
            "Volatility Risk": c.get("VOLATILITY_RISK"),
            "Funnel Status": c.get("funnel_status"),
            "Intraday Available": bool(c.get("intraday_available") or intra.get("intraday_available")),
            "Candidate Score": _num(c.get("candidate_score_calibrated") or c.get("candidate_score")),
        })
    if sort_by_rank:
        rows.sort(key=lambda r: (r["Rank"] is None, r["Rank"] if r["Rank"] is not None else 10**9))
    if limit is not None:
        rows = rows[:limit]
    return rows


def candidate_detail(c: dict[str, Any]) -> dict[str, Any]:
    m = c.get("metrics") if isinstance(c.get("metrics"), dict) else {}
    struct = c.get("structure") if isinstance(c.get("structure"), dict) else {}
    return {
        "1D": _num(c.get("daily_return_pct") or c.get("daily_return") or m.get("daily_return_pct")),
        "1W": _num(c.get("return_1w_pct") or c.get("return_1w") or m.get("return_1w_pct")),
        "1M": _num(c.get("return_1m_pct") or c.get("return_1m") or m.get("return_1m_pct")),
        "3M": _num(c.get("return_3m_pct") or c.get("return_3m") or m.get("return_3m_pct")),
        "6M": _num(c.get("return_6m_pct") or c.get("return_6m") or m.get("return_6m_pct")),
        "RVOL20": _num(c.get("RVOL20") or c.get("rvol_20") or m.get("rvol_20")),
        "SMA20": struct.get("above_or_below_SMA20") or c.get("above_or_below_SMA20"),
        "SMA50": struct.get("above_or_below_SMA50") or c.get("above_or_below_SMA50"),
        "Distance 20D High": _num(c.get("distance_20d_high") or c.get("dist_from_20d_high_pct") or m.get("dist_from_20d_high_pct")),
        "Distance 60D High": _num(c.get("distance_60d_high") or c.get("dist_from_60d_high_pct") or m.get("dist_from_60d_high_pct")),
        "Breakout 20D": c.get("breakout_20d") if c.get("breakout_20d") is not None else m.get("breakout_20d"),
        "Breakout 60D": c.get("breakout_60d") if c.get("breakout_60d") is not None else m.get("breakout_60d"),
        "History integrity": c.get("TECHNICAL_HISTORY_INTEGRITY"),
        "Funnel status": c.get("funnel_status"),
        "Intraday available": bool(c.get("intraday_available")),
    }


def candidate_audit(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_signal_id": c.get("canonical_signal_id"),
        "market_state_fingerprint": c.get("market_state_fingerprint"),
        "explorer_run_id": c.get("explorer_run_id"),
        "signal_family_id": c.get("signal_family_id"),
        "scoring_version": c.get("scoring_version"),
        "score_kind": c.get("score_kind"),
        "calibrated_rank": c.get("calibrated_rank"),
        "legacy_rank": c.get("legacy_rank"),
        "candidate_score_calibrated": c.get("candidate_score_calibrated"),
        "not_a_probability": True,
    }


def unique_values(candidates: list[dict[str, Any]], key: str) -> list[str]:
    out = []
    for c in candidates or []:
        v = c.get(key)
        if v is None or v == "":
            continue
        s = str(v)
        if s not in out:
            out.append(s)
    return sorted(out)


def filter_candidates(
    candidates: list[dict[str, Any]],
    *,
    lane: str | None = None,
    setup: str | None = None,
    realized: str | None = None,
    vol: str | None = None,
    funnel: str | None = None,
    intraday: str | None = None,
) -> list[dict[str, Any]]:
    rows = list(candidates or [])

    def keep(c: dict[str, Any]) -> bool:
        if lane and lane != "(all)" and str(c.get("candidate_lane") or "") != lane:
            return False
        if setup and setup != "(all)" and str(c.get("FORWARD_SETUP_QUALITY") or "") != setup:
            return False
        if realized and realized != "(all)" and str(c.get("MOVE_ALREADY_REALIZED") or "") != realized:
            return False
        if vol and vol != "(all)" and str(c.get("VOLATILITY_RISK") or "") != vol:
            return False
        if funnel and funnel != "(all)" and str(c.get("funnel_status") or "") != funnel:
            return False
        if intraday == "Yes" and not c.get("intraday_available"):
            return False
        if intraday == "No" and c.get("intraday_available"):
            return False
        return True

    return [c for c in rows if keep(c)]


def sort_candidates(candidates: list[dict[str, Any]], sort_by: str, descending: bool = False) -> list[dict[str, Any]]:
    key_map = {
        "Rank": lambda c: c.get("calibrated_rank") if c.get("calibrated_rank") is not None else 10**9,
        "Ticker": lambda c: str(c.get("ticker") or ""),
        "Candidate Score": lambda c: c.get("candidate_score_calibrated") or c.get("candidate_score") or 0,
        "RVOL20": lambda c: c.get("RVOL20") or c.get("rvol_20") or 0,
        "Forward Setup": lambda c: str(c.get("FORWARD_SETUP_QUALITY") or ""),
        "Lane": lambda c: str(c.get("candidate_lane") or ""),
    }
    fn = key_map.get(sort_by) or key_map["Rank"]
    return sorted(candidates, key=fn, reverse=descending)


def chatgpt_status_by_ticker(imports: dict[str, Any] | None, job: str) -> dict[str, str]:
    env = ((imports or {}).get(job) or {}).get("envelope") or {}
    out = {}
    for c in env.get("candidates") or []:
        if isinstance(c, dict) and c.get("ticker"):
            st = c.get("status") or c.get("next_session_status") or c.get("SETUP_STATE") or c.get("setup_state")
            if st:
                out[str(c["ticker"]).upper()] = str(st)
    return out


def intraday_panel_rows(
    candidates: list[dict[str, Any]],
    *,
    imports: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    intra_status = chatgpt_status_by_ticker(imports, "INTRADAY_OPPORTUNITY")
    pre_status = chatgpt_status_by_ticker(imports, "PREMARKET_CATALYSTS")
    rows = []
    for c in candidates or []:
        if not (c.get("intraday_available") or c.get("intraday_selection_reason") or c.get("intraday")):
            continue
        intra = c.get("intraday") if isinstance(c.get("intraday"), dict) else {}
        t = str(c.get("ticker") or "").upper()
        rows.append({
            "Ticker": t,
            "Current/Latest Price": (
                intra.get("current_session_price")
                or intra.get("last_price")
                or c.get("last_close")
                or c.get("latest_close")
            ),
            "Intraday session": intra.get("session_date"),
            "Latest Candle Time": (
                intra.get("normalized_cairo_timestamp")
                or intra.get("captured_at")
                or intra.get("queried_at")
                or intra.get("timestamp")
            ),
            "Freshness": intra.get("freshness"),
            "Forward Setup": c.get("FORWARD_SETUP_QUALITY"),
            "Lane": c.get("candidate_lane"),
            "RVOL": c.get("RVOL20") or c.get("rvol_20"),
            "Breakout State": c.get("breakout_20d"),
            "Pre-Market Status": pre_status.get(t) or "NOT IMPORTED",
            "Intraday ChatGPT Status": intra_status.get(t) or "NOT IMPORTED",
        })
    return rows
