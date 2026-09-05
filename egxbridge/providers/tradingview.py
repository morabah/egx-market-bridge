from __future__ import annotations

from typing import Any
import time
from datetime import datetime

from .base import (
    MarketDataProvider,
    ProviderCapabilities,
    Quote,
    Candle,
    ProviderError,
    utc_now_iso,
)
from ..semantics import (
    normalize_timestamp,
    session_date_cairo,
    is_latest_completed_session,
    BAR_VOLUME,
    DAILY_FINAL_VOLUME,
    BAR_OPEN,
    DAILY_BAR,
    CANDLE_CLOSE,
    DAILY_CLOSE,
)
from ..freshness import classify_freshness, FreshnessThresholds


INTERVAL_MAP = {
    "1m": "in_1_minute",
    "5m": "in_5_minute",
    "15m": "in_15_minute",
    "30m": "in_30_minute",
    "1h": "in_1_hour",
    "1d": "in_daily",
}


class TradingViewProvider(MarketDataProvider):
    """Optional TradingView-compatible adapter (tvDatafeed / TradeGlob).

    tvDatafeed converts exchange epoch seconds with datetime.fromtimestamp()
    (host-local naive wall time) and switches chart timezone to "exchange".
    We therefore treat naive TV timestamps as host-local, never as UTC.
    """

    name = "tradingview"

    def __init__(
        self,
        symbol_resolver,
        enabled: bool = True,
        username: str = "",
        password: str = "",
        n_bars_default: int = 200,
    ):
        super().__init__(enabled=enabled)
        self.symbol_resolver = symbol_resolver
        self.username = username
        self.password = password
        self.n_bars_default = n_bars_default
        self.mode = "authenticated" if username else "anonymous"
        self._tv = None
        self._import_error: str | None = None
        self._backend: str | None = None
        if enabled:
            self._try_init()

    def _try_init(self):
        self._ensure_ssl_certs()
        try:
            from tvDatafeed import TvDatafeed  # type: ignore
            if self.username and self.password:
                self._tv = TvDatafeed(self.username, self.password)
                self.mode = "authenticated"
            else:
                self._tv = TvDatafeed()
                self.mode = "anonymous"
            self._backend = "tvDatafeed"
            return
        except Exception as e:
            self._import_error = f"tvDatafeed: {e}"
        try:
            from tradeglob import TradeGlobFetcher  # type: ignore
            self._tv = TradeGlobFetcher()
            self._backend = "tradeglob"
            self.mode = "anonymous"
            return
        except Exception as e:
            self._import_error = (self._import_error or "") + f" | tradeglob: {e}"
            self._tv = None

    @staticmethod
    def _ensure_ssl_certs():
        import os
        if os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE"):
            return
        try:
            import certifi
            os.environ["SSL_CERT_FILE"] = certifi.where()
            os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
        except Exception:
            pass

    def capabilities(self) -> ProviderCapabilities:
        available = self._tv is not None
        return ProviderCapabilities(
            quote=available,
            daily_ohlcv=available,
            intraday_ohlcv=available,
            volume=available,
        )

    def status(self):
        from egxbridge import provider_health as ph

        st = super().status()
        st.mode = self.mode
        st.provider_type = ph.TYPE_HTTP
        st.main_role = ph.MAIN_ROLE.get(self.name, "Intraday OHLCV")

        if not self.enabled:
            return st

        if self._tv is None:
            st.reachable = False
            st.authenticated = None
            st.auth_status = ph.AUTH_ANONYMOUS if self.mode == "anonymous" else ph.AUTH_REQUIRED_STATUS
            st.health_state = ph.UNAVAILABLE
            st.notes = f"Optional dependency missing: {self._import_error}"
            st.last_error = self._import_error
            return st

        if self.mode == "anonymous":
            st.authenticated = None
            st.auth_status = ph.AUTH_ANONYMOUS
            if self._last_error and not self._last_success:
                if ph.is_network_failure(self._last_error, self._last_http_status):
                    st.reachable = False
                    st.health_state = ph.UNAVAILABLE
                else:
                    st.reachable = True if self._reachable is not False else False
                    st.health_state = ph.DEGRADED if st.reachable else ph.ERROR
                st.notes = self._last_error or ""
            else:
                st.reachable = True
                st.health_state = ph.ACTIVE_ANONYMOUS
                st.notes = (
                    f"backend={self._backend}; auth not required; naive timestamps are host-local "
                    f"(tvDatafeed fromtimestamp); never assume REALTIME"
                )
            return st

        # authenticated mode
        st.authenticated = True
        st.auth_status = ph.AUTH_AUTHENTICATED
        if self._last_success and not self._last_error:
            st.reachable = True
            st.health_state = ph.ACTIVE
        elif self._last_error:
            st.reachable = self._reachable
            st.health_state = ph.ERROR if self._reachable is not False else ph.UNAVAILABLE
        else:
            st.reachable = True
            st.health_state = ph.ACTIVE
        st.notes = f"backend={self._backend}"
        return st

    def _split_symbol(self, symbol: str) -> tuple[str, str]:
        mapped = self.symbol_resolver.to_provider(symbol, "tradingview")
        if ":" in mapped:
            ex, sym = mapped.split(":", 1)
            return sym, ex
        return mapped, "EGX"

    def _hist(self, symbol: str, interval: str, n_bars: int):
        if self._tv is None:
            raise ProviderError(self.name, f"TradingView unavailable: {self._import_error}")
        sym, exchange = self._split_symbol(symbol)
        if self._backend == "tradeglob":
            tg_map = {
                "1m": "1 Minute", "5m": "5 Minute", "15m": "15 Minute",
                "30m": "30 Minute", "1h": "1 Hour", "1d": "Daily",
            }
            return self._tv.get_ohlcv(sym, exchange, tg_map.get(interval, "Daily"), n_bars=n_bars)
        from tvDatafeed import Interval  # type: ignore
        iv_name = INTERVAL_MAP.get(interval, "in_daily")
        iv = getattr(Interval, iv_name)
        return self._tv.get_hist(symbol=sym, exchange=exchange, interval=iv, n_bars=n_bars)

    def _stamp_index(self, idx, interval: str) -> dict[str, Any]:
        """Build timestamp bundle for a TV bar index value."""
        raw = idx
        if hasattr(idx, "to_pydatetime"):
            raw = idx.to_pydatetime()
        ts_sem = DAILY_BAR if interval == "1d" else BAR_OPEN
        # tvDatafeed: fromtimestamp → naive host-local. Aware indexes: keep their tz.
        if isinstance(raw, datetime) and raw.tzinfo is None:
            bundle = normalize_timestamp(raw, provider_timezone_if_known="local", timestamp_semantics=ts_sem)
        else:
            bundle = normalize_timestamp(raw, timestamp_semantics=ts_sem)
        return bundle.to_dict()

    def get_candles(self, symbol: str, interval: str = "5m", n_bars: int = 100) -> list[Candle]:
        if not self.enabled:
            raise ProviderError(self.name, "TradingView provider disabled")
        start = time.time()
        try:
            df = self._hist(symbol, interval, n_bars or self.n_bars_default)
            self._latency_ms = (time.time() - start) * 1000
            if df is None or len(df) == 0:
                raise ProviderError(self.name, f"No TV candles for {symbol} {interval}")
            capture = utc_now_iso()
            out: list[Candle] = []
            vol_sem = DAILY_FINAL_VOLUME if interval == "1d" else BAR_VOLUME
            for idx, row in df.iterrows():
                stamp = self._stamp_index(idx, interval)
                # Prefer normalized UTC for internal timestamp; fall back to raw string if unknown
                ts_s = stamp["normalized_utc_timestamp"] or stamp["provider_raw_timestamp"] or str(idx)
                fclass, _ = ("UNKNOWN", None)
                if stamp["normalized_utc_timestamp"]:
                    fclass, _ = classify_freshness(stamp["normalized_utc_timestamp"], capture)
                sess = session_date_cairo(stamp["normalized_cairo_timestamp"] or stamp["normalized_utc_timestamp"])
                out.append(Candle(
                    symbol=symbol.upper(),
                    interval=interval,
                    timestamp=ts_s,
                    open=_f(row.get("open") if "open" in getattr(row, "index", []) else row.get("Open")),
                    high=_f(row.get("high") if "high" in getattr(row, "index", []) else row.get("High")),
                    low=_f(row.get("low") if "low" in getattr(row, "index", []) else row.get("Low")),
                    close=_f(row.get("close") if "close" in getattr(row, "index", []) else row.get("Close")),
                    volume=_f(row.get("volume") if "volume" in getattr(row, "index", []) else row.get("Volume")),
                    provider=self.name,
                    capture_timestamp=capture,
                    provider_timestamp=ts_s,
                    provider_mode=self.mode,
                    freshness_class=fclass,
                    volume_semantics=vol_sem,
                    session_date=sess,
                    provider_raw_timestamp=stamp["provider_raw_timestamp"],
                    provider_timezone_if_known=stamp["provider_timezone_if_known"],
                    normalized_utc_timestamp=stamp["normalized_utc_timestamp"],
                    normalized_cairo_timestamp=stamp["normalized_cairo_timestamp"],
                    timestamp_semantics=stamp["timestamp_semantics"],
                ))
            self.record_success()
            self._last_success = capture  # keep capture time from this call
            if out:
                self._latest_source_timestamp = out[-1].normalized_utc_timestamp or out[-1].timestamp
            return out
        except ProviderError as e:
            self.record_failure(str(e), http_status=getattr(e, "http_status", None))
            raise
        except Exception as e:
            self.record_failure(str(e))
            raise ProviderError(self.name, str(e)) from e

    def get_quote(self, symbol: str) -> Quote:
        """Price is candle-derived — never LIVE_QUOTE / REALTIME."""
        for iv in ("5m", "1d"):
            try:
                candles = self.get_candles(symbol, iv, n_bars=5)
                if not candles:
                    continue
                last_c = candles[-1]
                price_type = DAILY_CLOSE if iv == "1d" else CANDLE_CLOSE
                return Quote(
                    symbol=symbol.upper(),
                    provider=self.name,
                    capture_timestamp=last_c.capture_timestamp,
                    last=last_c.close,
                    open=last_c.open,
                    high=last_c.high,
                    low=last_c.low,
                    volume=last_c.volume,
                    provider_timestamp=last_c.normalized_utc_timestamp or last_c.timestamp,
                    provider_mode=self.mode,
                    raw_reference=f"tradingview:{iv}:candle_close",
                    freshness_class=last_c.freshness_class,
                    price_observation_type=price_type,
                    volume_semantics=last_c.volume_semantics,
                    volume_interval=iv,
                    session_date=last_c.session_date,
                    effective_session_date=last_c.session_date,
                    provider_raw_timestamp=last_c.provider_raw_timestamp,
                    provider_timezone_if_known=last_c.provider_timezone_if_known,
                    normalized_utc_timestamp=last_c.normalized_utc_timestamp,
                    normalized_cairo_timestamp=last_c.normalized_cairo_timestamp,
                    timestamp_semantics=last_c.timestamp_semantics,
                    latest_completed_session=is_latest_completed_session(last_c.session_date),
                )
            except Exception:
                continue
        raise ProviderError(self.name, f"No TradingView quote for {symbol}")

    def probe(self, symbol: str) -> dict[str, Any]:
        if not self.enabled:
            return {"provider": self.name, "enabled": False, "status": "DISABLED"}
        if self._tv is None:
            return {
                "provider": self.name,
                "status": "UNAVAILABLE",
                "backend": None,
                "error": self._import_error,
                "note": "Install tvDatafeed optionally: pip install tradingview-datafeed",
            }
        out: dict[str, Any] = {
            "provider": self.name,
            "backend": self._backend,
            "mode": self.mode,
            "symbol": symbol,
            "mapped": self.symbol_resolver.to_provider(symbol, "tradingview"),
            "timestamp_note": "tvDatafeed naive bars = host-local via fromtimestamp; normalized to UTC via local tz",
        }
        for label, iv in [("1m_candles", "1m"), ("5m_candles", "5m"), ("daily", "1d")]:
            try:
                bars = self.get_candles(symbol, iv, n_bars=10)
                b = bars[-1]
                out[label] = {
                    "ok": True,
                    "bars": len(bars),
                    "latest_timestamp_utc": b.normalized_utc_timestamp,
                    "latest_timestamp_cairo": b.normalized_cairo_timestamp,
                    "provider_raw_timestamp": b.provider_raw_timestamp,
                    "provider_timezone_if_known": b.provider_timezone_if_known,
                    "timestamp_semantics": b.timestamp_semantics,
                    "volume_semantics": b.volume_semantics,
                    "latest_close": b.close,
                    "latest_volume": b.volume,
                }
            except Exception as e:
                out[label] = {"ok": False, "error": str(e)}
        try:
            q = self.get_quote(symbol)
            out["quote"] = {
                "ok": True,
                "last": q.last,
                "price_observation_type": q.price_observation_type,
                "volume_semantics": q.volume_semantics,
                "latest_timestamp_utc": q.normalized_utc_timestamp,
                "latest_timestamp_cairo": q.normalized_cairo_timestamp,
            }
        except Exception as e:
            out["quote"] = {"ok": False, "error": str(e)}
        ok_any = any(isinstance(out.get(k), dict) and out[k].get("ok") for k in ("quote", "1m_candles", "5m_candles", "daily"))
        out["status"] = "OK" if ok_any else "ERROR"
        out["note"] = "Freshness from normalized UTC timestamps only; never assume REALTIME"
        return out


def _f(v):
    if v is None:
        return None
    try:
        if v != v:
            return None
        return float(v)
    except Exception:
        return None
