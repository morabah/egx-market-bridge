from __future__ import annotations

from typing import Any
import time
from datetime import datetime, timezone

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
    DAILY_FINAL_VOLUME,
    BAR_VOLUME,
    UNKNOWN_VOLUME,
    DAILY_BAR,
    BAR_OPEN,
    DAILY_CLOSE,
    DELAYED_QUOTE,
)
from ..freshness import classify_freshness


class YahooProvider(MarketDataProvider):
    """yfinance adapter for EGX (.CA) historical/daily data.

    Yahoo EGX daily index is typically Africa/Cairo-aware.
    Quote path uses latest daily bar → DAILY_CLOSE + DAILY_FINAL_VOLUME (not intraday).
    """

    name = "yahoo"

    def __init__(self, symbol_resolver, enabled: bool = True, timeout: int = 20):
        super().__init__(enabled=enabled)
        self.symbol_resolver = symbol_resolver
        self.timeout = timeout
        self.mode = "delayed"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            quote=True,
            daily_ohlcv=True,
            intraday_ohlcv=False,
            volume=True,
        )

    def status(self):
        from egxbridge import provider_health as ph

        st = super().status()
        st.mode = self.mode
        st.provider_type = ph.TYPE_HTTP
        st.main_role = ph.MAIN_ROLE.get(self.name, "Daily/Historical")
        st.authenticated = None
        st.auth_status = ph.AUTH_NOT_REQUIRED

        if not self.enabled:
            return st

        if self._last_success and not self._last_error:
            st.reachable = True
            st.health_state = ph.ACTIVE
            st.notes = "Authentication not required for current Yahoo integration"
        elif self._last_error:
            if ph.is_network_failure(self._last_error, self._last_http_status):
                st.reachable = False
                st.health_state = ph.UNAVAILABLE
            else:
                st.reachable = True if self._reachable is not False else False
                st.health_state = ph.ERROR if st.reachable else ph.UNAVAILABLE
            st.notes = self._last_error
        else:
            st.reachable = self._reachable
            st.health_state = ph.ACTIVE if st.reachable else ph.UNAVAILABLE
            st.notes = "Authentication not required for current Yahoo integration"
        return st

    def _ticker(self, symbol: str):
        try:
            import yfinance as yf
        except ImportError as e:
            raise ProviderError(self.name, "yfinance not installed") from e
        ysym = self.symbol_resolver.to_provider(symbol, "yahoo")
        return yf.Ticker(ysym), ysym

    def _stamp_idx(self, idx, *, interval: str) -> dict[str, Any]:
        raw = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
        ts_sem = DAILY_BAR if interval == "1d" else BAR_OPEN
        if isinstance(raw, datetime) and raw.tzinfo is None:
            # Yahoo EGX should be Cairo-aware; if naive, do not invent UTC.
            bundle = normalize_timestamp(
                raw,
                provider_timezone_if_known="Africa/Cairo",
                timestamp_semantics=ts_sem,
            )
        else:
            bundle = normalize_timestamp(raw, timestamp_semantics=ts_sem)
        return bundle.to_dict()

    def get_quote(self, symbol: str) -> Quote:
        if not self.enabled:
            raise ProviderError(self.name, "Yahoo provider disabled")
        start = time.time()
        try:
            ticker, ysym = self._ticker(symbol)
            hist = ticker.history(period="5d", auto_adjust=False)
            self._latency_ms = (time.time() - start) * 1000
            capture = utc_now_iso()
            if hist is None or len(hist) == 0:
                raise ProviderError(self.name, f"No Yahoo quote data for {ysym}")
            row = hist.iloc[-1]
            last = _f(row.get("Close"))
            open_ = _f(row.get("Open"))
            high = _f(row.get("High"))
            low = _f(row.get("Low"))
            volume = _f(row.get("Volume"))
            prev_close = _f(hist.iloc[-2]["Close"]) if len(hist) > 1 else None
            stamp = self._stamp_idx(hist.index[-1], interval="1d")
            if last is None:
                raise ProviderError(self.name, f"No Yahoo quote data for {ysym}")
            change_pct = None
            if last is not None and prev_close:
                change_pct = round((last - prev_close) / prev_close * 100, 4)
            fclass = "UNKNOWN"
            if stamp["normalized_utc_timestamp"]:
                fclass, _ = classify_freshness(stamp["normalized_utc_timestamp"], capture)
            sess = session_date_cairo(stamp["normalized_cairo_timestamp"] or stamp["normalized_utc_timestamp"])
            self.record_success()
            self._last_success = capture
            self._latest_source_timestamp = stamp["normalized_utc_timestamp"]
            return Quote(
                symbol=symbol.upper(),
                provider=self.name,
                capture_timestamp=capture,
                last=float(last),
                open=open_,
                high=high,
                low=low,
                prev_close=prev_close,
                change_pct=change_pct,
                volume=volume,
                provider_timestamp=stamp["normalized_utc_timestamp"] or stamp["provider_raw_timestamp"],
                provider_mode=self.mode,
                raw_reference=f"yahoo:{ysym}:daily_close",
                freshness_class=fclass,
                price_observation_type=DAILY_CLOSE,
                volume_semantics=DAILY_FINAL_VOLUME,
                volume_interval="1d",
                session_date=sess,
                effective_session_date=sess,
                provider_raw_timestamp=stamp["provider_raw_timestamp"],
                provider_timezone_if_known=stamp["provider_timezone_if_known"],
                normalized_utc_timestamp=stamp["normalized_utc_timestamp"],
                normalized_cairo_timestamp=stamp["normalized_cairo_timestamp"],
                timestamp_semantics=stamp["timestamp_semantics"],
                latest_completed_session=is_latest_completed_session(sess),
            )
        except ProviderError as e:
            self.record_failure(str(e), http_status=getattr(e, "http_status", None))
            raise
        except Exception as e:
            self.record_failure(str(e))
            self._latency_ms = (time.time() - start) * 1000
            raise ProviderError(self.name, str(e)) from e

    def get_candles(
        self,
        symbol: str,
        interval: str = "1d",
        n_bars: int = 100,
        *,
        start: str | None = None,
    ) -> list[Candle]:
        if not self.enabled:
            raise ProviderError(self.name, "Yahoo provider disabled")
        start_t = time.time()
        try:
            ticker, ysym = self._ticker(symbol)
            yf_interval = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "60m", "1d": "1d", "1wk": "1wk",
            }.get(interval, "1d")
            period = "5d" if yf_interval.endswith("m") or yf_interval == "60m" else "1y"
            if n_bars > 200 and yf_interval == "1d":
                period = "2y"
            hist_kwargs = {"interval": yf_interval, "auto_adjust": False}
            if start and yf_interval == "1d":
                hist_kwargs["start"] = start
            else:
                hist_kwargs["period"] = period
            hist = ticker.history(**hist_kwargs)
            self._latency_ms = (time.time() - start_t) * 1000
            if hist is None or len(hist) == 0:
                raise ProviderError(self.name, f"No Yahoo candles for {ysym} interval={interval}")
            if not start:
                hist = hist.tail(n_bars)
            capture = utc_now_iso()
            out: list[Candle] = []
            vol_sem = DAILY_FINAL_VOLUME if interval == "1d" else BAR_VOLUME
            # EGX intraday via Yahoo is not validated as execution-grade
            if interval != "1d":
                vol_sem = UNKNOWN_VOLUME
            for idx, row in hist.iterrows():
                stamp = self._stamp_idx(idx, interval=interval)
                ts_s = stamp["normalized_utc_timestamp"] or stamp["provider_raw_timestamp"] or str(idx)
                fclass = "UNKNOWN"
                if stamp["normalized_utc_timestamp"]:
                    fclass, _ = classify_freshness(stamp["normalized_utc_timestamp"], capture)
                sess = session_date_cairo(stamp["normalized_cairo_timestamp"] or stamp["normalized_utc_timestamp"])
                out.append(Candle(
                    symbol=symbol.upper(),
                    interval=interval,
                    timestamp=ts_s,
                    open=_f(row.get("Open")),
                    high=_f(row.get("High")),
                    low=_f(row.get("Low")),
                    close=_f(row.get("Close")),
                    volume=_f(row.get("Volume")),
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
            self._last_success = capture
            if out:
                self._latest_source_timestamp = out[-1].normalized_utc_timestamp or out[-1].timestamp
            return out
        except ProviderError as e:
            self.record_failure(str(e), http_status=getattr(e, "http_status", None))
            raise
        except Exception as e:
            self.record_failure(str(e))
            raise ProviderError(self.name, str(e)) from e

    def probe(self, symbol: str) -> dict[str, Any]:
        if not self.enabled:
            return {"provider": self.name, "enabled": False, "status": "DISABLED"}
        out: dict[str, Any] = {"provider": self.name, "symbol": symbol, "mode": self.mode}
        try:
            q = self.get_quote(symbol)
            out["quote"] = {
                "ok": True,
                "last": q.last,
                "volume": q.volume,
                "price_observation_type": q.price_observation_type,
                "volume_semantics": q.volume_semantics,
                "latest_timestamp_utc": q.normalized_utc_timestamp,
                "latest_timestamp_cairo": q.normalized_cairo_timestamp,
                "provider_timezone_if_known": q.provider_timezone_if_known,
                "yahoo_symbol": self.symbol_resolver.to_provider(symbol, "yahoo"),
            }
        except Exception as e:
            out["quote"] = {"ok": False, "error": str(e)}
        try:
            daily = self.get_candles(symbol, "1d", n_bars=5)
            out["daily"] = {
                "ok": True,
                "bars": len(daily),
                "latest_timestamp_utc": daily[-1].normalized_utc_timestamp,
                "latest_timestamp_cairo": daily[-1].normalized_cairo_timestamp,
                "volume_semantics": daily[-1].volume_semantics,
                "latest_close": daily[-1].close,
            }
        except Exception as e:
            out["daily"] = {"ok": False, "error": str(e)}
        out["intraday"] = {
            "ok": False,
            "note": "Yahoo EGX intraday not treated as execution-grade without explicit validation",
        }
        out["status"] = "OK" if out.get("quote", {}).get("ok") or out.get("daily", {}).get("ok") else "ERROR"
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
