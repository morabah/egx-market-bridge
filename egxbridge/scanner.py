from __future__ import annotations

from typing import Any
import math


def _returns(closes: list[float], days: int) -> float | None:
    if len(closes) <= days:
        return None
    a, b = closes[-1], closes[-1 - days]
    if b == 0:
        return None
    return round((a / b - 1) * 100, 4)


def _sma(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def _atr(highs: list[float], lows: list[float], closes: list[float], window: int = 14) -> float | None:
    if len(closes) < window + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    if len(trs) < window:
        return None
    return sum(trs[-window:]) / window


def compute_scanner_metrics(candles: list[dict[str, Any]]) -> dict[str, Any]:
    """Defensible metrics from daily candles only. No accumulation/distribution labels."""
    if not candles:
        return {"available": False}
    # Ensure chronological ascending (prefer normalized UTC)
    rows = sorted(
        candles,
        key=lambda c: c.get("normalized_utc_timestamp") or c.get("timestamp") or "",
    )
    closes = [float(c["close"]) for c in rows if c.get("close") is not None]
    highs = [float(c["high"]) for c in rows if c.get("high") is not None]
    lows = [float(c["low"]) for c in rows if c.get("low") is not None]
    vols = [float(c["volume"]) for c in rows if c.get("volume") is not None]
    if len(closes) < 2:
        return {"available": False, "bars": len(closes)}

    daily_ret = round((closes[-1] / closes[-2] - 1) * 100, 4) if closes[-2] else None
    vol_20 = _sma(vols, 20) if vols else None
    vol_60 = _sma(vols, 60) if vols else None
    rvol = None
    if vol_20 and vols:
        rvol = round(vols[-1] / vol_20, 4) if vol_20 else None

    high_20 = max(highs[-20:]) if len(highs) >= 20 else (max(highs) if highs else None)
    high_60 = max(highs[-60:]) if len(highs) >= 60 else (max(highs) if highs else None)
    dist_20 = round((closes[-1] / high_20 - 1) * 100, 4) if high_20 else None
    dist_60 = round((closes[-1] / high_60 - 1) * 100, 4) if high_60 else None

    # realized vol (stdev of daily returns) annualized-ish * sqrt(252)
    rets = []
    for i in range(1, len(closes)):
        if closes[i - 1]:
            rets.append(closes[i] / closes[i - 1] - 1)
    realized_vol = None
    if len(rets) >= 10:
        mean = sum(rets[-20:]) / len(rets[-20:])
        var = sum((x - mean) ** 2 for x in rets[-20:]) / len(rets[-20:])
        realized_vol = round(math.sqrt(var) * math.sqrt(252) * 100, 4)

    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    atr14 = _atr(highs, lows, closes, 14) if len(highs) == len(closes) == len(lows) else None

    breakout_20 = bool(high_20 is not None and closes[-1] >= high_20)
    breakout_60 = bool(high_60 is not None and closes[-1] >= high_60)

    return {
        "available": True,
        "bars": len(closes),
        "last_close": closes[-1],
        "daily_return_pct": daily_ret,
        "return_1w_pct": _returns(closes, 5),
        "return_1m_pct": _returns(closes, 21),
        "return_3m_pct": _returns(closes, 63),
        "return_6m_pct": _returns(closes, 126),
        "volume_sma_20": vol_20,
        "volume_sma_60": vol_60,
        "rvol_20": rvol,
        "dist_from_20d_high_pct": dist_20,
        "dist_from_60d_high_pct": dist_60,
        "atr_14": atr14,
        "realized_vol_20d_ann_pct": realized_vol,
        "sma_20": sma20,
        "sma_50": sma50,
        "breakout_flag_20d": breakout_20,
        "breakout_flag_60d": breakout_60,
        # Explorer-facing aliases (same booleans; False preserved)
        "breakout_20d": breakout_20,
        "breakout_60d": breakout_60,
        "note": "Metrics from candles only; not accumulation/distribution inference",
    }
