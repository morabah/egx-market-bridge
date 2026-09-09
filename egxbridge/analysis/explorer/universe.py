"""Explorer universe assembly — whole-EGX discovery without silent drops."""
from __future__ import annotations

from typing import Any

from egxbridge.universe import build_canonical_universe, assess_universe_coverage


def build_explorer_universe(
    db=None,
    *,
    explicit: list[str] | None = None,
    min_scanner_bars: int = 20,
    as_of=None,
) -> dict[str, Any]:
    """Assemble whole-EGX discovery universe. Never silently drop unavailable symbols."""
    built = build_canonical_universe(db=db, explicit=explicit)
    assessed = assess_universe_coverage(
        built, db=db, min_scanner_bars=min_scanner_bars, stock_explorer_only=True, as_of=as_of,
    )
    # Old Explorer tests iterate MAPPED_SYMBOLS as the discovery list (do not drop).
    discovery = list(assessed.get("all_symbols") or [])
    assessed["DISCOVERY_SYMBOLS"] = discovery
    assessed["MAPPED_SYMBOLS"] = discovery
    assessed["YAHOO_MAPPED_SYMBOLS"] = [
        s for s, st in (assessed.get("status_by_symbol") or {}).items()
        if st.get("mapped")
    ]
    assessed["UNIVERSE_TOTAL"] = len(discovery)
    assessed["universe_total"] = len(discovery)
    return assessed
