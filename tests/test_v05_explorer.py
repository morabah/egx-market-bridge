from __future__ import annotations

import json
from pathlib import Path

from egxbridge.analysis.common.environment import PRODUCTION, UNIT_TEST, ACCEPTANCE_TEST
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.coverage import classify_explorer_coverage
from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
from egxbridge.analysis.explorer.intraday import enrich_shortlist_intraday
from egxbridge.analysis.explorer.models import ExplorerRunConfig
from egxbridge.analysis.explorer.prescreen import (
    classify_candidate_families,
    prescreen_score,
    select_handoff_candidates,
)
from egxbridge.analysis.funnel.registry import FunnelRegistry
from egxbridge.db import Database
from egxbridge.providers.base import Candle


def _seed_daily(db: Database, symbol: str, n: int = 60, pattern: str = "up"):
    for i in range(n):
        if pattern == "gainer":
            close = 10 + i * 0.5
        elif pattern == "correction":
            close = 20 - (0.15 if i == n - 1 else 0) + (i / n)
        else:
            close = 10 + (i % 7) * 0.1
        ts = f"2026-06-{(i % 28) + 1:02d}T00:00:00+00:00"
        # unique timestamps: use sequential days via ordinal
        day = 1 + i
        month = 1 + (day - 1) // 28
        d = (day - 1) % 28 + 1
        ts = f"2026-{month:02d}-{d:02d}T00:00:00+00:00"
        db.upsert_candle({
            "symbol": symbol, "interval": "1d", "timestamp": ts,
            "normalized_utc_timestamp": ts,
            "open": close, "high": close + 0.4, "low": close - 0.3, "close": close,
            "volume": 8000 if pattern == "correction" else 1000 + i,
            "provider": "yahoo", "capture_timestamp": "2026-09-05T00:00:00+00:00",
            "session_date": ts[:10], "price_observation_type": "DAILY_CLOSE",
            "timestamp_semantics": "DAILY_BAR", "volume_semantics": "DAILY_FINAL_VOLUME",
        })


def test_negative_daily_can_qualify_clean_correction():
    metrics = {
        "available": True,
        "daily_return_pct": -2.4,
        "return_1w_pct": -1.0,
        "return_1m_pct": 8.0,
        "return_3m_pct": 12.0,
        "rvol_20": 1.8,
        "dist_from_20d_high_pct": -5.0,
        "dist_from_60d_high_pct": -8.0,
        "last_close": 10,
        "sma_20": 9.8,
        "sma_50": 9.5,
        "breakout_20d": False,
        "breakout_60d": False,
        "realized_vol_20d_ann_pct": 28,
    }
    fams = classify_candidate_families(metrics)
    assert "CLEAN_CORRECTION" in fams
    assert prescreen_score(metrics) > 0


def test_top_daily_gainer_does_not_automatically_rank_first():
    gainer = {
        "ticker": "GAIN",
        "metrics": {
            "available": True, "daily_return_pct": 18.0, "return_1w_pct": 1.0,
            "return_1m_pct": 2.0, "rvol_20": 0.6, "dist_from_20d_high_pct": 0.1,
            "last_close": 12, "sma_20": 11, "sma_50": 10, "breakout_20d": False,
            "breakout_60d": False, "realized_vol_20d_ann_pct": 20,
        },
    }
    correction = {
        "ticker": "PULL",
        "metrics": {
            "available": True, "daily_return_pct": -2.0, "return_1w_pct": -1.0,
            "return_1m_pct": 9.0, "return_3m_pct": 14.0, "rvol_20": 2.6,
            "dist_from_20d_high_pct": -4.5, "last_close": 10, "sma_20": 9.7,
            "sma_50": 9.2, "breakout_20d": False, "breakout_60d": False,
            "realized_vol_20d_ann_pct": 30,
        },
    }
    top = select_handoff_candidates([gainer, correction], max_handoff=2)
    assert top[0]["ticker"] == "PULL"
    assert any("RVOL" in r or "relative_volume" in r for r in top[0]["candidate_reasons"])


def test_intraday_only_shortlist_missing_interval_ok():
    queried: list[tuple] = []

    def fetch(symbol, interval, n_bars):
        queried.append((symbol, interval))
        if interval == "1m":
            raise RuntimeError("interval unavailable")
        return [Candle(
            symbol=symbol, interval=interval, timestamp="2026-09-04T11:00:00+00:00",
            open=1, high=1, low=1, close=1, volume=10, provider="tradingview",
            capture_timestamp="2026-09-04T11:01:00+00:00",
            normalized_utc_timestamp="2026-09-04T11:00:00+00:00",
            normalized_cairo_timestamp="2026-09-04T14:00:00+03:00",
            timestamp_semantics="BAR_OPEN", volume_semantics="BAR_VOLUME",
        )]

    pack = enrich_shortlist_intraday(["COMI", "MASR"], fetch_candles=fetch)
    assert pack["queried_tickers"] == ["COMI", "MASR"]
    assert pack["intraday_enriched"] == 2
    assert any(r["interval"] == "1m" and r["available"] is False for r in pack["rows"])
    assert all(r["latest_timestamp_utc"] is None or "T" in r["latest_timestamp_utc"] for r in pack["rows"] if r["available"])


def test_handoff_manifest_objects_zip_and_unavailable_retained(tmp_path: Path):
    store = AnalysisStore(tmp_path / "a.sqlite", environment=UNIT_TEST)
    db = Database(tmp_path / "m.sqlite")
    _seed_daily(db, "COMI", n=60, pattern="up")
    funnel = FunnelRegistry(
        workspace_root=tmp_path / "funnels", store=store, db=db, environment=UNIT_TEST,
    )
    out = tmp_path / "exp"
    res = prepare_explorer_handoff(
        ExplorerRunConfig(universe=["COMI", "MASR", "EGX30"], enrich_intraday=False, environment=UNIT_TEST),
        db=db, store=store, funnel_registry=funnel, output_root=out,
    )
    assert Path(res["zip_path"]).exists()
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert isinstance(man["funnel_status_counts"], dict)
    assert isinstance(man["previous_analysis_status"], dict)
    assert isinstance(man["coverage"], dict)
    assert "MASR" in (out / "universe_failures.csv").read_text(encoding="utf-8")
    uni_csv = (out / "universe.csv").read_text(encoding="utf-8")
    assert "EGX30" in uni_csv
    assert "EXCLUDED_INDEX" in uni_csv
    counts = json.loads((out / "universe_summary.json").read_text())["counts"]
    assert counts["UNIVERSE_TOTAL"] == 3
    assert counts["HANDOFF_CANDIDATES"] == res["handoff_candidate_count"]
    payload = json.loads((out / "explorer_handoff.json").read_text())
    comi = next(c for c in payload["candidates"] if c["ticker"] == "COMI")
    assert comi["fair_value_manufactured"] is False
    assert comi["orders_generated"] is False
    store.close()
    db.close()


def test_insufficient_coverage_blocks_market_wide_confidence():
    cov = classify_explorer_coverage(
        equity_universe_total=139, mapped_symbols=139,
        daily_data_available=4, scanner_eligible=4,
    )
    assert cov["EXPLORER_COVERAGE"] == "INSUFFICIENT"
    assert cov["market_wide_confidence_allowed"] is False
