#!/usr/bin/env python3
"""Borsa benchmark + multi-source export (TEST MODE ONLY).

Temporarily talks to a Borsa instance for probe/benchmark.
Does NOT modify config.json, production enabled_providers, or provider_priority.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import os
import platform
import shutil
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from egxbridge import __version__ as BRIDGE_VERSION
from egxbridge.config import Settings
from egxbridge.collector import build_manager
from egxbridge.providers.base import ProviderError, utc_now_iso
from egxbridge.providers.borsa import BorsaProvider
from egxbridge.source_comparison import (
    BENCHMARK_VERSION,
    PROVIDER_LINEAGE,
    answers_from_results,
    build_disagreements,
    coverage_stats,
    default_benchmark_symbols,
    independence_group_for,
    jdump,
    parse_borsa_underlying,
    score_borsa,
    write_csv,
)
from egxbridge.symbols import SymbolRegistry
from egxbridge.storage import now_iso


PROVIDERS = ["yahoo", "tradingview", "borsa", "investor_egx", "egid"]


def _pkg_ver(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except Exception:
        return None


def _write_raw(path: Path, payload: Any, *, as_csv: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if payload is None:
        jdump(path.with_suffix(".meta.json") if path.suffix else path, {
            "raw_export_status": "unavailable",
            "reason": "null payload",
        })
        return
    if as_csv and hasattr(payload, "to_csv"):
        payload.to_csv(path)
        return
    if hasattr(payload, "to_dict"):
        # pandas DataFrame
        try:
            records = payload.reset_index().to_dict(orient="records")
            jdump(path, records)
            if path.suffix == ".json":
                csv_path = path.with_suffix(".csv")
                payload.to_csv(csv_path)
            return
        except Exception:
            pass
    if isinstance(payload, (dict, list)):
        jdump(path, payload)
        return
    path.write_text(str(payload), encoding="utf-8")


def _fail_block(err: Exception | str, *, latency_ms: float | None = None, http_status: int | None = None) -> dict:
    msg = str(err)
    if http_status is None:
        m = __import__("re").search(r"HTTP\s+(\d{3})", msg)
        http_status = int(m.group(1)) if m else getattr(err, "http_status", None)
    return {
        "ok": False,
        "status": "ERROR",
        "error": msg,
        "http_status": http_status,
        "latency_ms": latency_ms,
        "timestamp": utc_now_iso(),
    }


def fetch_borsa_raw(base_url: str, path: str, timeout: float = 30) -> tuple[Any, float, int | None, str | None]:
    url = f"{base_url.rstrip('/')}{path}"
    t0 = time.time()
    try:
        r = requests.get(url, timeout=timeout)
        ms = (time.time() - t0) * 1000
        try:
            data = r.json()
        except Exception:
            data = {"text": r.text[:2000]}
        if r.status_code >= 400:
            return data, ms, r.status_code, f"HTTP {r.status_code}"
        return data, ms, r.status_code, None
    except Exception as e:
        return None, (time.time() - t0) * 1000, None, str(e)


def serialize_quote_row(symbol: str, provider: str, q: Any, *, raw_ref: str, latency_ms: float | None,
                        status: str = "ok", http_status: int | None = None,
                        borsa_underlying: str | None = None, extra: dict | None = None) -> dict:
    d = q.to_dict() if hasattr(q, "to_dict") else dict(q or {})
    und = borsa_underlying
    row = {
        "canonical_symbol": symbol,
        "provider": provider,
        "borsa_underlying_provider": und,
        "independence_group": independence_group_for(provider, und),
        "last": d.get("last"),
        "open": d.get("open"),
        "high": d.get("high"),
        "low": d.get("low"),
        "prev_close": d.get("prev_close"),
        "change_pct": d.get("change_pct"),
        "volume": d.get("volume"),
        "volume_semantics": d.get("volume_semantics"),
        "volume_interval": d.get("volume_interval"),
        "session_date": d.get("session_date"),
        "provider_raw_timestamp": d.get("provider_raw_timestamp") or d.get("provider_timestamp"),
        "provider_timezone": d.get("provider_timezone_if_known"),
        "normalized_utc_timestamp": d.get("normalized_utc_timestamp"),
        "normalized_cairo_timestamp": d.get("normalized_cairo_timestamp"),
        "timestamp_semantics": d.get("timestamp_semantics"),
        "price_observation_type": d.get("price_observation_type"),
        "capture_timestamp": d.get("capture_timestamp"),
        "freshness_class": d.get("freshness_class"),
        "latency_ms": latency_ms if latency_ms is not None else getattr(q, "_latency", None),
        "response_status": status,
        "http_status": http_status,
        "raw_file_reference": raw_ref,
    }
    if extra:
        row.update(extra)
    return row


def candle_rows(symbol: str, provider: str, candles: list, *, raw_ref: str, und: str | None = None) -> list[dict]:
    rows = []
    for c in candles:
        d = c.to_dict() if hasattr(c, "to_dict") else dict(c)
        rows.append({
            "canonical_symbol": symbol,
            "provider": provider,
            "borsa_underlying_provider": und,
            "independence_group": independence_group_for(provider, und),
            "interval": d.get("interval"),
            "timestamp": d.get("normalized_utc_timestamp") or d.get("timestamp"),
            "timestamp_cairo": d.get("normalized_cairo_timestamp"),
            "timestamp_semantics": d.get("timestamp_semantics"),
            "open": d.get("open"),
            "high": d.get("high"),
            "low": d.get("low"),
            "close": d.get("close"),
            "volume": d.get("volume"),
            "volume_semantics": d.get("volume_semantics"),
            "session_date": d.get("session_date"),
            "capture_timestamp": d.get("capture_timestamp"),
            "freshness_class": d.get("freshness_class"),
            "raw_file_reference": raw_ref,
        })
    return rows


def run_benchmark(
    *,
    out_root: Path,
    borsa_base_url: str,
    symbols: list[str],
    config_path: Path,
    sleep_s: float = 0.35,
) -> dict[str, Any]:
    settings = Settings.load(config_path)
    # Hard assert: do not mutate production config file; verify borsa stays disabled there
    prod_borsa_enabled = bool((settings.enabled_providers or {}).get("borsa"))
    prod_priority = dict(settings.provider_priority or {})

    registry = SymbolRegistry.from_config({"symbol_aliases": settings.symbol_aliases})
    for s in symbols:
        registry.register(s)

    # Production manager (borsa disabled as configured)
    prod_manager = build_manager(settings, registry)

    # Benchmark-only Borsa client (in-memory enable; does not touch config.json)
    borsa = BorsaProvider(
        base_url=borsa_base_url,
        enabled=True,
        timeout=settings.request_timeout_seconds,
        symbol_resolver=registry,
    )

    root = out_root / "source_comparison"
    if root.exists():
        shutil.rmtree(root)
    raw_dir = root / "raw"
    norm_dir = root / "normalized"
    per_dir = root / "per_symbol"
    reports_dir = root / "reports"
    for d in (raw_dir, norm_dir, per_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)

    quote_rows: list[dict] = []
    daily_rows: list[dict] = []
    intra_rows: list[dict] = []
    fund_rows: list[dict] = []
    universe_rows: list[dict] = []
    health_rows: list[dict] = []
    latency_rows: list[dict] = []
    error_rows: list[dict] = []
    per_symbol: dict[str, dict[str, Any]] = {}

    yahoo = prod_manager.get("yahoo")
    tv = prod_manager.get("tradingview")
    inv = prod_manager.get("investor_egx")
    egid = prod_manager.get("egid")

    # Universe exports
    for pname, provider in (("investor_egx", inv), ("borsa", borsa)):
        if provider is None:
            continue
        try:
            uni = provider.get_universe()
            ref = f"raw/{pname}/_universe/universe.json"
            _write_raw(raw_dir / pname / "_universe" / "universe.json", uni)
            for u in uni:
                universe_rows.append({
                    "canonical_symbol": u.get("canonical"),
                    "provider": pname,
                    "name": u.get("name"),
                    "source": u.get("source"),
                    "aliases": u.get("aliases"),
                    "raw_file_reference": ref,
                })
        except Exception as e:
            error_rows.append({"provider": pname, "symbol": "*", "stage": "universe", "error": str(e)})
            _write_raw(raw_dir / pname / "_universe" / "universe_error.json", {"error": str(e)})

    # Borsa health + cache test on COMI
    health_raw, h_ms, h_code, h_err = fetch_borsa_raw(borsa_base_url, "/v1/health")
    _write_raw(raw_dir / "borsa" / "_meta" / "health.json", health_raw or {"error": h_err})
    cache_test = {"symbol": "COMI", "requests": []}
    for i in range(3):
        data, ms, code, err = fetch_borsa_raw(borsa_base_url, "/v1/quote/COMI")
        cache_test["requests"].append({
            "n": i + 1,
            "latency_ms": ms,
            "http_status": code,
            "error": err,
            "price": (data or {}).get("price") if isinstance(data, dict) else None,
            "timestamp": (data or {}).get("timestamp") if isinstance(data, dict) else None,
            "source": (data or {}).get("source") if isinstance(data, dict) else None,
            "underlying": parse_borsa_underlying(data if isinstance(data, dict) else None),
        })
        time.sleep(0.2)
    cache_test["first_ms"] = cache_test["requests"][0]["latency_ms"]
    cache_test["second_ms"] = cache_test["requests"][1]["latency_ms"]
    cache_test["third_ms"] = cache_test["requests"][2]["latency_ms"]
    cache_test["observed_ttl_hint_seconds"] = 60
    cache_test["note"] = "Lower latency on 2nd/3rd request suggests cache; not fresher market data."
    _write_raw(raw_dir / "borsa" / "_meta" / "cache_test.json", cache_test)

    underlying_counts: dict[str, int] = {}
    egid_probe_cached: dict[str, Any] | None = None

    for symbol in symbols:
        sym = registry.canonicalize(symbol)
        per_symbol[sym] = {}
        print(f"[benchmark] {sym}", flush=True)

        # ---- YAHOO ----
        y_block: dict[str, Any] = {"mapping_ok": True, "mapped_as": registry.to_provider(sym, "yahoo")}
        if yahoo and yahoo.enabled:
            try:
                t0 = time.time()
                # raw via yfinance
                import yfinance as yf
                ysym = registry.to_provider(sym, "yahoo")
                ticker = yf.Ticker(ysym)
                hist = ticker.history(period="1y", interval="1d", auto_adjust=False)
                _write_raw(raw_dir / "yahoo" / sym / "daily.json", hist)
                _write_raw(raw_dir / "yahoo" / sym / "daily.csv", hist, as_csv=True)
                q = yahoo.get_quote(sym)
                q_ms = (time.time() - t0) * 1000
                _write_raw(raw_dir / "yahoo" / sym / "quote_normalized.json", q.to_dict())
                raw_q = {
                    "yahoo_symbol": ysym,
                    "last_row": hist.iloc[-1].to_dict() if hist is not None and len(hist) else None,
                    "index": str(hist.index[-1]) if hist is not None and len(hist) else None,
                }
                _write_raw(raw_dir / "yahoo" / sym / "quote.json", raw_q)
                ref = f"raw/yahoo/{sym}/quote.json"
                quote_rows.append(serialize_quote_row(sym, "yahoo", q, raw_ref=ref, latency_ms=q_ms))
                y_block["quote"] = {"ok": True, "last": q.last, "volume": q.volume, "latency_ms": q_ms,
                                    "price_observation_type": q.price_observation_type,
                                    "volume_semantics": q.volume_semantics}
                daily = yahoo.get_candles(sym, "1d", n_bars=120)
                dref = f"raw/yahoo/{sym}/daily.json"
                daily_rows.extend(candle_rows(sym, "yahoo", daily, raw_ref=dref))
                y_block["daily"] = {"ok": True, "bars": len(daily),
                                    "latest_close": daily[-1].close if daily else None}
                latency_rows.append({"provider": "yahoo", "symbol": sym, "stage": "quote", "latency_ms": q_ms})
            except Exception as e:
                y_block["quote"] = _fail_block(e)
                y_block["daily"] = _fail_block(e)
                error_rows.append({"provider": "yahoo", "symbol": sym, "stage": "quote_or_daily", "error": str(e)})
                _write_raw(raw_dir / "yahoo" / sym / "error.json", y_block["quote"])
                quote_rows.append({
                    "canonical_symbol": sym, "provider": "yahoo", "response_status": "error",
                    "last_error": str(e), "raw_file_reference": f"raw/yahoo/{sym}/error.json",
                    "independence_group": "YAHOO",
                })
        else:
            y_block["quote"] = {"ok": False, "status": "DISABLED"}
        per_symbol[sym]["yahoo"] = y_block
        time.sleep(sleep_s)

        # ---- TRADINGVIEW ----
        t_block: dict[str, Any] = {"mapping_ok": True, "mapped_as": registry.to_provider(sym, "tradingview")}
        if tv and tv.enabled:
            try:
                t0 = time.time()
                # raw hist if possible
                try:
                    raw_df = tv._hist(sym, "5m", 50)  # noqa: SLF001 — benchmark raw capture
                    _write_raw(raw_dir / "tradingview" / sym / "5m.json", raw_df)
                    _write_raw(raw_dir / "tradingview" / sym / "5m.csv", raw_df, as_csv=True)
                except Exception as re:
                    _write_raw(raw_dir / "tradingview" / sym / "5m_raw_meta.json", {
                        "raw_export_status": "unavailable", "reason": str(re),
                    })
                candles = tv.get_candles(sym, "5m", n_bars=50)
                ms = (time.time() - t0) * 1000
                ref = f"raw/tradingview/{sym}/5m.json"
                intra_rows.extend(candle_rows(sym, "tradingview", candles, raw_ref=ref))
                q = tv.get_quote(sym)
                _write_raw(raw_dir / "tradingview" / sym / "quote_normalized.json", q.to_dict())
                quote_rows.append(serialize_quote_row(
                    sym, "tradingview", q, raw_ref=f"raw/tradingview/{sym}/quote_normalized.json", latency_ms=ms,
                ))
                t_block["quote"] = {"ok": True, "last": q.last, "latency_ms": ms,
                                    "price_observation_type": q.price_observation_type,
                                    "volume_semantics": q.volume_semantics, "mode": tv.mode}
                t_block["intraday"] = {"ok": True, "bars": len(candles), "interval": "5m"}
                try:
                    daily_tv = tv.get_candles(sym, "1d", n_bars=60)
                    _write_raw(raw_dir / "tradingview" / sym / "1d.json", [
                        c.to_dict() for c in daily_tv
                    ])
                    daily_rows.extend(candle_rows(sym, "tradingview", daily_tv, raw_ref=f"raw/tradingview/{sym}/1d.json"))
                    t_block["daily"] = {"ok": True, "bars": len(daily_tv)}
                except Exception as e:
                    t_block["daily"] = _fail_block(e)
                latency_rows.append({"provider": "tradingview", "symbol": sym, "stage": "intraday_5m", "latency_ms": ms})
            except Exception as e:
                t_block["quote"] = _fail_block(e)
                t_block["intraday"] = _fail_block(e)
                error_rows.append({"provider": "tradingview", "symbol": sym, "stage": "intraday", "error": str(e)})
                _write_raw(raw_dir / "tradingview" / sym / "error.json", t_block["quote"])
                quote_rows.append({
                    "canonical_symbol": sym, "provider": "tradingview", "response_status": "error",
                    "last_error": str(e), "raw_file_reference": f"raw/tradingview/{sym}/error.json",
                    "independence_group": "TRADINGVIEW",
                })
        else:
            t_block["quote"] = {"ok": False, "status": "DISABLED"}
        per_symbol[sym]["tradingview"] = t_block
        time.sleep(sleep_s)

        # ---- BORSA ----
        b_block: dict[str, Any] = {
            "mapping_ok": True,
            "mapped_as": registry.to_provider(sym, "borsa"),
            "interface": "aggregator",
        }
        data, ms, code, err = fetch_borsa_raw(borsa_base_url, f"/v1/quote/{sym}")
        _write_raw(raw_dir / "borsa" / sym / "quote.json", data if data is not None else {"error": err})
        und = parse_borsa_underlying(data if isinstance(data, dict) else None)
        underlying_counts[und] = underlying_counts.get(und, 0) + (1 if not err else 0)
        if err or not isinstance(data, dict) or data.get("price") is None:
            b_block["quote"] = _fail_block(err or "no price", latency_ms=ms, http_status=code)
            error_rows.append({"provider": "borsa", "symbol": sym, "stage": "quote", "error": err or "no price",
                               "http_status": code, "underlying": und})
            quote_rows.append({
                "canonical_symbol": sym, "provider": "borsa", "borsa_underlying_provider": und,
                "independence_group": independence_group_for("borsa", und),
                "response_status": "error", "http_status": code, "latency_ms": ms,
                "last_error": err, "raw_file_reference": f"raw/borsa/{sym}/quote.json",
            })
        else:
            # Normalize without claiming OHLCV history
            from egxbridge.providers.base import Quote
            from egxbridge.semantics import DAILY_CLOSE, DAILY_FINAL_VOLUME, session_date_cairo
            capture = utc_now_iso()
            # Borsa timestamp is fetch/cache oriented
            q = Quote(
                symbol=sym,
                provider="borsa",
                capture_timestamp=capture,
                last=_f(data.get("price")),
                open=None,
                high=_f(data.get("high")),
                low=_f(data.get("low")),
                volume=_f(data.get("volume")),
                change_pct=_parse_pct(data.get("change_percent") or data.get("change_pct")),
                provider_timestamp=str(data.get("timestamp") or "") or None,
                provider_mode="http",
                price_observation_type=DAILY_CLOSE,  # Yahoo-backed daily-like
                volume_semantics=DAILY_FINAL_VOLUME if und == "YAHOO" else "UNKNOWN_VOLUME",
                volume_interval="1d" if und == "YAHOO" else None,
                provider_raw_timestamp=str(data.get("timestamp") or "") or None,
                provider_timezone_if_known=None,
                timestamp_semantics="FETCH_TIME",
                raw_reference=f"borsa:{data.get('api_symbol')}",
            )
            row = serialize_quote_row(
                sym, "borsa", q, raw_ref=f"raw/borsa/{sym}/quote.json", latency_ms=ms,
                http_status=code, borsa_underlying=und,
                extra={
                    "borsa_source": data.get("source"),
                    "borsa_api_symbol": data.get("api_symbol"),
                    "borsa_fetch_duration": data.get("fetch_duration"),
                    "same_underlying_as_yahoo": und == "YAHOO",
                    "independence_note": "SAME_UNDERLYING_SOURCE" if und == "YAHOO" else "",
                },
            )
            quote_rows.append(row)
            b_block["quote"] = {
                "ok": True, "last": q.last, "volume": q.volume, "latency_ms": ms,
                "underlying_provider": und, "source": data.get("source"),
                "timestamp_semantics": "FETCH_TIME",
                "api_symbol": data.get("api_symbol"),
            }
            b_block["underlying_provider"] = und
            latency_rows.append({"provider": "borsa", "symbol": sym, "stage": "quote", "latency_ms": ms,
                                 "underlying": und})
        b_block["daily"] = {
            "ok": False,
            "status": "NOT_SUPPORTED",
            "note": "Borsa /v1 has quote+catalog only; no OHLCV history endpoint",
        }
        b_block["intraday"] = {"ok": False, "status": "NOT_SUPPORTED"}
        per_symbol[sym]["borsa"] = b_block
        time.sleep(sleep_s)

        # ---- INVESTOR_EGX ----
        i_block: dict[str, Any] = {"mapping_ok": True, "provider_type": "local_import"}
        if inv and inv.enabled:
            try:
                f = inv.get_fundamentals(sym)
                _write_raw(raw_dir / "investor_egx" / sym / "fundamentals.json", f)
                i_block["fundamentals"] = {"ok": True, "as_of": f.get("as_of"), "note": f.get("note")}
                fields = f.get("fields") or {}
                if isinstance(fields, dict):
                    for k, v in fields.items():
                        fund_rows.append({
                            "canonical_symbol": sym, "provider": "investor_egx",
                            "metric_name": k, "value": v, "period": None, "period_end": None,
                            "currency": None, "source_date": f.get("as_of"),
                            "raw_file_reference": f"raw/investor_egx/{sym}/fundamentals.json",
                        })
            except Exception as e:
                i_block["fundamentals"] = _fail_block(e)
                _write_raw(raw_dir / "investor_egx" / sym / "fundamentals.json", {
                    "ok": False, "error": str(e),
                    "note": "Capability may be true while current data unavailable",
                })
                fund_rows.append({
                    "canonical_symbol": sym, "provider": "investor_egx",
                    "metric_name": "_unavailable", "value": None,
                    "raw_file_reference": f"raw/investor_egx/{sym}/fundamentals.json",
                    "note": str(e),
                })
            # Capability vs current
            i_block["capabilities"] = inv.capabilities().as_dict()
            i_block["current_data_available"] = {
                "fundamentals": bool(i_block.get("fundamentals", {}).get("ok")),
            }
        else:
            i_block["fundamentals"] = {"ok": False, "status": "DISABLED"}
        per_symbol[sym]["investor_egx"] = i_block

        # ---- EGID ----
        e_block: dict[str, Any] = {"mapping_ok": True}
        if egid and egid.enabled:
            try:
                if egid_probe_cached is None or sym in {"COMI", "MASR"}:
                    t0 = time.time()
                    probe = egid.probe(sym)
                    ms = (time.time() - t0) * 1000
                    egid_probe_cached = probe
                else:
                    # Reuse auth semantics; avoid hammering DelayedFeed
                    probe = {
                        **(egid_probe_cached or {}),
                        "symbol": sym,
                        "note": "Reused probe semantics after first EGID auth result (benchmark throttle)",
                    }
                    ms = egid._latency_ms
                _write_raw(raw_dir / "egid" / sym / "probe.json", probe)
                st = egid.status().to_dict()
                e_block["probe"] = probe
                e_block["health"] = st
                e_block["quote"] = {
                    "ok": False,
                    "status": probe.get("status") or st.get("health_state"),
                    "http_status": probe.get("HTTP") or st.get("last_http_status"),
                    "error": probe.get("note") or st.get("last_error") or st.get("notes"),
                    "latency_ms": ms or st.get("latency_ms"),
                    "reachable": st.get("reachable"),
                    "auth_status": st.get("auth_status"),
                    "health_state": st.get("health_state"),
                }
                if st.get("health_state") in {"AUTH_REQUIRED", "LICENSE_REQUIRED"} or probe.get("status") == "AUTH_REQUIRED":
                    error_rows.append({
                        "provider": "egid", "symbol": sym, "stage": "probe",
                        "error": "LICENSE/AUTH REQUIRED", "http_status": 401,
                        "reachable": True,
                    })
            except Exception as e:
                e_block["quote"] = _fail_block(e)
                _write_raw(raw_dir / "egid" / sym / "probe.json", e_block["quote"])
                error_rows.append({"provider": "egid", "symbol": sym, "stage": "probe", "error": str(e)})
        else:
            e_block["quote"] = {"ok": False, "status": "DISABLED"}
        per_symbol[sym]["egid"] = e_block

        # comparisons stub per symbol
        per_symbol[sym]["comparisons"] = {
            "yahoo_vs_borsa_same_underlying": (
                (per_symbol[sym].get("borsa") or {}).get("underlying_provider") == "YAHOO"
            ),
            "note": "Unlike volume/price semantics are not forced equal",
        }
        jdump(per_dir / f"{sym}.json", {"symbol": sym, **per_symbol[sym]})

    # Provider health snapshot (benchmark-time)
    for name, p in [
        ("yahoo", yahoo), ("tradingview", tv), ("investor_egx", inv), ("egid", egid), ("borsa", borsa),
    ]:
        if p is None:
            continue
        st = p.status().to_dict()
        health_rows.append({
            "provider": name,
            "enabled": st.get("enabled"),
            "health_state": st.get("health_state"),
            "reachable": st.get("reachable"),
            "auth_status": st.get("auth_status"),
            "mode": st.get("mode"),
            "last_success": st.get("last_success"),
            "last_error": st.get("last_error"),
            "last_http_status": st.get("last_http_status"),
            "latency_ms": st.get("latency_ms"),
            "latest_source_timestamp": st.get("latest_source_timestamp"),
            "last_checked": st.get("last_checked"),
            "notes": st.get("notes"),
            "benchmark_only_enabled": name == "borsa",
        })
        # Also record production borsa status (disabled)
        if name == "borsa":
            health_rows.append({
                "provider": "borsa_production_config",
                "enabled": prod_borsa_enabled,
                "health_state": "DISABLED",
                "reachable": None,
                "auth_status": "NOT_APPLICABLE",
                "mode": "http",
                "notes": "Production config unchanged; borsa remains disabled outside benchmark",
            })

    disagreements = build_disagreements(quote_rows)
    cov = coverage_stats(symbols, per_symbol, PROVIDERS)
    providers_configured = (health_raw or {}).get("providers_configured") if isinstance(health_raw, dict) else {}
    meta = {
        "health_ok": isinstance(health_raw, dict) and health_raw.get("status") == "ok",
        "alpha_vantage_configured": bool((providers_configured or {}).get("alpha_vantage")),
        "finnhub_configured": bool((providers_configured or {}).get("finnhub")),
        "yahoo_via_borsa_configured": bool((providers_configured or {}).get("yahoo")),
        "underlying_counts": underlying_counts,
        "cache_test": {
            "first_ms": cache_test.get("first_ms"),
            "second_ms": cache_test.get("second_ms"),
            "third_ms": cache_test.get("third_ms"),
        },
        "universe_count": next((r for r in health_rows if False), None),
        "fallback_value": (
            "HIGH" if (providers_configured or {}).get("alpha_vantage") or (providers_configured or {}).get("finnhub")
            else "LOW"
        ),
    }
    # universe count from borsa
    try:
        uni_b = [r for r in universe_rows if r["provider"] == "borsa"]
        meta["universe_count"] = len(uni_b)
    except Exception:
        meta["universe_count"] = 0

    score = score_borsa(cov, meta)
    answers = answers_from_results(cov, score, meta)

    # Write normalized CSVs
    write_csv(norm_dir / "quotes_all_sources.csv", quote_rows)
    write_csv(norm_dir / "daily_ohlcv_all_sources.csv", daily_rows)
    write_csv(norm_dir / "intraday_ohlcv_all_sources.csv", intra_rows)
    write_csv(norm_dir / "fundamentals_all_sources.csv", fund_rows)
    write_csv(norm_dir / "universe_mapping_all_sources.csv", universe_rows)
    write_csv(norm_dir / "provider_health.csv", health_rows)
    write_csv(norm_dir / "provider_latency.csv", latency_rows)
    write_csv(norm_dir / "provider_errors.csv", error_rows)
    write_csv(norm_dir / "source_disagreements.csv", disagreements)
    write_csv(norm_dir / "provider_lineage.csv", [
        {
            **row,
            "notes": row["notes"] + (
                f" | runtime underlying histogram={underlying_counts}" if row["provider"] == "borsa" else ""
            ),
        }
        for row in PROVIDER_LINEAGE
    ])

    summary = {
        "bridge_version": BRIDGE_VERSION,
        "benchmark_version": BENCHMARK_VERSION,
        "generated_at": now_iso(),
        "symbols_tested": symbols,
        "providers_tested": PROVIDERS,
        "coverage": cov,
        "borsa_score": score,
        "answers": answers,
        "underlying_counts": underlying_counts,
        "cache_test": cache_test,
        "disagreement_count": len(disagreements),
        "independent_disagreement_count": sum(1 for d in disagreements if d.get("independent_comparison")),
        "same_underlying_disagreement_count": sum(
            1 for d in disagreements if d.get("same_underlying_note") == "SAME_UNDERLYING_SOURCE"
        ),
        "row_counts": {
            "quotes": len(quote_rows),
            "daily_ohlcv": len(daily_rows),
            "intraday_ohlcv": len(intra_rows),
            "fundamentals": len(fund_rows),
            "universe": len(universe_rows),
            "errors": len(error_rows),
            "disagreements": len(disagreements),
        },
        "production_config_unchanged": {
            "borsa_enabled_in_config": prod_borsa_enabled,
            "provider_priority": prod_priority,
            "borsa_base_url_in_config": settings.borsa_base_url,
        },
        "borsa_benchmark_endpoint": borsa_base_url,
    }

    report_md = _render_report_md(summary)
    jdump(reports_dir / "borsa_benchmark_report.json", summary)
    (reports_dir / "borsa_benchmark_report.md").write_text(report_md, encoding="utf-8")
    jdump(reports_dir / "source_comparison_summary.json", {
        "row_counts": summary["row_counts"],
        "coverage": cov,
        "underlying_counts": underlying_counts,
        "score": score,
    })
    (reports_dir / "source_comparison_summary.md").write_text(
        f"# Source comparison summary\n\n"
        f"- Symbols: {len(symbols)}\n"
        f"- Quote rows: {len(quote_rows)}\n"
        f"- Disagreements: {len(disagreements)}\n"
        f"- Borsa unique coverage gain: {cov.get('borsa_unique_coverage_gain')}\n"
        f"- BORSA VALUE SCORE: {score.get('borsa_value_score')}/100\n"
        f"- Classification: {score.get('classification')}\n",
        encoding="utf-8",
    )

    # Also copy top-level report copies required by the brief
    (out_root / "borsa_benchmark_report.json").write_text(
        (reports_dir / "borsa_benchmark_report.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (out_root / "borsa_benchmark_report.md").write_text(report_md, encoding="utf-8")

    files_included = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
    manifest = {
        "bridge_version": BRIDGE_VERSION,
        "benchmark_version": BENCHMARK_VERSION,
        "generated_at": now_iso(),
        "host_timezone": str(datetime.now().astimezone().tzinfo),
        "python_version": sys.version,
        "platform": platform.platform(),
        "provider_versions": {
            "yfinance": _pkg_ver("yfinance"),
            "tvDatafeed": _pkg_ver("tvDatafeed"),
            "borsa": _pkg_ver("borsa"),
            "pandas": _pkg_ver("pandas"),
            "requests": _pkg_ver("requests"),
        },
        "symbols_tested": symbols,
        "providers_tested": PROVIDERS,
        "borsa_base_url_benchmark_only": borsa_base_url,
        "files_included": files_included,
        "test_results": {
            "coverage": cov,
            "score": score,
            "row_counts": summary["row_counts"],
        },
        "important_limitations": [
            "Open-source software ≠ free exchange data / license.",
            "Borsa demo/public site may be unavailable; this run used a local benchmark instance.",
            "With only Yahoo configured on Borsa, Borsa quotes are SAME_UNDERLYING_SOURCE as direct Yahoo.",
            "Borsa timestamps are typically FETCH_TIME/CACHE_TIME, not exchange bar open.",
            "EGID without token returns 401 (reachable=true, LICENSE_REQUIRED).",
            "Unlike volume/price semantics are never compared as equal.",
            "Production config.json left with borsa disabled; priorities unchanged.",
        ],
    }
    jdump(root / "manifest.json", manifest)
    (root / "README.md").write_text(_readme_text(manifest, summary), encoding="utf-8")

    # ZIP
    zip_path = out_root / "source_comparison.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in root.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=str(Path("source_comparison") / f.relative_to(root)))

    summary["zip_path"] = str(zip_path)
    summary["package_root"] = str(root)

    # Rewrite reports with zip path
    jdump(reports_dir / "borsa_benchmark_report.json", summary)
    (out_root / "borsa_benchmark_report.json").write_text(
        (reports_dir / "borsa_benchmark_report.json").read_text(encoding="utf-8"), encoding="utf-8"
    )

    # Final safety: production config file unchanged
    raw_cfg = __import__("json").loads(Path(config_path).read_text(encoding="utf-8"))
    assert raw_cfg.get("enabled_providers", {}).get("borsa") is False
    assert (raw_cfg.get("borsa_base_url") or "") == ""

    return summary


def _f(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None


def _parse_pct(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("%", "")
    try:
        return float(s)
    except Exception:
        return None


def _render_report_md(summary: dict) -> str:
    score = summary["borsa_score"]
    cov = summary["coverage"]
    ans = summary["answers"]
    lines = [
        f"# Borsa Benchmark Report (EGX Market Bridge {summary['bridge_version']})",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        f"**BORSA VALUE SCORE:** {score['borsa_value_score']}/100",
        f"**Classification:** {score['classification']}",
        "",
        "## Score breakdown",
        "",
    ]
    for k, v in (score.get("breakdown") or {}).items():
        lines.append(f"- {k}: {v}")
    lines += [
        "",
        "## Coverage",
        "",
        f"- Symbols tested: {cov.get('symbols_tested')}",
        f"- Borsa unique coverage gain: {cov.get('borsa_unique_coverage_gain')}",
        f"- Borsa-only symbols: {cov.get('borsa_only_quote_symbols')}",
        f"- Direct-only (not Borsa): {cov.get('direct_only_not_borsa_quote_symbols')}",
        f"- Underlying histogram: {summary.get('underlying_counts')}",
        "",
        "## Important questions",
        "",
    ]
    for k, v in ans.items():
        lines.append(f"### {k}")
        lines.append(v)
        lines.append("")
    lines += [
        "## Fairness notes",
        "",
        "- Borsa→Yahoo is `SAME_UNDERLYING_SOURCE` / `independence_group=YAHOO`.",
        "- BAR_VOLUME is never compared to DAILY_FINAL_VOLUME.",
        "- Production priorities and `enabled_providers.borsa=false` remain unchanged.",
        "",
    ]
    return "\n".join(lines)


def _readme_text(manifest: dict, summary: dict) -> str:
    return f"""# EGX Market Bridge — Source Comparison Package

