from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

from .freshness import egx_session_open_at, FreshnessThresholds
from .semantics import (
    LIVE_QUOTE,
    DELAYED_QUOTE,
    CANDLE_CLOSE,
    DAILY_CLOSE,
)


@dataclass
class QualityBreakdown:
    freshness: float = 0.0
    source_reliability: float = 0.0
    cross_source_agreement: float = 0.0
    completeness: float = 0.0
    timestamp_quality: float = 0.0

    def research_score(self) -> float:
        return round(
            self.freshness * 0.30
            + self.source_reliability * 0.25
            + self.cross_source_agreement * 0.20
            + self.completeness * 0.15
            + self.timestamp_quality * 0.10,
            1,
        )

    def execution_score(self) -> float:
        base = self.research_score()
        exec_ = (
            self.freshness * 0.50
            + self.source_reliability * 0.20
            + self.completeness * 0.20
            + self.timestamp_quality * 0.10
        )
        return round(min(base, exec_), 1)


PROVIDER_RELIABILITY = {
    "egid": 95.0,
    "tradingview": 75.0,
    "borsa": 70.0,
    "yahoo": 65.0,
    "investor_egx": 60.0,
}


FRESHNESS_SCORE = {
    "LIVE": 100.0,
    "FRESH": 85.0,
    "DELAYED": 55.0,
    "STALE_EXPECTED": 30.0,
    "STALE_UNEXPECTED": 20.0,
    "STALE": 25.0,
    "UNKNOWN": 20.0,
}

# Research boost when weekend/closed but observation is latest completed session
LATEST_COMPLETED_SESSION_FRESHNESS = 72.0


@dataclass
class SymbolQuality:
    symbol: str
    availability: dict[str, str] = field(default_factory=dict)
    research_data_quality: float = 0.0
    execution_data_quality: float = 0.0
    execution_grade: str = "NO"
    latest_completed_session: bool = False
    components: dict[str, float] = field(default_factory=dict)
    missing_execution_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_execution_grade(
    *,
    session_open: bool | None = None,
    price_observation_type: str = "UNKNOWN",
    freshness_class: str = "UNKNOWN",
    freshness_seconds: float | None = None,
    has_current_session_price: bool = False,
    has_current_session_volume: bool = False,
    timestamp_reliable: bool = False,
    has_bid_ask: bool = False,
    has_depth: bool = False,
    has_trades: bool = False,
    require_microstructure: bool = False,
    execution_fresh_seconds: float = 120,
) -> tuple[str, list[str]]:
    """Hard gate. Numeric EDQ must not override this."""
    missing: list[str] = []
    open_now = egx_session_open_at() if session_open is None else session_open
    if not open_now:
        missing.append("egx_session_open")
    if not has_current_session_price:
        missing.append("current_session_price")
    if price_observation_type in {CANDLE_CLOSE, DAILY_CLOSE, "UNKNOWN"}:
        # Candle-derived prices are not execution quotes unless session-open live path exists
        if price_observation_type != DELAYED_QUOTE and price_observation_type != LIVE_QUOTE:
            missing.append("execution_grade_price_observation")
    if not timestamp_reliable:
        missing.append("reliable_timestamp_semantics")
    if freshness_class not in {"LIVE", "FRESH"} and not (
        freshness_seconds is not None and freshness_seconds <= execution_fresh_seconds
    ):
        missing.append("execution_freshness")
    if not has_current_session_volume:
        missing.append("current_session_volume")
    if require_microstructure and not (has_bid_ask or has_depth or has_trades):
        missing.append("microstructure_fields")
    # Licensed EGID absence typically blocks microstructure; hard NO when any missing
    return ("YES" if not missing else "NO"), missing


