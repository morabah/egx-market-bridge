"""Canonical universe eligibility states — no silent ticker drops."""
from __future__ import annotations

from typing import Any


COVERED = "COVERED"
EXCLUDED_BY_RULE = "EXCLUDED_BY_RULE"
DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
SOURCE_MISSING = "SOURCE_MISSING"

UNIVERSE_STATES = (COVERED, EXCLUDED_BY_RULE, DATA_INSUFFICIENT, SOURCE_MISSING)


def eligibility_state(data_status: str | None, *, security_type: str | None = None) -> str:
    status = str(data_status or "").upper()
    if status in {"SCANNER_ELIGIBLE", "DATA_AVAILABLE", "COVERED"}:
        return COVERED
    if status in {"NO_MAPPING", "SOURCE_MISSING"}:
        return SOURCE_MISSING
    if status in {"DAILY_DATA_UNAVAILABLE", "INSUFFICIENT_HISTORY", "DATA_INSUFFICIENT", "DATA_UNAVAILABLE"}:
        return DATA_INSUFFICIENT
    if status.startswith("EXCLUDED") or status in {"UNKNOWN_SECURITY_TYPE"}:
        return EXCLUDED_BY_RULE
    if security_type and security_type not in {"EQUITY", None, ""}:
        return EXCLUDED_BY_RULE
    if not status:
        return SOURCE_MISSING
    return DATA_INSUFFICIENT


def identity_row(
    *,
    canonical_ticker: str,
    security_id: str | None = None,
    current_name: str = "",
    aliases: list[str] | None = None,
    exchange: str = "EGX",
    instrument_type: str = "EQUITY",
    data_status: str | None = None,
    eligibility_reason: str | None = None,
) -> dict[str, Any]:
    state = eligibility_state(data_status, security_type=instrument_type)
    ticker = str(canonical_ticker or "").upper()
    names = [a for a in (aliases or []) if a]
    if ticker and ticker not in {str(a).upper() for a in names}:
        names = [ticker, *names]
    return {
        "canonical_ticker": ticker,
        "security_id": security_id or ticker,
        "current_name": current_name or "",
        "aliases": names,
        "exchange": exchange,
        "instrument_type": instrument_type or "EQUITY",
        "eligibility_state": state,
        "eligibility_reason": eligibility_reason or data_status or state,
        "universe_state": state,
    }


