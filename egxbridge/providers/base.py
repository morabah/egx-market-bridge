from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Capability(str, Enum):
    QUOTE = "quote"
    DAILY_OHLCV = "daily_ohlcv"
    INTRADAY_OHLCV = "intraday_ohlcv"
    VOLUME = "volume"
    FUNDAMENTALS = "fundamentals"
    MARKET_UNIVERSE = "market_universe"
    BID_ASK = "bid_ask"
    DEPTH = "depth"
    TRADES = "trades"
    TRADE_COUNT = "trade_count"
    CORPORATE_ACTIONS = "corporate_actions"


@dataclass
class ProviderCapabilities:
    quote: bool = False
    daily_ohlcv: bool = False
    intraday_ohlcv: bool = False
    volume: bool = False
    fundamentals: bool = False
    market_universe: bool = False
    bid_ask: bool = False
    depth: bool = False
    trades: bool = False
    trade_count: bool = False
    corporate_actions: bool = False

    def supports(self, cap: Capability | str) -> bool:
        key = cap.value if isinstance(cap, Capability) else str(cap)
        return bool(getattr(self, key, False))

    def as_dict(self) -> dict[str, bool]:
        return asdict(self)


@dataclass
class Observation:
    """Single market-data observation with mandatory provenance."""
    symbol: str
    field: str
    value: Any
    provider: str
    capture_timestamp: str
    provider_timestamp: str | None = None
    freshness_seconds: float | None = None
    provider_mode: str = "unknown"
    quality: str = "UNKNOWN"
    raw_reference: str | None = None
    interval: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class Candle:
    symbol: str
    interval: str
    timestamp: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
    provider: str
    capture_timestamp: str
    freshness_class: str = "UNKNOWN"
    provider_timestamp: str | None = None
    provider_mode: str = "unknown"
    volume_semantics: str = "UNKNOWN_VOLUME"
    session_date: str | None = None
    provider_raw_timestamp: str | None = None
    provider_timezone_if_known: str | None = None
    normalized_utc_timestamp: str | None = None
    normalized_cairo_timestamp: str | None = None
    timestamp_semantics: str = "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Quote:
    symbol: str
    provider: str
    capture_timestamp: str
    last: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    prev_close: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    turnover: float | None = None
    trades: float | None = None
    bid: float | None = None
    bid_qty: float | None = None
    ask: float | None = None
    ask_qty: float | None = None
    provider_timestamp: str | None = None
    provider_mode: str = "unknown"
    freshness_class: str = "UNKNOWN"
    raw_reference: str | None = None
    price_observation_type: str = "UNKNOWN"
    volume_semantics: str = "UNKNOWN_VOLUME"
    volume_interval: str | None = None
    session_date: str | None = None
    effective_session_date: str | None = None
    provider_raw_timestamp: str | None = None
    provider_timezone_if_known: str | None = None
    normalized_utc_timestamp: str | None = None
    normalized_cairo_timestamp: str | None = None
    timestamp_semantics: str = "UNKNOWN"
    latest_completed_session: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderStatus:
    name: str
    enabled: bool
    reachable: bool | None = None
    authenticated: bool | None = None
    capabilities: dict[str, bool] = field(default_factory=dict)
    last_success: str | None = None
    last_error: str | None = None
    latency_ms: float | None = None
    latest_source_timestamp: str | None = None
    mode: str = "unknown"
    notes: str = ""
    # Health observability (v0.3.1)
    provider_type: str = "http"
    health_state: str = "UNKNOWN"
    auth_status: str = "UNKNOWN"
    last_http_status: int | None = None
    last_checked: str | None = None
    main_role: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProviderError(Exception):
    """Non-fatal provider failure."""

    def __init__(self, provider: str, message: str, *, code: str | None = None, http_status: int | None = None):
        super().__init__(message)
        self.provider = provider
        self.message = message
        self.code = code
        self.http_status = http_status

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "message": self.message,
            "code": self.code,
            "http_status": self.http_status,
        }


