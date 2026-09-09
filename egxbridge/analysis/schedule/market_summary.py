"""MACRO market context. Breadth is scanner-eligible equities — never the handoff shortlist."""
from __future__ import annotations

from typing import Any
from pathlib import Path
import csv
import statistics

from egxbridge.universe import EQUITY, INDEX, FUND, ETF, RIGHT, WARRANT, OTHER


MARKET_BREADTH_SCOPE = "SCANNER_ELIGIBLE_EQUITY_UNIVERSE"
SHORTLIST_BREADTH_LABEL = "CANDIDATE_BREADTH"
# Distance from high (pct) treated as "near". Display convention only — not a scoring weight.
NEAR_HIGH_THRESHOLD_PCT = -2.0
EXCLUDED_BREADTH_TYPES = {INDEX, FUND, ETF, RIGHT, WARRANT, OTHER}


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None


def _pick(row: dict[str, Any], *keys: str) -> Any:
    m = row.get("metrics") if isinstance(row.get("metrics"), dict) else None
    for k in keys:
        if row.get(k) is not None and row.get(k) != "":
            return row.get(k)
        if m and m.get(k) is not None and m.get(k) != "":
            return m.get(k)
    return None


def _boolish(v: Any) -> bool | None:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"1", "true", "yes"}:
        return True
    if s in {"0", "false", "no"}:
        return False
    return None


def _is_equity_row(row: dict[str, Any]) -> bool:
    sec = str(_pick(row, "security_type") or "").upper()
    if not sec:
        return True
    if sec in EXCLUDED_BREADTH_TYPES:
        return False
    return sec == EQUITY


def _eligible_row(row: dict[str, Any]) -> bool:
    if not _is_equity_row(row):
        return False
    status = str(_pick(row, "data_status") or "").upper()
    if any(tok in status for tok in ("UNAVAILABLE", "NO_MAPPING", "INSUFFICIENT", "EXCLUDED", "STALE")):
        return False
    if _boolish(_pick(row, "daily_bars_lagging")) is True:
        return False
    expected = _pick(row, "expected_session")
    actual = _pick(row, "latest_session", "session_date")
    if expected and actual != expected:
        return False
    if _pick(row, "available") in {False, "False", "false", "0"}:
        return False
    return True


def _sma_above(row: dict[str, Any], sma_key: str) -> bool | None:
    close = _f(_pick(row, "last_close", "latest_close"))
    sma = _f(_pick(row, sma_key))
    rel = _pick(row, f"above_or_below_{sma_key.upper()}", f"above_or_below_{sma_key}")
    if rel:
        s = str(rel).upper()
        if "ABOVE" in s:
            return True
        if "BELOW" in s:
            return False
    if close is None or sma is None:
        return None
    return close > sma


def _pct(n: int, d: int) -> float | None:
    if not d:
        return None
    return round(100.0 * n / d, 2)


def _median(xs: list[float]) -> float | None:
    if not xs:
        return None
    return round(statistics.median(xs), 4)


def _mean(xs: list[float]) -> float | None:
    if not xs:
        return None
    return round(statistics.fmean(xs), 4)


