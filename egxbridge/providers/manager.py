from __future__ import annotations

from typing import Any
from .base import MarketDataProvider, Capability, ProviderError, AuthRequiredError
from ..resilience import CircuitBreaker, RateLimiter, retry_call


DEFAULT_PRIORITY = {
    "intraday_ohlcv": ["egid", "tradingview", "borsa", "yahoo"],
    "daily_ohlcv": ["egid", "yahoo", "tradingview", "borsa"],
    "quote": ["egid", "tradingview", "borsa", "yahoo"],
    "depth": ["egid"],
    "trades": ["egid"],
    "fundamentals": ["investor_egx"],
    "market_universe": ["borsa", "investor_egx"],
}


class ProviderManager:
    def __init__(
        self,
        providers: list[MarketDataProvider],
        priority: dict[str, list[str]] | None = None,
        rate_limit_seconds: float = 0.4,
    ):
        self.providers = {p.name: p for p in providers}
        self.priority = priority or dict(DEFAULT_PRIORITY)
        # Defaults: threshold=3, cooldown=60s, one HALF-OPEN probe (see CircuitBreaker)
        self.breakers = {
            name: CircuitBreaker(fail_threshold=3, cool_down_seconds=60)
            for name in self.providers
        }
        self.limiters = {name: RateLimiter(rate_limit_seconds) for name in self.providers}

    def get(self, name: str) -> MarketDataProvider | None:
        return self.providers.get(name)

    def enabled_providers(self) -> list[MarketDataProvider]:
        return [p for p in self.providers.values() if p.enabled]

    def ordered_for(self, capability: str) -> list[MarketDataProvider]:
        names = self.priority.get(capability, list(self.providers.keys()))
        out = []
        for n in names:
            p = self.providers.get(n)
            if p and p.enabled and p.capabilities().supports(capability):
                out.append(p)
        # append any other enabled that support capability
        for p in self.providers.values():
            if p.enabled and p.capabilities().supports(capability) and p not in out:
                out.append(p)
        return out

    def call_first(self, capability: str, method: str, *args, provider_filter: str | None = None, **kwargs):
        """Try providers in priority order. Failures are skipped."""
        errors: list[dict[str, Any]] = []
        providers = self.ordered_for(capability)
        if provider_filter:
            providers = [p for p in providers if p.name == provider_filter]
            if not providers and provider_filter in self.providers:
                providers = [self.providers[provider_filter]]
        for p in providers:
            br = self.breakers[p.name]
            if not br.allow():
                errors.append({"provider": p.name, "error": "circuit_open", "breaker_state": br.state})
                continue
            self.limiters[p.name].wait()
            try:
                fn = getattr(p, method)
                result = retry_call(lambda: fn(*args, **kwargs), retries=1)
                br.record_success()
                return result, p.name, errors
            except AuthRequiredError as e:
                # Licensed/auth gaps are hard failures for that provider.
                br.record_failure()
                errors.append(e.to_dict())
            except ProviderError as e:
                # Soft empty-data misses must not open the breaker (e.g. missing 1m bars).
                if _is_soft_miss(e.message):
                    errors.append(e.to_dict())
                else:
                    br.record_failure()
                    errors.append(e.to_dict())
            except Exception as e:
                br.record_failure()
                errors.append({"provider": p.name, "error": str(e)})
        return None, None, errors

    def collect_all(self, capability: str, method: str, *args, provider_filter: str | None = None, **kwargs) -> list[tuple[Any, str]]:
        """Collect from all providers that support capability (for conflict detection)."""
        results = []
        providers = self.ordered_for(capability)
        if provider_filter:
            providers = [p for p in providers if p.name == provider_filter]
        for p in providers:
            if not self.breakers[p.name].allow():
                continue
            self.limiters[p.name].wait()
            try:
                fn = getattr(p, method)
                results.append((fn(*args, **kwargs), p.name))
                self.breakers[p.name].record_success()
            except AuthRequiredError:
                self.breakers[p.name].record_failure()
            except ProviderError as e:
                if not _is_soft_miss(str(e)):
                    self.breakers[p.name].record_failure()
            except Exception:
                self.breakers[p.name].record_failure()
        return results

    def statuses(self) -> list[dict[str, Any]]:
        return [p.status().to_dict() for p in self.providers.values()]

    def probe_all(self, symbol: str) -> dict[str, Any]:
        out = {}
        for p in self.providers.values():
            if not p.enabled:
                # Do not probe disabled providers unless explicitly requested elsewhere
                out[p.name] = {
                    **p.status().to_dict(),
                    "status": "DISABLED",
                    "enabled": False,
                    "note": "Provider disabled — not probed",
                }
                continue
            try:
                probed = p.probe(symbol)
                # Attach canonical health snapshot
                if isinstance(probed, dict) and "health" not in probed:
                    probed["health"] = p.status().to_dict()
                out[p.name] = probed
            except Exception as e:
                out[p.name] = {
                    "provider": p.name,
                    "status": "ERROR",
                    "error": str(e),
                    "health": p.status().to_dict(),
                }
        return out


def _is_soft_miss(message: str) -> bool:
    m = (message or "").lower()
    if any(x in m for x in ("ssl", "timeout", "certificate", "connection", "401", "403", "auth")):
        return False
    needles = (
        "no tv candles",
        "no yahoo candles",
        "no candles for",
        "no quote data",
        "no yahoo quote",
    )
    return any(n in m for n in needles)
