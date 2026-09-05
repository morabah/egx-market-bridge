"""Immutable point-in-time signal snapshots. Never rewritten from later data."""
from __future__ import annotations

from typing import Any
import hashlib

from egxbridge.analysis.explorer.calibration import SCORING_VERSION, SCORE_KIND
from egxbridge.analysis.schedule.session import session_context
from egxbridge.analysis.schedule.types import ANALYSIS_EXPLORER, LAYER_LOCAL_SIGNAL
from egxbridge.analysis.schedule.identity import (
    resolve_signal_identity, persist_identity_for_snapshots, ORIGIN_EXPLORER,
)


def snapshot_id(
    *,
    environment: str,
    analysis_type: str,
    ticker: str,
    analysis_timestamp: str | None,
    data_cutoff: str | None,
    scoring_version: str = SCORING_VERSION,
) -> str:
    raw = "|".join([
        environment or "",
        analysis_type or "",
        str(ticker or "").upper(),
        analysis_timestamp or "",
        data_cutoff or "",
        scoring_version or SCORING_VERSION,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_signal_snapshot(
    candidate: dict[str, Any],
    *,
    run_id: str,
    environment: str,
    analysis_type: str = ANALYSIS_EXPLORER,
    generated_at: str,
    latest_session: str | None,
    session_meta: dict[str, Any] | None = None,
    price_basis: str = "OFFICIAL_CLOSE",
    explorer_run_id: str | None = None,
) -> dict[str, Any]:
    """LOCAL_SIGNAL layer. Outcomes and ChatGPT labels are not stored here."""
    sess = session_meta or session_context()
    m = candidate.get("metrics") or candidate
    struct = candidate.get("structure") or {}
    if not isinstance(struct, dict):
        struct = {}
    ticker = str(candidate.get("ticker") or "").upper()
    ts_utc = sess.get("analysis_timestamp_utc") or generated_at
    sid = snapshot_id(
        environment=environment,
        analysis_type=analysis_type,
        ticker=ticker,
        analysis_timestamp=ts_utc,
        data_cutoff=generated_at,
        scoring_version=SCORING_VERSION,
    )
    xr = explorer_run_id or candidate.get("explorer_run_id") or run_id
    ident = resolve_signal_identity(
        candidate,
        environment=environment,
        explorer_run_id=xr,
        latest_session=latest_session,
        analysis_type=analysis_type,
        session_meta=sess,
        price_basis=price_basis,
    )
    price = (
        candidate.get("price_at_snapshot")
        or candidate.get("last_close")
        or candidate.get("latest_close")
        or m.get("last_close")
        or m.get("latest_close")
    )
    return {
        "snapshot_id": sid,
        "canonical_signal_id": ident["canonical_signal_id"],
        "market_state_fingerprint": ident.get("market_state_fingerprint"),
        "signal_family_id": ident.get("signal_family_id"),
        "parent_signal_id": ident.get("parent_signal_id"),
        "signal_origin": ident.get("signal_origin") or ORIGIN_EXPLORER,
        "explorer_run_id": xr,
        "run_id": run_id,
        "ticker": ticker,
        "analysis_type": analysis_type,
        "layer": LAYER_LOCAL_SIGNAL,
        "scoring_version": SCORING_VERSION,
        "score_kind": SCORE_KIND,
        "not_a_probability": True,
        "package_generated_at": generated_at,
        "analysis_timestamp_utc": ts_utc,
        "analysis_timestamp_cairo": sess.get("analysis_timestamp_cairo"),
        "latest_completed_market_session": latest_session,
        "market_session_basis": ident.get("market_session_basis") or latest_session,
        "session_phase": sess.get("session_phase") or "UNKNOWN",
        "intraday_state_bucket": ident.get("intraday_state_bucket"),
        "target_next_working_day": "UNKNOWN",
        "price_at_snapshot": price,
        "price_observation_type": ident.get("price_observation_type") or price_basis,
        "price_timestamp": latest_session,
        "candidate_score_calibrated": candidate.get("candidate_score_calibrated") or candidate.get("candidate_score"),
        "candidate_score_legacy": candidate.get("candidate_score_legacy"),
        "forward_setup_score": candidate.get("forward_setup_score"),
        "FORWARD_SETUP_QUALITY": candidate.get("FORWARD_SETUP_QUALITY"),
        "MOVE_ALREADY_REALIZED": candidate.get("MOVE_ALREADY_REALIZED"),
        "candidate_lane": candidate.get("candidate_lane"),
        "candidate_families": candidate.get("candidate_families") or [],
        "calibrated_rank": candidate.get("calibrated_rank"),
        "VOLATILITY_RISK": candidate.get("VOLATILITY_RISK"),
        "TECHNICAL_HISTORY_INTEGRITY": candidate.get("TECHNICAL_HISTORY_INTEGRITY"),
        "RVOL20": candidate.get("RVOL20") or m.get("rvol_20"),
        "distance_20d_high": candidate.get("distance_20d_high") or m.get("dist_from_20d_high_pct"),
        "distance_60d_high": candidate.get("distance_60d_high") or m.get("dist_from_60d_high_pct"),
        "above_or_below_SMA20": candidate.get("above_or_below_SMA20") or struct.get("above_or_below_SMA20"),
        "above_or_below_SMA50": candidate.get("above_or_below_SMA50") or struct.get("above_or_below_SMA50"),
        "atr_14": candidate.get("atr_14") or m.get("atr_14"),
        "realized_vol_20d_ann_pct": candidate.get("realized_vol_20d_ann_pct") or m.get("realized_vol_20d_ann_pct"),
        "funnel_status": candidate.get("funnel_status"),
        "funnel_valuation_status": (candidate.get("funnel_context") or {}).get("Valuation Date")
        if isinstance(candidate.get("funnel_context"), dict) else None,
        "catalyst_status": None,
        "no_lookahead": True,
        "future_bars": None,
        "outcomes_reserved": {
            "next_session_return": None,
            "return_3_session": None,
            "return_5_session": None,
            "mfe": None,
            "mae": None,
        },
        "environment": environment,
    }


def persist_snapshots(store, snapshots: list[dict[str, Any]], *, analysis_type: str | None = None, schedule_run_id: str | None = None, persist_identity: bool = True) -> dict[str, Any]:
    inserted = 0
    ignored = 0
    ids = []
    for snap in snapshots:
        sid, new = store.insert_signal_snapshot(snap)
        ids.append(sid)
        if new:
            inserted += 1
        else:
            ignored += 1
            prior = store.get_signal_snapshot(sid)
            if prior and prior.get("payload"):
                # Immutability: first payload wins even if a later call differs.
                pass
    ident_stats = {}
    if persist_identity:
        ident_stats = persist_identity_for_snapshots(
            store, snapshots,
            analysis_type=analysis_type or ANALYSIS_EXPLORER,
            schedule_run_id=schedule_run_id,
        )
    return {
        "inserted": inserted,
        "ignored_duplicates": ignored,
        "snapshot_ids": ids,
        **ident_stats,
    }


def snapshots_have_no_future_bars(snapshot: dict[str, Any]) -> bool:
    payload = snapshot.get("payload") or snapshot
    if payload.get("future_bars"):
        return False
    reserved = payload.get("outcomes_reserved") or {}
    for k, v in reserved.items():
        if v is not None:
            return False
    for k in ("next_session_return", "return_3_sessions", "return_5_sessions"):
        if payload.get(k) not in (None,):
            return False
    return True
