"""Daily bar provider selection. Prefer the freshest completed session without inventing prices."""
from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
import math

from egxbridge.semantics import previous_egx_session_date, session_date_cairo


def ohlcv_issue(row: dict[str, Any]) -> str | None:
    """Validate observed prices without repairing or inventing source values."""
    try:
        o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
    except (KeyError, TypeError, ValueError):
        return "MISSING_OHLC"
    if not all(math.isfinite(v) and v > 0 for v in (o, h, l, c)):
        return "INVALID_PRICE"
    tolerance = max(o, h, l, c) * 1e-8
    if h + tolerance < max(o, c, l) or l - tolerance > min(o, c, h):
        return "INCONSISTENT_OHLC"
    if row.get("volume") is not None:
        try:
            volume = float(row["volume"])
            if not math.isfinite(volume) or volume < 0:
                return "INVALID_VOLUME"
        except (TypeError, ValueError):
            return "INVALID_VOLUME"
    return None


def captured_after_session_close(row: dict[str, Any]) -> bool:
    """Finality is established at capture time; waiting cannot finalize an old bar."""
    session = session_of(row)
    if not session:
        return False
    capture = row.get("capture_timestamp")
    if not capture:
        return row.get("daily_session_complete") is True
    try:
        captured = datetime.fromisoformat(str(capture).replace("Z", "+00:00"))
        if captured.tzinfo is None:
            return False
        return session <= previous_egx_session_date(captured)
    except (TypeError, ValueError):
        return False


def session_of(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    sess = str(row.get("session_date") or "").strip()
    if len(sess) >= 10:
        return sess[:10]
    for key in ("normalized_cairo_timestamp", "normalized_utc_timestamp", "timestamp"):
        derived = session_date_cairo(row.get(key))
        if derived:
            return derived
    ts = str(row.get("timestamp") or "")
    return ts[:10] if len(ts) >= 10 else ""


def max_session(rows: list[dict[str, Any]] | None) -> str:
    dates = [session_of(r) for r in (rows or []) if session_of(r)]
    return max(dates) if dates else ""


def completed_session_rows(
    rows: list[dict[str, Any]] | None,
    *,
    as_of=None,
    through_session: str | None = None,
) -> list[dict[str, Any]]:
    """Drop incomplete in-progress session bars from daily OHLCV used as session closes."""
    as_of = as_of or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    cutoff = through_session or previous_egx_session_date(as_of)
    out = []
    for row in rows or []:
        if row.get("daily_session_complete") is False or not captured_after_session_close(row):
            continue
        sess = session_of(row)
        if not sess:
            continue
        if cutoff and sess > cutoff:
            continue
        if as_of is not None and row.get("capture_timestamp"):
            captured = datetime.fromisoformat(str(row["capture_timestamp"]).replace("Z", "+00:00"))
            if captured > as_of:
                continue
        out.append(row)
    return out


def select_daily_pool(
    rows: list[dict[str, Any]] | None,
    *,
    as_of=None,
    through_session: str | None = None,
) -> tuple[list[dict[str, Any]], str, str]:
    """Pick one provider series for metrics: newest *completed* session wins; Yahoo wins ties."""
    rows = completed_session_rows(rows, as_of=as_of, through_session=through_session)
    if not rows:
        return [], "none", "No completed daily bars available."
    by_provider: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        prov = (row.get("provider") or "unknown").lower()
        by_provider.setdefault(prov, []).append(row)
    # A bad bar breaks the indicator lookback. Do not bridge across rejected days
    # and silently turn a 20-session statistic into 20 scattered observations.
    for prov, series in list(by_provider.items()):
        unique = {}
        for row in sorted(series, key=lambda c: c.get("capture_timestamp") or ""):
            unique[session_of(row)] = row
        tail = []
        for session in sorted(unique):
            row = unique[session]
            if ohlcv_issue(row):
                tail = []
            else:
                tail.append(row)
        if tail:
            by_provider[prov] = tail
        else:
            del by_provider[prov]
    if not by_provider:
        return [], "none", "No valid daily series remains after OHLCV validation. Raw records are retained for audit."
    ranked = sorted(
        by_provider.items(),
        key=lambda item: (max_session(item[1]), len({session_of(r) for r in item[1]}), item[0] == "yahoo"),
        reverse=True,
    )
    provider, pool = ranked[0]
    latest = max_session(pool)
    yahoo = by_provider.get("yahoo") or []
    yahoo_latest = max_session(yahoo)
    if provider != "yahoo" and yahoo_latest and latest > yahoo_latest:
        note = (
            f"Yahoo daily stops at {yahoo_latest}; using {provider} through {latest}."
        )
    elif provider != "yahoo":
        note = f"Using {provider} daily bars through {latest or '—'}."
    else:
        note = f"Using Yahoo daily bars through {latest or '—'}."
    return pool, provider, note


def daily_session_status(
    rows_or_max: list[dict[str, Any]] | str | None,
    *,
    as_of=None,
) -> dict[str, Any]:
    """Compare stored daily coverage to the expected last completed EGX session."""
    if isinstance(rows_or_max, str):
        stored = rows_or_max
        provider = "unknown"
        note = ""
    else:
        _pool, provider, note = select_daily_pool(rows_or_max, as_of=as_of)
        stored = max_session(_pool)
    expected = previous_egx_session_date(as_of)
    lagging = bool(expected and (not stored or stored < expected))
    return {
        "stored_session": stored or None,
        "expected_session": expected,
        "lagging": lagging,
        "provider": provider,
        "note": (
            f"Stored daily bars ({stored or 'none'}) are behind expected session {expected}."
            if lagging else
            note or f"Daily bars current through {stored or '—'}."
        ),
    }
