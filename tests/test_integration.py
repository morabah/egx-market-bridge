"""Optional live integration tests. Not required for normal pytest success."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_yahoo_live_comi():
    from egxbridge.symbols import SymbolRegistry
    from egxbridge.providers.yahoo import YahooProvider

    reg = SymbolRegistry()
    p = YahooProvider(reg)
    q = p.get_quote("COMI")
    assert q.last is not None
    candles = p.get_candles("COMI", "1d", n_bars=5)
    assert len(candles) >= 1
