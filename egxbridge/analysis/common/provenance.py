"""Bridge market evidence assembly for Funnel/Explorer handoffs."""
from __future__ import annotations

from typing import Any
from pathlib import Path
import json

from egxbridge import __version__ as BRIDGE_VERSION
from egxbridge.analysis.common.models import Availability
from egxbridge.analysis.common.candle_export import (
    enrich_candles,
    timing_safe_candles,
    provenance_record,
    NORMALIZED,
    LEGACY_UNNORMALIZED,
)
from egxbridge.quality import score_symbol


def availability(status: str, notes: str = "") -> dict[str, Any]:
    return Availability(status=status, notes=notes).to_dict()


def _dq_grade(score: float | None, *, execution: bool = False, execution_grade: str = "NO") -> str:
    if execution and execution_grade == "NO":
        return "NOT_RELIABLE"
    if score is None:
        return "UNKNOWN"
    if score >= 70:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


def _latest_completed_session(daily_enriched: list[dict[str, Any]]) -> str | None:
    """Prefer Yahoo (or any) daily session_date from NORMALIZED rows only."""
    safe = [
        r for r in daily_enriched
        if r.get("timestamp_normalization_status") == NORMALIZED and r.get("session_date")
    ]
    if not safe:
        return None
    # Prefer yahoo when present
    yahoo = [r for r in safe if (r.get("provider") or "").lower() == "yahoo"]
    pool = yahoo or safe
    return max(r["session_date"] for r in pool)


def _classify_stored_quote(q: dict[str, Any]) -> dict[str, Any]:
    """Repair quote-row semantics at handoff export. Do not invent live quotes from daily bars."""
    out = dict(q)
    prov = (out.get("provider") or "").lower()
    raw_ref = str(out.get("raw_reference") or "")

    if "daily_close" in raw_ref.lower():
        out["price_observation_type"] = "DAILY_CLOSE"
        out["timestamp_semantics"] = "DAILY_BAR"
        out["volume_semantics"] = "DAILY_FINAL_VOLUME"
        out["volume_interval"] = "1d"
    elif "candle_close" in raw_ref.lower():
        out["price_observation_type"] = out.get("price_observation_type") or "CANDLE_CLOSE"
        out["timestamp_semantics"] = out.get("timestamp_semantics") or "BAR_OPEN"
        if not out.get("volume_semantics"):
            out["volume_semantics"] = "BAR_VOLUME"
    elif ":quote" in raw_ref.lower() or raw_ref.lower().endswith("quote"):
        if not out.get("price_observation_type") or out.get("price_observation_type") == "UNKNOWN":
            if prov == "egid" and out.get("bid") is not None:
                out["price_observation_type"] = "LIVE_QUOTE"
            else:
                out["price_observation_type"] = "DELAYED_QUOTE"
        out["timestamp_semantics"] = out.get("timestamp_semantics") or "QUOTE_OBSERVATION"
        if not out.get("volume_semantics") and out.get("volume") is not None:
            out["volume_semantics"] = "UNKNOWN_VOLUME"
    elif prov == "yahoo":
        # Legacy yahoo rows without raw_reference: historical path was daily_close
        out["price_observation_type"] = "DAILY_CLOSE"
        out["timestamp_semantics"] = "DAILY_BAR"
        out["volume_semantics"] = "DAILY_FINAL_VOLUME"
        out["volume_interval"] = "1d"
    else:
        if not out.get("price_observation_type") or out.get("price_observation_type") == "UNKNOWN":
            if prov == "egid":
                out["price_observation_type"] = "LIVE_QUOTE" if out.get("bid") is not None else "DELAYED_QUOTE"
            elif prov == "tradingview":
                out["price_observation_type"] = "DELAYED_QUOTE"
            else:
                out["price_observation_type"] = "UNKNOWN"
        if not out.get("timestamp_semantics"):
            pot = out.get("price_observation_type")
            if pot in {"LIVE_QUOTE", "DELAYED_QUOTE"}:
                out["timestamp_semantics"] = "QUOTE_OBSERVATION"
            elif pot == "DAILY_CLOSE":
                out["timestamp_semantics"] = "DAILY_BAR"
            elif pot == "CANDLE_CLOSE":
                out["timestamp_semantics"] = "BAR_OPEN"
            else:
                out["timestamp_semantics"] = "UNKNOWN"
        if not out.get("volume_semantics") and out.get("volume") is not None:
            out["volume_semantics"] = "UNKNOWN_VOLUME"

    out.setdefault("session_date", None)
    out.setdefault("effective_session_date", None)
    out.setdefault("provider_raw_timestamp", out.get("provider_timestamp"))
    out.setdefault(
        "normalized_utc_timestamp",
        out.get("normalized_utc_timestamp") or out.get("provider_timestamp"),
    )
    out.setdefault("normalized_cairo_timestamp", None)
    return out


