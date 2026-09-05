"""Stage A — deterministic broad-universe pre-screen (no financial conclusions)."""
from __future__ import annotations

from typing import Any


def normalize_scanner_metrics(metrics: dict[str, Any] | None) -> dict[str, Any]:
    """Map scanner field names used by Explorer candidates; preserve False."""
    m = dict(metrics or {})
    if "breakout_20d" not in m and "breakout_flag_20d" in m:
        m["breakout_20d"] = m["breakout_flag_20d"]
    if "breakout_60d" not in m and "breakout_flag_60d" in m:
        m["breakout_60d"] = m["breakout_flag_60d"]
    # Keep flag aliases too
    if "breakout_flag_20d" not in m and "breakout_20d" in m:
        m["breakout_flag_20d"] = m["breakout_20d"]
    if "breakout_flag_60d" not in m and "breakout_60d" in m:
        m["breakout_flag_60d"] = m["breakout_60d"]
    if "latest_close" not in m and m.get("last_close") is not None:
        m["latest_close"] = m["last_close"]
    if "last_close" not in m and m.get("latest_close") is not None:
        m["last_close"] = m["latest_close"]
    return m


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def candidate_reasons(metrics: dict[str, Any]) -> list[str]:
    """Transparent quantitative reasons — not BUY recommendations."""
    m = normalize_scanner_metrics(metrics)
    reasons: list[str] = []
    rvol = _f(m.get("rvol_20"))
    if rvol >= 1.5:
        reasons.append(f"relative_volume_rvol20={rvol:.2f}")
    d20 = m.get("dist_from_20d_high_pct")
    d60 = m.get("dist_from_60d_high_pct")
    if d20 is not None and _f(d20) >= -3:
        reasons.append(f"proximity_20d_high={_f(d20):.2f}%")
    if d60 is not None and _f(d60) >= -5:
        reasons.append(f"proximity_60d_high={_f(d60):.2f}%")
    for key, label in (
        ("daily_return_pct", "return_1d"),
        ("return_1w_pct", "return_1w"),
        ("return_1m_pct", "return_1m"),
        ("return_3m_pct", "return_3m"),
        ("return_6m_pct", "return_6m"),
    ):
        if m.get(key) is not None:
            reasons.append(f"{label}={_f(m.get(key)):.2f}%")
    sma20, sma50, last = m.get("sma_20"), m.get("sma_50"), m.get("last_close")
    if sma20 is not None and last is not None:
        reasons.append("trend_vs_sma20=" + ("above" if _f(last) >= _f(sma20) else "below"))
    if sma50 is not None and last is not None:
        reasons.append("trend_vs_sma50=" + ("above" if _f(last) >= _f(sma50) else "below"))
    if m.get("realized_vol_20d_ann_pct") is not None:
        reasons.append(f"volatility_20d_ann={_f(m.get('realized_vol_20d_ann_pct')):.1f}%")
    if m.get("breakout_20d") is True:
        reasons.append("breakout_state_20d=True")
    elif m.get("breakout_20d") is False:
        reasons.append("breakout_state_20d=False")
    if m.get("breakout_60d") is True:
        reasons.append("breakout_state_60d=True")
    elif m.get("breakout_60d") is False:
        reasons.append("breakout_state_60d=False")
    # Correction / reversal structure (distance from highs without requiring gainer)
    if d20 is not None and -15 <= _f(d20) <= -3:
        reasons.append("clean_correction_structure_20d")
    if d20 is not None and _f(d20) < -15 and _f(m.get("return_1w_pct")) > 0:
        reasons.append("early_reversal_structure")
    rvol = _f(m.get("rvol_20"))
    if rvol >= 1.5:
        reasons.append(f"RVOL20 = {rvol:.2f}x")
    if d20 is not None and abs(_f(d20)) <= 1.0:
        reasons.append(f"within {abs(_f(d20)):.2f}% of 20D high")
    if m.get("breakout_20d") is True:
        reasons.append("20D breakout true")
    if not reasons:
        reasons.append("baseline_coverage")
    return reasons


def candidate_warnings(metrics: dict[str, Any]) -> list[str]:
    m = normalize_scanner_metrics(metrics)
    warnings: list[str] = []
    if m.get("available") is False:
        warnings.append("metrics_unavailable")
    bars = m.get("days_of_history") or m.get("bars")
    if bars is not None and _f(bars) < 50:
        warnings.append(f"sma50_history_limited_bars={int(_f(bars))}")
    if m.get("sma_50") is None:
        warnings.append("sma_50_unavailable")
    if m.get("return_6m_pct") is None:
        warnings.append("return_6m_unavailable")
    if m.get("breakout_20d") is False and m.get("daily_return_pct") is not None and _f(m.get("daily_return_pct")) > 8:
        warnings.append("sharp_daily_move_without_20d_breakout")
    vol = m.get("realized_vol_20d_ann_pct")
    if vol is not None and _f(vol) >= 80:
        warnings.append(f"volatility_elevated_{_f(vol):.0f}pct_ann")
    if not warnings:
        warnings.append("none")
    return warnings


def classify_candidate_families(
    metrics: dict[str, Any],
    *,
    watchlist: bool = False,
    **kwargs,
) -> list[str]:
    """Delegate to v0.5.1 tightened family rules (lazy import — avoid cycle)."""
    from egxbridge.analysis.explorer.calibration import classify_candidate_families as _classify
    return _classify(metrics, watchlist=watchlist, **kwargs)