def compute_breadth(
    rows: list[dict[str, Any]] | None,
    *,
    scope: str,
    label: str | None = None,
) -> dict[str, Any]:
    """Compute participation stats. Only rows that belong to `scope` should be passed in."""
    eligible = [r for r in (rows or []) if isinstance(r, dict) and _eligible_row(r)]
    breadth_n = len(eligible)
    d1 = [_f(_pick(r, "daily_return_pct", "daily_return")) for r in eligible]
    d1_ok = [x for x in d1 if x is not None]
    up = sum(1 for x in d1_ok if x > 0)
    down = sum(1 for x in d1_ok if x < 0)
    flat = sum(1 for x in d1_ok if x == 0)
    rvol = [_f(_pick(r, "rvol_20", "RVOL20")) for r in eligible]
    rvol_ok = [x for x in rvol if x is not None]
    vol = [_f(_pick(r, "realized_vol_20d_ann_pct")) for r in eligible]
    vol_ok = [x for x in vol if x is not None]
    above20 = [_sma_above(r, "sma_20") for r in eligible]
    above50 = [_sma_above(r, "sma_50") for r in eligible]
    a20 = [x for x in above20 if x is not None]
    a50 = [x for x in above50 if x is not None]
    d20 = [_f(_pick(r, "dist_from_20d_high_pct", "distance_20d_high")) for r in eligible]
    d60 = [_f(_pick(r, "dist_from_60d_high_pct", "distance_60d_high")) for r in eligible]
    d20_ok = [x for x in d20 if x is not None]
    d60_ok = [x for x in d60 if x is not None]
    b20 = [_boolish(_pick(r, "breakout_20d", "breakout_flag_20d")) for r in eligible]
    b60 = [_boolish(_pick(r, "breakout_60d", "breakout_flag_60d")) for r in eligible]
    b20_ok = [x for x in b20 if x is not None]
    b60_ok = [x for x in b60 if x is not None]

    def rate(n_true: int, denom: int) -> float | None:
        return _pct(n_true, denom)

    out = {
        "breadth_scope": scope,
        "label": label or scope,
        "is_market_breadth": scope == MARKET_BREADTH_SCOPE,
        "breadth_n": breadth_n,
        "advancers": up,
        "decliners": down,
        "unchanged": flat,
        "advancers_pct": rate(up, len(d1_ok)),
        "decliners_pct": rate(down, len(d1_ok)),
        "unchanged_pct": rate(flat, len(d1_ok)),
        "median_daily_return_pct": _median(d1_ok),
        "mean_daily_return_pct": _mean(d1_ok),
        "median_rvol20": _median(rvol_ok),
        "mean_rvol20": _mean(rvol_ok),
        "pct_above_sma20": rate(sum(1 for x in a20 if x), len(a20)),
        "pct_above_sma50": rate(sum(1 for x in a50 if x), len(a50)),
        "pct_with_rvol_gt_1": rate(sum(1 for x in rvol_ok if x > 1.0), len(rvol_ok)),
        "pct_with_rvol_gt_1_5": rate(sum(1 for x in rvol_ok if x > 1.5), len(rvol_ok)),
        "pct_with_rvol_gt_2": rate(sum(1 for x in rvol_ok if x > 2.0), len(rvol_ok)),
        "pct_near_20d_high": rate(sum(1 for x in d20_ok if x >= NEAR_HIGH_THRESHOLD_PCT), len(d20_ok)),
        "pct_near_60d_high": rate(sum(1 for x in d60_ok if x >= NEAR_HIGH_THRESHOLD_PCT), len(d60_ok)),
        "pct_breakout_20d": rate(sum(1 for x in b20_ok if x), len(b20_ok)),
        "pct_breakout_60d": rate(sum(1 for x in b60_ok if x), len(b60_ok)),
        "median_realized_vol_20d_ann_pct": _median(vol_ok),
        "near_high_threshold_pct": NEAR_HIGH_THRESHOLD_PCT,
        "metric_n": {
            "breadth_n": breadth_n,
            "daily_return": len(d1_ok),
            "rvol20": len(rvol_ok),
            "sma20": len(a20),
            "sma50": len(a50),
            "dist_20d_high": len(d20_ok),
            "dist_60d_high": len(d60_ok),
            "breakout_20d": len(b20_ok),
            "breakout_60d": len(b60_ok),
            "realized_vol_20d": len(vol_ok),
        },
        "indices_funds_rights_warrants_excluded": True,
        "note": (
            "Scanner-eligible EQUITY universe for the latest completed session. "
            "Not an official EGX breadth feed. Not candidate-shortlist breadth."
            if scope == MARKET_BREADTH_SCOPE
            else "Candidate shortlist only. Do not call this market breadth."
        ),
    }
    return out