def bridge_market_evidence(db, symbol: str) -> dict[str, Any]:
    """Gather deterministic Bridge evidence. Never fabricate fundamentals/fair value."""
    symbol = symbol.upper()
    out: dict[str, Any] = {
        "symbol": symbol,
        "bridge_version": BRIDGE_VERSION,
        "fabricated_fundamentals": False,
        "fabricated_fair_value": False,
    }
    if db is None:
        out["market_data"] = availability("UNAVAILABLE", "No database")
        out["execution_grade"] = "NO"
        out["research_data_quality"] = "UNKNOWN"
        out["research_data_quality_score"] = None
        out["research_data_quality_grade"] = "UNKNOWN"
        out["execution_data_quality"] = "NOT_RELIABLE"
        out["execution_data_quality_score"] = None
        out["execution_data_quality_grade"] = "NOT_RELIABLE"
        out["missing_capabilities"] = ["quotes", "candles", "depth", "trades", "bid_ask"]
        out["session_date"] = None
        out["latest_completed_market_session"] = None
        out["latest_session"] = None
        return out

    quotes = db.fetch_latest_quotes(symbol)
    daily_raw = db.fetch_candles(symbol, "1d", limit=200)
    intraday_raw: list[dict[str, Any]] = []
    for iv in ("5m", "15m", "1h"):
        rows = db.fetch_candles(symbol, iv, limit=100)
        if rows:
            intraday_raw.extend([{**r, "interval": iv} for r in rows])

    daily = enrich_candles([{**r, "interval": r.get("interval") or "1d"} for r in daily_raw])
    intraday = enrich_candles(intraday_raw)
    daily_timing = timing_safe_candles(daily)
    intraday_timing = timing_safe_candles(intraday)

    q = _classify_stored_quote(quotes[0]) if quotes else {}
    out["quote"] = q or None
    close_src = daily_timing[-1] if daily_timing else (daily[-1] if daily else None)
    out["latest_close"] = q.get("last") if q else (close_src.get("close") if close_src else None)

    latest_session = _latest_completed_session(daily)
    if q:
        q["session_date"] = q.get("session_date") or latest_session
        q["effective_session_date"] = q.get("effective_session_date") or latest_session
    out["session_date"] = latest_session
    out["latest_completed_market_session"] = latest_session
    out["latest_session"] = latest_session
    out["effective_session_date"] = latest_session

    # Selected / alternate observations with full semantics (not live-quote mislabels)
    if close_src:
        out["selected_price_observation"] = {
            "source": "daily_candle",
            "provider": close_src.get("provider"),
            "price_observation_type": close_src.get("price_observation_type") or "DAILY_CLOSE",
            "volume_semantics": close_src.get("volume_semantics") or "DAILY_FINAL_VOLUME",
            "volume_interval": close_src.get("volume_interval") or "1d",
            "timestamp_semantics": close_src.get("timestamp_semantics") or "DAILY_BAR",
            "session_date": close_src.get("session_date") or latest_session,
            "effective_session_date": close_src.get("effective_session_date") or latest_session,
            "provider_raw_timestamp": close_src.get("provider_raw_timestamp"),
            "normalized_utc_timestamp": close_src.get("normalized_utc_timestamp"),
            "normalized_cairo_timestamp": close_src.get("normalized_cairo_timestamp"),
            "close": close_src.get("close"),
        }
    if intraday_timing:
        alt = intraday_timing[-1]
        out["alternate_price_observation"] = {
            "source": "intraday_candle",
            "provider": alt.get("provider"),
            "price_observation_type": alt.get("price_observation_type") or "CANDLE_CLOSE",
            "volume_semantics": alt.get("volume_semantics"),
            "volume_interval": alt.get("volume_interval") or alt.get("interval"),
            "timestamp_semantics": alt.get("timestamp_semantics"),
            "session_date": alt.get("session_date"),
            "effective_session_date": alt.get("effective_session_date"),
            "provider_raw_timestamp": alt.get("provider_raw_timestamp"),
            "normalized_utc_timestamp": alt.get("normalized_utc_timestamp"),
            "normalized_cairo_timestamp": alt.get("normalized_cairo_timestamp"),
            "close": alt.get("close"),
            "note": "CANDLE_CLOSE is not a genuine live quote",
        }

    out["providers_used"] = sorted({r.get("provider") for r in quotes if r.get("provider")})
    if daily:
        out["providers_used"] = sorted(
            set(out["providers_used"]) | {r.get("provider") for r in daily if r.get("provider")}
        )

    from egxbridge.scanner import compute_scanner_metrics
    # Scanner / freshness: NORMALIZED only
    metrics = compute_scanner_metrics(daily_timing)
    if latest_session:
        metrics["session_date"] = latest_session
        metrics["latest_completed_market_session"] = latest_session
    out["scanner_metrics"] = metrics

    has_price = out["latest_close"] is not None
    has_daily = bool(daily_timing)
    has_intraday = bool(intraday_timing)
    has_volume = bool(daily_timing and daily_timing[-1].get("volume") is not None)
    has_bid = q.get("bid") is not None and q.get("ask") is not None
    freshness = (q.get("freshness_class") if q else None) or (
        daily_timing[-1].get("freshness_class") if daily_timing else "UNKNOWN"
    )
    ts_reliable = bool(daily_timing)  # only normalized rows participate

    quality = score_symbol(
        symbol=symbol,
        freshness_class=freshness or "UNKNOWN",
        providers_used=out["providers_used"],
        has_price=has_price,
        has_volume=has_volume,
        has_daily=has_daily,
        has_intraday=has_intraday,
        has_bid_ask=has_bid,
        has_depth=False,
        has_trades=False,
        timestamp_known=ts_reliable,
        timestamp_reliable=ts_reliable,
        price_observation_type="DAILY_CLOSE" if has_daily else "UNKNOWN",
        latest_completed_session=bool(latest_session),
        has_current_session_price=False,
        has_current_session_volume=False,
    )
    out["execution_grade"] = quality.execution_grade
    out["research_data_quality_score"] = quality.research_data_quality
    out["execution_data_quality_score"] = quality.execution_data_quality
    out["research_data_quality_grade"] = _dq_grade(quality.research_data_quality)
    out["execution_data_quality_grade"] = _dq_grade(
        quality.execution_data_quality,
        execution=True,
        execution_grade=quality.execution_grade,
    )
    # Preserve both letter (compat) and numeric
    out["research_data_quality"] = out["research_data_quality_grade"]
    out["execution_data_quality"] = out["execution_data_quality_grade"]
    out["quality_components"] = quality.components
    out["missing_capabilities"] = list(quality.missing_execution_fields)
    if not has_intraday:
        out["missing_capabilities"].append("intraday_ohlcv")
    if not has_daily:
        out["missing_capabilities"].append("daily_ohlcv")
    out["missing_capabilities"] = list(dict.fromkeys(out["missing_capabilities"]))

    out["daily_candles"] = daily
    out["intraday_candles"] = intraday
    out["daily_candles_timing_safe"] = daily_timing
    out["intraday_candles_timing_safe"] = intraday_timing

    prov_daily = [provenance_record(r) for r in daily]
    prov_intra = [provenance_record(r) for r in intraday]
    out["provider_provenance"] = {
        "quotes": [
            {
                "provider": cq.get("provider"),
                "capture_timestamp": cq.get("capture_timestamp"),
                "provider_timestamp": cq.get("provider_timestamp"),
                "raw_reference": cq.get("raw_reference"),
                "price_observation_type": cq.get("price_observation_type"),
                "timestamp_semantics": cq.get("timestamp_semantics"),
                "volume_semantics": cq.get("volume_semantics"),
                "volume_interval": cq.get("volume_interval"),
                "session_date": cq.get("session_date"),
                "effective_session_date": cq.get("effective_session_date"),
                "provider_raw_timestamp": cq.get("provider_raw_timestamp"),
                "normalized_utc_timestamp": cq.get("normalized_utc_timestamp"),
                "normalized_cairo_timestamp": cq.get("normalized_cairo_timestamp"),
                "timestamp_normalization_status": (
                    NORMALIZED if cq.get("normalized_utc_timestamp") or cq.get("provider_timestamp") else "UNKNOWN"
                ),
            }
            for cq in ([_classify_stored_quote(r) for r in quotes] if quotes else [])
        ],
        "daily": prov_daily,
        "intraday": prov_intra,
        "daily_providers": sorted({r.get("provider") for r in daily if r.get("provider")}),
        "intraday_providers": sorted({r.get("provider") for r in intraday if r.get("provider")}),
        "legacy_unnormalized_excluded_from_timing": any(
            r.get("timestamp_normalization_status") == LEGACY_UNNORMALIZED for r in daily + intraday
        ),
        "note": "LEGACY_UNNORMALIZED timestamps must not drive freshness or Explorer timing",
    }
    out["known_missing_data"] = {
        "fundamentals": availability("UNAVAILABLE", "Bridge does not fabricate fundamentals; ChatGPT researches"),
        "news": availability("UNAVAILABLE", "ChatGPT researches news within Funnel rules"),
        "bid_ask": availability("UNAVAILABLE" if not has_bid else "AVAILABLE"),
        "depth": availability("UNAVAILABLE"),
        "trades": availability("UNAVAILABLE"),
        "note": "EXECUTION_GRADE=NO does not block long-term Funnel valuation",
    }
    try:
        out["provider_quality"] = db.fetch_provider_status()
    except Exception:
        out["provider_quality"] = []
    return out


