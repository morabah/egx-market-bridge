"""Canonical EGX universe builder and security-type hygiene."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import re

from egxbridge.freshness import classify_freshness


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    is_active_if_known: bool | None = True
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
        if not self.last_verified_at:
            self.last_verified_at = _now()
        self.is_tradable_candidate = (
            self.security_type == EQUITY and self.is_active_if_known is not False and self.mapped
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _reference_symbols() -> list[str]:
    return _symbols_from_payload(_load_json(REF_UNIVERSE) or [])


def _provider_universe() -> tuple[list[str], str]:
    try:
        from egxbridge.config import Settings
        settings = Settings.load(HERE / "config.json")
    except Exception:
        settings = None

    if settings and settings.investor_egx_universe_path:
        p = Path(settings.investor_egx_universe_path)
        if not p.is_absolute():
            p = HERE / p
        syms = _symbols_from_payload(_load_json(p) or [])
        if syms:
            return syms, "investor_egx_universe_path"

    try:
        from egxbridge.providers.investor_egx import InvestorEGXProvider
        kwargs: dict[str, Any] = {"enabled": True}
        if settings:
            kwargs["universe_path"] = settings.investor_egx_universe_path or ""
            kwargs["sqlite_path"] = settings.investor_egx_sqlite_path or ""
        prov = InvestorEGXProvider(**kwargs)
        rows = prov.get_universe()
        syms = [str(r.get("canonical")).upper() for r in rows if r.get("canonical")]
        src = "investor_egx"
        if syms and all(r.get("source") == "seed" for r in rows if isinstance(r, dict)):
            src = "investor_egx_seed"
        if syms:
            return syms, src
    except Exception:
        pass

    uni = HERE / "output" / "universe.json"
    syms = _symbols_from_payload(_load_json(uni) or [])
    if syms:
        return syms, "output/universe.json"
    return [], "none"


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


def _config_symbols() -> tuple[list[str], dict[str, dict[str, str]]]:
    aliases: dict[str, dict[str, str]] = {}
    try:
        from egxbridge.config import Settings
        settings = Settings.load(HERE / "config.json")
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
) -> dict[str, Any]:
    """Build canonical EGX records. Never hard-codes a 10-name list."""
    type_map = load_security_type_map()
    cfg_syms, cfg_aliases = _config_symbols()
    sources: list[str] = []

    if explicit:
        symbols = sorted({s.upper().strip() for s in explicit if s and str(s).strip()})
        source = "explicit"
        provider_syms: list[str] = []
        ref: list[str] = []
    else:
        provider_syms, psrc = _provider_universe()
        ref = _reference_symbols()
        db_syms = _db_symbols(db)
        symbols = sorted(set(ref) | set(provider_syms) | set(cfg_syms) | set(db_syms))
        source = f"{psrc}+reference_registry+config+db"
        sources = [psrc, "egx_reference_universe", "config", "db"]

    records: list[UniverseRecord] = []
    by_type: dict[str, int] = {t: 0 for t in sorted(SECURITY_TYPES)}

    for sym in symbols:
        al = dict(_registry_aliases(sym))
        al.update(cfg_aliases.get(sym) or {})
        rec = UniverseRecord(
            canonical_symbol=sym,
            display_name_if_known="",
            provider_alias_yahoo=al.get("yahoo") or yahoo_alias(sym),
            provider_alias_tradingview=al.get("tradingview") or tradingview_alias(sym),
            provider_alias_egid=al.get("egid") or al.get("borsa") or sym,
            provider_alias_other=al.get("borsa") or "",
            security_type=classify_security_type(sym, explicit_map=type_map),
            sector_if_known="",
            industry_if_known="",
            is_active_if_known=True,
            source=source,
            last_verified_at=_now(),
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


def _daily_stats(db, symbol: str) -> dict[str, Any]:
    if db is None:
        return {"count": 0, "latest_session": None, "latest_ts": None, "provider": None}
    try:
        row = db._conn.execute(
            """SELECT COUNT(*) AS c FROM candles WHERE symbol=? AND interval='1d'""",
            (symbol.upper(),),
        ).fetchone()
        count = int(row["c"] if hasattr(row, "keys") else row[0])
    except Exception:
        count = 0
    latest_session = None
    latest_ts = None
    provider = None
    try:
        rows = db.fetch_candles(symbol, "1d", limit=5)
        if rows:
            # fetch_candles is DESC
            latest = rows[0]
            latest_session = latest.get("session_date")
            latest_ts = latest.get("normalized_utc_timestamp") or latest.get("timestamp")
            provider = latest.get("provider")
            if not latest_session and latest_ts:
                latest_session = str(latest_ts)[:10]
    except Exception:
        pass
    return {
        "count": count,
        "latest_session": latest_session,
        "latest_ts": latest_ts,
        "provider": provider,
    }


def assess_universe_coverage(
    built: dict[str, Any],
    db=None,
    *,
    min_scanner_bars: int = 20,
    stock_explorer_only: bool = True,
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

        stats = _daily_stats(db, sym)
        count = int(stats.get("count") or 0)
        freshness = "UNKNOWN"
        if stats.get("latest_ts"):
            freshness, _ = classify_freshness(stats["latest_ts"])

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
                reason = "DAILY_DATA_UNAVAILABLE"
                data_status = "DAILY_DATA_UNAVAILABLE"
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
            "security_type": rec.security_type,
            "data_status": data_status,
            "exclusion_reason": reasons[sym],
            "mapped": rec.mapped,
            "is_tradable_candidate": rec.is_tradable_candidate,
            "daily_bars": count,
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