def market_participation(breadth: dict[str, Any]) -> dict[str, Any]:
    return {
        "breadth_scope": breadth.get("breadth_scope") or MARKET_BREADTH_SCOPE,
        "breadth_n": breadth.get("breadth_n"),
        "advancers_pct": breadth.get("advancers_pct"),
        "median_daily_return_pct": breadth.get("median_daily_return_pct"),
        "median_rvol20": breadth.get("median_rvol20"),
        "pct_above_sma20": breadth.get("pct_above_sma20"),
        "pct_above_sma50": breadth.get("pct_above_sma50"),
        "pct_near_20d_high": breadth.get("pct_near_20d_high"),
        "pct_breakout_20d": breadth.get("pct_breakout_20d"),
    }


def compact_scanner_metric_row(row: dict[str, Any]) -> dict[str, Any]:
    ticker = str(_pick(row, "ticker") or "").upper()
    return {
        "ticker": ticker,
        "security_type": _pick(row, "security_type") or EQUITY,
        "available": _pick(row, "available"),
        "data_status": _pick(row, "data_status"),
        "last_close": _pick(row, "last_close", "latest_close"),
        "daily_return_pct": _pick(row, "daily_return_pct", "daily_return"),
        "rvol_20": _pick(row, "rvol_20", "RVOL20"),
        "sma_20": _pick(row, "sma_20"),
        "sma_50": _pick(row, "sma_50"),
        "dist_from_20d_high_pct": _pick(row, "dist_from_20d_high_pct", "distance_20d_high"),
        "dist_from_60d_high_pct": _pick(row, "dist_from_60d_high_pct", "distance_60d_high"),
        "breakout_20d": _pick(row, "breakout_20d", "breakout_flag_20d"),
        "breakout_60d": _pick(row, "breakout_60d", "breakout_flag_60d"),
        "realized_vol_20d_ann_pct": _pick(row, "realized_vol_20d_ann_pct"),
        "latest_session": _pick(row, "latest_completed_market_session", "latest_session", "session_date"),
        "expected_session": _pick(row, "expected_session"),
        "daily_bars_lagging": _pick(row, "daily_bars_lagging"),
    }


