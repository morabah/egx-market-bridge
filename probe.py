#!/usr/bin/env python3
"""Multi-provider probe for EGX Market Bridge v0.3."""
from pathlib import Path
import argparse
import json
from egxbridge.config import Settings
from egxbridge.symbols import SymbolRegistry
from egxbridge.collector import build_manager
from egxbridge.freshness import classify_freshness, FreshnessThresholds
from egxbridge.storage import now_iso

HERE = Path(__file__).resolve().parent


def enrich_freshness(probe: dict, settings: Settings) -> dict:
    th = FreshnessThresholds(
        settings.freshness.live_seconds,
        settings.freshness.fresh_seconds,
        settings.freshness.delayed_seconds,
    )
    capture = now_iso()
    for key, val in list(probe.items()):
        if isinstance(val, dict) and val.get("latest_timestamp"):
            fclass, fsec = classify_freshness(val["latest_timestamp"], capture, th)
            val["freshness"] = fclass
            val["freshness_seconds"] = fsec
    return probe


def main():
    p = argparse.ArgumentParser(description="Probe all configured market-data providers.")
    p.add_argument("symbol", nargs="?", default="MASR", help="Canonical EGX symbol")
    p.add_argument("--all", action="store_true", help="Probe every enabled provider")
    p.add_argument("--config", default=str(HERE / "config.json"))
    args = p.parse_args()

    settings = Settings.load(args.config)
    registry = SymbolRegistry.from_config({"symbol_aliases": settings.symbol_aliases})
    manager = build_manager(settings, registry)
    symbol = registry.canonicalize(args.symbol)

    if args.all or True:
        # Always multi-provider in v0.3; --all kept for CLI compatibility
        results = manager.probe_all(symbol)
        for name, probe in results.items():
            results[name] = enrich_freshness(probe, settings)

    out = {
        "generated_at": now_iso(),
        "symbol": symbol,
        "aliases": registry.get(symbol).aliases,
        "providers": results,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    outdir = HERE / "output"
    outdir.mkdir(exist_ok=True)
    (outdir / "probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("\nSaved output/probe.json")


if __name__ == "__main__":
    main()
