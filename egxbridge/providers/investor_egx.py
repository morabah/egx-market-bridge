from __future__ import annotations

from typing import Any
import json
from pathlib import Path

from .base import (
    MarketDataProvider,
    ProviderCapabilities,
    ProviderError,
    utc_now_iso,
)


class InvestorEGXProvider(MarketDataProvider):
    """Optional adapter for universe / fundamental discovery.

    Does not vendor investor-egx. Supports:
    - loading a local universe JSON exported by investor-egx or hand-maintained
    - optional path to an investor-egx SQLite DB (read-only) if present
    """

    name = "investor_egx"
    provider_type = "local_import"

    def __init__(
        self,
        enabled: bool = True,
        universe_path: str = "",
        sqlite_path: str = "",
        symbol_resolver=None,
    ):
        super().__init__(enabled=enabled)
        self.universe_path = universe_path
        self.sqlite_path = sqlite_path
        self.symbol_resolver = symbol_resolver
        self.mode = "import"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            market_universe=True,
            fundamentals=True,
            daily_ohlcv=False,
        )

    def status(self):
        from egxbridge import provider_health as ph

        st = super().status()
        st.provider_type = ph.TYPE_LOCAL_IMPORT
        st.mode = self.mode
        st.main_role = ph.MAIN_ROLE.get(self.name, "Universe/Fundamentals")
        st.reachable = None
        st.authenticated = None
        st.auth_status = ph.AUTH_NOT_APPLICABLE
        st.last_http_status = None

        if not self.enabled:
            return st

        # Local/import adapter is available when enabled (seed universe always works).
        st.health_state = ph.LOCAL_AVAILABLE
        st.notes = (
            "Local/import adapter — reachable/auth N/A. "
            "Capability=true does not imply current-run data for a symbol."
        )
        if self._last_error and "unavailable" in (self._last_error or "").lower():
            st.health_state = ph.LOCAL_UNAVAILABLE
            st.notes = self._last_error
        return st

    def get_universe(self) -> list[dict[str, Any]]:
        if not self.enabled:
            raise ProviderError(self.name, "investor_egx disabled")
        # Prefer explicit universe file
        if self.universe_path and Path(self.universe_path).exists():
            data = json.loads(Path(self.universe_path).read_text(encoding="utf-8"))
            rows = data if isinstance(data, list) else data.get("symbols") or data.get("tickers") or []
            out = []
            for r in rows:
                if isinstance(r, str):
                    out.append({"canonical": r.upper(), "name": "", "source": "investor_egx"})
                elif isinstance(r, dict):
                    sym = str(r.get("symbol") or r.get("ticker") or r.get("canonical") or "").upper()
                    if sym:
                        out.append({
                            "canonical": sym,
                            "name": r.get("name") or "",
                            "aliases": r.get("aliases") or {},
                            "source": "investor_egx",
                        })
            self._last_success = utc_now_iso()
            return out

        if self.sqlite_path and Path(self.sqlite_path).exists():
            import sqlite3
            conn = sqlite3.connect(str(self.sqlite_path))
            conn.row_factory = sqlite3.Row
            # Try common table names from investor-egx
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            out = []
            for table in ("tickers", "symbols", "universe"):
                if table in tables:
                    cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()]
                    sym_col = next((c for c in cols if c.lower() in {"symbol", "ticker", "canonical"}), None)
                    name_col = next((c for c in cols if c.lower() in {"name", "company", "company_name"}), None)
                    if not sym_col:
                        continue
                    for row in conn.execute(f"SELECT * FROM {table}").fetchall():
                        d = dict(row)
                        sym = str(d.get(sym_col, "")).upper()
                        if sym:
                            out.append({
                                "canonical": sym,
                                "name": str(d.get(name_col, "")) if name_col else "",
                                "source": "investor_egx_sqlite",
                            })
                    break
            conn.close()
            self._last_success = utc_now_iso()
            return out

        # Built-in seed universe (not claimed complete)
        seed = ["COMI", "MASR", "RAYA", "LUTS", "KASABF", "HRHO", "ETEL", "EFID", "TMGH", "ORWE"]
        self._last_success = utc_now_iso()
        return [
            {"canonical": s, "name": "", "source": "seed", "note": "incomplete seed; not full EGX"}
            for s in seed
        ]

    def get_fundamentals(self, symbol: str) -> dict[str, Any]:
        if self.sqlite_path and Path(self.sqlite_path).exists():
            import sqlite3
            conn = sqlite3.connect(str(self.sqlite_path))
            conn.row_factory = sqlite3.Row
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            for table in ("fundamentals", "fundamental"):
                if table not in tables:
                    continue
                cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()]
                sym_col = next((c for c in cols if c.lower() in {"symbol", "ticker"}), None)
                if not sym_col:
                    continue
                row = conn.execute(
                    f"SELECT * FROM {table} WHERE UPPER({sym_col})=?",
                    (symbol.upper(),),
                ).fetchone()
                conn.close()
                if row:
                    payload = dict(row)
                    self._last_success = utc_now_iso()
                    return {
                        "symbol": symbol.upper(),
                        "provider": self.name,
                        "as_of": payload.get("as_of") or payload.get("date"),
                        "fields": payload,
                        "note": "Aggregated/imported fundamentals — not official EGX/FRA filings",
                    }
                break
            conn.close()
        raise ProviderError(self.name, f"No fundamentals for {symbol} (provide investor_egx sqlite_path)")

    def probe(self, symbol: str) -> dict[str, Any]:
        if not self.enabled:
            return {"provider": self.name, "enabled": False, "status": "DISABLED"}
        out: dict[str, Any] = {"provider": self.name, "symbol": symbol}
        try:
            uni = self.get_universe()
            out["universe"] = {
                "ok": True,
                "count": len(uni),
                "note": "Do not claim complete EGX coverage unless verified",
                "sample": [u["canonical"] for u in uni[:10]],
            }
        except Exception as e:
            out["universe"] = {"ok": False, "error": str(e)}
        try:
            f = self.get_fundamentals(symbol)
            out["fundamentals"] = {"ok": True, "as_of": f.get("as_of"), "note": f.get("note")}
        except Exception as e:
            out["fundamentals"] = {"ok": False, "error": str(e)}
        out["status"] = "OK" if out.get("universe", {}).get("ok") else "ERROR"
        return out