def write_market_bundle(dest: Path, evidence: dict[str, Any]):
    """Write market evidence under dest (typically package/market/)."""
    dest.mkdir(parents=True, exist_ok=True)
    from egxbridge.analysis.common.packaging import write_json
    from egxbridge.storage import rows_to_csv

    snapshot = {
        k: v for k, v in evidence.items()
        if k not in {
            "daily_candles", "intraday_candles",
            "daily_candles_timing_safe", "intraday_candles_timing_safe",
        }
    }
    write_json(dest / "market_snapshot.json", snapshot)
    write_json(dest / "scanner_metrics.json", evidence.get("scanner_metrics") or {})
    write_json(dest / "data_quality.json", {
        "research_data_quality": evidence.get("research_data_quality"),
        "research_data_quality_score": evidence.get("research_data_quality_score"),
        "research_data_quality_grade": evidence.get("research_data_quality_grade"),
        "execution_data_quality": evidence.get("execution_data_quality"),
        "execution_data_quality_score": evidence.get("execution_data_quality_score"),
        "execution_data_quality_grade": evidence.get("execution_data_quality_grade"),
        "execution_grade": evidence.get("execution_grade"),
        "missing_capabilities": evidence.get("missing_capabilities"),
        "known_missing_data": evidence.get("known_missing_data"),
        "session_date": evidence.get("session_date"),
        "latest_completed_market_session": evidence.get("latest_completed_market_session"),
    })
    write_json(dest / "provider_provenance.json", evidence.get("provider_provenance") or {})
    write_json(dest / "provider_quality.json", evidence.get("provider_quality") or [])
    write_json(dest / "known_missing_data.json", evidence.get("known_missing_data") or {})
    write_json(dest / "session_meta.json", {
        "session_date": evidence.get("session_date"),
        "latest_completed_market_session": evidence.get("latest_completed_market_session"),
        "effective_session_date": evidence.get("effective_session_date"),
        "note": "Distinct from package_generated_at / data_capture_cutoff",
    })
    rows_to_csv(dest / "daily_candles.csv", evidence.get("daily_candles") or [])
    rows_to_csv(dest / "intraday_candles.csv", evidence.get("intraday_candles") or [])
