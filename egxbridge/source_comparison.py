"""Source comparison / Borsa benchmark export helpers (test-mode only).

Does not mutate production config or provider priority.
"""
from __future__ import annotations

from typing import Any
import csv
import json
import re
from pathlib import Path


BENCHMARK_VERSION = "1.0.0"

PROVIDER_LINEAGE = [
    {
        "provider": "yahoo",
        "interface": "direct",
        "underlying_provider": "yahoo",
        "independence_group": "YAHOO",
        "is_independent_source": True,
        "notes": "Direct yfinance EGX (.CA) adapter",
    },
    {
        "provider": "tradingview",
        "interface": "direct-ish",
        "underlying_provider": "tradingview_backend",
        "independence_group": "TRADINGVIEW",
        "is_independent_source": True,
        "notes": "tvDatafeed/TradeGlob; anonymous mode common",
    },
    {
        "provider": "borsa",
        "interface": "aggregator",
        "underlying_provider": "varies",
        "independence_group": "BORSA_AGGREGATOR",
        "is_independent_source": False,
        "notes": "Self-hosted aggregator; often Yahoo/AV/Finnhub — check per-quote underlying",
    },
    {
        "provider": "investor_egx",
        "interface": "local_import",
        "underlying_provider": "import_or_seed",
        "independence_group": "INVESTOR_EGX",
        "is_independent_source": True,
        "notes": "Local/import fundamentals/universe; not live quotes",
    },
    {
        "provider": "egid",
        "interface": "licensed_http",
        "underlying_provider": "egid",
        "independence_group": "EGID",
        "is_independent_source": True,
        "notes": "Licensed DelayedFeed/Feed; 401 without token is auth gap not network-down",
    },
]

# Fields that may be compared only when semantics match
COMPARABLE_QUOTE_FIELDS = ("last", "open", "high", "low", "prev_close", "volume")


def parse_borsa_underlying(raw: dict[str, Any] | None) -> str:
    """Map Borsa response attribution/source to YAHOO / ALPHA_VANTAGE / FINNHUB / OTHER / UNKNOWN."""
    if not raw or not isinstance(raw, dict):
        return "UNKNOWN"
    attr = raw.get("attribution") or {}
    provider = ""
    if isinstance(attr, dict):
        provider = str(attr.get("provider") or "")
    source = str(raw.get("source") or "")
    blob = f"{provider} {source}".lower()
    if "yahoo" in blob:
        return "YAHOO"
    if "alpha" in blob and "vantage" in blob:
        return "ALPHA_VANTAGE"
    if "finnhub" in blob:
        return "FINNHUB"
    if provider or source:
        return "OTHER"
    return "UNKNOWN"


def independence_group_for(provider: str, borsa_underlying: str | None = None) -> str:
    p = (provider or "").lower()
    if p == "yahoo":
        return "YAHOO"
    if p == "tradingview":
        return "TRADINGVIEW"
    if p == "investor_egx":
        return "INVESTOR_EGX"
    if p == "egid":
        return "EGID"
    if p == "borsa":
        u = (borsa_underlying or "UNKNOWN").upper()
        if u == "YAHOO":
            return "YAHOO"
        if u == "ALPHA_VANTAGE":
            return "ALPHA_VANTAGE"
        if u == "FINNHUB":
            return "FINNHUB"
        return "BORSA_OTHER"
    return "UNKNOWN"


def is_independent_pair(group_a: str, group_b: str) -> bool:
    if not group_a or not group_b or group_a == "UNKNOWN" or group_b == "UNKNOWN":
        return False
    return group_a != group_b


def volumes_comparable(sem_a: str | None, sem_b: str | None) -> bool:
    a = (sem_a or "UNKNOWN_VOLUME").upper()
    b = (sem_b or "UNKNOWN_VOLUME").upper()
    if a == "UNKNOWN_VOLUME" or b == "UNKNOWN_VOLUME":
        return False
    return a == b