def load_scanner_eligible_metrics(explorer_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Never returns the handoff shortlist as a substitute for market breadth rows."""
    payload = explorer_payload or {}
    existing = payload.get("scanner_eligible_metrics")
    if isinstance(existing, list) and existing:
        return [compact_scanner_metric_row(r) for r in existing if isinstance(r, dict)]
    pkg = payload.get("_package_dir")
    eligible = set()
    counts = payload.get("counts") or {}
    lst = counts.get("SCANNER_ELIGIBLE_SYMBOLS_LIST") or payload.get("SCANNER_ELIGIBLE_SYMBOLS") or []
    if isinstance(lst, list):
        eligible = {str(x).upper() for x in lst}
    type_by: dict[str, str] = {}
    if pkg:
        uni = Path(pkg) / "universe.csv"
        if uni.exists():
            with uni.open(encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    t = str(row.get("canonical_symbol") or row.get("ticker") or "").upper()
                    type_by[t] = str(row.get("security_type") or "").upper()
        metrics_path = Path(pkg) / "daily_market_metrics.csv"
        if not metrics_path.exists():
            metrics_path = Path(pkg) / "market_metrics.csv"
        if metrics_path.exists():
            out = []
            with metrics_path.open(encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    t = str(row.get("ticker") or "").upper()
                    if eligible and t not in eligible:
                        continue
                    sec = type_by.get(t) or EQUITY
                    if sec in EXCLUDED_BREADTH_TYPES:
                        continue
                    rec = dict(row)
                    rec["security_type"] = sec
                    rec["ticker"] = t
                    out.append(compact_scanner_metric_row(rec))
            if out:
                return out
    ranked = payload.get("ranked_comparison") or payload.get("all_scored") or []
    if isinstance(ranked, list) and ranked and not payload.get("candidates"):
        return [compact_scanner_metric_row(r) for r in ranked if isinstance(r, dict)]
    if isinstance(ranked, list) and ranked:
        handoff = {str(c.get("ticker") or "").upper() for c in (payload.get("candidates") or [])}
        # ranked_comparison on Explorer includes the full scored eligible set.
        if len(ranked) > len(handoff):
            return [compact_scanner_metric_row(r) for r in ranked if isinstance(r, dict)]
    return []


def build_market_summary(
    *,
    coverage: dict[str, Any] | None,
    counts: dict[str, Any] | None,
    scanner_rows: list[dict[str, Any]] | None,
    latest_session: str | None,
    session_meta: dict[str, Any] | None,
    data_limitations: list[str] | None = None,
    portfolio_context: str = "",
    breadth_rows: list[dict[str, Any]] | None = None,
    explorer_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    shortlist = list(scanner_rows or [])
    market_rows = list(breadth_rows) if breadth_rows is not None else load_scanner_eligible_metrics(explorer_payload)
    market_b = compute_breadth(market_rows, scope=MARKET_BREADTH_SCOPE, label="BROAD_MARKET_EVIDENCE")
    cand_b = compute_breadth(shortlist, scope=SHORTLIST_BREADTH_LABEL, label=SHORTLIST_BREADTH_LABEL)
    cand_b["do_not_infer_market_regime_from_this"] = True
    if not market_rows:
        market_b["note"] = (
            "Scanner-eligible equity metrics were not provided. "
            "Do NOT substitute candidate shortlist breadth for market breadth."
        )
        market_b["missing_eligible_metrics"] = True
    return {
        "latest_completed_market_session": latest_session,
        "target_next_working_day": "UNKNOWN",
        "session_phase": (session_meta or {}).get("session_phase") or "UNKNOWN",
        "explorer_coverage": (coverage or {}).get("EXPLORER_COVERAGE"),
        "selection_basis": (coverage or {}).get("selection_basis"),
        "counts": {
            "UNIVERSE_TOTAL": (counts or {}).get("UNIVERSE_TOTAL"),
            "EQUITY_UNIVERSE_TOTAL": (counts or {}).get("EQUITY_UNIVERSE_TOTAL"),
            "SCANNER_ELIGIBLE": (counts or {}).get("SCANNER_ELIGIBLE_SYMBOLS"),
            "PRESCREEN_SELECTED": (counts or {}).get("PRESCREEN_SELECTED"),
            "HANDOFF_CANDIDATES": (counts or {}).get("HANDOFF_CANDIDATES"),
            "INTRADAY_ENRICHED": (counts or {}).get("INTRADAY_ENRICHED"),
        },
        "MARKET_BREADTH_SCOPE": MARKET_BREADTH_SCOPE,
        "broad_market_evidence": market_b,
        "market_breadth": market_b,
        "market_participation": market_participation(market_b),
        "candidate_shortlist_context": {
            "label": SHORTLIST_BREADTH_LABEL,
            "n": len(shortlist),
            "breadth": cand_b,
            "note": "Secondary context. Do not infer market regime from candidate shortlist breadth.",
        },
        "shortlist_breadth": cand_b,
        "index_context": "UNAVAILABLE_LOCALLY",
        "sector_participation": "UNAVAILABLE_LOCALLY",
        "event_calendar": "UNAVAILABLE_LOCALLY",
        "portfolio_holdings_context": portfolio_context or "NONE_PROVIDED",
        "data_quality_limitations": data_limitations or [
            "No official EGX trading calendar locally — target_next_working_day=UNKNOWN",
            "No bid/ask/depth/trades — execution_grade typically NO",
            "Do not infer absorption/distribution/order-book imbalance",
            "Macro/news is not manufactured locally",
            "Do not infer market regime from candidate shortlist breadth",
        ],
        "scoring_version": "0.5.1",
        "not_a_stock_ranking": True,
        # Legacy key kept so old tests that only check presence still see a breadth object.
        # It is the BROAD market object, never shortlist-as-market.
        "breadth": market_b,
    }