def score_symbol(
    *,
    symbol: str,
    freshness_class: str = "UNKNOWN",
    freshness_seconds: float | None = None,
    providers_used: list[str] | None = None,
    agreement: bool | None = None,
    has_price: bool = False,
    has_volume: bool = False,
    has_daily: bool = False,
    has_intraday: bool = False,
    has_bid_ask: bool = False,
    has_depth: bool = False,
    has_trades: bool = False,
    has_trade_count: bool = False,
    timestamp_known: bool = False,
    timestamp_reliable: bool = False,
    price_observation_type: str = "UNKNOWN",
    latest_completed_session: bool = False,
    has_current_session_price: bool = False,
    has_current_session_volume: bool = False,
    require_microstructure: bool = False,
    execution_fresh_seconds: float = 120,
) -> SymbolQuality:
    providers_used = providers_used or []
    reliability = 0.0
    if providers_used:
        reliability = max(PROVIDER_RELIABILITY.get(p, 50.0) for p in providers_used)

    completeness_bits = [has_price, has_volume, has_daily, has_intraday]
    completeness = 100.0 * sum(1 for b in completeness_bits if b) / len(completeness_bits)

    if agreement is True:
        agree_score = 100.0
    elif agreement is False:
        agree_score = 40.0
    else:
        agree_score = 60.0

    ts_score = 100.0 if (timestamp_known and timestamp_reliable) else (50.0 if timestamp_known else 20.0)
    fresh_score = FRESHNESS_SCORE.get(freshness_class, 20.0)
    # Do not heavily penalize research on weekend when observation is latest completed session
    if freshness_class == "STALE_EXPECTED" and latest_completed_session:
        fresh_score = max(fresh_score, LATEST_COMPLETED_SESSION_FRESHNESS)

    bd = QualityBreakdown(
        freshness=fresh_score,
        source_reliability=reliability,
        cross_source_agreement=agree_score,
        completeness=completeness,
        timestamp_quality=ts_score,
    )

    availability = {
        "Price": "AVAILABLE" if has_price else "UNAVAILABLE",
        "Volume": "AVAILABLE" if has_volume else "UNAVAILABLE",
        "Daily candles": "AVAILABLE" if has_daily else "UNAVAILABLE",
        "Intraday candles": "AVAILABLE" if has_intraday else "UNAVAILABLE",
        "Trade count": "AVAILABLE" if has_trade_count else "UNAVAILABLE",
        "Bid/Ask": "AVAILABLE" if has_bid_ask else "UNAVAILABLE",
        "Depth": "AVAILABLE" if has_depth else "UNAVAILABLE",
        "Trades": "AVAILABLE" if has_trades else "UNAVAILABLE",
    }

    grade, grade_missing = compute_execution_grade(
        price_observation_type=price_observation_type,
        freshness_class=freshness_class,
        freshness_seconds=freshness_seconds,
        has_current_session_price=has_current_session_price,
        has_current_session_volume=has_current_session_volume,
        timestamp_reliable=timestamp_reliable,
        has_bid_ask=has_bid_ask,
        has_depth=has_depth,
        has_trades=has_trades,
        require_microstructure=require_microstructure,
        execution_fresh_seconds=execution_fresh_seconds,
    )

    missing = list(grade_missing)
    if not has_bid_ask:
        missing.append("bid_ask")
    if not has_depth:
        missing.append("depth")
    if not has_trades:
        missing.append("trades")
    missing = list(dict.fromkeys(missing))

    warnings = []
    if freshness_class in {"DELAYED", "STALE", "STALE_EXPECTED", "STALE_UNEXPECTED", "UNKNOWN"}:
        warnings.append(f"Not suitable for execution timing (freshness={freshness_class})")
    if freshness_class == "STALE_EXPECTED":
        warnings.append("STALE_EXPECTED: EGX session closed (weekend/off-hours); not treated as provider failure")
    if latest_completed_session and freshness_class == "STALE_EXPECTED":
        warnings.append("LATEST_COMPLETED_SESSION=YES: research-usable despite weekend/off-hours")
    if freshness_class == "STALE_UNEXPECTED":
        warnings.append("STALE_UNEXPECTED: EGX session expected open but latest observation is stale")
    if price_observation_type in {CANDLE_CLOSE, DAILY_CLOSE}:
        warnings.append(f"price_observation_type={price_observation_type} (not a live quote)")
    if grade == "NO":
        warnings.append("EXECUTION_GRADE=NO (hard gate)")
    if not has_depth:
        warnings.append("Depth unavailable without licensed feed")

    edq = bd.execution_score()
    if not (has_bid_ask or has_depth or has_trades):
        edq = min(edq, 45.0)
    # Hard gate: grade NO does not change numeric EDQ formula, but documents override prohibition
    # (scanner must use EXECUTION_GRADE, not EDQ alone)

    return SymbolQuality(
        symbol=symbol,
        availability=availability,
        research_data_quality=bd.research_score(),
        execution_data_quality=edq,
        execution_grade=grade,
        latest_completed_session=latest_completed_session,
        components={
            "freshness": bd.freshness,
            "source_reliability": bd.source_reliability,
            "cross_source_agreement": bd.cross_source_agreement,
            "completeness": bd.completeness,
            "timestamp_quality": bd.timestamp_quality,
        },
        missing_execution_fields=missing,
        warnings=warnings,
    )