def observations_comparable(
    *,
    field: str,
    semantic_type_a: str | None,
    semantic_type_b: str | None,
    interval_a: str | None = None,
    interval_b: str | None = None,
    price_type_a: str | None = None,
    price_type_b: str | None = None,
) -> bool:
    """Fair-comparison gate: never mix unlike observations."""
    if field == "volume":
        return volumes_comparable(semantic_type_a, semantic_type_b)
    if field in ("last", "open", "high", "low", "close", "prev_close"):
        # Daily close vs 5m candle close are not the same observation
        if interval_a and interval_b and interval_a != interval_b:
            return False
        if price_type_a and price_type_b and price_type_a != price_type_b:
            # Allow DAILY_CLOSE vs DAILY_CLOSE only; CANDLE_CLOSE vs CANDLE_CLOSE
            return price_type_a == price_type_b
        return True
    return True


def diff_numeric(a: Any, b: Any) -> tuple[float | None, float | None]:
    try:
        fa = float(a)
        fb = float(b)
    except (TypeError, ValueError):
        return None, None
    if fa != fa or fb != fb:  # NaN
        return None, None
    abs_d = abs(fa - fb)
    pct = None if fb == 0 else abs_d / abs(fb) * 100.0
    return abs_d, pct


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols = fieldnames or list(dict.fromkeys(k for r in rows for k in r.keys()))
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in cols})


def _csv_cell(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, default=str)
    return v


