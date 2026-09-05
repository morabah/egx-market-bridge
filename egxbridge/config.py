from __future__ import annotations

from dataclasses import dataclass, field, asdict, fields
from pathlib import Path
from typing import Any
import json
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


@dataclass
class FreshnessConfig:
    live_seconds: float = 15
    fresh_seconds: float = 120
    delayed_seconds: float = 1200


@dataclass
class Settings:
    provider_mode: str = "delayed"
    base_url: str = "https://ticker.egidegypt.com"
    swagger_url: str = "https://ticker.egidegypt.com/swagger/v1/swagger.json"
    symbols: list[str] = field(default_factory=lambda: ["MASR", "LUTS"])
    focus_symbols: list[str] = field(default_factory=lambda: ["MASR", "LUTS"])
    poll_seconds: int = 60
    request_timeout_seconds: int = 15
    output_dir: str = "./output"
    collect_depth: bool = True
    collect_trades: bool = True
    collect_chart: bool = True
    max_trade_rows: int = 5000
    session_only: bool = False
    cairo_timezone: str = "Africa/Cairo"
    egid_token: str = ""

    database_path: str = "./output/egx_bridge.sqlite"
    raw_retention_days: int = 14
    enabled_providers: dict[str, bool] = field(default_factory=lambda: {
        "egid": True,
        "yahoo": True,
        "tradingview": True,
        "borsa": False,
        "investor_egx": True,
    })
    provider_priority: dict[str, list[str]] = field(default_factory=lambda: {
        "intraday_ohlcv": ["egid", "tradingview", "borsa", "yahoo"],
        "daily_ohlcv": ["egid", "yahoo", "tradingview", "borsa"],
        "quote": ["egid", "tradingview", "borsa", "yahoo"],
        "depth": ["egid"],
        "trades": ["egid"],
        "fundamentals": ["investor_egx"],
        "market_universe": ["borsa", "investor_egx"],
    })
    symbol_aliases: dict[str, dict[str, str]] = field(default_factory=dict)
    borsa_base_url: str = ""
    investor_egx_universe_path: str = ""
    investor_egx_sqlite_path: str = ""
    tradingview_username: str = ""
    tradingview_password: str = ""
    candle_intervals: list[str] = field(default_factory=lambda: ["1d", "5m", "15m", "1h"])
    freshness: FreshnessConfig = field(default_factory=FreshnessConfig)
    rate_limit_seconds: float = 0.5
    collect_multi_provider_quotes: bool = True

    @classmethod
    def load(cls, path: str | Path = "config.json") -> "Settings":
        p = Path(path)
        data: dict[str, Any] = {}
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))

        fresh_raw = data.get("freshness") if isinstance(data.get("freshness"), dict) else {}
        init: dict[str, Any] = {}
        valid = {f.name for f in fields(cls)}
        for k, v in data.items():
            if k == "freshness":
                continue
            if k in valid:
                init[k] = v

        obj = cls(**init)
        if fresh_raw:
            obj.freshness = FreshnessConfig(
                live_seconds=float(fresh_raw.get("live_seconds", obj.freshness.live_seconds)),
                fresh_seconds=float(fresh_raw.get("fresh_seconds", obj.freshness.fresh_seconds)),
                delayed_seconds=float(fresh_raw.get("delayed_seconds", obj.freshness.delayed_seconds)),
            )

        # Merge enabled_providers defaults
        defaults_ep = {
            "egid": True, "yahoo": True, "tradingview": True, "borsa": False, "investor_egx": True,
        }
        defaults_ep.update(obj.enabled_providers or {})
        obj.enabled_providers = defaults_ep

        obj.symbols = [str(x).strip().upper() for x in obj.symbols if str(x).strip()]
        obj.focus_symbols = [str(x).strip().upper() for x in obj.focus_symbols if str(x).strip()]
        obj.egid_token = os.getenv("EGID_TOKEN", obj.egid_token or "").strip()
        obj.tradingview_username = os.getenv("TRADINGVIEW_USERNAME", obj.tradingview_username or "").strip()
        obj.tradingview_password = os.getenv("TRADINGVIEW_PASSWORD", obj.tradingview_password or "").strip()
        if os.getenv("BORSA_BASE_URL"):
            obj.borsa_base_url = os.getenv("BORSA_BASE_URL", "").strip()
            if obj.borsa_base_url:
                obj.enabled_providers["borsa"] = True
        return obj

    def output_path(self, root: str | Path = ".") -> Path:
        p = Path(self.output_dir)
        if not p.is_absolute():
            p = Path(root) / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    def db_path(self, root: str | Path = ".") -> Path:
        p = Path(self.database_path)
        if not p.is_absolute():
            p = Path(root) / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def to_public_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("egid_token", None)
        d.pop("tradingview_password", None)
        return d
