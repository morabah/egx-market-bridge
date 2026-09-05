from __future__ import annotations

from typing import Any
import time
import requests

from .base import (
    MarketDataProvider,
    ProviderCapabilities,
    Quote,
    ProviderError,
    utc_now_iso,
)


class BorsaProvider(MarketDataProvider):
    """Optional HTTP client for self-hosted or demo borsa API (MIT).

    Does not embed borsa. Configure borsa_base_url (e.g. http://localhost:8000).
    """

    name = "borsa"

    def __init__(self, base_url: str = "", enabled: bool = False, timeout: int = 15, symbol_resolver=None):
        # Default disabled unless URL configured — avoid hammering public demo.
        super().__init__(enabled=enabled and bool(base_url))
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout
        self.symbol_resolver = symbol_resolver
        self.mode = "http"
        self.session = requests.Session()

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            quote=True,
            market_universe=True,
            volume=True,
        )

    def status(self):
        from egxbridge import provider_health as ph

        st = super().status()
        st.mode = self.mode
        st.provider_type = ph.TYPE_HTTP
        st.main_role = ph.MAIN_ROLE.get(self.name, "Fallback quotes/universe")
        if not self.enabled:
            return st
        st.auth_status = ph.AUTH_NOT_REQUIRED
        st.authenticated = None
        if self._last_success and not self._last_error:
            st.reachable = True
            st.health_state = ph.ACTIVE
        elif self._last_error:
            http = self._last_http_status or ph.extract_http_status(self._last_error)
            if http in (401, 403):
                st.reachable = True
                st.authenticated = False
                st.auth_status = ph.AUTH_REQUIRED_STATUS
                st.health_state = ph.AUTH_REQUIRED
                st.last_http_status = http
            elif ph.is_network_failure(self._last_error, http):
                st.reachable = False
                st.health_state = ph.UNAVAILABLE
            else:
                st.reachable = True if http else self._reachable
                st.health_state = ph.ERROR
        return st

    def _get(self, path: str, params: dict | None = None) -> Any:
        if not self.enabled or not self.base_url:
            raise ProviderError(self.name, "Borsa disabled or base_url empty")
        url = f"{self.base_url}{path}"
        start = time.time()
        try:
            r = self.session.get(url, params=params, timeout=self.timeout)
            self._latency_ms = (time.time() - start) * 1000
            if r.status_code >= 400:
                self.record_failure(f"HTTP {r.status_code}: {r.text[:300]}", http_status=r.status_code)
                raise ProviderError(self.name, f"HTTP {r.status_code}: {r.text[:300]}", http_status=r.status_code)
            self.record_success()
            return r.json()
        except ProviderError:
            raise
        except Exception as e:
            self._latency_ms = (time.time() - start) * 1000
            self.record_failure(str(e))
            raise ProviderError(self.name, str(e)) from e

    def get_quote(self, symbol: str) -> Quote:
        mapped = symbol.upper()
        if self.symbol_resolver:
            mapped = self.symbol_resolver.to_provider(symbol, "borsa")
        data = self._get(f"/v1/quote/{mapped}")
        capture = utc_now_iso()
        # Flexible field extraction
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
            data = data["data"]
        last = _num(data.get("price") or data.get("last") or data.get("close"))
        self._last_success = capture
        self._last_error = None
        return Quote(
            symbol=symbol.upper(),
            provider=self.name,
            capture_timestamp=capture,
            last=last,
            open=_num(data.get("open")),
            high=_num(data.get("high")),
            low=_num(data.get("low")),
            volume=_num(data.get("volume")),
            change_pct=_num(data.get("change_percent") or data.get("change_pct")),
            provider_timestamp=str(data.get("timestamp") or data.get("as_of") or "") or None,
            provider_mode=self.mode,
            raw_reference=f"borsa:{mapped}",
        )

    def get_universe(self) -> list[dict[str, Any]]:
        data = self._get("/v1/stocks")
        rows = data if isinstance(data, list) else data.get("data") or data.get("stocks") or []
        out = []
        for r in rows:
            if isinstance(r, str):
                out.append({"canonical": r.upper(), "name": "", "source": "borsa"})
            elif isinstance(r, dict):
                sym = str(r.get("symbol") or r.get("canonical") or r.get("ticker") or "").upper()
                if sym:
                    out.append({
                        "canonical": sym,
                        "name": r.get("name") or r.get("company") or "",
                        "aliases": r.get("providers") or r.get("aliases") or {},
                        "source": "borsa",
                    })
        self._last_success = utc_now_iso()
        return out

    def probe(self, symbol: str) -> dict[str, Any]:
        if not self.enabled:
            return {
                "provider": self.name,
                "enabled": False,
                "status": "DISABLED",
                "note": "Set providers.borsa.enabled=true and borsa_base_url to use",
            }
        out: dict[str, Any] = {"provider": self.name, "base_url": self.base_url, "symbol": symbol}
        try:
            health = self._get("/v1/health")
            out["health"] = {"ok": True, "data": health}
        except Exception as e:
            out["health"] = {"ok": False, "error": str(e)}
        try:
            q = self.get_quote(symbol)
            out["quote"] = {"ok": True, "last": q.last, "latest_timestamp": q.provider_timestamp}
        except Exception as e:
            out["quote"] = {"ok": False, "error": str(e)}
        try:
            uni = self.get_universe()
            out["universe"] = {"ok": True, "count": len(uni)}
        except Exception as e:
            out["universe"] = {"ok": False, "error": str(e)}
        out["status"] = "OK" if out.get("quote", {}).get("ok") or out.get("health", {}).get("ok") else "ERROR"
        return out


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None
