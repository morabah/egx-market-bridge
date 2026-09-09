"""Explicit clocks for operator downloads: session close vs capture vs last bar."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from egxbridge.analysis.common.packaging import write_json, write_text

CAIRO = ZoneInfo("Africa/Cairo")
PREFERRED_INTRADAY = ("1m", "5m", "15m")


def parse_dt(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def clocks(at: datetime | str | None = None) -> dict[str, str]:
    dt = parse_dt(at) if not isinstance(at, datetime) else at
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    utc = dt.astimezone(timezone.utc)
    cairo = dt.astimezone(CAIRO)
    return {
        "utc": utc.isoformat(),
        "cairo": cairo.isoformat(),
        "cairo_display": cairo.strftime("%Y-%m-%d %H:%M Cairo"),
        "utc_display": utc.strftime("%Y-%m-%d %H:%M UTC"),
        "filename_tag": cairo.strftime("%Y%m%d-%H%M"),
        "session_hint": cairo.date().isoformat(),
    }


def display_cairo(value: str | datetime | None, *, fallback: str = "unknown") -> str:
    if parse_dt(value) is None:
        return fallback
    clk = clocks(value)
    return clk["cairo_display"]


def delay_seconds(later: str | datetime | None, earlier: str | datetime | None) -> float | None:
    a = parse_dt(later)
    b = parse_dt(earlier)
    if a is None or b is None:
        return None
    return max(0.0, (a.astimezone(timezone.utc) - b.astimezone(timezone.utc)).total_seconds())


def _interval_rows(source: dict[str, Any] | None) -> list[dict[str, Any]]:
    src = source or {}
    rows: list[dict[str, Any]] = []
    for rec in src.get("rows") or []:
        if isinstance(rec, dict):
            rows.append(rec)
    by_ticker = src.get("by_ticker") or src.get("intraday_fetch_by_ticker") or {}
    if isinstance(by_ticker, dict):
        for rec in by_ticker.values():
            if not isinstance(rec, dict):
                continue
            for iv in rec.get("intervals") or []:
                if isinstance(iv, dict):
                    rows.append(iv)
    for c in src.get("candidates") or []:
        if not isinstance(c, dict):
            continue
        intra = c.get("intraday") or {}
        if not isinstance(intra, dict):
            continue
        for iv in intra.get("intervals") or intra.get("interval_rows") or intra.get("rows") or []:
            if isinstance(iv, dict):
                rows.append({**iv, "ticker": iv.get("ticker") or c.get("ticker")})
        if intra.get("normalized_utc_timestamp") or intra.get("latest_timestamp_utc"):
            rows.append({
                "ticker": c.get("ticker"),
                "interval": intra.get("interval") or "best",
                "latest_timestamp_utc": intra.get("normalized_utc_timestamp") or intra.get("latest_timestamp_utc"),
                "latest_timestamp_cairo": intra.get("normalized_cairo_timestamp"),
                "current_session": intra.get("current_session"),
                "session_date": intra.get("session_date"),
                "provider": intra.get("provider") or "tradingview",
            })
    return rows


def summarize_intraday(source: dict[str, Any] | None, *, as_of=None) -> dict[str, Any]:
    """Newest TradingView bar in a pack or Explorer payload. Prefer 1m/5m of today's session."""
    rows = [r for r in _interval_rows(source) if r.get("latest_timestamp_utc") or r.get("normalized_utc_timestamp")]
    reference = parse_dt(as_of) or parse_dt((source or {}).get("fetched_at")) or datetime.now(timezone.utc)
    today = reference.astimezone(CAIRO).date().isoformat()
    current = [r for r in rows if str(r.get("session_date") or "") == today]
    pool = current or rows
    preferred = [r for r in pool if (r.get("interval") or "") in PREFERRED_INTRADAY]
    ranked = preferred or pool

    def _key(rec: dict[str, Any]):
        raw = rec.get("latest_timestamp_utc") or rec.get("normalized_utc_timestamp")
        dt = parse_dt(raw) or datetime.min.replace(tzinfo=timezone.utc)
        iv = rec.get("interval") or ""
        prefer = 0 if iv in ("1m", "5m") else 1
        return (dt.astimezone(timezone.utc), -prefer)

    best = max(ranked, key=_key) if ranked else None
    fetched = source.get("fetched_at") or source.get("intraday_refreshed_at") if source else None
    if not fetched and source:
        by_ticker = source.get("by_ticker") or {}
        queried = [
            rec.get("queried_at")
            for rec in (by_ticker.values() if isinstance(by_ticker, dict) else [])
            if isinstance(rec, dict) and rec.get("queried_at")
        ]
        fetched = max(queried) if queried else ((source.get("data_stamp") or {}).get("intraday") or {}).get("fetched_at_utc")
    if source and ((source.get("intraday_fetch_diagnostics") or {}).get("provider_state") == "NOT_REQUESTED" or source.get("live_fetch_requested") is False):
        fetched = None
    last_utc = None
    last_cairo = None
    interval = None
    ticker = None
    if best:
        last_utc = best.get("latest_timestamp_utc") or best.get("normalized_utc_timestamp")
        last_cairo = best.get("latest_timestamp_cairo") or best.get("normalized_cairo_timestamp")
        if last_utc and not last_cairo:
            last_cairo = clocks(last_utc)["cairo"]
        interval = best.get("interval")
        ticker = best.get("ticker")
    delay = delay_seconds(as_of or fetched or datetime.now(timezone.utc), last_utc)
    per_ticker: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rec in sorted(pool, key=_key, reverse=True):
        t = str(rec.get("ticker") or "").upper()
        if not t or t in seen:
            continue
        seen.add(t)
        ts = rec.get("latest_timestamp_utc") or rec.get("normalized_utc_timestamp")
        cairo = rec.get("latest_timestamp_cairo") or (clocks(ts)["cairo"] if ts else None)
        age = delay_seconds(as_of or fetched or datetime.now(timezone.utc), ts)
        per_ticker.append({
            "ticker": t,
            "interval": rec.get("interval"),
            "last_bar_utc": ts,
            "last_bar_cairo": cairo,
            "last_bar_cairo_display": display_cairo(cairo or ts),
            "delay_seconds": age,
            "current_session": bool(str(rec.get("session_date") or "") == today),
        })
    return {
        "fetched_at_utc": clocks(fetched)["utc"] if fetched else None,
        "fetched_at_cairo": clocks(fetched)["cairo"] if fetched else None,
        "fetched_at_cairo_display": display_cairo(fetched) if fetched else None,
        "last_bar_utc": last_utc,
        "last_bar_cairo": last_cairo,
        "last_bar_cairo_display": display_cairo(last_cairo or last_utc) if (last_cairo or last_utc) else None,
        "last_bar_interval": interval,
        "last_bar_ticker": ticker,
        "last_bar_delay_seconds": delay,
        "provider": (best or {}).get("provider") or "UNKNOWN",
        "provider_note": ", ".join(sorted({str(r.get('provider')) for r in rows if r.get('provider')})) + " candles. Not live bid/ask.",
        "tickers": per_ticker,
        "today_session": source.get("today_session") if source else None,
    }