class AuthRequiredError(ProviderError):
    def __init__(self, provider: str, message: str = "AUTH/LICENSE REQUIRED", *, http_status: int | None = 401):
        super().__init__(provider, message, code="AUTH_REQUIRED", http_status=http_status)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MarketDataProvider(ABC):
    name: str = "base"
    provider_type: str = "http"

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._last_success: str | None = None
        self._last_error: str | None = None
        self._latency_ms: float | None = None
        self._latest_source_timestamp: str | None = None
        self._reachable: bool | None = None
        self._last_http_status: int | None = None
        self._last_checked: str | None = None

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        raise NotImplementedError

    def record_success(self):
        self._last_success = utc_now_iso()
        self._last_error = None
        self._last_http_status = None
        self._reachable = True if getattr(self, "provider_type", "http") == "http" else None
        self._last_checked = self._last_success

    def record_failure(self, message: str, *, http_status: int | None = None):
        from egxbridge.provider_health import extract_http_status, classify_http_reachability

        self._last_error = message
        self._last_http_status = extract_http_status(message, http_status)
        self._last_checked = utc_now_iso()
        if getattr(self, "provider_type", "http") != "http":
            self._reachable = None
            return
        classified = classify_http_reachability(message, self._last_http_status)
        if classified is not None:
            self._reachable = classified

    def status(self) -> ProviderStatus:
        from egxbridge.provider_health import (
            DISABLED,
            ACTIVE,
            ERROR,
            UNAVAILABLE,
            AUTH_NOT_APPLICABLE,
            AUTH_UNKNOWN,
            MAIN_ROLE,
        )

        ptype = getattr(self, "provider_type", "http")
        if not self.enabled:
            return ProviderStatus(
                name=self.name,
                enabled=False,
                reachable=None,
                authenticated=None,
                capabilities=self.capabilities().as_dict(),
                last_success=self._last_success,
                last_error=None,
                latency_ms=self._latency_ms,
                latest_source_timestamp=self._latest_source_timestamp,
                mode=getattr(self, "mode", "unknown"),
                notes="Provider disabled",
                provider_type=ptype,
                health_state=DISABLED,
                auth_status=AUTH_NOT_APPLICABLE,
                last_http_status=None,
                last_checked=self._last_checked,
                main_role=MAIN_ROLE.get(self.name, ""),
            )
        if self._last_success and not self._last_error:
            health = ACTIVE
        elif self._last_error:
            health = ERROR
        else:
            health = UNAVAILABLE
        return ProviderStatus(
            name=self.name,
            enabled=True,
            reachable=self._reachable,
            authenticated=None,
            capabilities=self.capabilities().as_dict(),
            last_success=self._last_success,
            last_error=self._last_error,
            latency_ms=self._latency_ms,
            latest_source_timestamp=self._latest_source_timestamp,
            mode=getattr(self, "mode", "unknown"),
            notes="",
            provider_type=ptype,
            health_state=health,
            auth_status=AUTH_UNKNOWN,
            last_http_status=self._last_http_status,
            last_checked=self._last_checked,
            main_role=MAIN_ROLE.get(self.name, ""),
        )

    def probe(self, symbol: str) -> dict[str, Any]:
        return {"provider": self.name, "symbol": symbol, "ok": False, "note": "not implemented"}

    def get_quote(self, symbol: str) -> Quote:
        raise ProviderError(self.name, f"{self.name} does not support quote")

    def get_candles(self, symbol: str, interval: str = "1d", n_bars: int = 100) -> list[Candle]:
        raise ProviderError(self.name, f"{self.name} does not support candles")

    def get_depth(self, symbol: str) -> list[dict[str, Any]]:
        raise ProviderError(self.name, f"{self.name} does not support depth")

    def get_trades(self, symbol: str) -> list[dict[str, Any]]:
        raise ProviderError(self.name, f"{self.name} does not support trades")

    def get_universe(self) -> list[dict[str, Any]]:
        raise ProviderError(self.name, f"{self.name} does not support universe")

    def get_fundamentals(self, symbol: str) -> dict[str, Any]:
        raise ProviderError(self.name, f"{self.name} does not support fundamentals")
