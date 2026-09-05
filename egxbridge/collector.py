from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta
import time
import json
import traceback
import shutil
from typing import Any

from .config import Settings
from .symbols import SymbolRegistry
from .db import Database
from .freshness import classify_freshness, FreshnessThresholds, egx_session_open_at
from .conflicts import select_observation, conflict_to_dict
from .quality import score_symbol
from .scanner import compute_scanner_metrics
from .storage import jdump, rows_to_csv, append_csv, write_handoff, write_scanner_handoff, now_iso
from .normalize import unwrap_rows, normalize_quote, normalize_depth, normalize_trades, normalize_candles, sym_of
from .semantics import is_latest_completed_session
from .providers import (
    ProviderManager,
    EGIDAdapter,
    YahooProvider,
    TradingViewProvider,
    BorsaProvider,
    InvestorEGXProvider,
)


def depth_metrics(depth: list[dict]):
    bids = [x for x in depth if x.get("side") == "BID" and x.get("qty") is not None]
    asks = [x for x in depth if x.get("side") == "ASK" and x.get("qty") is not None]
    bq = sum((x.get("qty") or 0) for x in bids[:5])
    aq = sum((x.get("qty") or 0) for x in asks[:5])
    imb = None if bq + aq == 0 else round((bq - aq) / (bq + aq), 4)
    return bq, aq, imb


def spread_bps(q: dict):
    b, a = q.get("bid"), q.get("ask")
    if b is None or a is None or b <= 0 or a <= 0:
        return None
    mid = (a + b) / 2
    return round((a - b) / mid * 10000, 2) if mid else None


def build_manager(settings: Settings, registry: SymbolRegistry) -> ProviderManager:
    ep = settings.enabled_providers or {}
    providers = [
        EGIDAdapter(
            settings.base_url,
            settings.swagger_url,
            settings.request_timeout_seconds,
            settings.provider_mode,
            settings.egid_token,
            enabled=ep.get("egid", True),
        ),
        YahooProvider(registry, enabled=ep.get("yahoo", True)),
        TradingViewProvider(
            registry,
            enabled=ep.get("tradingview", True),
            username=settings.tradingview_username,
            password=settings.tradingview_password,
        ),
        BorsaProvider(
            base_url=settings.borsa_base_url,
            enabled=ep.get("borsa", False),
            timeout=settings.request_timeout_seconds,
            symbol_resolver=registry,
        ),
        InvestorEGXProvider(
            enabled=ep.get("investor_egx", True),
            universe_path=settings.investor_egx_universe_path,
            sqlite_path=settings.investor_egx_sqlite_path,
            symbol_resolver=registry,
        ),
    ]
    return ProviderManager(providers, priority=settings.provider_priority, rate_limit_seconds=settings.rate_limit_seconds)


def _thresholds(settings: Settings) -> FreshnessThresholds:
    f = settings.freshness
    return FreshnessThresholds(f.live_seconds, f.fresh_seconds, f.delayed_seconds)


def _prune_raw(raw_root: Path, retention_days: int):
    if retention_days <= 0 or not raw_root.exists():
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    for p in raw_root.rglob("*"):
        if p.is_file():
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    p.unlink(missing_ok=True)
            except Exception:
                pass


