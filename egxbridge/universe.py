"""Canonical EGX universe builder and security-type hygiene."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json
import re

from egxbridge.symbols import canonicalize_any, load_name_aliases


HERE = Path(__file__).resolve().parent.parent
REF_UNIVERSE = HERE / "egxbridge" / "data" / "egx_reference_universe.json"
SECURITY_TYPES_PATH = HERE / "egxbridge" / "data" / "egx_security_types.json"

EQUITY = "EQUITY"
INDEX = "INDEX"
FUND = "FUND"
ETF = "ETF"
RIGHT = "RIGHT"
WARRANT = "WARRANT"
OTHER = "OTHER"
UNKNOWN = "UNKNOWN"

SECURITY_TYPES = {EQUITY, INDEX, FUND, ETF, RIGHT, WARRANT, OTHER, UNKNOWN}

# Default Explorer stock universe includes EQUITY only.
EXCLUDED_FROM_STOCK_EXPLORER = {INDEX, RIGHT, WARRANT}
# Funds/ETFs stay in the registry but are not mixed silently with ordinary equities.
NOT_ORDINARY_EQUITY = {INDEX, FUND, ETF, RIGHT, WARRANT, OTHER}

_INDEX_RE = re.compile(r"^EGX\d+", re.IGNORECASE)


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _symbols_from_payload(data: Any) -> list[str]:
    out: list[str] = []
    if isinstance(data, list):
        for r in data:
            if isinstance(r, str) and r.strip():
                out.append(r.strip().upper())
            elif isinstance(r, dict):
                s = r.get("canonical") or r.get("canonical_symbol") or r.get("symbol") or r.get("ticker")
                if s:
                    out.append(str(s).strip().upper())
    elif isinstance(data, dict):
        for key in ("successful_symbols", "symbols", "tickers", "mapped_symbols", "universe"):
            rows = data.get(key)
            if isinstance(rows, list):
                return _symbols_from_payload(rows)
    return out


def load_security_type_map() -> dict[str, str]:
    data = _load_json(SECURITY_TYPES_PATH)
    if not isinstance(data, dict):
        return {}
    out = {}
    for k, v in data.items():
        t = str(v).upper()
        if t in SECURITY_TYPES:
            out[str(k).upper()] = t
    return out


def classify_security_type(ticker: str, *, name: str = "", explicit_map: dict[str, str] | None = None) -> str:
    t = (ticker or "").strip().upper()
    if not t:
        return UNKNOWN
    mapping = explicit_map if explicit_map is not None else load_security_type_map()
    if t in mapping:
        return mapping[t]
    if _INDEX_RE.match(t):
        return INDEX
    n = (name or "").upper()
    if "INDEX" in n or "EGX 30" in n or "EGX 70" in n or "EGX 100" in n:
        return INDEX
    if "ETF" in n:
        return ETF
    if "FUND" in n or "MUTUAL" in n:
        return FUND
    if "RIGHT" in n:
        return RIGHT
    if "WARRANT" in n:
        return WARRANT
    return EQUITY


def yahoo_alias(canonical: str) -> str:
    c = canonical.upper().strip()
    if c.endswith(".CA"):
        return c
    return f"{c}.CA"


def tradingview_alias(canonical: str) -> str:
    c = canonical.upper().strip()
    if c.startswith("EGX:"):
        return c
    return f"EGX:{c}"


@dataclass
class UniverseRecord:
    canonical_symbol: str
    display_name_if_known: str = ""
    provider_alias_yahoo: str = ""
    provider_alias_tradingview: str = ""
    provider_alias_egid: str = ""
    provider_alias_other: str = ""
    security_type: str = EQUITY
    sector_if_known: str = ""
    industry_if_known: str = ""
    is_active_if_known: bool | None = None
    is_tradable_candidate: bool = True
    source: str = ""
    last_verified_at: str = ""
    exclusion_reason: str | None = None
    mapped: bool = True

    def __post_init__(self):
        self.canonical_symbol = self.canonical_symbol.upper().strip()
        if self.mapped:
            if not self.provider_alias_yahoo:
                self.provider_alias_yahoo = yahoo_alias(self.canonical_symbol)
            if not self.provider_alias_tradingview:
                self.provider_alias_tradingview = tradingview_alias(self.canonical_symbol)
            if not self.provider_alias_egid:
                self.provider_alias_egid = self.canonical_symbol
        else:
            self.exclusion_reason = self.exclusion_reason or "NO_MAPPING"
        self.is_tradable_candidate = (
            self.security_type == EQUITY and self.is_active_if_known is not False and self.mapped
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonicalize_symbols(raw: list[str]) -> list[str]:
    """Collapse ticker + issuer-name aliases to one security identity."""
    out: list[str] = []
    seen: set[str] = set()
    for s in raw or []:
        c = canonicalize_any(s)
        if not c or c in seen:
            continue
        seen.add(c)
        out.append(c)
    return sorted(out)


def _reference_symbols() -> list[str]:
    return _symbols_from_payload(_load_json(REF_UNIVERSE) or [])


def _provider_universe(settings=None, root: Path | None = None) -> tuple[list[dict[str, Any]], str]:
    """Merge imported and last-good discovered records; a seed never masks a catalog."""
    from egxbridge.config import Settings
    from egxbridge.providers.investor_egx import InvestorEGXProvider

    root = root or HERE
    settings = settings or Settings.load(root / "config.json")
    records = []
    sources = []
    if (settings.enabled_providers or {}).get("investor_egx", True):
        def local_path(value):
            return str(root / value) if value and not Path(value).is_absolute() else value
        try:
            records.extend(InvestorEGXProvider(
                universe_path=local_path(settings.investor_egx_universe_path),
                sqlite_path=local_path(settings.investor_egx_sqlite_path),
            ).get_universe())
            sources.append("investor_egx")
        except Exception:
            sources.append("investor_egx_unavailable")
    output = Path(settings.output_dir)
    if not output.is_absolute():
        output = root / output
    saved = _load_json(output / "universe.json") or {}
    saved_rows = saved.get("records") if isinstance(saved, dict) else None
    if saved_rows:
        records.extend(saved_rows)
    else:
        records.extend({"canonical": s, "source": "cached_discovery"} for s in _symbols_from_payload(saved))
    if saved:
        sources.append("cached_discovery")
    return records, "+".join(sources) or "none"


def _db_symbols(db) -> list[str]:
    if db is None:
        return []
    out = set()
    try:
        for r in db._conn.execute("SELECT DISTINCT symbol FROM candles").fetchall():
            out.add(r["symbol"] if hasattr(r, "keys") else r[0])
    except Exception:
        pass
    try:
        for r in db._conn.execute("SELECT canonical FROM symbols").fetchall():
            out.add(r["canonical"] if hasattr(r, "keys") else r[0])
    except Exception:
        pass
    return sorted({str(s).upper() for s in out if s})


def _config_symbols(settings=None) -> tuple[list[str], dict[str, dict[str, str]]]:
    aliases: dict[str, dict[str, str]] = {}
    try:
        from egxbridge.config import Settings
        settings = settings or Settings.load(HERE / "config.json")
        keys = list((settings.symbol_aliases or {}).keys())
        for k, v in (settings.symbol_aliases or {}).items():
            if isinstance(v, dict):
                aliases[k.upper()] = {str(pk): str(pv) for pk, pv in v.items()}
        syms = sorted({s.upper() for s in (settings.symbols or []) + (settings.focus_symbols or []) + keys})
        return syms, aliases
    except Exception:
        return [], {}


def _registry_aliases(canonical: str) -> dict[str, str]:
    try:
        from egxbridge.symbols import SymbolRegistry
        rec = SymbolRegistry().get(canonical)
        return dict(rec.aliases or {})
    except Exception:
        return {}


def build_canonical_universe(
    db=None,
    *,
    explicit: list[str] | None = None,
    include_non_equity_in_registry: bool = True,
    settings=None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Build canonical EGX records. Never hard-codes a 10-name list."""
    type_map = load_security_type_map()
    cfg_syms, cfg_aliases = _config_symbols(settings)
    provider_rows, psrc = _provider_universe(settings, root)
    metadata = {canonicalize_any(r.get("canonical") or r.get("symbol")): r for r in provider_rows}
    name_aliases = load_name_aliases()
    sources: list[str] = []

    if explicit:
        symbols = _canonicalize_symbols([s for s in explicit if s and str(s).strip()])
        source = "explicit"
        provider_syms: list[str] = []
        ref: list[str] = []
    else:
        provider_syms = list(metadata)
        ref = _reference_symbols()
        db_syms = _db_symbols(db)
        symbols = _canonicalize_symbols(list(ref) + list(provider_syms) + list(cfg_syms) + list(db_syms))
        source = f"{psrc}+reference_registry+config+db"
        sources = [psrc, "egx_reference_universe", "config", "db"]

    records: list[UniverseRecord] = []
    by_type: dict[str, int] = {t: 0 for t in sorted(SECURITY_TYPES)}

    for sym in symbols:
        info = metadata.get(sym) or {}
        al = dict(_registry_aliases(sym))
        al.update(info.get("aliases") or {})
        al.update(cfg_aliases.get(sym) or {})
        names = list(name_aliases.get(sym) or [])
        display = ""
        named = [n for n in names if str(n).strip() and str(n).upper() != sym]
        if named:
            display = max(named, key=lambda s: len(str(s)))
        rec = UniverseRecord(
            canonical_symbol=sym,
            display_name_if_known=info.get("name") or display,
            provider_alias_yahoo=al.get("yahoo") or yahoo_alias(sym),
            provider_alias_tradingview=al.get("tradingview") or tradingview_alias(sym),
            provider_alias_egid=al.get("egid") or al.get("borsa") or sym,
            provider_alias_other=al.get("borsa") or "",
            security_type=type_map.get(sym) or info.get("security_type") or classify_security_type(sym, name=info.get("name") or "", explicit_map=type_map),
            sector_if_known="",
            industry_if_known="",
            is_active_if_known=info.get("is_active_if_known"),
            source=info.get("source") or source,
            last_verified_at=info.get("last_verified_at") or "",
            mapped=bool(al.get("yahoo") or yahoo_alias(sym)),
        )
        if rec.security_type in EXCLUDED_FROM_STOCK_EXPLORER:
            rec.exclusion_reason = f"EXCLUDED_{rec.security_type}"
            rec.is_tradable_candidate = False
        elif rec.security_type in {FUND, ETF}:
            rec.exclusion_reason = f"EXCLUDED_{rec.security_type}_NOT_ORDINARY_EQUITY"
            rec.is_tradable_candidate = False
        elif rec.security_type == UNKNOWN:
            rec.exclusion_reason = "UNKNOWN_SECURITY_TYPE"
            rec.is_tradable_candidate = False
        elif not rec.mapped:
            rec.exclusion_reason = "NO_MAPPING"
            rec.is_tradable_candidate = False
        by_type[rec.security_type] = by_type.get(rec.security_type, 0) + 1
        if include_non_equity_in_registry or rec.security_type == EQUITY or explicit:
            records.append(rec)

    equity = [r for r in records if r.security_type == EQUITY]
    stock_default = [r for r in records if r.is_tradable_candidate]
    return {
        "catalog_status": "PROVIDER_CATALOG" if any(r.get("source") == "tradingview" for r in provider_rows) else "UNVERIFIED_LOCAL_REGISTRY",
        "exchange_completeness_verified": False,
        "records": records,
        "records_by_symbol": {r.canonical_symbol: r for r in records},
        "universe_source": source,
        "sources": sources or [source],
        "UNIVERSE_TOTAL": len(records),
        "EQUITY_UNIVERSE_TOTAL": len(equity),
        "security_type_counts": by_type,
        "stock_explorer_symbols": [r.canonical_symbol for r in stock_default],
        "equity_symbols": [r.canonical_symbol for r in equity],
        "all_symbols": [r.canonical_symbol for r in records],
        "reference_universe_count": len(ref) if not explicit else 0,
        "provider_universe_count": len(provider_syms) if not explicit else len(symbols),
    }


