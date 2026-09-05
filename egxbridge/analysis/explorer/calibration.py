"""v0.5.1 Explorer signal calibration — heuristic / uncalibrated.

Separates two visible dimensions:

  MOVE_ALREADY_REALIZED  — how much historical repricing is already in the price
  FORWARD_SETUP_QUALITY  — whether a next-session structural setup is still present

This module does NOT:
  - emit BUY/SELL
  - map scores to probabilities
  - infer accumulation/distribution/absorption
  - modify Funnel Fair Value
  - look ahead at future returns

Transforms (documented, not silent magic)
----------------------------------------
Legacy v0.5 `prescreen_score` added `abs(return_pct) * weight * 0.35` with no cap.
A +478% 6M move contributed ~134 points versus ~28 from RVOL 3.5x.

Calibrated ranking therefore:

1. Uses a saturating log for any return that still enters the tactical score:
     sat(r, scale) = ln(1 + |r| / scale)
   scale_1d=4, scale_1w=8, scale_1m=15, scale_3m=25, scale_6m=40
   so doubling an already-huge 6M return barely increases contribution.

2. Caps 3M+6M *combined* tactical context at LONG_HORIZON_CAP points (default 4).
   Historical gains are context, not rank.

3. Primary rank key is forward_setup_score (0–100, HEURISTIC_UNCALIBRATED).
   MOVE_ALREADY_REALIZED / VOLATILITY_RISK / TECHNICAL_HISTORY_INTEGRITY
   apply documented penalties; they do not auto-exclude.

4. TECHNICAL_HISTORY_INTEGRITY:
     NOT_VERIFIED            → long-horizon context × 0.35
     POSSIBLE_DISCONTINUITY  → long-horizon context neutralized (0)
     NOT_RELIABLE            → long-horizon context excluded
   One-session close ratio > 45% flags POSSIBLE_DISCONTINUITY only —
   it never asserts STOCK_SPLIT / RIGHTS / BONUS.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any
import json
import math

from egxbridge.analysis.explorer.prescreen import normalize_scanner_metrics, _f


SCORE_KIND = "HEURISTIC_UNCALIBRATED"
# Frozen in v0.6 — do not retune weights/thresholds here.
SCORING_VERSION = "0.5.1"

# Saturating scales: |return_pct| equal to `scale` yields ln(2) ≈ 0.69 units.
SAT_SCALE_1D = 4.0
SAT_SCALE_1W = 8.0
SAT_SCALE_1M = 15.0
SAT_SCALE_3M = 25.0
SAT_SCALE_6M = 40.0
LONG_HORIZON_CAP = 4.0
LONG_HORIZON_WEIGHT_NOT_VERIFIED = 0.35

# One-day close/close ratio that is implausible as ordinary EGX trading
# (cash session limits are typically well below this). Conservative.
DISCONTINUITY_ONE_DAY_RATIO = 0.45
DISCONTINUITY_GAP_WITH_HUGE_6M = 0.25
HUGE_6M_FOR_GAP_FLAG = 250.0

# CLEAN_CORRECTION pullback from 20D high (pct). Configurable bands.
CLEAN_PULLBACK_MIN = -12.0  # more negative = deeper
CLEAN_PULLBACK_MAX = -2.0
CLEAN_BREAKDOWN_BOTH_SMA = True

# PRE_BREAKOUT distance to 20D high.
PREBREAKOUT_NEAR = -2.0
PREBREAKOUT_OVERSHOOT = 0.35

# Volatility bands when no cross-section is supplied (annualized %).
VOL_BANDS = {"LOW": 25.0, "NORMAL": 45.0, "ELEVATED": 80.0}

LANE_A = "LANE_A_EARLY_PRE_IGNITION"
LANE_B = "LANE_B_CONTINUATION"
LANE_C = "LANE_C_CORRECTION_REVERSAL"
LANE_D = "LANE_D_HIGH_RISK_EXTENDED"
LANE_E = "LANE_E_FUNNEL_FOLLOW_UP"

DEFAULT_LANE_SLOTS = {LANE_A: 8, LANE_B: 6, LANE_C: 8, LANE_D: 4, LANE_E: 4}

INTRADAY_PRIORITY_FAMILIES = (
    "PRE_BREAKOUT",
    "EARLY_MOMENTUM",
    "FRESH_CONTINUATION",
    "CONTINUATION",
    "EARLY_REVERSAL",
)

MOVE_PENALTY = {"LOW": 0.0, "MODERATE": 4.0, "HIGH": 10.0, "EXTREME": 18.0, "NOT_RELIABLE": 2.0}
VOL_PENALTY = {"LOW": 0.0, "NORMAL": 0.0, "ELEVATED": 4.0, "EXTREME": 8.0, "NOT_RELIABLE": 1.0}


@dataclass
class CalibrationConfig:
    clean_pullback_min: float = CLEAN_PULLBACK_MIN
    clean_pullback_max: float = CLEAN_PULLBACK_MAX
    prebreakout_near: float = PREBREAKOUT_NEAR
    prebreakout_overshoot: float = PREBREAKOUT_OVERSHOOT
    long_horizon_cap: float = LONG_HORIZON_CAP
    discontinuity_one_day_ratio: float = DISCONTINUITY_ONE_DAY_RATIO
    lane_slots: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_LANE_SLOTS))
    vol_bands: dict[str, float] = field(default_factory=lambda: dict(VOL_BANDS))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sat_return(r: Any, scale: float) -> float:
    """ln(1 + |r|/scale) — bounded, documented saturating transform."""
    if r is None or scale <= 0:
        return 0.0
    return math.log(1.0 + abs(_f(r)) / scale)


def _none(v: Any) -> bool:
    return v is None


def _rel_sma(last: Any, sma: Any) -> str | None:
    if last is None or sma is None:
        return None
    return "above" if _f(last) >= _f(sma) else "below"


def _pct_above(last: Any, ref: Any) -> float | None:
    if last is None or ref is None or _f(ref) == 0:
        return None
    return round((_f(last) / _f(ref) - 1.0) * 100.0, 4)


def enrich_structure(metrics: dict[str, Any], candles: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Transparent structure fields used by families and MOVE_ALREADY_REALIZED."""
    m = normalize_scanner_metrics(metrics)
    last = m.get("last_close")
    sma20 = m.get("sma_20")
    sma50 = m.get("sma_50")
    atr = m.get("atr_14")
    d20 = m.get("dist_from_20d_high_pct")
    out = dict(m)
    out["above_or_below_SMA20"] = _rel_sma(last, sma20)
    out["above_or_below_SMA50"] = _rel_sma(last, sma50)
    out["dist_above_sma20_pct"] = _pct_above(last, sma20)
    out["dist_above_sma50_pct"] = _pct_above(last, sma50)
    out["drawdown_from_recent_peak_pct"] = round(_f(d20), 4) if d20 is not None else None
    out["recent_peak"] = None
    out["drawdown_in_ATR"] = None
    rows = []
    if candles:
        rows = sorted(
            [c for c in candles if c.get("close") is not None],
            key=lambda c: c.get("normalized_utc_timestamp") or c.get("timestamp") or "",
        )
    if rows:
        closes = [float(c["close"]) for c in rows]
        highs = [float(c["high"]) for c in rows if c.get("high") is not None]
        window = highs[-20:] if len(highs) >= 5 else highs
        if window:
            peak = max(window)
            out["recent_peak"] = peak
            if last is not None and peak:
                dd = (float(last) / peak - 1.0) * 100.0
                out["drawdown_from_recent_peak_pct"] = round(dd, 4)
                if atr and _f(atr) > 0:
                    out["drawdown_in_ATR"] = round((peak - float(last)) / _f(atr), 4)
        out["_closes"] = closes
        out["_highs"] = highs
        out["_vols"] = [float(c["volume"]) for c in rows if c.get("volume") is not None]
    if out.get("drawdown_in_ATR") is None and atr and last and d20 is not None and _f(atr) > 0 and _f(last) > 0:
        # Proxy: 20D-high distance expressed in ATR using last as the scale.
        peak_px = float(last) / (1.0 + _f(d20) / 100.0) if _f(d20) > -99 else None
        if peak_px:
            out["recent_peak"] = out.get("recent_peak") or round(peak_px, 6)
            out["drawdown_in_ATR"] = round((peak_px - float(last)) / _f(atr), 4)
    return out


