from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from egxbridge.db import Database
from egxbridge.providers.base import Candle, ProviderError
from egxbridge.symbols import SymbolRegistry
from egxbridge.collect_universe import collect_universe_daily, merge_daily_candles, _bar_count
from egxbridge.semantics import DAILY_BAR, DAILY_CLOSE, DAILY_FINAL_VOLUME
from egxbridge.scanner import compute_scanner_metrics


class FakeYahoo:
    name = "yahoo"
    enabled = True
    mode = "delayed"
    _latency_ms = 7.0

    def __init__(self):
        self.calls: list[tuple] = []
        self.fail = set()

    def get_candles(self, symbol: str, interval: str = "1d", n_bars: int = 100, *, start: str | None = None):
        self.calls.append((symbol.upper(), interval, n_bars, start))
        if symbol.upper() in self.fail:
            raise ProviderError(self.name, f"No Yahoo candles for {symbol}.CA interval={interval}")
        n = min(int(n_bars), 130)
        base = date(2025, 1, 2)
        out = []
        for i in range(n):
            d = base + timedelta(days=i)
            ts = f"{d.isoformat()}T00:00:00+00:00"
            close = 10.0 + (i % 5) * 0.1
            out.append(Candle(
                symbol=symbol.upper(),
                interval="1d",
                timestamp=ts,
                open=close,
                high=close + 0.2,
                low=close - 0.2,
                close=close,
                volume=1000 + i,
                provider="yahoo",
                capture_timestamp="2026-09-05T00:00:00+00:00",
                freshness_class="DELAYED",
                provider_mode="delayed",
                volume_semantics=DAILY_FINAL_VOLUME,
                session_date=d.isoformat(),
                normalized_utc_timestamp=ts,
                normalized_cairo_timestamp=f"{d.isoformat()}T02:00:00+03:00",
                timestamp_semantics=DAILY_BAR,
            ))
        return out


def test_one_ticker_failure_does_not_stop_universe(tmp_path: Path):
    db = Database(tmp_path / "m.sqlite")
    yahoo = FakeYahoo()
    yahoo.fail.add("FAILME")
    res = collect_universe_daily(
        db=db, symbols=["COMI", "FAILME"], yahoo=yahoo, max_workers=1, min_cache_bars=10_000,
        history_days=130, refresh=True,
    )
    by = {r["ticker"]: r for r in res["results"]}
    assert by["COMI"]["status"] in {"SUCCESS", "STALE_EXPECTED", "STALE_UNEXPECTED"}
    assert by["FAILME"]["status"] in {"NO_DATA", "PROVIDER_ERROR", "INVALID_SYMBOL"}
    assert _bar_count(db, "COMI") >= 100
    db.close()


def test_incremental_update_deduplicates_and_preserves_provenance(tmp_path: Path):
    db = Database(tmp_path / "m.sqlite")
    yahoo = FakeYahoo()
    collect_universe_daily(
        db=db, symbols=["COMI"], yahoo=yahoo, max_workers=1, min_cache_bars=10_000,
        history_days=130, refresh=True,
    )
    n1 = _bar_count(db, "COMI")
    collect_universe_daily(
        db=db, symbols=["COMI"], yahoo=yahoo, max_workers=1, min_cache_bars=10,
        history_days=130, refresh=False,
    )
    n2 = _bar_count(db, "COMI")
    assert n2 == n1
    assert any(c[3] is not None for c in yahoo.calls[1:])  # incremental start= used
    row = db.fetch_candles("COMI", "1d", limit=1)[0]
    assert row["provider"] == "yahoo"
    assert row.get("price_observation_type") == DAILY_CLOSE
    assert row.get("timestamp_semantics") == DAILY_BAR
    assert row.get("volume_semantics") == DAILY_FINAL_VOLUME
    db.close()


def test_cached_history_reused_when_already_current(tmp_path: Path):
    db = Database(tmp_path / "m.sqlite")
    today = date.today().isoformat()
    ts = f"{today}T00:00:00+00:00"
    for i in range(125):
        d = (date.today() - timedelta(days=124 - i)).isoformat()
        db.upsert_candle({
            "symbol": "COMI", "interval": "1d",
            "timestamp": f"{d}T00:00:00+00:00",
            "normalized_utc_timestamp": f"{d}T00:00:00+00:00",
            "open": 10, "high": 10.1, "low": 9.9, "close": 10, "volume": 1000,
            "provider": "yahoo", "capture_timestamp": ts,
            "session_date": d,
            "price_observation_type": DAILY_CLOSE,
            "timestamp_semantics": DAILY_BAR,
            "volume_semantics": DAILY_FINAL_VOLUME,
        })
    yahoo = FakeYahoo()
    res = collect_universe_daily(
        db=db, symbols=["COMI"], yahoo=yahoo, max_workers=1, min_cache_bars=120,
        history_days=130, refresh=False,
    )
    by = {r["ticker"]: r for r in res["results"]}
    assert by["COMI"]["cache_hit"] is True or by["COMI"]["incremental"] is True
    db.close()


def test_merge_conflict_logged_not_silent_overwrite(tmp_path: Path):
    db = Database(tmp_path / "m.sqlite")
    ts = "2026-01-02T00:00:00+00:00"
    db.upsert_candle({
        "symbol": "COMI", "interval": "1d", "timestamp": ts,
        "normalized_utc_timestamp": ts, "open": 10, "high": 11, "low": 9, "close": 10.5,
        "volume": 100, "provider": "yahoo", "capture_timestamp": ts,
        "price_observation_type": DAILY_CLOSE,
    })
    merge_daily_candles(db, [{
        "symbol": "COMI", "interval": "1d", "timestamp": ts,
        "normalized_utc_timestamp": ts, "open": 12, "high": 13, "low": 11, "close": 12.5,
        "volume": 200, "provider": "yahoo", "capture_timestamp": ts,
        "price_observation_type": DAILY_CLOSE,
        "timestamp_semantics": DAILY_BAR,
        "volume_semantics": DAILY_FINAL_VOLUME,
    }], refresh=False)
    row = db.fetch_candles("COMI", "1d", limit=1)[0]
    assert row["close"] == 10.5
    assert db.fetch_conflicts()
    db.close()


def test_scanner_formulas_unchanged_and_false_breakout():
    candles = []
    base = 10.0
    for i in range(30):
        high = base + 2
        close = base if i < 29 else base - 1  # last close below 20d high
        candles.append({
            "timestamp": f"2026-01-{i+1:02d}T00:00:00+00:00",
            "normalized_utc_timestamp": f"2026-01-{i+1:02d}T00:00:00+00:00",
            "open": base, "high": high, "low": base - 0.5, "close": close, "volume": 1000 + i,
        })
    m = compute_scanner_metrics(candles)
    assert m["available"] is True
    assert m["breakout_flag_20d"] is False
    assert m["breakout_20d"] is False
    assert m["note"].startswith("Metrics from candles only")
    short = compute_scanner_metrics(candles[:5])
    assert short["sma_50"] is None
    assert short["return_6m_pct"] is None
    assert short["available"] is True
