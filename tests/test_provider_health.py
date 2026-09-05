from __future__ import annotations

from pathlib import Path

import pytest

from egxbridge import provider_health as ph
from egxbridge.db import Database
from egxbridge.provider_health import serialize_status_for_display
from egxbridge.providers.egid import EGIDAdapter
from egxbridge.providers.yahoo import YahooProvider
from egxbridge.providers.tradingview import TradingViewProvider
from egxbridge.providers.investor_egx import InvestorEGXProvider
from egxbridge.providers.borsa import BorsaProvider


class _Resolver:
    def to_provider(self, symbol: str, provider: str) -> str:
        if provider == "yahoo":
            return f"{symbol.upper()}.CA"
        if provider == "tradingview":
            return f"EGX:{symbol.upper()}"
        return symbol.upper()


def _egid_shell() -> EGIDAdapter:
    """Build EGID adapter without network swagger fetch."""
    p = EGIDAdapter(
        "https://example.invalid",
        "https://example.invalid/swagger.json",
        enabled=False,
        token="",
    )
    p.enabled = True
    p.mode = "delayed"
    return p


def test_http_401_reachable_auth_required():
    p = _egid_shell()
    p.record_failure("HTTP 401: Unauthorized", http_status=401)
    p._latency_ms = 42.5
    st = p.status()
    assert st.reachable is True
    assert st.authenticated is False
    assert st.auth_status in {ph.AUTH_LICENSE_REQUIRED, ph.AUTH_REQUIRED_STATUS}
    assert st.health_state in {ph.LICENSE_REQUIRED, ph.AUTH_REQUIRED}
    assert st.last_http_status == 401
    assert st.latency_ms == 42.5
    assert "token" in (st.notes or "").lower() or "license" in (st.notes or "").lower() or "auth" in (st.last_error or "").lower()


def test_http_403_reachable_license_or_auth_required():
    p = _egid_shell()
    p.record_failure("HTTP 403: Forbidden", http_status=403)
    st = p.status()
    assert st.reachable is True
    assert st.authenticated is False
    assert st.health_state in {ph.LICENSE_REQUIRED, ph.AUTH_REQUIRED}
    assert st.last_http_status == 403


def test_timeout_reachable_false():
    p = _egid_shell()
    p.record_failure("HTTPSConnectionPool: Read timed out.", http_status=None)
    st = p.status()
    assert st.reachable is False
    assert st.health_state == ph.UNAVAILABLE


def test_tradingview_anonymous_active():
    tv = TradingViewProvider(_Resolver(), enabled=True)
    # Simulate successful anonymous backend without requiring live network
    tv._tv = object()
    tv._backend = "tvDatafeed"
    tv.mode = "anonymous"
    tv.record_success()
    st = tv.status()
    assert st.health_state == ph.ACTIVE_ANONYMOUS
    assert st.auth_status == ph.AUTH_ANONYMOUS
    assert st.authenticated is None
    assert st.reachable is True
    assert st.mode == "anonymous"


def test_yahoo_active_not_required_auth():
    y = YahooProvider(_Resolver(), enabled=True)
    y.record_success()
    st = y.status()
    assert st.health_state == ph.ACTIVE
    assert st.auth_status == ph.AUTH_NOT_REQUIRED
    assert st.authenticated is None
    assert st.reachable is True


def test_investor_egx_local_available():
    inv = InvestorEGXProvider(enabled=True)
    st = inv.status()
    assert st.health_state == ph.LOCAL_AVAILABLE
    assert st.reachable is None
    assert st.authenticated is None
    assert st.auth_status == ph.AUTH_NOT_APPLICABLE
    assert st.provider_type == ph.TYPE_LOCAL_IMPORT


def test_borsa_disabled():
    b = BorsaProvider(base_url="", enabled=False)
    st = b.status()
    assert st.enabled is False
    assert st.health_state == ph.DISABLED
    assert st.auth_status == ph.AUTH_NOT_APPLICABLE
    assert st.reachable is None


def test_capability_true_current_data_false_valid():
    inv = InvestorEGXProvider(enabled=True)
    caps = inv.capabilities().as_dict()
    assert caps["fundamentals"] is True
    # Simulate current run: capability remains true, current data unavailable
    run = {
        "provider": "investor_egx",
        "capabilities": caps,
        "fundamentals_available": False,
    }
    assert run["capabilities"]["fundamentals"] is True
    assert run["fundamentals_available"] is False


def test_serialize_preserves_null_na(tmp_path: Path):
    inv = InvestorEGXProvider(enabled=True)
    st = inv.status().to_dict()
    row = serialize_status_for_display(st)
    assert row["reachable"] == "N/A"
    assert row["auth"] == "N/A"
    assert row["state"] == ph.LOCAL_AVAILABLE

    db = Database(tmp_path / "t.sqlite")
    db.upsert_provider_status(st)
    fetched = db.fetch_provider_status()
    assert len(fetched) == 1
    assert fetched[0]["reachable"] is None
    assert fetched[0]["authenticated"] is None
    assert fetched[0]["health_state"] == ph.LOCAL_AVAILABLE
    assert fetched[0]["auth_status"] == ph.AUTH_NOT_APPLICABLE
    db.close()


def test_classify_helpers():
    assert ph.classify_http_reachability("HTTP 401 Unauthorized", 401) is True
    assert ph.classify_http_reachability("HTTP 403 Forbidden", 403) is True
    assert ph.classify_http_reachability("Connection timed out") is False
    assert ph.is_network_failure("Read timed out") is True
    assert ph.is_network_failure("HTTP 401", 401) is False