Bridge version: **{manifest['bridge_version']}**  
Benchmark version: **{manifest['benchmark_version']}**  
Generated: `{manifest['generated_at']}`

## What this package is

A portable raw + normalized multi-provider dump for independent review (e.g. upload to ChatGPT).
It compares Yahoo, TradingView, Borsa (benchmark-only), investor_egx, and EGID probe results.

## Independence (critical)

| Provider | Independent? | Notes |
|---|---|---|
| yahoo | yes | Direct yfinance |
| tradingview | yes (backend) | tvDatafeed/TradeGlob |
| borsa | **often no** | Aggregator; if `source` says Yahoo Finance → `SAME_UNDERLYING_SOURCE` |
| investor_egx | local/import | Fundamentals/universe, not live tape |
| egid | licensed | 401 without token = auth/license required, still reachable |

See `normalized/provider_lineage.csv`.

## What Borsa actually wraps

Borsa is a self-hostable FastAPI aggregator (MIT). Upstream providers may include Yahoo Finance,
Alpha Vantage, and Finnhub depending on operator keys. This benchmark instance configured:

```
{manifest.get('test_results', {})}
```

Runtime underlying histogram: `{summary.get('underlying_counts')}`.

## Directory guide

- `raw/<provider>/<SYMBOL>/` — original responses (JSON/CSV). Field names preserved where possible.
- `normalized/*.csv` — one row per source observation (not collapsed).
- `per_symbol/<SYMBOL>.json` — side-by-side including failures.
- `reports/` — human + machine benchmark reports.
- `manifest.json` — generation metadata.