def run_once(
    settings: Settings,
    root: str | Path = ".",
    *,
    symbol_filter: str | None = None,
    provider_filter: str | None = None,
    intervals: list[str] | None = None,
) -> dict:
    root = Path(root)
    outdir = settings.output_path(root)
    registry = SymbolRegistry.from_config({"symbol_aliases": settings.symbol_aliases})
    for s in set(settings.symbols + settings.focus_symbols):
        registry.register(s)
    db = Database(settings.db_path(root))
    manager = build_manager(settings, registry)
    th = _thresholds(settings)
    symbols = settings.symbols
    if symbol_filter:
        symbols = [registry.canonicalize(symbol_filter)]
    run_id = db.start_run(symbols)
    capture = now_iso()
    payload: dict[str, Any] = {
        "generated_at": capture,
        "version": "0.3.1",
        "provider_mode": settings.provider_mode,
        "status": "OK",
        "symbols": [],
        "errors": [],
        "providers": manager.statuses(),
    }
    scanner_records = []

    # Persist provider status
    for st in payload["providers"]:
        db.upsert_provider_status(st)

    # Optional EGID market watch (non-fatal)
    market_rows = []
    egid = manager.get("egid")
    if egid and egid.enabled and (provider_filter in (None, "egid")):
        try:
            market_raw = egid.market_watch()  # type: ignore[attr-defined]
            jdump(outdir / "raw" / "egid" / capture[:10] / "market_watch.json", market_raw)
            market_rows = unwrap_rows(market_raw)
            if market_rows:
                rows_to_csv(outdir / "market_watch.csv", market_rows)
        except Exception as e:
            msg = str(e)
            if "AUTH" in msg.upper() or "401" in msg:
                payload["errors"].append("egid market_watch: LICENSE/AUTH REQUIRED")
            else:
                payload["errors"].append(f"market_watch: {e}")

    focus = set(settings.focus_symbols)
    ivs = intervals or settings.candle_intervals

    for symbol in symbols:
        sdir = outdir / symbol
        warnings: list[str] = []
        quote_dict: dict[str, Any] = {}
        providers_used: list[str] = []
        quote_candidates = []

        # Multi-provider quotes for conflict engine
        if settings.collect_multi_provider_quotes:
            collected = manager.collect_all("quote", "get_quote", symbol, provider_filter=provider_filter)
        else:
            q, pname, errs = manager.call_first("quote", "get_quote", symbol, provider_filter=provider_filter)
            collected = [(q, pname)] if q is not None else []
            for e in errs:
                warnings.append(f"quote:{e.get('provider')}:{e.get('code') or e.get('message') or e.get('error')}")

        for qobj, pname in collected:
            if qobj is None:
                continue
            qd = qobj.to_dict() if hasattr(qobj, "to_dict") else dict(qobj)
            # Prefer normalized UTC for freshness; never invent UTC from naive
            ts_for_fresh = qd.get("normalized_utc_timestamp") or None
            if ts_for_fresh:
                fclass, fsec = classify_freshness(ts_for_fresh, qd.get("capture_timestamp"), th)
            else:
                fclass, fsec = "UNKNOWN", None
            qd["freshness_class"] = fclass
            qd["freshness_seconds"] = fsec
            if qd.get("latest_completed_session") is None:
                qd["latest_completed_session"] = is_latest_completed_session(qd.get("session_date"))
            if qd.get("session_date") and not qd.get("effective_session_date"):
                qd["effective_session_date"] = qd.get("session_date")
            db.insert_quote(qd)
            jdump(outdir / "raw" / pname / capture[:10] / symbol / "quote.json", qd)
            quote_candidates.append({
                "symbol": symbol,
                "provider": pname,
                "value": qd.get("last"),
                "provider_timestamp": qd.get("normalized_utc_timestamp") or qd.get("provider_timestamp"),
                "provider_raw_timestamp": qd.get("provider_raw_timestamp"),
                "normalized_utc_timestamp": qd.get("normalized_utc_timestamp"),
                "timestamp": qd.get("normalized_utc_timestamp") or qd.get("provider_timestamp"),
                "freshness_seconds": fsec,
                "volume_semantics": qd.get("volume_semantics"),
                "interval": qd.get("volume_interval"),
                "session_date": qd.get("session_date"),
                "effective_session_date": qd.get("effective_session_date") or qd.get("session_date"),
                "timestamp_semantics": qd.get("timestamp_semantics"),
                "price_observation_type": qd.get("price_observation_type"),
                "full": qd,
            })
            providers_used.append(pname)

        selected_quote = None
        if quote_candidates:
            sel = select_observation(
                quote_candidates,
                priority=settings.provider_priority.get("quote", ["egid", "tradingview", "borsa", "yahoo"]),
                created_at=capture,
                field="last",
                symbol=symbol,
            )
            if sel.conflict:
                db.insert_conflict(conflict_to_dict(sel.conflict))
                warnings.append(f"CONFLICT last: {sel.reason}")
            for c in quote_candidates:
                if c["provider"] == sel.selected_provider:
                    selected_quote = c["full"]
                    break
            quote_dict = selected_quote or quote_candidates[0]["full"]
            jdump(sdir / "quote.json", quote_dict)
            append_csv(sdir / "quote_history.csv", [quote_dict])
        else:
            row = None
            for r in market_rows:
                rs = sym_of(r)
                if rs == symbol or rs.startswith(symbol):
                    row = r
                    break
            if row:
                quote_dict = normalize_quote(row, symbol)
                quote_dict["provider"] = "egid"
                quote_dict["provider_mode"] = settings.provider_mode
                quote_dict["capture_timestamp"] = capture
                quote_dict["price_observation_type"] = "DELAYED_QUOTE"
                jdump(sdir / "quote.json", quote_dict)
            else:
                warnings.append("quote: unavailable from all providers")

        # Volume conflict: only same semantics + session/interval
        vol_cands = [
            {
                "symbol": symbol,
                "provider": c["provider"],
                "value": c["full"].get("volume"),
                "provider_timestamp": c["full"].get("normalized_utc_timestamp") or c["full"].get("provider_timestamp"),
                "provider_raw_timestamp": c["full"].get("provider_raw_timestamp"),
                "normalized_utc_timestamp": c["full"].get("normalized_utc_timestamp"),
                "freshness_seconds": c.get("freshness_seconds"),
                "volume_semantics": c["full"].get("volume_semantics"),
                "interval": c["full"].get("volume_interval"),
                "session_date": c["full"].get("session_date"),
                "effective_session_date": c["full"].get("effective_session_date") or c["full"].get("session_date"),
                "timestamp_semantics": c["full"].get("timestamp_semantics"),
                "price_observation_type": c["full"].get("price_observation_type"),
            }
            for c in quote_candidates
            if c["full"].get("volume") is not None
        ]
        volume_meta = {}
        if vol_cands:
            vsel = select_observation(
                vol_cands,
                priority=settings.provider_priority.get("quote", []),
                created_at=capture,
                field="volume",
                symbol=symbol,
                require_comparable_volume=True,
            )
            volume_meta = {
                "volume_value": vsel.selected_value,
                "volume_semantics": next(
                    (c.get("volume_semantics") for c in vol_cands if c["provider"] == vsel.selected_provider),
                    None,
                ),
                "interval": next(
                    (c.get("interval") for c in vol_cands if c["provider"] == vsel.selected_provider),
                    None,
                ),
                "session_date": next(
                    (c.get("session_date") for c in vol_cands if c["provider"] == vsel.selected_provider),
                    None,
                ),
                "provider": vsel.selected_provider,
                "provider_timestamp": vsel.selected_timestamp,
                "skipped_incomparable": vsel.skipped_incomparable,
            }
            if vsel.conflict:
                db.insert_conflict(conflict_to_dict(vsel.conflict))
                warnings.append(f"CONFLICT volume: {vsel.reason}")
            elif vsel.skipped_incomparable:
                warnings.append(
                    f"volume: skipped {len(vsel.skipped_incomparable)} incomparable source(s) "
                    f"(different semantics/interval/session — not a conflict)"
                )

        # Candles
        daily_rows: list[dict] = []
        intraday_ok = False
        candle_meta = {}
        for interval in ivs:
            cap = "daily_ohlcv" if interval == "1d" else "intraday_ohlcv"
            if interval != "1d" and symbol not in focus and not symbol_filter:
                continue
            candles, pname, errs = manager.call_first(
                cap, "get_candles", symbol, interval=interval, n_bars=120, provider_filter=provider_filter
            )
            if candles is None:
                for e in errs:
                    code = e.get("code") or ""
                    if code == "AUTH_REQUIRED":
                        warnings.append(f"candles {interval}: LICENSE/AUTH REQUIRED ({e.get('provider')})")
                    else:
                        warnings.append(f"candles {interval}:{e.get('provider')}:{e.get('message') or e.get('error')}")
                candle_meta[interval] = {"available": False}
                continue
            rows = []
            for c in candles:
                cd = c.to_dict() if hasattr(c, "to_dict") else dict(c)
                ts_for_fresh = cd.get("normalized_utc_timestamp")
                if ts_for_fresh:
                    fclass, _ = classify_freshness(ts_for_fresh, cd.get("capture_timestamp"), th)
                else:
                    fclass = "UNKNOWN"
                cd["freshness_class"] = fclass
                db.upsert_candle(cd)
                rows.append(cd)
            if rows:
                providers_used.append(pname)
                rows_to_csv(sdir / f"candles_{interval}.csv", rows)
                if interval == "1d":
                    rows_to_csv(sdir / "candles.csv", rows)
                    daily_rows = rows
                else:
                    intraday_ok = True
                jdump(outdir / "raw" / (pname or "unknown") / capture[:10] / symbol / f"candles_{interval}.json", rows[-5:])
                candle_meta[interval] = {
                    "available": True,
                    "provider": pname,
                    "bars": len(rows),
                    "latest_timestamp": rows[-1].get("normalized_utc_timestamp") or rows[-1].get("timestamp"),
                    "latest_timestamp_cairo": rows[-1].get("normalized_cairo_timestamp"),
                    "volume_semantics": rows[-1].get("volume_semantics"),
                    "timestamp_semantics": rows[-1].get("timestamp_semantics"),
                    "latest_close": rows[-1].get("close"),
                }

        # Depth / trades — EGID only, never fabricate
        depth = []
        trades = []
        if settings.collect_depth and (symbol in focus or symbol_filter):
            d, pname, errs = manager.call_first("depth", "get_depth", symbol, provider_filter=provider_filter)
            if d is not None:
                depth = d
                rows_to_csv(sdir / "depth.csv", depth)
                providers_used.append(pname)
            else:
                for e in errs:
                    if e.get("code") == "AUTH_REQUIRED":
                        warnings.append("depth: LICENSE/AUTH REQUIRED")
                    else:
                        warnings.append(f"depth: {e.get('message') or e.get('error')}")

        if settings.collect_trades and (symbol in focus or symbol_filter):
            t, pname, errs = manager.call_first("trades", "get_trades", symbol, provider_filter=provider_filter)
            if t is not None:
                trades = t[-settings.max_trade_rows:]
                rows_to_csv(sdir / "trades.csv", trades)
                providers_used.append(pname)
            else:
                for e in errs:
                    if e.get("code") == "AUTH_REQUIRED":
                        warnings.append("trades: LICENSE/AUTH REQUIRED")
                    else:
                        warnings.append(f"trades: {e.get('message') or e.get('error')}")

        # Fundamentals optional
        fundamentals_avail = False
        try:
            f, pname, _ = manager.call_first("fundamentals", "get_fundamentals", symbol, provider_filter=provider_filter)
            if f:
                db.insert_fundamentals(symbol, pname or "investor_egx", f.get("as_of"), f)
                jdump(sdir / "fundamentals.json", f)
                fundamentals_avail = True
        except Exception:
            pass

        bq, aq, imb = depth_metrics(depth)
        fsec = quote_dict.get("freshness_seconds")
        fclass = quote_dict.get("freshness_class") or "UNKNOWN"
        ts_for_fresh = quote_dict.get("normalized_utc_timestamp")
        if ts_for_fresh:
            fclass, fsec = classify_freshness(ts_for_fresh, quote_dict.get("capture_timestamp") or capture, th)
            quote_dict["freshness_class"] = fclass
            quote_dict["freshness_seconds"] = fsec

        latest_completed = bool(quote_dict.get("latest_completed_session")) or is_latest_completed_session(
            quote_dict.get("session_date")
        )
        quote_dict["latest_completed_session"] = latest_completed
        session_open = egx_session_open_at()
        current_session_date = None
        if session_open:
            from datetime import datetime, timezone
            from .freshness import CAIRO_TZ
            current_session_date = datetime.now(timezone.utc).astimezone(CAIRO_TZ).date().isoformat()
        has_current_session_price = bool(
            quote_dict.get("last") is not None
            and quote_dict.get("session_date")
            and (
                (session_open and quote_dict.get("session_date") == current_session_date)
                or (not session_open and latest_completed)
            )
        )
        # For execution hard gate, current-session means *today's open session* only
        has_exec_session_price = bool(
            session_open
            and quote_dict.get("last") is not None
            and quote_dict.get("session_date") == current_session_date
        )
        has_exec_session_volume = bool(
            session_open
            and quote_dict.get("volume") is not None
            and quote_dict.get("session_date") == current_session_date
        )
        has_bid = quote_dict.get("bid") is not None and quote_dict.get("ask") is not None
        ts_reliable = bool(quote_dict.get("normalized_utc_timestamp") and quote_dict.get("timestamp_semantics") not in (None, "UNKNOWN", ""))
        quality = score_symbol(
            symbol=symbol,
            freshness_class=fclass,
            freshness_seconds=fsec,
            providers_used=list(dict.fromkeys(providers_used)),
            agreement=None if len(quote_candidates) < 2 else not any("CONFLICT last" in w for w in warnings),
            has_price=quote_dict.get("last") is not None,
            has_volume=quote_dict.get("volume") is not None,
            has_daily=bool(daily_rows),
            has_intraday=intraday_ok,
            has_bid_ask=has_bid,
            has_depth=bool(depth),
            has_trades=bool(trades),
            has_trade_count=quote_dict.get("trades") is not None,
            timestamp_known=bool(quote_dict.get("normalized_utc_timestamp") or quote_dict.get("provider_timestamp")),
            timestamp_reliable=ts_reliable,
            price_observation_type=quote_dict.get("price_observation_type") or "UNKNOWN",
            latest_completed_session=latest_completed,
            has_current_session_price=has_exec_session_price,
            has_current_session_volume=has_exec_session_volume,
            require_microstructure=False,
            execution_fresh_seconds=th.fresh_seconds,
        )

        metrics = compute_scanner_metrics(daily_rows)
        if daily_rows:
            db.upsert_scanner_signal(symbol, capture[:10], metrics)

        sym_payload = {
            "symbol": symbol,
            "quote": quote_dict,
            "price": quote_dict.get("last"),
            "price_source": quote_dict.get("provider"),
            "price_observation_type": quote_dict.get("price_observation_type"),
            "freshness": fclass,
            "volume": volume_meta.get("volume_value", quote_dict.get("volume")),
            "volume_source": volume_meta.get("provider") or quote_dict.get("provider"),
            "volume_semantics": volume_meta.get("volume_semantics") or quote_dict.get("volume_semantics"),
            "volume_interval": volume_meta.get("interval") or quote_dict.get("volume_interval"),
            "session_date": quote_dict.get("session_date"),
            "effective_session_date": quote_dict.get("effective_session_date") or quote_dict.get("session_date"),
            "latest_completed_session": latest_completed,
            "normalized_utc_timestamp": quote_dict.get("normalized_utc_timestamp"),
            "normalized_cairo_timestamp": quote_dict.get("normalized_cairo_timestamp"),
            "timestamp_semantics": quote_dict.get("timestamp_semantics"),
            "spread_bps": spread_bps(quote_dict),
            "top5_bid_qty": bq,
            "top5_ask_qty": aq,
            "depth_imbalance": imb,
            "trade_rows": len(trades),
            "candle_rows": len(daily_rows),
            "candles": candle_meta,
            "scanner": metrics,
            "fundamentals_available": fundamentals_avail,
            "corporate_action_data_available": False,
            "research_data_quality": quality.research_data_quality,
            "execution_data_quality": quality.execution_data_quality,
            "execution_grade": quality.execution_grade,
            "quality_components": quality.components,
            "availability": quality.availability,
            "missing_execution_fields": quality.missing_execution_fields,
            "warnings": warnings + quality.warnings,
            "providers_used": list(dict.fromkeys(providers_used)),
        }
        payload["symbols"].append(sym_payload)
        scanner_records.append(sym_payload)
        db.upsert_symbol(symbol, aliases=registry.get(symbol).aliases)

    if payload["errors"] or any(s["warnings"] for s in payload["symbols"]):
        payload["status"] = "PARTIAL"
    if all(s.get("price") is None for s in payload["symbols"]) and payload["symbols"]:
        # Still not a crash — likely auth / empty providers
        payload["status"] = "PARTIAL"

    write_handoff(outdir, payload)
    write_scanner_handoff(outdir, {
        "generated_at": capture,
        "version": "0.3.1",
        "status": payload["status"],
        "candidates": scanner_records,
        "note": "Collector does not label BUY/SELL. Downstream scanner consumes these fields.",
    })

    _prune_raw(outdir / "raw", settings.raw_retention_days)
    db.finish_run(run_id, payload["status"], payload["errors"])
    # refresh statuses after run
    for st in manager.statuses():
        db.upsert_provider_status(st)
    db.close()
    return payload


