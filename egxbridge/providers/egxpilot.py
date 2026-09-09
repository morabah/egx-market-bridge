"""One public bulk snapshot; provider update times are not exchange trade times."""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

import requests

from egxbridge.analysis.common.data_stamp import CAIRO, parse_dt
from egxbridge.daily_bars import ohlcv_issue
from egxbridge.providers.base import Quote

ENDPOINT = "https://egxpilot.com/api/stocks/all"
DOCUMENTATION = "https://www.egxpilot.com/developers.html"


def _number(value) -> float | None:
    try:
        result = float(str(value).replace(",", "").rstrip("%"))
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def fetch_market_snapshot(tickers: list[str], *, timeout: float = 15) -> dict[str, Any]:
    """Bounded supplementary evidence. Never fills or overwrites daily candles.

    Only explicit canonical matches are attached. No ratings, signals, AI text,
    or implied dates are imported from this source.
    """
    started = datetime.now(timezone.utc)
    report: dict[str, Any] = {
        "provider": "egxpilot", "endpoint": ENDPOINT, "documentation": DOCUMENTATION,
        "started_at": started.isoformat(), "network_attempts": 1,
        "exchange_timestamp_verified": False, "daily_history_available": False,
        "timestamp_semantics": "PROVIDER_RECORD_UPDATE_NOT_TRADE",
        "note": "Supplementary snapshot only. CreatedAt is a provider record update, not a verified trade time or final daily close. Batch updatedAt does not date individual prices.",
        "quotes": [],
    }
    try:
        response = requests.get(ENDPOINT, timeout=max(1, min(float(timeout), 20)))
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("stocks") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not rows or len(rows) > 2000:
            raise ValueError("Invalid or empty bulk stock response")
        captured = datetime.now(timezone.utc)
        known = set(tickers)
        seen: set[str] = set()
        quotes = []
        unmatched = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("Symbol") or "").upper()
            if symbol not in known:
                unmatched.append(symbol)
                continue
            updated = parse_dt(row.get("CreatedAt"))
            quote = Quote(
                symbol=symbol, provider="egxpilot", capture_timestamp=captured.isoformat(),
                last=_number(row.get("LastPrice")), open=_number(row.get("OpenPrice")),
                high=_number(row.get("High")), low=_number(row.get("Low")),
                prev_close=_number(row.get("PrevClose")), change_pct=_number(row.get("DailyChange")),
                volume=_number(row.get("Volume")), turnover=_number(row.get("Turnover")),
                provider_mode="supplemental_snapshot", freshness_class="UNVERIFIED",
                provider_raw_timestamp=row.get("CreatedAt"),
                timestamp_semantics="PROVIDER_RECORD_UPDATE_NOT_TRADE", raw_reference=ENDPOINT,
            ).to_dict()
            issue = ohlcv_issue({**quote, "close": quote["last"]})
            issues = [issue] if issue else []
            if not updated:
                issues.append("MISSING_SOURCE_TIMESTAMP")
            elif updated > captured:
                issues.append("FUTURE_SOURCE_TIMESTAMP")
            if symbol in seen:
                issues.append("DUPLICATE_SYMBOL")
            seen.add(symbol)
            if quote["last"] and quote["prev_close"] and quote["change_pct"] is not None:
                calculated = (quote["last"] / quote["prev_close"] - 1) * 100
                if abs(calculated - quote["change_pct"]) > 0.15:
                    issues.append("INCONSISTENT_CHANGE_PCT")
            provider_date = updated.astimezone(CAIRO).date().isoformat() if updated else None
            quote.update(
                provider_record_updated_at=updated.isoformat() if updated else None,
                provider_record_date=provider_date,
                provider_record_age_seconds=(captured - updated).total_seconds() if updated else None,
                validation_issues=issues,
                state="QUARANTINED" if issues else "STALE" if provider_date < captured.astimezone(CAIRO).date().isoformat() else "UNVERIFIED",
            )
            quotes.append(quote)
        report.update(
            status="SUPPLEMENTAL_UNVERIFIED", quotes=quotes, returned_instruments=len(rows),
            matched_equities=len(seen), unmatched_symbols=sorted(set(unmatched)),
            provider_batch_updated_at=payload.get("updatedAt"),
            quarantined=sum(bool(q["validation_issues"]) for q in quotes),
            stale=sum(q["state"] == "STALE" for q in quotes),
        )
    except (requests.RequestException, ValueError, TypeError) as exc:
        report.update(status="UNAVAILABLE", error=str(exc)[:240])
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    return report