def build_data_stamp(
    *,
    packaged_at: str | datetime | None = None,
    session_close_date: str | None = None,
    session_phase: str | None = None,
    daily_provider: str | None = None,
    explorer_payload: dict[str, Any] | None = None,
    intraday_pack: dict[str, Any] | None = None,
    package_kind: str = "HANDOFF",
    daily_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pkg_clk = clocks(packaged_at)
    payload = explorer_payload or {}
    session = (
        session_close_date
        or payload.get("latest_completed_market_session")
        or payload.get("latest_session")
    )
    intra_src = intraday_pack or payload
    intra = summarize_intraday(intra_src, as_of=pkg_clk["utc"])
    fetch_diag = (intraday_pack or {}).get("intraday_fetch_diagnostics") or payload.get("intraday_fetch_diagnostics")
    if fetch_diag:
        intra["fetch_diagnostics"] = fetch_diag
        intra["provider_state"] = fetch_diag.get("provider_state")
        if not intra.get("tickers"):
            by = (intraday_pack or {}).get("by_ticker") or payload.get("intraday_fetch_by_ticker") or {}
            queried = (intraday_pack or {}).get("queried_tickers") or payload.get("intraday_queried_tickers") or []
            intra["tickers"] = [
                {
                    "ticker": t,
                    "interval": None,
                    "last_bar_utc": (by.get(t) or {}).get("latest_bar_timestamp") if isinstance(by, dict) else None,
                    "last_bar_cairo": None,
                    "last_bar_cairo_display": None,
                    "delay_seconds": None,
                    "current_session": False,
                    "intraday_fetch_state": (by.get(t) or {}).get("intraday_fetch_state") if isinstance(by, dict) else None,
                }
                for t in queried
            ]
    daily_rows = daily_rows if daily_rows is not None else payload.get("daily_data_status") or []
    daily_src = daily_provider or ", ".join(sorted({r["provider"] for r in daily_rows if r.get("provider") and r["provider"] != "none"})) or payload.get("daily_provider") or "UNKNOWN"
    from egxbridge.semantics import previous_egx_session_date
    expected = previous_egx_session_date(parse_dt(pkg_clk["utc"]))
    daily_states = []
    for row in daily_rows:
        rec = dict(row)
        latest = rec.get("latest_session")
        rec["data_state"] = "EXCLUDED" if rec.get("security_type", "EQUITY") != "EQUITY" else "MISSING" if not latest else "STALE" if latest < expected else "CURRENT"
        daily_states.append(rec)
    equities = [r for r in daily_states if r["data_state"] != "EXCLUDED"]
    coverage = {
        "expected_session": expected, "equities": len(equities),
        "current": sum(r["data_state"] == "CURRENT" for r in equities),
        "stale": sum(r["data_state"] == "STALE" for r in equities),
        "missing": sum(r["data_state"] == "MISSING" for r in equities),
        "excluded": len(daily_states) - len(equities),
        "invalid_daily_bars": sum(r.get("invalid_daily_bars", 0) for r in equities),
        "state": "UNKNOWN" if not equities else "CURRENT" if all(r["data_state"] == "CURRENT" for r in equities) else "PARTIAL",
    }
    return {
        "package_kind": package_kind,
        "daily_collection": {k: (payload.get("daily_collection_report") or {}).get(k) for k in (
            "status", "scope", "started_at", "finished_at", "expected_session", "performance", "reason",
        )},
        "daily_coverage": coverage,
        "supplemental_source": {k: ((payload.get("daily_collection_report") or {}).get("supplemental_market_snapshot") or {}).get(k) for k in (
            "provider", "status", "finished_at", "matched_equities", "quarantined", "stale", "exchange_timestamp_verified", "note",
        )},
        "daily_tickers": daily_states,
        "exchange_completeness_verified": False,
        "session_close_date": session,
        "session_phase": session_phase,
        "packaged_at_utc": pkg_clk["utc"],
        "packaged_at_cairo": pkg_clk["cairo"],
        "packaged_at_cairo_display": pkg_clk["cairo_display"],
        "packaged_at_utc_display": pkg_clk["utc_display"],
        "filename_tag": pkg_clk["filename_tag"],
        "daily_provider": daily_src,
        "daily_note": "Session close = last completed EGX day. Incomplete today bars are not used as closes.",
        "intraday": intra,
        "intraday_fetch_diagnostics": fetch_diag,
        "clocks_note": (
            "Three different clocks: (1) last completed session close, "
            "(2) when this file was packaged, (3) timestamp of the newest TradingView candle. "
            "Today's Intraday downloads delayed candles; it does not create live quotes. "
            "STALE_CACHE bars are last-good data, never current-session live evidence."
        ),
    }


def stamp_caption(stamp: dict[str, Any] | None) -> str:
    if not stamp:
        return ""
    intra = stamp.get("intraday") or {}
    delay = intra.get("last_bar_delay_seconds")
    delay_txt = ""
    if delay is not None:
        mins = int(delay // 60)
        delay_txt = f" · last bar {mins} min delayed" if mins else " · last bar <1 min delayed"
    last_bar = intra.get("last_bar_cairo_display") or "no intraday bar"
    return (
        f"Daily coverage: {(stamp.get('daily_coverage') or {}).get('state', 'UNKNOWN')} · "
        f"Data as of: session close {stamp.get('session_close_date') or 'unknown'}  ·  "
        f"file packaged {stamp.get('packaged_at_cairo_display') or 'unknown'}"
        f"{delay_txt}  ·  newest intraday bar {last_bar}"
    )


def stamp_markdown(stamp: dict[str, Any] | None) -> str:
    stamp = stamp or {}
    intra = stamp.get("intraday") or {}
    delay = intra.get("last_bar_delay_seconds")
    delay_line = "unknown"
    if delay is not None:
        delay_line = f"{int(delay // 60)} min ({int(delay)}s)"
    lines = [
        "# DATA AS OF",
        "",
        "Do not conflate these clocks.",
        "",
        f"- **Last completed EGX session (daily closes):** {stamp.get('session_close_date') or 'UNKNOWN'}",
        f"- **This file packaged:** {stamp.get('packaged_at_cairo_display')} ({stamp.get('packaged_at_utc_display')})",
        f"- **Newest intraday bar:** {intra.get('last_bar_cairo_display') or 'none'} "
        f"({intra.get('last_bar_interval') or 'n/a'} {intra.get('last_bar_ticker') or ''})".rstrip(),
        f"- **Bar delay vs package time:** {delay_line}",
        f"- **Intraday fetched at:** {intra.get('fetched_at_cairo_display') or 'not refreshed this package'}",
        f"- **Daily source:** {stamp.get('daily_provider') or 'yahoo / tradingview fallback'}",
        f"- **Intraday source:** {intra.get('provider_note') or 'TradingView delayed candles'}",
        f"- **Session phase at package time:** {stamp.get('session_phase') or 'UNKNOWN'}",
        "",
        stamp.get("clocks_note") or "",
        "",
        stamp.get("daily_note") or "",
        "",
        "## Per-ticker newest bar",
        "",
    ]
    tickers = intra.get("tickers") or []
    if not tickers:
        lines.append("No intraday bars in this package.")
    else:
        lines.append("| ticker | interval | last bar Cairo | delay | today's session |")
        lines.append("|---|---|---|---|---|")
        for rec in tickers:
            age = rec.get("delay_seconds")
            age_txt = f"{int(age // 60)} min" if age is not None else "—"
            lines.append(
                f"| {rec.get('ticker')} | {rec.get('interval') or '—'} | "
                f"{rec.get('last_bar_cairo_display') or '—'} | {age_txt} | "
                f"{'yes' if rec.get('current_session') else 'no'} |"
            )
    coverage = stamp.get("daily_coverage") or {}
    collection = stamp.get("daily_collection") or {}
    perf = collection.get("performance") or {}
    lines.extend([
        "", "## Collection run", "",
        f"Status: {collection.get('status') or 'UNAVAILABLE'}. Scope: {collection.get('scope') or 'UNKNOWN'}.",
        f"Started: {display_cairo(collection.get('started_at'))}. Finished: {display_cairo(collection.get('finished_at'))}.",
        f"Network attempts: {perf.get('network_attempts', 'unknown')}; cache hits: {perf.get('cache_hits', 'unknown')}; deferred retries: {perf.get('deferred_retries', 'unknown')}.",
        "See daily_collection_report.json for per-company attempts, results, and retry times. Collection completion and package creation are separate clocks.",
    ])
    lines.extend([
        "", "## Daily evidence coverage", "",
        f"Expected completed session: {coverage.get('expected_session') or 'UNKNOWN'}. "
        f"State: {coverage.get('state') or 'UNKNOWN'}. "
        f"Current: {coverage.get('current', 0)}; stale: {coverage.get('stale', 0)}; missing: {coverage.get('missing', 0)}.",
        f"Rejected OHLCV observations: {coverage.get('invalid_daily_bars', 0)}. Missing means no qualifying daily series; the per-company reason distinguishes unavailable data from invalid source history.",
        "Indicators use a continuous valid sequence after the last invalid observation. Rejected source values are retained in daily_rejected_ohlcv.jsonl and daily_collection_rejections.jsonl.",
        "Provider catalogs are not an official exchange reconciliation. Package creation does not refresh its market data.",
        "", "| ticker | state | sessions from / through | bars | source | data fetched UTC |",
        "|---|---|---|---|---|---|",
    ])
    for rec in stamp.get("daily_tickers") or []:
        lines.append(f"| {rec.get('ticker')} | {rec.get('data_state')} | {rec.get('first_session') or '—'} / {rec.get('latest_session') or '—'} | {rec.get('daily_bars', 0)} | {rec.get('provider') or 'unknown'} | {rec.get('data_captured_at') or 'unknown'} |")
    lines.append("")
    return "\n".join(lines)


def job_stamp_preamble(stamp: dict[str, Any] | None) -> str:
    return stamp_markdown(stamp).replace("# DATA AS OF", "# DATA AS OF — read before the job") + "\n---\n"


def dated_zip_name(stem: str, stamp: dict[str, Any] | None) -> str:
    stamp = stamp or {}
    session = str(stamp.get("session_close_date") or "unknown").replace("/", "-")
    tag = stamp.get("filename_tag") or clocks()["filename_tag"]
    clean = Path(stem).name
    if clean.lower().endswith(".zip"):
        clean = clean[:-4]
    return f"{clean}_session-{session}_cairo-{tag}.zip"


def write_package_stamp(package_dir: Path, stamp: dict[str, Any]) -> dict[str, Any]:
    package_dir.mkdir(parents=True, exist_ok=True)
    write_json(package_dir / "DATA_STAMP.json", stamp)
    write_text(package_dir / "DATA_STAMP.md", stamp_markdown(stamp))
    return stamp


def write_zip_sidecar(zip_path: Path | str, stamp: dict[str, Any]) -> Path:
    path = Path(zip_path)
    side = Path(str(path) + ".stamp.json")
    write_json(side, stamp)
    return side


def load_zip_stamp(zip_path: Path | str | None) -> dict[str, Any] | None:
    if not zip_path:
        return None
    path = Path(zip_path)
    side = Path(str(path) + ".stamp.json")
    if not side.exists():
        return None
    try:
        import json
        data = json.loads(side.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def copy_zip_sidecar(src: Path | str, dest: Path | str):
    src_side = Path(str(src) + ".stamp.json")
    dest_side = Path(str(dest) + ".stamp.json")
    if not src_side.exists():
        dest_side.unlink(missing_ok=True)
        return
    dest_side.write_bytes(src_side.read_bytes())


def bar_age_seconds(source: dict[str, Any] | None, *, now: datetime | None = None) -> float | None:
    intra = summarize_intraday(source)
    last = intra.get("last_bar_utc")
    if not last:
        return None
    return delay_seconds(now or datetime.now(timezone.utc), last)