def score_candidates(
    rows: list[dict[str, Any]],
    *,
    watchlist: list[str] | None = None,
    cfg=None,
    cross_section_vols: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Calibrate every available scanner row. Does not shortlist."""
    from egxbridge.analysis.explorer.calibration import calibrate_candidate, CalibrationConfig
    wl = {s.upper() for s in (watchlist or [])}
    cfg = cfg or CalibrationConfig()
    vols = cross_section_vols
    if vols is None:
        vols = []
        for r in rows:
            m = normalize_scanner_metrics(r.get("metrics") or r)
            if m.get("realized_vol_20d_ann_pct") is not None:
                vols.append(float(m["realized_vol_20d_ann_pct"]))
    scored = []
    export_keys = (
        "MOVE_ALREADY_REALIZED", "FORWARD_SETUP_QUALITY", "forward_setup_score",
        "forward_setup_components", "TECHNICAL_HISTORY_INTEGRITY", "VOLATILITY_RISK",
        "move_realized_reasons", "structure", "rvol_context", "score_kind",
        "not_a_probability", "history_integrity", "volatility_detail",
        "do_not_chase_price", "do_not_chase_note", "extension_context",
        "move_realized_detail", "fair_value_used_in_tactical_score",
        "candidate_score_calibrated", "breakdown",
    )
    for r in rows:
        m = normalize_scanner_metrics(r.get("metrics") or r)
        if not m.get("available"):
            continue
        ticker = str(r.get("ticker") or "").upper()
        legacy = prescreen_score(m)
        cal = calibrate_candidate(
            m,
            candles=r.get("candles"),
            funnel_ctx=r.get("funnel_ctx"),
            watchlist=ticker in wl,
            cross_section_vols=vols,
            cfg=cfg,
            legacy_score=legacy,
        )
        item = {k: v for k, v in r.items() if k != "candles"}
        item["ticker"] = ticker
        item["metrics"] = m
        item["prescreen_score"] = legacy
        item["candidate_score_legacy"] = legacy
        item["candidate_score_calibrated"] = cal["candidate_score_calibrated"]
        item["candidate_score"] = cal["candidate_score_calibrated"]
        item["candidate_families"] = cal["candidate_families"]
        item["candidate_lane"] = cal["candidate_lane"]
        item["candidate_reasons"] = candidate_reasons(m)
        warns = list(candidate_warnings(m)) + list(cal.get("calibration_warnings") or [])
        item["candidate_warnings"] = [w for w in warns if w and w != "none"] or ["none"]
        item["breakout_20d"] = m.get("breakout_20d")
        item["breakout_60d"] = m.get("breakout_60d")
        for k in export_keys:
            if k in cal:
                item[k] = cal[k]
        scored.append(item)
    return scored


def select_handoff_candidates(
    rows: list[dict[str, Any]],
    *,
    max_handoff: int = 30,
    watchlist: list[str] | None = None,
    cfg=None,
    cross_section_vols: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Stage A shortlist. Production rank = calibrated forward-setup score."""
    from egxbridge.analysis.explorer.calibration import diversify_by_lane, CalibrationConfig
    cfg = cfg or CalibrationConfig()
    scored = score_candidates(
        rows, watchlist=watchlist, cfg=cfg, cross_section_vols=cross_section_vols,
    )
    return diversify_by_lane(scored, max_handoff=max_handoff, cfg=cfg)



def prescreen_score(metrics: dict[str, Any]) -> float:
    """Multi-horizon interest score — not a recommendation. Avoid top-gainer-only bias."""
    m = normalize_scanner_metrics(metrics)
    if not m.get("available"):
        return -1.0
    score = 0.0
    # Relative volume
    rvol = _f(m.get("rvol_20"))
    score += min(rvol, 5.0) * 8.0
    # Proximity to highs (pre-breakout / continuation)
    d20 = m.get("dist_from_20d_high_pct")
    if d20 is not None:
        d = abs(_f(d20))
        score += max(0.0, 12.0 - d)  # closer to high → higher, still allow corrections
        if -12 <= _f(d20) <= -2:
            score += 6.0  # clean correction zone
    d60 = m.get("dist_from_60d_high_pct")
    if d60 is not None:
        score += max(0.0, 8.0 - abs(_f(d60)) * 0.5)
    # Multi-horizon returns (balanced — not only 1d)
    for key, w in (
        ("daily_return_pct", 0.5),
        ("return_1w_pct", 1.0),
        ("return_1m_pct", 1.2),
        ("return_3m_pct", 1.0),
        ("return_6m_pct", 0.8),
    ):
        if m.get(key) is not None:
            score += abs(_f(m.get(key))) * w * 0.35
    # Trend relationship
    last, sma20, sma50 = m.get("last_close"), m.get("sma_20"), m.get("sma_50")
    if last is not None and sma20 is not None and _f(last) >= _f(sma20):
        score += 3.0
    if last is not None and sma50 is not None and _f(last) >= _f(sma50):
        score += 3.0
    # Volatility presence
    if m.get("realized_vol_20d_ann_pct") is not None:
        score += min(_f(m.get("realized_vol_20d_ann_pct")) / 10.0, 5.0)
    # Breakout state (boolean False preserved — no bonus)
    if m.get("breakout_20d") is True:
        score += 5.0
    if m.get("breakout_60d") is True:
        score += 4.0
    return round(score, 4)


def enrich_metrics_fields(metrics: dict[str, Any], *, latest_session: str | None = None) -> dict[str, Any]:
    """Add Explorer extras without changing scanner formulas."""
    m = dict(metrics or {})
    m["days_of_history"] = m.get("bars")
    m["latest_session"] = latest_session or m.get("latest_completed_market_session") or m.get("session_date")
    if "latest_close" not in m and m.get("last_close") is not None:
        m["latest_close"] = m["last_close"]
    return m