def refresh_universe(settings: Settings, root: str | Path = ".") -> dict:
    root = Path(root)
    registry = SymbolRegistry.from_config({"symbol_aliases": settings.symbol_aliases})
    manager = build_manager(settings, registry)
    db = Database(settings.db_path(root))
    outdir = settings.output_path(root)
    result = {
        "last_refresh": now_iso(),
        "universe_count": 0,
        "successful_symbols": [],
        "failed_symbols": [],
        "unmapped_symbols": [],
        "note": "Coverage not claimed complete unless verified",
    }
    uni, pname, errs = manager.call_first("market_universe", "get_universe")
    if uni is None:
        result["failed_symbols"] = errs
        jdump(outdir / "universe.json", result)
        db.close()
        return result
    for item in uni:
        sym = item.get("canonical") or item.get("symbol")
        if not sym:
            result["unmapped_symbols"].append(item)
            continue
        registry.register(sym, name=item.get("name", ""), aliases=item.get("aliases") or {})
        db.upsert_symbol(sym, name=item.get("name", ""), aliases=registry.get(sym).aliases)
        result["successful_symbols"].append(sym)
    result["universe_count"] = len(result["successful_symbols"])
    result["source"] = pname
    jdump(outdir / "universe.json", result)
    db.close()
    return result


def loop(settings: Settings, root: str | Path = "."):
    print(f"EGX Market Bridge v0.3 running every {settings.poll_seconds}s. Ctrl+C to stop.")
    while True:
        start = time.time()
        try:
            result = run_once(settings, root)
            print(
                result["generated_at"],
                result["status"],
                [(s["symbol"], s.get("price"), s.get("price_source"), s.get("freshness")) for s in result["symbols"]],
            )
        except KeyboardInterrupt:
            raise
        except Exception:
            traceback.print_exc()
        elapsed = time.time() - start
        time.sleep(max(1, settings.poll_seconds - elapsed))
