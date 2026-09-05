from __future__ import annotations

from typing import Any
import time
import re

from ..normalize import normalize_quote, normalize_depth, normalize_trades, normalize_candles, unwrap_rows
from ..provider import EGIDProvider as LegacyEGIDProvider
from .base import (
    MarketDataProvider,
    ProviderCapabilities,
    ProviderStatus,
    Quote,
    Candle,
    ProviderError,
    AuthRequiredError,
    utc_now_iso,
)


def _is_auth_error(exc: Exception) -> bool:
    text = str(exc)
    return "HTTP 401" in text or "HTTP 403" in text or "401" in text and "Unauthorized" in text


class EGIDAdapter(MarketDataProvider):
    """Wraps the existing EGID Swagger client. 401/403 => AUTH_REQUIRED."""

    name = "egid"

    def __init__(
        self,
        base_url: str,
        swagger_url: str,
        timeout: int = 15,
        mode: str = "delayed",
        token: str = "",
        enabled: bool = True,
    ):
        super().__init__(enabled=enabled)
        self.mode = mode
        self.token = token
        self._legacy: LegacyEGIDProvider | None = None
        self._init_error: str | None = None
        if enabled:
            try:
                self._legacy = LegacyEGIDProvider(base_url, swagger_url, timeout, mode, token)
            except Exception as e:
                self._init_error = str(e)
                self._last_error = self._init_error

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            quote=True,
            daily_ohlcv=True,
            intraday_ohlcv=True,
            volume=True,
            bid_ask=True,
            depth=True,
            trades=True,
            trade_count=True,
        )

    def status(self) -> ProviderStatus:
        from egxbridge import provider_health as ph

        st = super().status()
        st.mode = self.mode
        st.provider_type = ph.TYPE_HTTP
        st.main_role = ph.MAIN_ROLE.get(self.name, "Depth/Trades/Feed")
        st.last_http_status = self._last_http_status

        if not self.enabled:
            return st

        has_token = bool(self.token)
        err = self._last_error or self._init_error
        http = self._last_http_status or ph.extract_http_status(err)

        if http in (401, 403) or (err and ("LICENSE" in err.upper() or "AUTH" in err.upper())):
            # Server responded — auth/license gap, not network down
            st.reachable = True
            st.authenticated = False
            st.auth_status = ph.AUTH_LICENSE_REQUIRED
            st.health_state = ph.LICENSE_REQUIRED
            st.last_http_status = http or 401
            st.last_error = err
            st.notes = "no token/license" if not has_token else (err or "LICENSE/AUTH REQUIRED")
            return st

        if err and ph.is_network_failure(err, http):
            st.reachable = False
            st.authenticated = False if not has_token else None
            st.auth_status = ph.AUTH_LICENSE_REQUIRED if not has_token else ph.AUTH_UNKNOWN
            st.health_state = ph.UNAVAILABLE
            st.last_error = err
            st.notes = err
            return st

        if has_token and self._last_success and not self._last_error:
            st.reachable = True
            st.authenticated = True
            st.auth_status = ph.AUTH_AUTHENTICATED
            st.health_state = ph.ACTIVE
            st.notes = ""
            return st

        # Enabled, no successful licensed call yet
        st.authenticated = False if not has_token else None
        st.auth_status = ph.AUTH_LICENSE_REQUIRED if not has_token else ph.AUTH_UNKNOWN
        if not has_token:
            st.health_state = ph.LICENSE_REQUIRED
            st.notes = "No EGID_TOKEN; DelayedFeed may require license"
            # Do not claim unreachable before a probe
            if st.reachable is False and not err:
                st.reachable = None
        elif self._last_success:
            st.reachable = True
            st.health_state = ph.ACTIVE
            st.authenticated = True
            st.auth_status = ph.AUTH_AUTHENTICATED
        return st

    def _client(self) -> LegacyEGIDProvider:
        if not self.enabled:
            raise ProviderError(self.name, "EGID provider disabled")
        if self._legacy is None:
            raise AuthRequiredError(self.name, f"EGID unavailable: {self._init_error or 'not initialized'}")
        return self._legacy

    def _wrap(self, fn, *args, **kwargs):
        start = time.time()
        try:
            result = fn(*args, **kwargs)
            self.record_success()
            self._latency_ms = (time.time() - start) * 1000
            return result
        except Exception as e:
            self._latency_ms = (time.time() - start) * 1000
            http = None
            m = re.search(r"HTTP\s+(\d{3})", str(e), re.I)
            if m:
                http = int(m.group(1))
            if _is_auth_error(e):
                http = http or 401
                msg = str(e) if "HTTP" in str(e) else f"HTTP {http}: LICENSE/AUTH REQUIRED"
                self.record_failure(msg, http_status=http)
                raise AuthRequiredError(self.name, "LICENSE/AUTH REQUIRED", http_status=http) from e
            self.record_failure(str(e), http_status=http)
            raise ProviderError(self.name, str(e), http_status=http) from e

    def get_quote(self, symbol: str) -> Quote:
        raw = self._wrap(self._client().quote, symbol)
        nq = normalize_quote(raw, symbol)
        capture = utc_now_iso()
        return Quote(
            symbol=symbol.upper(),
            provider=self.name,
            capture_timestamp=capture,
            last=nq.get("last"),
            open=nq.get("open"),
            high=nq.get("high"),
            low=nq.get("low"),
            prev_close=nq.get("prev_close"),
            change_pct=nq.get("change_pct"),
            volume=nq.get("volume"),
            turnover=nq.get("turnover"),
            trades=nq.get("trades"),
            bid=nq.get("bid"),
            bid_qty=nq.get("bid_qty"),
            ask=nq.get("ask"),
            ask_qty=nq.get("ask_qty"),
            provider_timestamp=str(nq.get("timestamp")) if nq.get("timestamp") else None,
            provider_mode=self.mode,
            raw_reference="egid:quote",
        )

    def get_candles(self, symbol: str, interval: str = "1d", n_bars: int = 100) -> list[Candle]:
        raw = self._wrap(self._client().chart, symbol)
        rows = normalize_candles(raw, symbol)[-n_bars:]
        capture = utc_now_iso()
        out = []
        for r in rows:
            out.append(Candle(
                symbol=symbol.upper(),
                interval=interval,
                timestamp=str(r.get("time") or capture),
                open=r.get("open"),
                high=r.get("high"),
                low=r.get("low"),
                close=r.get("close"),
                volume=r.get("volume"),
                provider=self.name,
                capture_timestamp=capture,
                provider_timestamp=str(r.get("time")) if r.get("time") else None,
                provider_mode=self.mode,
            ))
        return out

    def get_depth(self, symbol: str) -> list[dict[str, Any]]:
        raw = self._wrap(self._client().depth, symbol)
        return normalize_depth(raw, symbol)

    def get_trades(self, symbol: str) -> list[dict[str, Any]]:
        raw = self._wrap(self._client().trades, symbol)
        return normalize_trades(raw, symbol)

    def market_watch(self) -> Any:
        return self._wrap(self._client().market_watch)

    def probe(self, symbol: str) -> dict[str, Any]:
        if not self.enabled:
            return {"provider": self.name, "enabled": False, "status": "DISABLED"}
        if self._legacy is None:
            return {
                "provider": self.name,
                "status": "AUTH_REQUIRED" if not self.token else "UNAVAILABLE",
                "error": self._init_error,
                "HTTP": None,
                "health": self.status().to_dict(),
            }
        results = {}
        overall = "OK"
        try:
            legacy_results = self._client().probe(symbol)
        except Exception as e:
            if _is_auth_error(e):
                self.record_failure(str(e) if "HTTP" in str(e) else "HTTP 401: LICENSE/AUTH REQUIRED", http_status=401)
                return {
                    "provider": self.name,
                    "status": "AUTH_REQUIRED",
                    "HTTP": 401,
                    "error": str(e),
                    "health": self.status().to_dict(),
                }
            self.record_failure(str(e))
            return {"provider": self.name, "status": "ERROR", "error": str(e), "health": self.status().to_dict()}

        auth_hits = 0
        ok_hits = 0
        for item in legacy_results:
            name = item.get("name", "?")
            if item.get("ok"):
                results[name] = {"ok": True, "path": item.get("path"), "preview": item.get("preview", "")[:200]}
                ok_hits += 1
            else:
                err = item.get("error", "")
                m = re.search(r"HTTP (\d+)", str(err))
                http = int(m.group(1)) if m else None
                if http in (401, 403) or "401" in str(err) or "403" in str(err):
                    auth_hits += 1
                    results[name] = {"ok": False, "status": "AUTH_REQUIRED", "HTTP": http, "error": err}
                else:
                    results[name] = {"ok": False, "error": err, "HTTP": http}

        if auth_hits and not ok_hits:
            overall = "AUTH_REQUIRED"
        elif ok_hits and auth_hits:
            overall = "PARTIAL"
        elif not ok_hits:
            overall = "ERROR"

        if overall == "AUTH_REQUIRED":
            self.record_failure("HTTP 401: LICENSE/AUTH REQUIRED", http_status=401)
        elif ok_hits:
            self.record_success()

        return {
            "provider": self.name,
            "mode": self.mode,
            "status": overall,
            "HTTP": 401 if overall == "AUTH_REQUIRED" else None,
            "note": "LICENSE/AUTH REQUIRED" if overall == "AUTH_REQUIRED" else "",
            "endpoints": results,
            "legacy": legacy_results,
            "health": self.status().to_dict(),
        }
