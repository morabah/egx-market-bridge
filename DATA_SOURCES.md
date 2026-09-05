# Data Sources

Open-source code is **not** a license to redistribute or treat exchange data as free for any purpose. Respect each upstream provider's terms of use.

## Source roles

| Need | Preferred sources | Notes |
|---|---|---|
| Intraday OHLCV | Licensed EGID → TradingView-compatible → borsa → Yahoo | Yahoo EGX intraday is often weak/daily-like |
| Daily OHLCV | EGID (if available) → Yahoo → TradingView | Yahoo EGX daily is the most reliable free path tested here |
| Quote fallback | Same as above | Always keep provider + timestamp |
| Depth / trades / bid-ask | Licensed EGID (or other verified licensed feed) | Otherwise **UNAVAILABLE** — never inferred |
| Universe | borsa catalog / investor-egx import / seed list | Do not claim full EGX coverage without verification |
| Fundamentals | Optional investor-egx import | Not official EGX/FRA filings |
| Official corporate facts | EGX / FRA / company IR (future layer) | Outside collector core in v0.3 |

## Delay / freshness

- A vendor calling itself “live” is insufficient. Classification uses **actual timestamps** when present.
- Default classes: LIVE ≤15s, FRESH ≤120s, DELAYED ≤20m, else STALE; UNKNOWN if no timestamp.
- Delayed daily bars can be excellent for research scanners and unsuitable for BUY-NOW timing.

## What remains unavailable without a license

- True Level-2 depth
- Time & sales / trade prints from EGID
- Guaranteed real-time bid/ask
- Execution-quality timestamps

When unavailable, handoffs mark fields `UNAVAILABLE` and list `missing_execution_fields`.