def _daily_stats(db, symbol: str, *, as_of=None) -> dict[str, Any]:
    from egxbridge.daily_bars import select_daily_pool, session_of, completed_session_rows, ohlcv_issue
    from egxbridge.semantics import previous_egx_session_date
    rows = db.fetch_candles(symbol, "1d", limit=5000) if db is not None else []
    invalid = [r for r in completed_session_rows(rows, as_of=as_of) if ohlcv_issue(r)]
    pool, provider, _ = select_daily_pool(rows, as_of=as_of)
    latest = pool[-1] if pool else {}
    expected = previous_egx_session_date(as_of)
    session = session_of(latest) or None
    return {
        "count": len(pool), "latest_session": session,
        "first_session": session_of(pool[0]) if pool else None,
        "latest_ts": latest.get("normalized_utc_timestamp") or latest.get("timestamp"),
        "captured_at": latest.get("capture_timestamp"), "provider": provider,
        "expected_session": expected,
        "data_state": "MISSING" if not pool else "STALE" if session < expected else "CURRENT",
        "invalid_daily_bars": len(invalid),
        "latest_invalid_session": max((session_of(r) for r in invalid), default=None),
    }


def assess_universe_coverage(
    built: dict[str, Any],
    db=None,
    *,
    min_scanner_bars: int = 20,
    stock_explorer_only: bool = True,
    as_of=None,
) -> dict[str, Any]:
    """Attach daily-data / scanner eligibility. Never silently drop a symbol."""
    records: list[UniverseRecord] = list(built.get("records") or [])
    mapped: list[str] = []
    unmapped: list[str] = []
    daily_available: list[str] = []
    daily_unavailable: list[str] = []
    stale_expected: list[str] = []
    stale_unexpected: list[str] = []
    scanner_eligible: list[str] = []
    reasons: dict[str, str] = {}
    status_by_symbol: dict[str, dict[str, Any]] = {}
    name_aliases = load_name_aliases()

    target = records
    if stock_explorer_only:
        # Still iterate ALL records so exclusions are visible; eligibility is equity-only.
        target = records

    for rec in target:
        sym = rec.canonical_symbol
        if rec.mapped:
            mapped.append(sym)
        else:
            unmapped.append(sym)

        stats = _daily_stats(db, sym, as_of=as_of)
        count = int(stats.get("count") or 0)
        freshness = "UNKNOWN"
        if stats.get("latest_ts"):
            freshness = "STALE_UNEXPECTED" if stats["data_state"] == "STALE" else "STALE_EXPECTED"

        if rec.security_type in EXCLUDED_FROM_STOCK_EXPLORER:
            reason = rec.exclusion_reason or f"EXCLUDED_{rec.security_type}"
            data_status = reason
        elif rec.security_type in {FUND, ETF}:
            reason = rec.exclusion_reason or f"EXCLUDED_{rec.security_type}_NOT_ORDINARY_EQUITY"
            data_status = reason
        elif rec.security_type == UNKNOWN:
            reason = rec.exclusion_reason or "UNKNOWN_SECURITY_TYPE"
            data_status = reason
        elif not rec.mapped:
            reason = "NO_MAPPING"
            data_status = "NO_MAPPING"
        elif rec.security_type == EQUITY:
            if count <= 0:
                daily_unavailable.append(sym)
                reason = "INVALID_DAILY_OHLCV" if stats.get("invalid_daily_bars") else "DAILY_DATA_UNAVAILABLE"
                data_status = reason
            else:
                daily_available.append(sym)
                if freshness == "STALE_UNEXPECTED":
                    stale_unexpected.append(sym)
                elif freshness == "STALE_EXPECTED":
                    stale_expected.append(sym)
                # Daily close from the last completed session is research-acceptable
                # even if quote-style freshness is STALE_* during a live session.
                if count < min_scanner_bars:
                    reason = "INSUFFICIENT_HISTORY"
                    data_status = "INSUFFICIENT_HISTORY"
                elif stats["data_state"] != "CURRENT":
                    reason = "STALE_DAILY_SESSION"
                    data_status = "STALE_DAILY_SESSION"
                else:
                    scanner_eligible.append(sym)
                    reason = "SCANNER_ELIGIBLE"
                    data_status = "SCANNER_ELIGIBLE"
        else:
            reason = rec.exclusion_reason or f"EXCLUDED_{rec.security_type}"
            data_status = reason

        rec.exclusion_reason = reason
        reasons[sym] = reason or data_status
        status_by_symbol[sym] = {
            "ticker": sym,
            "canonical_ticker": sym,
            "security_id": rec.provider_alias_egid or sym,
            "current_name": rec.display_name_if_known or "",
            "aliases": [a for a in dict.fromkeys(
                [sym, rec.display_name_if_known, rec.provider_alias_yahoo, rec.provider_alias_tradingview]
                + list(name_aliases.get(sym) or [])
            ) if a],
            "exchange": "EGX",
            "instrument_type": rec.security_type,
            "security_type": rec.security_type,
            "data_status": data_status,
            "exclusion_reason": reasons[sym],
            "eligibility_reason": reasons[sym],
            "mapped": rec.mapped,
            "is_tradable_candidate": rec.is_tradable_candidate,
            "daily_bars": count,
            "invalid_daily_bars": stats.get("invalid_daily_bars", 0),
            "latest_invalid_session": stats.get("latest_invalid_session"),
            "first_session": stats.get("first_session"),
            "provider": stats.get("provider"),
            "data_captured_at": stats.get("captured_at"),
            "data_state": stats.get("data_state"),
            "expected_session": stats.get("expected_session"),
            "daily_bars_lagging": stats.get("data_state") != "CURRENT",
            "source_timestamp": stats.get("latest_ts"),
            "latest_session": stats.get("latest_session"),
            "freshness_class": freshness,
            "yahoo_alias": rec.provider_alias_yahoo,
        }

    equity_n = int(built.get("EQUITY_UNIVERSE_TOTAL") or 0) or len(
        [r for r in records if r.security_type == EQUITY]
    )
    out = dict(built)
    out.update({
        "MAPPED_SYMBOLS": mapped,
        "UNMAPPED_SYMBOLS": unmapped,
        "DAILY_DATA_AVAILABLE": daily_available,
        "DAILY_DATA_UNAVAILABLE": daily_unavailable,
        "DAILY_DATA_STALE_EXPECTED": stale_expected,
        "DAILY_DATA_STALE_UNEXPECTED": stale_unexpected,
        "SCANNER_ELIGIBLE_SYMBOLS": scanner_eligible,
        "exclusion_reasons": reasons,
        "status_by_symbol": status_by_symbol,
        "min_scanner_bars": min_scanner_bars,
        # Backward-compatible Explorer keys
        "DATA_AVAILABLE_SYMBOLS": daily_available,
        "DATA_UNAVAILABLE_SYMBOLS": daily_unavailable,
        "data_eligible_count": len(daily_available),
        "scanner_candidate_count": len(scanner_eligible),
        "universe_total": int(built.get("UNIVERSE_TOTAL") or len(records)),
    })
    out["MAPPED_SYMBOLS_COUNT"] = len(mapped)
    out["UNMAPPED_SYMBOLS_COUNT"] = len(unmapped)
    _ = equity_n
    return out
