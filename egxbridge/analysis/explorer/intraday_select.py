"""Intraday enrichment selection — lane representation, not score retuning.

Does not modify candidate_score_calibrated. Weak names are not selected
merely to fill a lane quota; unused slots flow to stronger remaining names.
"""
from __future__ import annotations

from typing import Any


LANE_A = "LANE_A_EARLY_PRE_IGNITION"
LANE_B = "LANE_B_CONTINUATION"
LANE_C = "LANE_C_CORRECTION_REVERSAL"
LANE_D = "LANE_D_HIGH_RISK_EXTENDED"
LANE_E = "LANE_E_FUNNEL_FOLLOW_UP"

DEFAULT_INTRADAY_LANE_SLOTS = {
    LANE_A: 8,
    LANE_B: 2,
    LANE_C: 4,
    LANE_D: 1,
}

WEAK_QUALITY = {"WEAK", "NOT_RELIABLE"}

INTRADAY_LANES = (LANE_A, LANE_B, LANE_C, LANE_D)


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def _lane(item: dict[str, Any]) -> str:
    lane = item.get("candidate_lane") or LANE_D
    if lane == LANE_E:
        return LANE_D
    if lane not in INTRADAY_LANES:
        return LANE_D
    return lane


def quality_ok(item: dict[str, Any]) -> bool:
    q = item.get("FORWARD_SETUP_QUALITY")
    if q in WEAK_QUALITY:
        return False
    return True


def scale_lane_slots(limit: int, base: dict[str, int] | None = None) -> dict[str, int]:
    """Largest-remainder allocation so quotas sum to `limit`."""
    base = dict(base or DEFAULT_INTRADAY_LANE_SLOTS)
    total = sum(max(0, int(v)) for v in base.values()) or 15
    limit = max(0, int(limit))
    if limit == 0:
        return {k: 0 for k in INTRADAY_LANES}
    raw = []
    for lane in INTRADAY_LANES:
        share = limit * max(0, int(base.get(lane) or 0)) / total
        whole = int(share)
        raw.append((lane, whole, share - whole))
    assigned = sum(w for _, w, _ in raw)
    remain = limit - assigned
    raw.sort(key=lambda t: t[2], reverse=True)
    slots = {lane: whole for lane, whole, _ in raw}
    for i in range(remain):
        slots[raw[i % len(raw)][0]] += 1
    return {lane: int(slots.get(lane) or 0) for lane in INTRADAY_LANES}


def select_intraday_enrichment(
    rows: list[dict[str, Any]],
    limit: int,
    *,
    lane_slots: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Return selection records with reasons. Ranking scores are not changed."""
    limit = max(0, int(limit))
    if limit <= 0 or not rows:
        return []
    slots = scale_lane_slots(limit, lane_slots)
    ranked = sorted(rows, key=lambda x: _f(x.get("candidate_score_calibrated")), reverse=True)
    by_lane: dict[str, list[dict[str, Any]]] = {k: [] for k in INTRADAY_LANES}
    for item in ranked:
        by_lane[_lane(item)].append(item)

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    within: dict[str, int] = {k: 0 for k in INTRADAY_LANES}

    def _add(item: dict[str, Any], reason: str, lane: str) -> None:
        t = item.get("ticker")
        if not t or t in seen:
            return
        within[lane] = within.get(lane, 0) + 1
        selected.append({
            "ticker": t,
            "candidate_lane": lane,
            "intraday_selection_lane": lane,
            "intraday_selection_rank_within_lane": within[lane],
            "intraday_selection_reason": reason,
            "FORWARD_SETUP_QUALITY": item.get("FORWARD_SETUP_QUALITY"),
            "candidate_score_calibrated": item.get("candidate_score_calibrated"),
            "quality_ok": quality_ok(item),
        })
        seen.add(t)

    for lane in INTRADAY_LANES:
        n = int(slots.get(lane) or 0)
        taken = 0
        for item in by_lane.get(lane) or []:
            if taken >= n or len(selected) >= limit:
                break
            if not quality_ok(item):
                continue
            _add(item, f"lane_quota:{lane}", lane)
            taken += 1
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for item in ranked:
            if len(selected) >= limit:
                break
            t = item.get("ticker")
            if t in seen:
                continue
            if not quality_ok(item):
                continue
            lane = _lane(item)
            _add(item, "leftover_flow:strongest_remaining", lane)

    return selected[:limit]


def select_intraday_tickers_diversified(
    rows: list[dict[str, Any]],
    limit: int,
    *,
    lane_slots: dict[str, int] | None = None,
) -> list[str]:
    return [r["ticker"] for r in select_intraday_enrichment(rows, limit, lane_slots=lane_slots)]


def lane_slots_from_run(config: Any | None) -> dict[str, int]:
    if config is None:
        return dict(DEFAULT_INTRADAY_LANE_SLOTS)
    return {
        LANE_A: int(getattr(config, "intraday_lane_a_slots", 8) or 8),
        LANE_B: int(getattr(config, "intraday_lane_b_slots", 2) or 2),
        LANE_C: int(getattr(config, "intraday_lane_c_slots", 4) or 4),
        LANE_D: int(getattr(config, "intraday_lane_d_slots", 1) or 1),
    }