def build_universe_coverage(rows: list[dict[str, Any]], *, expected_equities: int | None = None, exchange_completeness_verified: bool = False) -> dict[str, Any]:
    """Reconcile equity-level coverage. Indices/funds are excluded_by_rule and not the denominator."""
    equities = [r for r in rows if str(r.get("instrument_type") or "EQUITY").upper() == "EQUITY"]
    expected = expected_equities if expected_equities is not None else len(equities)
    counts = {s: 0 for s in UNIVERSE_STATES}
    missing_tickers: list[str] = []
    for r in equities:
        state = r.get("eligibility_state") or r.get("universe_state") or SOURCE_MISSING
        if state not in counts:
            state = DATA_INSUFFICIENT
        counts[state] += 1
        if state in {DATA_INSUFFICIENT, SOURCE_MISSING}:
            missing_tickers.append(str(r.get("canonical_ticker") or ""))
    denom_ok = expected is not None and int(expected) > 0
    covered = counts[COVERED]
    coverage_pct = round(100.0 * covered / float(expected), 2) if denom_ok else None
    states_sum = sum(counts.values())
    reconcile_ok = denom_ok and states_sum == int(expected)
    # Whole-EGX is an identity claim: every expected equity is present and COVERED.
    # Scanner coverage % (e.g. 80%+) is exploratory quality, not this flag.
    registry_complete = bool(
        denom_ok
        and reconcile_ok
        and counts[SOURCE_MISSING] == 0
        and counts[DATA_INSUFFICIENT] == 0
        and covered == int(expected)
    )
    whole = registry_complete and exchange_completeness_verified
    if not denom_ok:
        coverage_status = "NOT_RELIABLE"
        run_scope = "PARTIAL_UNIVERSE"
        whole = False
        coverage_pct = None
    elif not reconcile_ok:
        coverage_status = "NOT_RELIABLE"
        run_scope = "PARTIAL_UNIVERSE"
        whole = False
    elif not registry_complete:
        coverage_status = "PARTIAL"
        run_scope = "PARTIAL_UNIVERSE"
    else:
        coverage_status = "OK"
        run_scope = "WHOLE_EGX" if whole else "FULL_KNOWN_UNIVERSE"
    return {
        "expected_equities": int(expected) if denom_ok else None,
        "scanner_eligible": covered,
        "covered": covered,
        "data_insufficient": counts[DATA_INSUFFICIENT],
        "source_missing": counts[SOURCE_MISSING],
        "excluded_by_rule": counts[EXCLUDED_BY_RULE],
        "coverage_pct": coverage_pct,
        "exploratory_coverage_quality": (
            "HIGH" if coverage_pct is not None and coverage_pct >= 80
            else "MEDIUM" if coverage_pct is not None and coverage_pct >= 60
            else "LOW" if coverage_pct is not None and coverage_pct >= 30
            else "INSUFFICIENT"
        ) if coverage_pct is not None else "INSUFFICIENT",
        "whole_egx_claim_allowed": whole,
        "known_universe_complete": registry_complete,
        "exchange_completeness_verified": exchange_completeness_verified,
        "market_wide_confidence_allowed": whole,
        "coverage_status": coverage_status,
        "run_scope": run_scope,
        "states_sum": states_sum,
        "reconcile_ok": reconcile_ok,
        "missing_tickers": [t for t in missing_tickers if t],
    }


def ensure_canonical_identities(
    rows: list[dict[str, Any]] | None,
    *,
    name_aliases: dict[str, list[str]] | None = None,
    expected_tickers: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Every aliased canonical security must appear, even with SOURCE_MISSING."""
    from egxbridge.symbols import canonicalize_any, load_name_aliases

    aliases = name_aliases if name_aliases is not None else load_name_aliases()
    by: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        t = str(row.get("canonical_ticker") or "").upper()
        if not t:
            continue
        canon = canonicalize_any(t) or t
        existing = by.get(canon)
        if existing is None:
            merged = dict(row)
            merged["canonical_ticker"] = canon
            by[canon] = merged
        else:
            names = list(existing.get("aliases") or [])
            for a in row.get("aliases") or []:
                if a and a not in names:
                    names.append(a)
            existing["aliases"] = names
            if not existing.get("current_name") and row.get("current_name"):
                existing["current_name"] = row.get("current_name")
    expected_set = {canonicalize_any(t) or str(t).upper() for t in (expected_tickers or []) if t}
    for canon, names in (aliases or {}).items():
        c = canonicalize_any(canon) or str(canon).upper()
        if not c:
            continue
        if c not in by:
            if expected_tickers is not None and c not in expected_set:
                continue
            if expected_tickers is None:
                continue
            by[c] = identity_row(
                canonical_ticker=c,
                current_name=max([n for n in names if n], key=len) if names else c,
                aliases=list(names or [c]),
                instrument_type="EQUITY",
                data_status="SOURCE_MISSING",
            )
            continue
        have = {str(a).upper() for a in (by[c].get("aliases") or [])}
        extra = [a for a in (names or []) if a and str(a).upper() not in have]
        if extra:
            by[c]["aliases"] = list(by[c].get("aliases") or []) + extra
        if not by[c].get("current_name"):
            named = [n for n in (names or []) if n and str(n).upper() != c]
            if named:
                by[c]["current_name"] = max(named, key=len)
    for raw in expected_tickers or []:
        c = canonicalize_any(raw) or str(raw).upper()
        if c and c not in by:
            by[c] = identity_row(
                canonical_ticker=c,
                aliases=[c],
                instrument_type="EQUITY",
                data_status="SOURCE_MISSING",
            )
    return list(by.values())
