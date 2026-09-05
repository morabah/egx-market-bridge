# Providers

## egid (preserved from v0.2)

- Swagger-discovered client for DelayedFeed / Feed.
- Capabilities: quote, candles, depth, trades, bid/ask (when authorized).
- Without `EGID_TOKEN`: expect HTTP 401 → status `AUTH_REQUIRED` / **LICENSE/AUTH REQUIRED**.
- This is not a crash.

## yahoo (yfinance)

- Primary free/public path for EGX **daily** OHLCV and quote-like last close.
- Symbol form: `TICKER.CA` via symbol registry.
- Treat as delayed. Do not use for execution timing.

## tradingview (optional)

- Backends: `tvDatafeed` or `TradeGlob` if installed.
- Used for intraday OHLCV when available.
- Anonymous mode may be limited; optional username/password via env.
- Never label REALTIME unless timestamp evidence supports LIVE/FRESH.

## borsa (optional HTTP)

- Client for [7ashraf/borsa](https://github.com/7ashraf/borsa) (MIT) self-hosted API.
- Disabled by default. Set `borsa_base_url` / `BORSA_BASE_URL` and enable in config.
- Useful for symbol catalog + quote fallback. Do not hammer public demos.

## investor_egx (optional adapter)

- Thin import layer inspired by [labib2002/investor-egx](https://github.com/labib2002/investor-egx) (MIT).
- Does **not** vendor that repository.
- Reads optional universe JSON or an external investor-egx SQLite path.
- Falls back to a small incomplete seed list.

## Adding a provider

1. Implement `MarketDataProvider` in `egxbridge/providers/`.
2. Declare `ProviderCapabilities`.
3. Register in `collector.build_manager`.
4. Add priority entries in config.
5. Add unit tests with mocks.