def jdump(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def build_disagreements(quote_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pairwise disagreements for semantically compatible, independent or same-session quotes."""
    by_symbol: dict[str, list[dict]] = {}
    for r in quote_rows:
        if r.get("response_status") != "ok":
            continue
        by_symbol.setdefault(r["canonical_symbol"], []).append(r)

    out: list[dict[str, Any]] = []
    for sym, rows in by_symbol.items():
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                a, b = rows[i], rows[j]
                # Same session when available
                sa, sb = a.get("session_date"), b.get("session_date")
                if sa and sb and sa != sb:
                    continue
                ga = a.get("independence_group") or independence_group_for(
                    a.get("provider"), a.get("borsa_underlying_provider")
                )
                gb = b.get("independence_group") or independence_group_for(
                    b.get("provider"), b.get("borsa_underlying_provider")
                )
                independent = is_independent_pair(ga, gb)
                for field in COMPARABLE_QUOTE_FIELDS:
                    if not observations_comparable(
                        field=field,
                        semantic_type_a=a.get("volume_semantics") if field == "volume" else a.get("price_observation_type"),
                        semantic_type_b=b.get("volume_semantics") if field == "volume" else b.get("price_observation_type"),
                        interval_a=a.get("volume_interval") or a.get("interval"),
                        interval_b=b.get("volume_interval") or b.get("interval"),
                        price_type_a=a.get("price_observation_type"),
                        price_type_b=b.get("price_observation_type"),
                    ):
                        continue
                    va, vb = a.get(field), b.get(field)
                    if va is None or vb is None or va == "" or vb == "":
                        continue
                    abs_d, pct = diff_numeric(va, vb)
                    if abs_d is None:
                        continue
                    # Skip exact matches
                    if abs_d == 0:
                        continue
                    out.append({
                        "symbol": sym,
                        "field": field,
                        "semantic_type": (
                            a.get("volume_semantics") if field == "volume" else a.get("price_observation_type")
                        ),
                        "session_date": sa or sb,
                        "interval": a.get("volume_interval") or a.get("interval") or "",
                        "provider_a": a.get("provider"),
                        "value_a": va,
                        "provider_b": b.get("provider"),
                        "value_b": vb,
                        "difference_absolute": abs_d,
                        "difference_pct": pct,
                        "independence_group_a": ga,
                        "independence_group_b": gb,
                        "independent_comparison": independent,
                        "same_underlying_note": (
                            "SAME_UNDERLYING_SOURCE" if ga == gb else ""
                        ),
                        "selected_provider_if_any": "",
                        "selection_reason": "",
                    })
    return out


def coverage_stats(
    symbols: list[str],
    per_symbol: dict[str, dict[str, Any]],
    providers: list[str],
) -> dict[str, Any]:
    stats: dict[str, Any] = {"symbols_tested": len(symbols), "by_provider": {}}
    for p in providers:
        quote_ok = daily_ok = intra_ok = fund_ok = map_ok = 0
        unique_only: list[str] = []
        for sym in symbols:
            block = (per_symbol.get(sym) or {}).get(p) or {}
            if block.get("mapping_ok"):
                map_ok += 1
            if block.get("quote", {}).get("ok"):
                quote_ok += 1
            if block.get("daily", {}).get("ok"):
                daily_ok += 1
            if block.get("intraday", {}).get("ok"):
                intra_ok += 1
            if block.get("fundamentals", {}).get("ok"):
                fund_ok += 1
        n = max(len(symbols), 1)
        stats["by_provider"][p] = {
            "mapping_success_rate": round(map_ok / n, 4),
            "quote_success_rate": round(quote_ok / n, 4),
            "daily_ohlcv_success_rate": round(daily_ok / n, 4),
            "intraday_success_rate": round(intra_ok / n, 4),
            "fundamentals_success_rate": round(fund_ok / n, 4),
            "quote_ok_count": quote_ok,
            "daily_ok_count": daily_ok,
            "intraday_ok_count": intra_ok,
            "fundamentals_ok_count": fund_ok,
        }

    # Unique coverage: symbols with quote ok only on this provider
    for p in providers:
        only = []
        for sym in symbols:
            oks = {
                q: bool(((per_symbol.get(sym) or {}).get(q) or {}).get("quote", {}).get("ok"))
                for q in providers
            }
            if oks.get(p) and not any(oks[o] for o in providers if o != p):
                only.append(sym)
        stats["by_provider"][p]["symbols_uniquely_available_quote"] = only
        stats["by_provider"][p]["unique_coverage_gain"] = len(only)

    # Borsa resolves but directs don't / reverse
    borsa_only = []
    directs_only = []
    directs = [x for x in providers if x != "borsa"]
    for sym in symbols:
        b_ok = bool(((per_symbol.get(sym) or {}).get("borsa") or {}).get("quote", {}).get("ok"))
        d_ok = any(
            bool(((per_symbol.get(sym) or {}).get(d) or {}).get("quote", {}).get("ok"))
            for d in directs
        )
        if b_ok and not d_ok:
            borsa_only.append(sym)
        if d_ok and not b_ok:
            directs_only.append(sym)
    stats["borsa_only_quote_symbols"] = borsa_only
    stats["direct_only_not_borsa_quote_symbols"] = directs_only
    stats["borsa_unique_coverage_gain"] = len(borsa_only)
    return stats


def score_borsa(coverage: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    """Score Borsa only on incremental value (max 100)."""
    unique_gain = int(coverage.get("borsa_unique_coverage_gain") or 0)
    n = max(int(coverage.get("symbols_tested") or 1), 1)
    borsa_stats = (coverage.get("by_provider") or {}).get("borsa") or {}
    yahoo_stats = (coverage.get("by_provider") or {}).get("yahoo") or {}

    # Coverage improvement (30): unique symbols Borsa alone can quote
    cov_pts = min(30.0, unique_gain * 10.0)  # 3+ unique → full; 0 → 0
    # If Borsa quote rate materially exceeds Yahoo (catalog help), partial credit
    bq = float(borsa_stats.get("quote_success_rate") or 0)
    yq = float(yahoo_stats.get("quote_success_rate") or 0)
    if unique_gain == 0 and bq > yq + 0.05:
        cov_pts = min(30.0, (bq - yq) * 60)

    # Symbol mapping quality (20)
    map_rate = float(borsa_stats.get("mapping_success_rate") or 0)
    map_pts = round(map_rate * 20, 2)

    # Reliability / fallback (20): cache hits / success when Yahoo also works is low incremental
    fb = meta.get("fallback_value", "LOW")
    fb_pts = {"HIGH": 20, "MEDIUM": 12, "LOW": 4}.get(str(fb).upper(), 4)
    # If no Alpha/Finnhub configured, fallback value stays low
    if not meta.get("alpha_vantage_configured") and not meta.get("finnhub_configured"):
        fb_pts = min(fb_pts, 6)

    # Independent data quality (15): credit only if non-Yahoo underlying observed
    und = meta.get("underlying_counts") or {}
    non_yahoo = sum(int(und.get(k, 0)) for k in ("ALPHA_VANTAGE", "FINNHUB", "OTHER"))
    yahoo_via = int(und.get("YAHOO", 0))
    if non_yahoo > 0:
        ind_pts = min(15.0, 5 + non_yahoo * 2)
    elif yahoo_via > 0:
        ind_pts = 2.0  # almost no credit — same underlying
    else:
        ind_pts = 0.0

    # Latency / operational simplicity (10)
    lat = meta.get("cache_test") or {}
    lat_pts = 0.0
    if lat.get("first_ms") is not None:
        lat_pts += 3
        if lat.get("second_ms") is not None and lat["second_ms"] < lat["first_ms"] * 0.5:
            lat_pts += 4  # cache helps ops
        lat_pts += 3 if meta.get("health_ok") else 0
    lat_pts = min(10.0, lat_pts)

    # Unique fields (5): catalog/universe
    uniq_pts = 5.0 if meta.get("universe_count", 0) > 50 else (2.0 if meta.get("universe_count", 0) > 0 else 0.0)

    total = round(cov_pts + map_pts + fb_pts + ind_pts + lat_pts + uniq_pts, 2)
    if total >= 70:
        classification = "ENABLE AS PRODUCTION FALLBACK"
    elif total >= 35:
        classification = "KEEP BENCHMARK-ONLY"
    else:
        classification = "NO MATERIAL VALUE"

    return {
        "borsa_value_score": total,
        "max_score": 100,
        "breakdown": {
            "coverage_improvement": cov_pts,
            "symbol_mapping_quality": map_pts,
            "reliability_fallback_benefit": fb_pts,
            "independent_data_quality": ind_pts,
            "latency_operational_simplicity": lat_pts,
            "unique_fields": uniq_pts,
        },
        "classification": classification,
        "notes": [
            "No double-credit for Yahoo data received through Borsa.",
            "Independent quality scored only when non-Yahoo upstream is observed.",
        ],
    }


def default_benchmark_symbols() -> list[str]:
    """≥24 EGX symbols spanning large/mid/small and coverage edges."""
    return [
        # required
        "COMI", "MASR", "RAYA", "LUTS",
        # large / EGX30-ish
        "TMGH", "SWDY", "ETEL", "HRHO", "FWRY", "ORAS", "EAST", "ABUK",
        # mid
        "EFID", "JUFO", "PHDC", "ORWE", "AMOC", "ADIB", "QNBE", "CLHO",
        # smaller / weaker coverage edges
        "KASABF", "ISPH", "POUL", "EGTS", "CIRA", "PHAR", "CCAP", "ORHD",
    ]


def answers_from_results(coverage: dict[str, Any], score: dict[str, Any], meta: dict[str, Any]) -> dict[str, str]:
    und = meta.get("underlying_counts") or {}
    return {
        "1_unique_symbols": (
            f"Borsa-only quote symbols: {coverage.get('borsa_only_quote_symbols') or []}. "
            f"Unique coverage gain={coverage.get('borsa_unique_coverage_gain', 0)}."
        ),
        "2_mapping": (
            f"Borsa mapping success rate="
            f"{(coverage.get('by_provider') or {}).get('borsa', {}).get('mapping_success_rate')}."
        ),
        "3_completeness": (
            "Borsa API exposes quotes + catalog; no daily/intraday OHLCV history endpoints "
            "in the standard /v1 surface — completeness vs Yahoo/TV for bars is not improved."
        ),
        "4_independent_data": (
            f"Underlying counts={und}. Independence is false when underlying is YAHOO."
        ),
        "5_upstream_per_result": "See per_symbol/*.json borsa.underlying_provider and provider_lineage.csv.",
        "6_alpha_finnhub": (
            "Meaningful EGX coverage from Alpha Vantage/Finnhub only if those keys are configured "
            f"on the Borsa instance (configured AV={meta.get('alpha_vantage_configured')}, "
            f"Finnhub={meta.get('finnhub_configured')})."
        ),
        "7_timestamps": (
            "Borsa `timestamp` is typically fetch/cache time on the aggregator, not exchange session "
            "bar open — treat as FETCH_TIME/CACHE_TIME unless upstream proves otherwise."
        ),
        "8_failure_rate": (
            f"Direct-only (not Borsa) symbols={coverage.get('direct_only_not_borsa_quote_symbols')}; "
            f"Borsa quote rate="
            f"{(coverage.get('by_provider') or {}).get('borsa', {}).get('quote_success_rate')}."
        ),
        "9_unique_capability": (
            "Primary unique capability is unified EGX catalog + multi-provider failover when "
            "non-Yahoo keys are present; with Yahoo-only it is mostly a proxy."
        ),
        "10_recommendation": score.get("classification", "KEEP BENCHMARK-ONLY"),
    }