def detect_possible_discontinuity(
    candles: list[dict[str, Any]] | None,
    metrics: dict[str, Any] | None = None,
    *,
    cfg: CalibrationConfig | None = None,
) -> dict[str, Any]:
    """Conservative detector. Flags POSSIBLE_DISCONTINUITY only — never a corp-action type."""
    cfg = cfg or CalibrationConfig()
    m = normalize_scanner_metrics(metrics)
    clues: list[str] = []
    max_gap = None
    if candles:
        rows = sorted(
            [c for c in candles if c.get("close") not in (None, 0)],
            key=lambda c: c.get("normalized_utc_timestamp") or c.get("timestamp") or "",
        )
        for a, b in zip(rows, rows[1:]):
            prev, cur = float(a["close"]), float(b["close"])
            if prev == 0:
                continue
            gap = abs(cur / prev - 1.0)
            if max_gap is None or gap > max_gap:
                max_gap = gap
            if gap > cfg.discontinuity_one_day_ratio:
                clues.append(f"one_session_close_ratio={gap:.2f}")
    r6 = m.get("return_6m_pct")
    if max_gap is not None and r6 is not None and _f(r6) >= HUGE_6M_FOR_GAP_FLAG and max_gap >= DISCONTINUITY_GAP_WITH_HUGE_6M:
        clues.append(f"huge_6m={_f(r6):.1f}%_with_gap={max_gap:.2f}")
    if r6 is not None and _f(r6) >= 400 and m.get("return_1m_pct") is not None and abs(_f(m.get("return_1m_pct"))) < 5:
        # Implausible: enormous 6M with a quiet recent month can still be real,
        # but combined with a large gap it supports discontinuity. Gap-only already flagged.
        if max_gap is not None and max_gap >= 0.20:
            clues.append("implausible_horizon_vs_quiet_recent_with_gap")
    return {
        "possible_discontinuity": bool(clues),
        "clues": clues,
        "max_one_session_abs_return": round(max_gap * 100.0, 4) if max_gap is not None else None,
        "note": "POSSIBLE_DISCONTINUITY is not a verified split/rights/bonus/merger label",
    }


