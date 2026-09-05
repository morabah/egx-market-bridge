from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import time

import pytest

from egxbridge.symbols import SymbolRegistry
from egxbridge.freshness import classify_freshness, FreshnessThresholds, parse_timestamp
from egxbridge.conflicts import select_observation, values_conflict
from egxbridge.quality import score_symbol
from egxbridge.db import Database
from egxbridge.providers.base import ProviderCapabilities, Capability, AuthRequiredError
from egxbridge.providers.manager import ProviderManager
from egxbridge.providers.base import MarketDataProvider, Quote, Candle, utc_now_iso
from egxbridge.storage import write_handoff, write_scanner_handoff
from egxbridge.scanner import compute_scanner_metrics


class FakeProvider(MarketDataProvider):
    name = "fake"

    def __init__(self, enabled=True, fail=False, last=10.0, ts=None):
        super().__init__(enabled=enabled)
        self.fail = fail
        self.last = last
        self.ts = ts or utc_now_iso()
        self.mode = "test"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(quote=True, daily_ohlcv=True, volume=True)

    def get_quote(self, symbol: str) -> Quote:
        if self.fail:
            raise AuthRequiredError(self.name, "LICENSE/AUTH REQUIRED", http_status=401)
        return Quote(
            symbol=symbol,
            provider=self.name,
            capture_timestamp=utc_now_iso(),
            last=self.last,
            volume=1000,
            provider_timestamp=self.ts,
            provider_mode=self.mode,
        )

    def get_candles(self, symbol: str, interval: str = "1d", n_bars: int = 100):
        if self.fail:
            raise RuntimeError("fail")
        return [
            Candle(
                symbol=symbol,
                interval=interval,
                timestamp=self.ts,
                open=1, high=2, low=0.5, close=self.last, volume=100,
                provider=self.name,
                capture_timestamp=utc_now_iso(),
                provider_timestamp=self.ts,
            )
        ]


class FakeYahoo(FakeProvider):
    name = "yahoo"


class FakeTV(FakeProvider):
    name = "tradingview"


def test_symbol_mapping():
    reg = SymbolRegistry()
    assert reg.canonicalize("MASR.CA") == "MASR"
    assert reg.canonicalize("EGX:COMI") == "COMI"
    assert reg.to_provider("MASR", "yahoo") == "MASR.CA"
    assert reg.to_provider("COMI", "tradingview") == "EGX:COMI"
    assert reg.to_provider("RAYA", "egid") == "RAYA"


def test_provider_capabilities():
    caps = ProviderCapabilities(quote=True, depth=False)
    assert caps.supports(Capability.QUOTE)
    assert not caps.supports("depth")
    assert caps.as_dict()["quote"] is True


def test_freshness_classification():
    now = datetime.now(timezone.utc)
    th = FreshnessThresholds(15, 120, 1200)
    assert classify_freshness(now.isoformat(), now.isoformat(), th)[0] == "LIVE"
    assert classify_freshness((now - timedelta(seconds=60)).isoformat(), now.isoformat(), th)[0] == "FRESH"
    assert classify_freshness((now - timedelta(minutes=10)).isoformat(), now.isoformat(), th)[0] == "DELAYED"
    stale_cls, _ = classify_freshness((now - timedelta(hours=2)).isoformat(), now.isoformat(), th)
    assert stale_cls in {"STALE_EXPECTED", "STALE_UNEXPECTED"}
    assert classify_freshness(None, now.isoformat(), th)[0] == "UNKNOWN"


def test_stale_expected_on_weekend():
    from egxbridge.freshness import egx_session_open_at
    # Saturday 2026-09-05 12:00 Cairo ≈ 09:00 UTC
    saturday = datetime(2026, 9, 5, 9, 0, tzinfo=timezone.utc)
    assert egx_session_open_at(saturday) is False
    cls, _ = classify_freshness(
        "2026-09-03T14:25:00+00:00",
        saturday.isoformat(),
        FreshnessThresholds(),
    )
    assert cls == "STALE_EXPECTED"


def test_stale_unexpected_during_session():
    from egxbridge.freshness import egx_session_open_at
    # Monday 2026-09-07 11:00 Cairo = 08:00 UTC
    monday_session = datetime(2026, 9, 7, 8, 0, tzinfo=timezone.utc)
    assert egx_session_open_at(monday_session) is True
    cls, _ = classify_freshness(
        "2026-09-03T14:25:00+00:00",
        monday_session.isoformat(),
        FreshnessThresholds(),
    )
    assert cls == "STALE_UNEXPECTED"


def test_circuit_breaker_closed_open_half_open_closed():
    from egxbridge.resilience import CircuitBreaker
    br = CircuitBreaker(fail_threshold=3, cool_down_seconds=0.05)
    assert br.state == CircuitBreaker.CLOSED
    assert br.allow() is True
    br.record_failure()
    br.record_failure()
    assert br.state == CircuitBreaker.CLOSED
    br.record_failure()
    assert br.state == CircuitBreaker.OPEN
    assert br.allow() is False
    time.sleep(0.06)
    assert br.allow() is True  # transitions to HALF_OPEN, consumes probe
    assert br.state == CircuitBreaker.HALF_OPEN
    assert br.allow() is False  # only one probe
    br.record_success()
    assert br.state == CircuitBreaker.CLOSED
    assert br.allow() is True


def test_parse_timestamp():
    assert parse_timestamp("2026-09-05T10:00:00+00:00") is not None
    assert parse_timestamp(1725537600) is not None or parse_timestamp("1725537600") is not None