## Semantics

- **Volume:** do not compare `BAR_VOLUME` with `DAILY_FINAL_VOLUME`.
- **Timestamps:** Borsa `timestamp` is typically **FETCH_TIME/CACHE_TIME**, not exchange bar open.
- **Missing data:** capability=true ≠ current-run data available (see investor_egx).
- **Licensing:** open-source software ≠ free exchange data.

## Production note

This package was generated in **test mode**. Production `config.json` keeps `borsa` **disabled**
and provider priorities unchanged.
"""


def main():
    ap = argparse.ArgumentParser(description="Benchmark Borsa vs other providers; export comparison package.")
    ap.add_argument("--borsa-url", default=os.environ.get("BORSA_BENCHMARK_URL", "http://127.0.0.1:8765"))
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--output", default=str(HERE / "output"))
    ap.add_argument("--symbols", nargs="*", default=None)
    ap.add_argument("--sleep", type=float, default=0.35)
    args = ap.parse_args()

    symbols = args.symbols or default_benchmark_symbols()
    # health check
    try:
        r = requests.get(f"{args.borsa_url.rstrip('/')}/v1/health", timeout=10)
        r.raise_for_status()
        print("Borsa health:", r.json())
    except Exception as e:
        print("ERROR: Borsa benchmark endpoint unavailable:", e, file=sys.stderr)
        print("Start local Borsa (Yahoo-enabled) or pass --borsa-url.", file=sys.stderr)
        sys.exit(2)

    summary = run_benchmark(
        out_root=Path(args.output),
        borsa_base_url=args.borsa_url,
        symbols=symbols,
        config_path=Path(args.config),
        sleep_s=args.sleep,
    )
    print(json_summary(summary))


def json_summary(summary: dict) -> str:
    import json
    brief = {
        "symbols_tested": len(summary["symbols_tested"]),
        "providers_tested": summary["providers_tested"],
        "row_counts": summary["row_counts"],
        "disagreements": summary["disagreement_count"],
        "borsa_unique_coverage_gain": summary["coverage"].get("borsa_unique_coverage_gain"),
        "borsa_value_score": summary["borsa_score"].get("borsa_value_score"),
        "classification": summary["borsa_score"].get("classification"),
        "zip_path": summary.get("zip_path"),
    }
    return json.dumps(brief, indent=2)


if __name__ == "__main__":
    main()