def classify_history_integrity(
    metrics: dict[str, Any],
    candles: list[dict[str, Any]] | None = None,
    *,
    cfg: CalibrationConfig | None = None,
    funnel_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Default NOT_VERIFIED — no corporate-action feed is assumed."""
    disc = detect_possible_discontinuity(candles, metrics, cfg=cfg)
    m = normalize_scanner_metrics(metrics)
    reasons: list[str] = []
    status = "NOT_VERIFIED"
    reasons.append("no_verified_corporate_action_feed")
    if disc["possible_discontinuity"]:
        status = "POSSIBLE_DISCONTINUITY"
        reasons.extend(disc["clues"])
    long_missing = all(m.get(k) is None for k in ("return_1m_pct", "return_3m_pct", "return_6m_pct"))
    bars = m.get("days_of_history") or m.get("bars")
    if long_missing and (bars is None or _f(bars) < 30):
        status = "NOT_RELIABLE"
        reasons.append("insufficient_history_for_long_horizon")
    # Funnel may mention capital actions as text; we still do not assert a type.
    if funnel_ctx:
        blob = json.dumps(funnel_ctx, default=str).lower()
        if any(w in blob for w in ("split", "bonus", "rights issue", "capital increase")):
            reasons.append("funnel_text_mentions_capital_action_unverified")
            if status == "NOT_VERIFIED":
                status = "POSSIBLE_DISCONTINUITY"
    return {
        "TECHNICAL_HISTORY_INTEGRITY": status,
        "reasons": reasons,
        "detector": disc,
        "long_horizon_weight": {
            "CLEAN": 1.0,
            "ADJUSTED": 1.0,
            "NOT_VERIFIED": LONG_HORIZON_WEIGHT_NOT_VERIFIED,
            "POSSIBLE_DISCONTINUITY": 0.0,
            "NOT_RELIABLE": 0.0,
        }.get(status, LONG_HORIZON_WEIGHT_NOT_VERIFIED),
    }


def classify_move_already_realized(metrics: dict[str, Any]) -> dict[str, Any]:
    """Not a sell signal. Multi-factor extension / historical-move context."""
    m = enrich_structure(metrics)
    r1m, r3m, r6m = m.get("return_1m_pct"), m.get("return_3m_pct"), m.get("return_6m_pct")
    vol = m.get("realized_vol_20d_ann_pct")
    ext50 = m.get("dist_above_sma50_pct")
    reasons: list[str] = []
    if all(v is None for v in (r1m, r3m, r6m)):
        return {
            "MOVE_ALREADY_REALIZED": "NOT_RELIABLE",
            "reasons": ["long_horizon_returns_unavailable"],
            "metrics": {"return_1m_pct": r1m, "return_3m_pct": r3m, "return_6m_pct": r6m},
        }
    score = 0
    if r6m is not None:
        reasons.append(f"return_6m={_f(r6m):.1f}%")
        if _f(r6m) >= 120:
            score += 4
        elif _f(r6m) >= 80:
            score += 3
        elif _f(r6m) >= 50:
            score += 2
        elif _f(r6m) >= 20:
            score += 1
    if r3m is not None:
        reasons.append(f"return_3m={_f(r3m):.1f}%")
        if _f(r3m) >= 80:
            score += 4
        elif _f(r3m) >= 35:
            score += 2
        elif _f(r3m) >= 12:
            score += 1
    if r1m is not None:
        reasons.append(f"return_1m={_f(r1m):.1f}%")
        if _f(r1m) >= 25:
            score += 2
        elif _f(r1m) >= 10:
            score += 1
    if ext50 is not None:
        reasons.append(f"dist_above_sma50={_f(ext50):.1f}%")
        if _f(ext50) >= 40:
            score += 2
        elif _f(ext50) >= 20:
            score += 1
    if vol is not None and _f(vol) >= 80 and (r3m is not None and _f(r3m) >= 20):
        reasons.append(f"realized_vol_20d_ann={_f(vol):.0f}%_with_intermediate_gain")
        score += 1
    # Acceleration: 1M still carrying a large share of 3M
    if r1m is not None and r3m is not None and _f(r3m) >= 20 and _f(r1m) >= 0.6 * _f(r3m):
        reasons.append("recent_acceleration_1m_large_share_of_3m")
        score += 1
    if score >= 6:
        klass = "EXTREME"
        reasons.append("price_materially_extended_vs_structural_baseline")
    elif score >= 4:
        klass = "HIGH"
    elif score >= 2:
        klass = "MODERATE"
    else:
        klass = "LOW"
    return {
        "MOVE_ALREADY_REALIZED": klass,
        "reasons": reasons,
        "metrics": {
            "return_1m_pct": r1m,
            "return_3m_pct": r3m,
            "return_6m_pct": r6m,
            "dist_above_sma50_pct": ext50,
            "realized_vol_20d_ann_pct": vol,
        },
        "note": "Not a sell/do-not-own signal; extension context only",
    }


def classify_volatility_risk(
    metrics: dict[str, Any],
    *,
    cross_section_vols: list[float] | None = None,
    cfg: CalibrationConfig | None = None,
) -> dict[str, Any]:
    cfg = cfg or CalibrationConfig()
    vol = metrics.get("realized_vol_20d_ann_pct")
    if vol is None:
        return {"VOLATILITY_RISK": "NOT_RELIABLE", "realized_vol_20d_ann_pct": None, "basis": "missing"}
    v = _f(vol)
    basis = "fixed_bands"
    if cross_section_vols and len(cross_section_vols) >= 20:
        xs = sorted(float(x) for x in cross_section_vols if x is not None)
        def _pctile(p: float) -> float:
            if not xs:
                return v
            k = min(len(xs) - 1, max(0, int(round((p / 100.0) * (len(xs) - 1)))))
            return xs[k]
        p90, p70, p30 = _pctile(90), _pctile(70), _pctile(30)
        basis = "cross_sectional_percentiles"
        if v >= p90:
            klass = "EXTREME"
        elif v >= p70:
            klass = "ELEVATED"
        elif v >= p30:
            klass = "NORMAL"
        else:
            klass = "LOW"
        return {
            "VOLATILITY_RISK": klass,
            "realized_vol_20d_ann_pct": round(v, 4),
            "basis": basis,
            "percentiles": {"p30": p30, "p70": p70, "p90": p90},
        }
    bands = cfg.vol_bands
    if v >= bands["ELEVATED"]:
        klass = "EXTREME"
    elif v >= bands["NORMAL"]:
        klass = "ELEVATED"
    elif v >= bands["LOW"]:
        klass = "NORMAL"
    else:
        klass = "LOW"
    return {
        "VOLATILITY_RISK": klass,
        "realized_vol_20d_ann_pct": round(v, 4),
        "basis": basis,
        "bands": bands,
    }


def _clip01(x: float) -> float:
    return max(0.0, min(100.0, x))


def forward_setup_components(
    metrics: dict[str, Any],
    *,
    move: dict[str, Any],
    vol: dict[str, Any],
    families: list[str],
    intraday_available: bool | None = None,
    cfg: CalibrationConfig | None = None,
) -> dict[str, Any]:
    cfg = cfg or CalibrationConfig()
    m = enrich_structure(metrics)
    rvol = _f(m.get("rvol_20"))
    d20 = m.get("dist_from_20d_high_pct")
    d60 = m.get("dist_from_60d_high_pct")
    daily = m.get("daily_return_pct")
    r1w = m.get("return_1w_pct")
    r1m = m.get("return_1m_pct")

    # VOLUME: 1.0x → ~40, 1.5x → ~70, 2.5x+ → ~95. High RVOL is not automatically bullish;
    # direction is applied in STRUCTURE, not here.
    volume = _clip01(20.0 + min(rvol, 4.0) * 22.0)

    structure = 40.0
    if d20 is not None:
        x = _f(d20)
        if cfg.prebreakout_near <= x <= cfg.prebreakout_overshoot:
            structure = 88.0
        elif -1.0 <= x <= 1.5:
            structure = 80.0
        elif cfg.clean_pullback_min <= x <= cfg.clean_pullback_max:
            structure = 78.0
        elif x < -18:
            structure = 25.0
        elif x > 3:
            structure = 35.0  # already far through the high
        else:
            structure = 55.0
    if d60 is not None and -2 <= _f(d60) <= 1:
        structure = min(100.0, structure + 6.0)

    trend = 40.0
    if m.get("above_or_below_SMA20") == "above":
        trend += 25
    if m.get("above_or_below_SMA50") == "above":
        trend += 20
    if m.get("above_or_below_SMA20") == "below" and m.get("above_or_below_SMA50") == "below":
        trend = 22.0

    ext_map = {"LOW": 88.0, "MODERATE": 70.0, "HIGH": 45.0, "EXTREME": 22.0, "NOT_RELIABLE": 50.0}
    extension = ext_map.get(move.get("MOVE_ALREADY_REALIZED") or "NOT_RELIABLE", 50.0)

    vmap = {"LOW": 90.0, "NORMAL": 78.0, "ELEVATED": 55.0, "EXTREME": 28.0, "NOT_RELIABLE": 50.0}
    vol_comp = vmap.get(vol.get("VOLATILITY_RISK") or "NOT_RELIABLE", 50.0)

    signs = [s for s in (daily, r1w, r1m) if s is not None]
    if len(signs) >= 2:
        pos = sum(1 for s in signs if _f(s) > 0)
        neg = sum(1 for s in signs if _f(s) < 0)
        if pos == len(signs) or (pos >= 2 and daily is not None and _f(daily) < 0 and r1m is not None and _f(r1m) > 0):
            multi = 78.0  # pullback inside constructive intermediate trend still consistent
        elif neg == len(signs):
            multi = 28.0
        else:
            multi = 52.0
    else:
        multi = 45.0

    if intraday_available is True:
        intra = 85.0
    elif intraday_available is False:
        intra = 40.0
    else:
        intra = 50.0  # unknown / not yet enriched

    fam_bonus = 0.0
    setup_fams = [f for f in families if f in {
        "PRE_BREAKOUT", "EARLY_MOMENTUM", "CLEAN_CORRECTION", "EARLY_REVERSAL",
        "FRESH_CONTINUATION", "CONTINUATION",
    }]
    fam_bonus = min(12.0, 4.0 * len(setup_fams))

    parts = {
        "VOLUME_CONFIRMATION": round(volume, 2),
        "STRUCTURE_QUALITY": round(structure, 2),
        "TREND_QUALITY": round(min(100.0, trend), 2),
        "EXTENSION_RISK": round(extension, 2),  # high = lower extension risk
        "VOLATILITY_RISK": round(vol_comp, 2),  # high = easier to execute
        "MULTI_HORIZON_CONSISTENCY": round(multi, 2),
        "INTRADAY_CONFIRMATION_AVAILABILITY": round(intra, 2),
        "FAMILY_CONFLUENCE": round(fam_bonus, 2),
    }
    weights = {
        "VOLUME_CONFIRMATION": 0.22,
        "STRUCTURE_QUALITY": 0.22,
        "TREND_QUALITY": 0.14,
        "EXTENSION_RISK": 0.14,
        "VOLATILITY_RISK": 0.08,
        "MULTI_HORIZON_CONSISTENCY": 0.10,
        "INTRADAY_CONFIRMATION_AVAILABILITY": 0.04,
        "FAMILY_CONFLUENCE": 0.06,
    }
    score = sum(parts[k] * weights[k] for k in weights)
    # FAMILY_CONFLUENCE is 0–12; scale into 0–100 equivalent already small via weight.
    score = _clip01(score)
    if score >= 70:
        quality = "STRONG"
    elif score >= 55:
        quality = "GOOD"
    elif score >= 40:
        quality = "MIXED"
    elif m.get("available"):
        quality = "WEAK"
    else:
        quality = "NOT_RELIABLE"
        score = 0.0
    return {
        "FORWARD_SETUP_QUALITY": quality,
        "forward_setup_score": round(score, 2),
        "forward_setup_components": parts,
        "component_weights": weights,
        "score_kind": SCORE_KIND,
        "not_a_probability": True,
    }


def long_horizon_context_points(
    metrics: dict[str, Any],
    integrity: dict[str, Any],
    *,
    cfg: CalibrationConfig | None = None,
) -> dict[str, Any]:
    cfg = cfg or CalibrationConfig()
    m = normalize_scanner_metrics(metrics)
    raw = sat_return(m.get("return_3m_pct"), SAT_SCALE_3M) + sat_return(m.get("return_6m_pct"), SAT_SCALE_6M)
    w = float(integrity.get("long_horizon_weight") or 0.0)
    capped = min(cfg.long_horizon_cap, raw) * w
    return {
        "unsaturated_log_sum": round(raw, 4),
        "weight": w,
        "points": round(capped, 4),
        "cap": cfg.long_horizon_cap,
        "transform": "ln(1+|r|/scale) then cap; 3M/6M never scale linearly",
    }


def calibrated_ranking_score(
    fwd: dict[str, Any],
    move: dict[str, Any],
    vol: dict[str, Any],
    integrity: dict[str, Any],
    metrics: dict[str, Any],
    *,
    cfg: CalibrationConfig | None = None,
) -> dict[str, Any]:
    """Production Explorer rank key. HEURISTIC_UNCALIBRATED — not a probability."""
    cfg = cfg or CalibrationConfig()
    base = _f(fwd.get("forward_setup_score"))
    move_pen = MOVE_PENALTY.get(move.get("MOVE_ALREADY_REALIZED") or "NOT_RELIABLE", 2.0)
    vol_pen = VOL_PENALTY.get(vol.get("VOLATILITY_RISK") or "NOT_RELIABLE", 1.0)
    short = (
        3.0 * sat_return(metrics.get("daily_return_pct"), SAT_SCALE_1D)
        + 4.0 * sat_return(metrics.get("return_1w_pct"), SAT_SCALE_1W)
        + 3.0 * sat_return(metrics.get("return_1m_pct"), SAT_SCALE_1M)
    )
    # Short-horizon saturating terms are small by construction (ln).
    lh = long_horizon_context_points(metrics, integrity, cfg=cfg)
    total = base - move_pen - vol_pen + short + lh["points"]
    return {
        "candidate_score_calibrated": round(total, 4),
        "score_kind": SCORE_KIND,
        "not_a_probability": True,
        "breakdown": {
            "forward_setup_score": base,
            "move_already_realized_penalty": move_pen,
            "volatility_penalty": vol_pen,
            "short_horizon_saturating": round(short, 4),
            "long_horizon_context_points": lh["points"],
            "long_horizon_detail": lh,
        },
    }


def rvol_context(metrics: dict[str, Any]) -> dict[str, Any]:
    m = normalize_scanner_metrics(metrics)
    rvol = m.get("rvol_20")
    daily = m.get("daily_return_pct")
    d20 = m.get("dist_from_20d_high_pct")
    vol = m.get("realized_vol_20d_ann_pct")
    direction = "flat"
    if daily is not None:
        direction = "up" if _f(daily) > 0.15 else ("down" if _f(daily) < -0.15 else "flat")
    dist_state = None
    if d20 is not None:
        if _f(d20) >= -2:
            dist_state = "near_high"
        elif _f(d20) <= -12:
            dist_state = "far_from_high"
        else:
            dist_state = "mid_range"
    vol_state = None
    if vol is not None:
        vol_state = classify_volatility_risk(m)["VOLATILITY_RISK"]
    note = "High RVOL is not automatically bullish; no distribution/absorption inferred"
    constructive = bool(
        rvol is not None and _f(rvol) >= 1.5 and direction == "up" and dist_state == "near_high"
    )
    event_risk = bool(
        rvol is not None and _f(rvol) >= 1.5 and direction == "down" and dist_state in {"far_from_high", "mid_range"}
    )
    return {
        "RVOL20": None if rvol is None else round(_f(rvol), 4),
        "price_direction": direction,
        "distance_from_high": dist_state,
        "volatility_state": vol_state,
        "constructive_volume_structure": constructive,
        "breakdown_event_risk": event_risk,
        "note": note,
    }


def classify_candidate_families(
    metrics: dict[str, Any],
    *,
    watchlist: bool = False,
    cfg: CalibrationConfig | None = None,
    move: dict[str, Any] | None = None,
) -> list[str]:
    """Tightened families. A ticker may match several. Daily return is not a universal gate."""
    cfg = cfg or CalibrationConfig()
    m = enrich_structure(metrics)
    if not m.get("available"):
        return []
    families: list[str] = []
    rvol = _f(m.get("rvol_20"))
    daily = m.get("daily_return_pct")
    r1w = m.get("return_1w_pct")
    r1m = m.get("return_1m_pct")
    r3m = m.get("return_3m_pct")
    r6m = m.get("return_6m_pct")
    d20 = m.get("dist_from_20d_high_pct")
    d60 = m.get("dist_from_60d_high_pct")
    last = m.get("last_close")
    sma20 = m.get("sma_20")
    sma50 = m.get("sma_50")
    br20 = m.get("breakout_20d") is True
    br60 = m.get("breakout_60d") is True
    above20 = last is not None and sma20 is not None and _f(last) >= _f(sma20)
    above50 = last is not None and sma50 is not None and _f(last) >= _f(sma50)
    below20 = last is not None and sma20 is not None and _f(last) < _f(sma20)
    below50 = last is not None and sma50 is not None and _f(last) < _f(sma50)
    dd = m.get("drawdown_from_recent_peak_pct")
    if dd is None:
        dd = d20
    vol = m.get("realized_vol_20d_ann_pct")
    move_cls = (move or {}).get("MOVE_ALREADY_REALIZED")

    if rvol >= 1.5:
        families.append("HIGH_RELATIVE_VOLUME")
    if d20 is not None and _f(d20) >= -2.0:
        families.append("NEAR_HIGH_STRENGTH")

    # PRE_BREAKOUT: pressure at a reference high, not already accepted through it.
    if (
        d20 is not None
        and cfg.prebreakout_near <= _f(d20) <= cfg.prebreakout_overshoot
        and not br20
        and (above20 or (r1w is not None and _f(r1w) >= 0) or (r1m is not None and _f(r1m) > 0))
        and (daily is None or _f(daily) > -3.5)
        and (r1w is None or _f(r1w) > -6)
    ):
        families.append("PRE_BREAKOUT")
        m["breakout_reference"] = "20D_HIGH"
        m["distance_to_breakout_pct"] = round(-_f(d20), 4)

    # CONTINUATION
    if (br20 or br60) and (d20 is None or _f(d20) >= -5) and (above20 or br20):
        families.append("CONTINUATION")
        fresh = (r1w is not None and _f(r1w) > 0) and (d20 is None or _f(d20) >= -2)
        mature = (r3m is not None and _f(r3m) >= 25) or (r6m is not None and _f(r6m) >= 40)
        if fresh:
            families.append("FRESH_CONTINUATION")
        if mature:
            families.append("MATURE_CONTINUATION")

    # CLEAN_CORRECTION: actual pullback after constructive intermediate trend
    prior_trend = (r1m is not None and _f(r1m) > 0) or (r3m is not None and _f(r3m) > 0)
    pullback = dd is not None and cfg.clean_pullback_min <= _f(dd) <= cfg.clean_pullback_max
    not_collapse = not (below20 and below50 and (r1m is not None and _f(r1m) < 0))
    near_support = above20 or (sma50 is not None and last is not None and _f(last) >= _f(sma50) * 0.98)
    vol_ok = vol is None or _f(vol) < 140 or above20
    if prior_trend and pullback and not_collapse and near_support and vol_ok:
        families.append("CLEAN_CORRECTION")

    # EARLY_MOMENTUM: recent acceleration, not already severely extended
    short_pos = (daily is not None and _f(daily) > 0) or (r1w is not None and _f(r1w) > 0)
    near_range = d20 is None or (-8.0 <= _f(d20) <= 2.0)
    not_extreme = move_cls not in {"EXTREME"} or (d20 is not None and _f(d20) <= 0.5 and rvol >= 1.8)
    if short_pos and rvol >= 1.2 and near_range and not_extreme and (above20 or (d20 is not None and _f(d20) >= -3)):
        families.append("EARLY_MOMENTUM")

    # EARLY_REVERSAL: prior weakness + reclaim evidence
    prior_weak = (d20 is not None and _f(d20) < -8) or (r1m is not None and _f(r1m) < 0)
    reclaim = (r1w is not None and _f(r1w) > 0) or (daily is not None and _f(daily) > 0 and above20)
    not_breakout = d20 is None or _f(d20) < -5
    if prior_weak and reclaim and not_breakout:
        families.append("EARLY_REVERSAL")

    # DELAYED_REPRICING as technical hypothesis only (no local catalyst/news)
    prior_reprice = (r3m is not None and _f(r3m) >= 20) or (r6m is not None and _f(r6m) >= 30)
    pause = (r1w is not None and _f(r1w) <= 0) or (d20 is not None and _f(d20) <= -3)
    second_leg = above20 or rvol >= 1.3 or (d20 is not None and cfg.prebreakout_near <= _f(d20) <= 0.5)
    not_just_huge_and_red = prior_reprice and pause and second_leg
    if not_just_huge_and_red:
        families.append("DELAYED_REPRICING_TECHNICAL_HYPOTHESIS")

    if move_cls in {"HIGH", "EXTREME"} and (
        "FRESH_CONTINUATION" in families or "PRE_BREAKOUT" in families or "CONTINUATION" in families
    ):
        families.append("HIGH_BASE_SECOND_LEG")

    if watchlist:
        families.append("USER_WATCHLIST")

    seen: set[str] = set()
    out: list[str] = []
    for fam in families:
        if fam not in seen:
            seen.add(fam)
            out.append(fam)
    return out


def family_structure_fields(metrics: dict[str, Any], cfg: CalibrationConfig | None = None) -> dict[str, Any]:
    cfg = cfg or CalibrationConfig()
    m = enrich_structure(metrics)
    d20 = m.get("dist_from_20d_high_pct")
    rvol = m.get("rvol_20")
    return {
        "breakout_reference": "20D_HIGH" if d20 is not None else None,
        "distance_to_breakout_pct": None if d20 is None else round(-_f(d20), 4),
        "prebreakout_volume_state": (
            "elevated" if rvol is not None and _f(rvol) >= 1.5 else (
                "quiet" if rvol is not None and _f(rvol) < 1.0 else "normal_or_unknown"
            )
        ),
        "extension_state": (classify_move_already_realized(m).get("MOVE_ALREADY_REALIZED")),
        "recent_peak": m.get("recent_peak"),
        "drawdown_from_recent_peak_pct": m.get("drawdown_from_recent_peak_pct"),
        "drawdown_in_ATR": m.get("drawdown_in_ATR"),
        "above_or_below_SMA20": m.get("above_or_below_SMA20"),
        "above_or_below_SMA50": m.get("above_or_below_SMA50"),
        "dist_above_sma20_pct": m.get("dist_above_sma20_pct"),
        "dist_above_sma50_pct": m.get("dist_above_sma50_pct"),
    }


def assign_lane(
    families: list[str],
    move_cls: str | None,
    vol_cls: str | None,
    funnel_status: str | None,
) -> str:
    fams = set(families or [])
    # Extreme realized moves occupy the high-risk lane so they cannot crowd early slots.
    if move_cls == "EXTREME":
        return LANE_D
    if "EARLY_MOMENTUM" in fams or "PRE_BREAKOUT" in fams:
        return LANE_A
    if "FRESH_CONTINUATION" in fams or "CONTINUATION" in fams or "MATURE_CONTINUATION" in fams:
        return LANE_B
    if "CLEAN_CORRECTION" in fams or "EARLY_REVERSAL" in fams:
        return LANE_C
    if (
        move_cls in {"EXTREME", "HIGH"}
        or vol_cls == "EXTREME"
        or "DELAYED_REPRICING_TECHNICAL_HYPOTHESIS" in fams
        or "HIGH_BASE_SECOND_LEG" in fams
    ):
        return LANE_D
    if funnel_status and funnel_status not in {"NOT_FOUND"}:
        return LANE_E
    if "NEAR_HIGH_STRENGTH" in fams:
        return LANE_A
    return LANE_D


def calibrate_candidate(
    metrics: dict[str, Any],
    *,
    candles: list[dict[str, Any]] | None = None,
    funnel_ctx: dict[str, Any] | None = None,
    watchlist: bool = False,
    intraday_available: bool | None = None,
    cross_section_vols: list[float] | None = None,
    cfg: CalibrationConfig | None = None,
    legacy_score: float | None = None,
) -> dict[str, Any]:
    cfg = cfg or CalibrationConfig()
    m = enrich_structure(metrics, candles)
    integrity = classify_history_integrity(m, candles, cfg=cfg, funnel_ctx=funnel_ctx)
    move = classify_move_already_realized(m)
    vol = classify_volatility_risk(m, cross_section_vols=cross_section_vols, cfg=cfg)
    families = classify_candidate_families(m, watchlist=watchlist, cfg=cfg, move=move)
    fwd = forward_setup_components(
        m, move=move, vol=vol, families=families, intraday_available=intraday_available, cfg=cfg,
    )
    rank = calibrated_ranking_score(fwd, move, vol, integrity, m, cfg=cfg)
    funnel_status = (funnel_ctx or {}).get("funnel_status")
    lane = assign_lane(families, move.get("MOVE_ALREADY_REALIZED"), vol.get("VOLATILITY_RISK"), funnel_status)
    structure = family_structure_fields(m, cfg)
    rctx = rvol_context(m)
    warnings: list[str] = []
    if move["MOVE_ALREADY_REALIZED"] in {"HIGH", "EXTREME"}:
        warnings.append(f"MOVE_ALREADY_REALIZED={move['MOVE_ALREADY_REALIZED']}")
    if vol["VOLATILITY_RISK"] in {"ELEVATED", "EXTREME"}:
        warnings.append(f"VOLATILITY_RISK={vol['VOLATILITY_RISK']}")
    if integrity["TECHNICAL_HISTORY_INTEGRITY"] in {"POSSIBLE_DISCONTINUITY", "NOT_RELIABLE"}:
        warnings.append(f"TECHNICAL_HISTORY_INTEGRITY={integrity['TECHNICAL_HISTORY_INTEGRITY']}")
    if "DELAYED_REPRICING_TECHNICAL_HYPOTHESIS" in families:
        warnings.append("delayed_repricing_requires_external_catalyst_verification")
    atr = m.get("atr_14")
    ext_note = None
    if m.get("drawdown_in_ATR") is not None:
        ext_note = f"drawdown_from_peak_atr={m['drawdown_in_ATR']}"
    return {
        **rank,
        "candidate_score_legacy": legacy_score,
        "MOVE_ALREADY_REALIZED": move["MOVE_ALREADY_REALIZED"],
        "move_realized_reasons": move["reasons"],
        "move_realized_detail": move,
        "FORWARD_SETUP_QUALITY": fwd["FORWARD_SETUP_QUALITY"],
        "forward_setup_score": fwd["forward_setup_score"],
        "forward_setup_components": fwd["forward_setup_components"],
        "candidate_families": families,
        "candidate_lane": lane,
        "TECHNICAL_HISTORY_INTEGRITY": integrity["TECHNICAL_HISTORY_INTEGRITY"],
        "history_integrity": integrity,
        "VOLATILITY_RISK": vol["VOLATILITY_RISK"],
        "volatility_detail": vol,
        "rvol_context": rctx,
        "structure": structure,
        "calibration_warnings": warnings,
        "extension_context": ext_note,
        "do_not_chase_price": None,
        "do_not_chase_note": "No exact do-not-chase price without an execution rule; use ATR/extension/move-realized with news",
        "score_kind": SCORE_KIND,
        "not_a_probability": True,
        "fair_value_used_in_tactical_score": False,
    }


def diversify_by_lane(
    rows: list[dict[str, Any]],
    *,
    max_handoff: int,
    cfg: CalibrationConfig | None = None,
) -> list[dict[str, Any]]:
    cfg = cfg or CalibrationConfig()
    slots = dict(cfg.lane_slots)
    scored = sorted(rows, key=lambda x: float(x.get("candidate_score_calibrated") or 0), reverse=True)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    by_lane: dict[str, list[dict[str, Any]]] = {k: [] for k in slots}
    funnel_follow = []
    for item in scored:
        lane = item.get("candidate_lane") or LANE_D
        by_lane.setdefault(lane, []).append(item)
        st = (item.get("funnel_ctx") or {}).get("funnel_status")
        if st and st not in {"NOT_FOUND"}:
            funnel_follow.append(item)
    by_lane[LANE_E] = funnel_follow or by_lane.get(LANE_E, [])

    order = [LANE_A, LANE_B, LANE_C, LANE_D, LANE_E]
    for lane in order:
        n = int(slots.get(lane) or 0)
        if n <= 0:
            continue
        taken = 0
        for item in by_lane.get(lane) or []:
            t = item.get("ticker")
            if t in seen:
                continue
            selected.append(item)
            seen.add(t)
            taken += 1
            if taken >= n or len(selected) >= max_handoff:
                break
        if len(selected) >= max_handoff:
            break
    for item in scored:
        if len(selected) >= max_handoff:
            break
        t = item.get("ticker")
        if t not in seen:
            selected.append(item)
            seen.add(t)
    selected.sort(key=lambda x: float(x.get("candidate_score_calibrated") or 0), reverse=True)
    return selected[:max_handoff]


def select_intraday_tickers(rows: list[dict[str, Any]], limit: int) -> list[str]:
    def prio(item: dict[str, Any]) -> tuple[int, float]:
        fams = item.get("candidate_families") or []
        rank = 99
        for i, f in enumerate(INTRADAY_PRIORITY_FAMILIES):
            if f in fams:
                rank = i
                break
        return (rank, -float(item.get("candidate_score_calibrated") or 0))
    ordered = sorted(rows, key=prio)
    return [c["ticker"] for c in ordered[:limit] if c.get("ticker")]


def point_in_time_snapshot(item: dict[str, Any], *, generated_at: str, session: str | None) -> dict[str, Any]:
    m = item.get("metrics") or {}
    return {
        "ticker": item.get("ticker"),
        "selection_timestamp": generated_at,
        "latest_completed_market_session": session,
        "candidate_lane": item.get("candidate_lane"),
        "candidate_families": item.get("candidate_families"),
        "forward_setup_score": item.get("forward_setup_score"),
        "FORWARD_SETUP_QUALITY": item.get("FORWARD_SETUP_QUALITY"),
        "MOVE_ALREADY_REALIZED": item.get("MOVE_ALREADY_REALIZED"),
        "history_integrity": item.get("TECHNICAL_HISTORY_INTEGRITY"),
        "volatility": item.get("VOLATILITY_RISK"),
        "realized_vol_20d_ann_pct": m.get("realized_vol_20d_ann_pct"),
        "price_at_signal": m.get("last_close") or m.get("latest_close"),
        "dist_from_20d_high_pct": m.get("dist_from_20d_high_pct"),
        "dist_from_60d_high_pct": m.get("dist_from_60d_high_pct"),
        "no_lookahead": True,
        "outcomes_reserved": {
            "next_session_return": None,
            "return_3_session": None,
            "return_5_session": None,
            "mfe": None,
            "mae": None,
        },
    }


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = min(len(xs), len(ys))
    if n < 3:
        return None
    x = xs[:n]
    y = ys[:n]
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    if dx == 0 or dy == 0:
        return None
    return round(num / (dx * dy), 4)


def _ranks(xs: list[float]) -> list[float]:
    indexed = sorted(enumerate(xs), key=lambda t: t[1])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float | None:
    n = min(len(xs), len(ys))
    if n < 3:
        return None
    return pearson(_ranks(xs[:n]), _ranks(ys[:n]))


def correlation_profile(rows: list[dict[str, Any]], score_key: str) -> dict[str, Any]:
    paired: dict[str, tuple[list[float], list[float]]] = {
        "daily_return_pct": ([], []),
        "return_1w_pct": ([], []),
        "return_1m_pct": ([], []),
        "return_3m_pct": ([], []),
        "return_6m_pct": ([], []),
        "rvol_20": ([], []),
        "dist_from_20d_high_pct": ([], []),
    }
    for r in rows:
        m = r.get("metrics") or r
        s = r.get(score_key)
        if s is None:
            continue
        for k in paired:
            v = m.get(k)
            if v is None:
                continue
            paired[k][0].append(float(s))
            paired[k][1].append(float(v))
    out = {}
    for k, (sx, sy) in paired.items():
        out[k] = {
            "n": len(sx),
            "pearson": pearson(sx, sy),
            "spearman": spearman(sx, sy),
        }
    return out


def audit_legacy_contributions(metrics: dict[str, Any]) -> dict[str, float]:
    """Quantify v0.5 linear terms — diagnostic only, formulas unchanged in prescreen_score."""
    m = normalize_scanner_metrics(metrics)
    parts: dict[str, float] = {}
    rvol = _f(m.get("rvol_20"))
    parts["rvol"] = min(rvol, 5.0) * 8.0
    d20 = m.get("dist_from_20d_high_pct")
    if d20 is not None:
        parts["dist_20d"] = max(0.0, 12.0 - abs(_f(d20)))
        parts["correction_zone"] = 6.0 if -12 <= _f(d20) <= -2 else 0.0
    d60 = m.get("dist_from_60d_high_pct")
    if d60 is not None:
        parts["dist_60d"] = max(0.0, 8.0 - abs(_f(d60)) * 0.5)
    for key, w, label in (
        ("daily_return_pct", 0.5, "return_1d"),
        ("return_1w_pct", 1.0, "return_1w"),
        ("return_1m_pct", 1.2, "return_1m"),
        ("return_3m_pct", 1.0, "return_3m"),
        ("return_6m_pct", 0.8, "return_6m"),
    ):
        if m.get(key) is not None:
            parts[label] = abs(_f(m.get(key))) * w * 0.35
    last, sma20, sma50 = m.get("last_close"), m.get("sma_20"), m.get("sma_50")
    parts["sma20"] = 3.0 if last is not None and sma20 is not None and _f(last) >= _f(sma20) else 0.0
    parts["sma50"] = 3.0 if last is not None and sma50 is not None and _f(last) >= _f(sma50) else 0.0
    if m.get("realized_vol_20d_ann_pct") is not None:
        parts["vol"] = min(_f(m.get("realized_vol_20d_ann_pct")) / 10.0, 5.0)
    parts["breakout_20d"] = 5.0 if m.get("breakout_20d") is True else 0.0
    parts["breakout_60d"] = 4.0 if m.get("breakout_60d") is True else 0.0
    parts["long_horizon_3m_6m"] = parts.get("return_3m", 0.0) + parts.get("return_6m", 0.0)
    return {k: round(v, 4) for k, v in parts.items()}


def calibration_config_from_run(config: Any | None = None) -> CalibrationConfig:
    if config is None:
        return CalibrationConfig()
    return CalibrationConfig(
        lane_slots={
            LANE_A: int(getattr(config, "lane_a_slots", 8) or 8),
            LANE_B: int(getattr(config, "lane_b_slots", 6) or 6),
            LANE_C: int(getattr(config, "lane_c_slots", 8) or 8),
            LANE_D: int(getattr(config, "lane_d_slots", 4) or 4),
            LANE_E: int(getattr(config, "lane_e_slots", 4) or 4),
        }
    )


def ranking_comparison(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """legacy_rank vs calibrated_rank over the same eligible universe."""
    by_legacy = sorted(rows, key=lambda x: float(x.get("candidate_score_legacy") or 0), reverse=True)
    by_cal = sorted(rows, key=lambda x: float(x.get("candidate_score_calibrated") or 0), reverse=True)
    lrank = {r["ticker"]: i + 1 for i, r in enumerate(by_legacy)}
    crank = {r["ticker"]: i + 1 for i, r in enumerate(by_cal)}
    out: list[dict[str, Any]] = []
    for r in by_cal:
        t = r["ticker"]
        lr, cr = lrank[t], crank[t]
        m = r.get("metrics") or {}
        delta = lr - cr  # positive = improved (smaller rank number)
        reasons = []
        if delta > 0:
            reasons.append(f"rose_{delta}_vs_legacy")
        elif delta < 0:
            reasons.append(f"fell_{abs(delta)}_vs_legacy")
        else:
            reasons.append("rank_unchanged")
        reasons.append(f"FORWARD_SETUP_QUALITY={r.get('FORWARD_SETUP_QUALITY')}")
        reasons.append(f"MOVE_ALREADY_REALIZED={r.get('MOVE_ALREADY_REALIZED')}")
        reasons.append(f"lane={r.get('candidate_lane')}")
        if m.get("return_6m_pct") is not None:
            reasons.append(f"return_6m={float(m['return_6m_pct']):.1f}%")
        if m.get("return_3m_pct") is not None:
            reasons.append(f"return_3m={float(m['return_3m_pct']):.1f}%")
        if m.get("rvol_20") is not None:
            reasons.append(f"RVOL20={float(m['rvol_20']):.2f}")
        if m.get("dist_from_20d_high_pct") is not None:
            reasons.append(f"d20={float(m['dist_from_20d_high_pct']):.2f}%")
        out.append({
            "ticker": t,
            "legacy_score": r.get("candidate_score_legacy"),
            "legacy_rank": lr,
            "calibrated_score": r.get("candidate_score_calibrated"),
            "calibrated_rank": cr,
            "rank_change": delta,
            "reason_for_change": "; ".join(reasons),
            "candidate_lane": r.get("candidate_lane"),
            "candidate_families": "|".join(r.get("candidate_families") or []),
            "MOVE_ALREADY_REALIZED": r.get("MOVE_ALREADY_REALIZED"),
            "FORWARD_SETUP_QUALITY": r.get("FORWARD_SETUP_QUALITY"),
            "forward_setup_score": r.get("forward_setup_score"),
            "TECHNICAL_HISTORY_INTEGRITY": r.get("TECHNICAL_HISTORY_INTEGRITY"),
            "VOLATILITY_RISK": r.get("VOLATILITY_RISK"),
            "RVOL20": m.get("rvol_20"),
            "distance_20d_high": m.get("dist_from_20d_high_pct"),
            "return_1w": m.get("return_1w_pct"),
            "return_1m": m.get("return_1m_pct"),
            "return_3m": m.get("return_3m_pct"),
            "return_6m": m.get("return_6m_pct"),
        })
    return out


def lane_tops(rows: list[dict[str, Any]], n: int = 5) -> dict[str, list[str]]:
    by_lane: dict[str, list[str]] = {}
    scored = sorted(rows, key=lambda x: float(x.get("candidate_score_calibrated") or 0), reverse=True)
    for item in scored:
        lane = item.get("candidate_lane") or LANE_D
        by_lane.setdefault(lane, [])
        t = item.get("ticker")
        if t and t not in by_lane[lane] and len(by_lane[lane]) < n:
            by_lane[lane].append(t)
    return by_lane