def test_conflict_resolution_no_average():
    now = utc_now_iso()
    cands = [
        {"provider": "tradingview", "value": 7.65, "provider_timestamp": now, "freshness_seconds": 10},
        {"provider": "yahoo", "value": 7.61, "provider_timestamp": now, "freshness_seconds": 900},
    ]
    sel = select_observation(cands, priority=["tradingview", "yahoo"], created_at=now, field="last", symbol="MASR")
    assert sel.selected_value == 7.65
    assert sel.selected_provider == "tradingview"
    assert sel.conflict is not None
    assert sel.selected_value != (7.65 + 7.61) / 2


def test_values_conflict_tolerance():
    assert values_conflict(7.65, 7.61)
    assert not values_conflict(7.65, 7.6501, rel_tol=0.01, abs_tol=0.1)


def test_sqlite_upsert_candles(tmp_path: Path):
    db = Database(tmp_path / "t.sqlite")
    c = {
        "symbol": "MASR", "interval": "1d", "timestamp": "2026-09-01T00:00:00+00:00",
        "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100,
        "provider": "yahoo", "capture_timestamp": utc_now_iso(), "freshness_class": "DELAYED",
        "provider_mode": "delayed",
    }
    db.upsert_candle(c)
    db.upsert_candle({**c, "close": 1.6, "capture_timestamp": utc_now_iso()})
    rows = db.fetch_candles("MASR", "1d")
    assert len(rows) == 1
    assert rows[0]["close"] == 1.6
    db.close()


def test_fallback_when_primary_fails():
    egid = FakeProvider(fail=True)
    egid.name = "egid"
    yahoo = FakeYahoo(last=12.3)
    mgr = ProviderManager([egid, yahoo], priority={"quote": ["egid", "yahoo"]})
    result, name, errors = mgr.call_first("quote", "get_quote", "MASR")
    assert result is not None
    assert name == "yahoo"
    assert result.last == 12.3
    assert any(e.get("code") == "AUTH_REQUIRED" or "AUTH" in str(e) for e in errors)


def test_egid_401_auth_required_code():
    p = FakeProvider(fail=True)
    p.name = "egid"
    with pytest.raises(AuthRequiredError) as ei:
        p.get_quote("MASR")
    assert ei.value.code == "AUTH_REQUIRED"
    assert ei.value.http_status == 401


def test_missing_fields_quality():
    q = score_symbol(
        symbol="MASR",
        freshness_class="DELAYED",
        providers_used=["yahoo"],
        has_price=True,
        has_volume=True,
        has_daily=True,
        has_intraday=False,
        has_bid_ask=False,
        has_depth=False,
        has_trades=False,
        timestamp_known=True,
    )
    assert q.availability["Depth"] == "UNAVAILABLE"
    assert q.availability["Bid/Ask"] == "UNAVAILABLE"
    assert "bid_ask" in q.missing_execution_fields
    assert q.research_data_quality > q.execution_data_quality


def test_different_provider_timestamps_selection():
    now = datetime.now(timezone.utc)
    newer = now.isoformat()
    older = (now - timedelta(minutes=30)).isoformat()
    cands = [
        {"provider": "yahoo", "value": 10.0, "provider_timestamp": older, "freshness_seconds": 1800},
        {"provider": "tradingview", "value": 10.0, "provider_timestamp": newer, "freshness_seconds": 5},
    ]
    sel = select_observation(cands, priority=["yahoo", "tradingview"], created_at=now.isoformat(), field="last", symbol="X")
    # same value ~ no material conflict; priority picks yahoo
    assert sel.selected_provider == "yahoo"
    assert sel.conflict is None


def test_handoff_generation(tmp_path: Path):
    payload = {
        "generated_at": utc_now_iso(),
        "version": "0.3.0",
        "provider_mode": "delayed",
        "status": "OK",
        "symbols": [{
            "symbol": "MASR",
            "quote": {"last": 7.5, "provider": "yahoo", "volume": 1},
            "price": 7.5,
            "price_source": "yahoo",
            "freshness": "DELAYED",
            "research_data_quality": 70,
            "execution_data_quality": 30,
            "missing_execution_fields": ["depth"],
            "warnings": [],
        }],
    }
    write_handoff(tmp_path, payload)
    write_scanner_handoff(tmp_path, {"generated_at": payload["generated_at"], "candidates": payload["symbols"]})
    assert (tmp_path / "chatgpt_handoff.json").exists()
    assert (tmp_path / "chatgpt_handoff.md").exists()
    assert (tmp_path / "scanner_handoff.json").exists()
    md = (tmp_path / "chatgpt_handoff.md").read_text()
    assert "MASR" in md
    assert "Research DQ" in md


def test_scanner_metrics_no_accumulation_label():
    candles = []
    base = 10.0
    for i in range(80):
        candles.append({
            "timestamp": f"2026-01-{(i % 28) + 1:02d}",
            "open": base, "high": base + 1, "low": base - 1, "close": base + 0.1 * (i % 5),
            "volume": 1000 + i * 10,
        })
        base += 0.05
    m = compute_scanner_metrics(candles)
    assert m["available"] is True
    assert "rvol_20" in m
    # Must not emit accumulation/distribution as inferred states/flags
    assert "accumulation" not in {k.lower() for k in m}
    assert "distribution" not in {k.lower() for k in m}
    assert m.get("breakout_flag_20d") in (True, False)


def test_duplicate_candles_unique(tmp_path: Path):
    db = Database(tmp_path / "d.sqlite")
    for _ in range(3):
        db.upsert_candle({
            "symbol": "COMI", "interval": "5m", "timestamp": "2026-09-05T08:00:00+00:00",
            "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1,
            "provider": "tradingview", "capture_timestamp": utc_now_iso(),
            "freshness_class": "UNKNOWN", "provider_mode": "anonymous",
        })
    assert len(db.fetch_candles("COMI", "5m")) == 1
    db.close()
