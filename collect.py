#!/usr/bin/env python3
"""EGX Market Bridge collector CLI."""
from pathlib import Path
import argparse
import json
from egxbridge.config import Settings
from egxbridge.collector import run_once, loop, refresh_universe

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(
        description="EGX Market Bridge v0.3 hybrid collector (read-only, no order placement)."
    )
    p.add_argument("--config", default=str(HERE / "config.json"))
    p.add_argument("--once", action="store_true", help="Collect one snapshot and exit")
    p.add_argument("--symbol", help="Collect a single canonical symbol (e.g. MASR)")
    p.add_argument("--provider", help="Restrict to one provider (yahoo|tradingview|egid|borsa|investor_egx)")
    p.add_argument("--interval", help="Candle interval override (e.g. 5m, 1d). Repeatable via comma list.")
    p.add_argument("--refresh-universe", action="store_true", help="Refresh EGX universe discovery and exit")
    args = p.parse_args()
    settings = Settings.load(args.config)

    if args.refresh_universe:
        print(json.dumps(refresh_universe(settings, HERE), ensure_ascii=False, indent=2, default=str))
        return

    intervals = None
    if args.interval:
        intervals = [x.strip() for x in args.interval.split(",") if x.strip()]

    if args.once or args.symbol or args.provider or intervals:
        result = run_once(
            settings,
            HERE,
            symbol_filter=args.symbol,
            provider_filter=args.provider,
            intervals=intervals,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        loop(settings, HERE)


if __name__ == "__main__":
    main()
