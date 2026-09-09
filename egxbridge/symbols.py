from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import re
import unicodedata


NAME_ALIASES_PATH = Path(__file__).resolve().parent / "data" / "egx_name_aliases.json"


def normalize_issuer_name(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return " ".join(text.split())


def load_name_aliases(path: Path | None = None) -> dict[str, list[str]]:
    p = path or NAME_ALIASES_PATH
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, list[str]] = {}
    if not isinstance(data, dict):
        return {}
    for ticker, names in data.items():
        key = str(ticker).upper().strip()
        rows = names if isinstance(names, list) else [names]
        out[key] = [str(n) for n in rows if n]
    return out


def build_name_index(extra: dict[str, list[str]] | None = None) -> dict[str, str]:
    index: dict[str, str] = {}
    mapping = load_name_aliases()
    if extra:
        for k, names in extra.items():
            mapping.setdefault(k.upper(), [])
            mapping[k.upper()] = list(dict.fromkeys((mapping.get(k.upper()) or []) + list(names or [])))
    for ticker, names in mapping.items():
        t = ticker.upper().strip()
        index[t] = t
        index[normalize_issuer_name(t)] = t
        for name in names:
            n = normalize_issuer_name(name)
            if n:
                index[n] = t
            compact = n.replace(" ", "")
            if compact:
                index[compact] = t
    return index


_NAME_INDEX = build_name_index()


def canonicalize_any(value: str | None, *, extra_index: dict[str, str] | None = None) -> str:
    """Resolve a ticker or issuer name to one canonical EGX ticker."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    upper = raw.upper()
    if upper.endswith(".CA"):
        upper = upper[:-3]
    if upper.startswith("EGX:"):
        upper = upper[4:]
    index = dict(_NAME_INDEX)
    if extra_index:
        index.update(extra_index)
    if upper in index:
        return index[upper]
    named = normalize_issuer_name(raw)
    if named in index:
        return index[named]
    compact = named.replace(" ", "")
    if compact in index:
        return index[compact]
    return upper


DEFAULT_ALIASES: dict[str, dict[str, str]] = {
    "MASR": {"yahoo": "MASR.CA", "tradingview": "EGX:MASR", "egid": "MASR", "borsa": "MASR"},
    "COMI": {"yahoo": "COMI.CA", "tradingview": "EGX:COMI", "egid": "COMI", "borsa": "COMI"},
    "RAYA": {"yahoo": "RAYA.CA", "tradingview": "EGX:RAYA", "egid": "RAYA", "borsa": "RAYA"},
    "LUTS": {"yahoo": "LUTS.CA", "tradingview": "EGX:LUTS", "egid": "LUTS", "borsa": "LUTS"},
    "KASABF": {"yahoo": "KASABF.CA", "tradingview": "EGX:KASABF", "egid": "KASABF", "borsa": "KASABF"},
    "HRHO": {"yahoo": "HRHO.CA", "tradingview": "EGX:HRHO", "egid": "HRHO", "borsa": "HRHO"},
    "ETEL": {"yahoo": "ETEL.CA", "tradingview": "EGX:ETEL", "egid": "ETEL", "borsa": "ETEL"},
}


@dataclass
class SymbolRecord:
    canonical: str
    name: str = ""
    aliases: dict[str, str] = field(default_factory=dict)
    sector: str = ""
    active: bool = True

    def alias(self, provider: str) -> str:
        if provider in self.aliases:
            return self.aliases[provider]
        # Sensible defaults
        c = self.canonical.upper()
        if provider == "yahoo":
            return f"{c}.CA"
        if provider == "tradingview":
            return f"EGX:{c}"
        return c


class SymbolRegistry:
    """Single place for canonical EGX symbol ↔ provider alias mapping."""

    def __init__(self, aliases: dict[str, dict[str, str]] | None = None):
        self._symbols: dict[str, SymbolRecord] = {}
        seed = dict(DEFAULT_ALIASES)
        if aliases:
            for k, v in aliases.items():
                seed.setdefault(k.upper(), {}).update(v)
        for canon, al in seed.items():
            self.register(canon, aliases=al)

    def register(self, canonical: str, name: str = "", aliases: dict[str, str] | None = None, sector: str = ""):
        c = canonical.upper().strip()
        existing = self._symbols.get(c)
        merged = dict(existing.aliases) if existing else {}
        if aliases:
            merged.update({k: str(v) for k, v in aliases.items()})
        self._symbols[c] = SymbolRecord(
            canonical=c,
            name=name or (existing.name if existing else ""),
            aliases=merged,
            sector=sector or (existing.sector if existing else ""),
        )

    def canonicalize(self, symbol: str) -> str:
        resolved = canonicalize_any(symbol)
        if resolved in self._symbols:
            return resolved
        s = (resolved or str(symbol or "")).upper().strip()
        if s in self._symbols:
            return s
        if s.endswith(".CA"):
            return s[:-3]
        if s.startswith("EGX:"):
            return s[4:]
        for rec in self._symbols.values():
            for a in rec.aliases.values():
                if a.upper() == s or a.upper().endswith(":" + s) or a.upper() == s + ".CA":
                    return rec.canonical
            if rec.name and canonicalize_any(rec.name) == resolved:
                return rec.canonical
        return s or resolved

    def to_provider(self, symbol: str, provider: str) -> str:
        c = self.canonicalize(symbol)
        rec = self._symbols.get(c)
        if rec:
            return rec.alias(provider)
        if provider == "yahoo":
            return f"{c}.CA"
        if provider == "tradingview":
            return f"EGX:{c}"
        return c

    def get(self, symbol: str) -> SymbolRecord:
        c = self.canonicalize(symbol)
        if c not in self._symbols:
            self.register(c)
        return self._symbols[c]

    def all_canonical(self) -> list[str]:
        return sorted(self._symbols.keys())

    def to_dict(self) -> dict[str, Any]:
        return {
            k: {"name": v.name, "aliases": v.aliases, "sector": v.sector, "active": v.active}
            for k, v in self._symbols.items()
        }

    @classmethod
    def from_config(cls, cfg: dict[str, Any] | None) -> "SymbolRegistry":
        aliases = (cfg or {}).get("symbol_aliases") or {}
        # Normalize nested structure
        norm: dict[str, dict[str, str]] = {}
        for k, v in aliases.items():
            if isinstance(v, dict):
                norm[k.upper()] = {str(pk): str(pv) for pk, pv in v.items()}
            elif isinstance(v, str):
                norm[k.upper()] = {"yahoo": v}
        return cls(aliases=norm)

    def load_json(self, path: Path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for k, v in data.items():
            if isinstance(v, dict):
                self.register(k, name=v.get("name", ""), aliases=v.get("aliases", {}), sector=v.get("sector", ""))
