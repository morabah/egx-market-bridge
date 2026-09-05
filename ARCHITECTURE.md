# Architecture — EGX Market Bridge v0.7.0

```text
                     Provider Manager
                            |
    +-----------+-----------+-----------+-----------+
    |           |           |           |           |
TradingView   Yahoo       Borsa    investor-egx   EGID
 (optional)  (yfinance)  (HTTP)    (universe)   (optional)
    |           |           |           |           |
intraday     daily/quote  quotes    discovery   depth/trades
 OHLCV        fallback    catalog   fundamentals  if licensed
    |           |           |           |           |
    +-----------+-----------+-----------+-----------+
                            |
                   Normalization + Symbol Registry
                            |
                   Freshness / Conflict / Quality
                            |
                         SQLite + raw/
                            |
              +-------------+-------------+
              |             |             |
           Scanner      Handoffs      Dashboard
```

## Design rules

1. **Providers are adapters.** App logic never hardcodes one upstream schema.
2. **EGID is optional.** HTTP 401/403 ⇒ `AUTH_REQUIRED` / LICENSE REQUIRED.
3. **Provenance is mandatory.** Every quote/candle stores provider + timestamps.
4. **No silent averaging** of conflicting cross-source values.
5. **Research ≠ execution quality.** Delayed daily data can score high for research and low for execution.
6. **Depth / time & sales are never fabricated** from candles.

## Package layout

```text
egxbridge/
  providers/     base, egid, yahoo, tradingview, borsa, investor_egx, manager
  symbols.py     canonical registry
  freshness.py   LIVE/FRESH/DELAYED/STALE/UNKNOWN
  conflicts.py   reconciliation
  quality.py     research/execution scores
  db.py          SQLite
  scanner.py     defensible candle metrics
  collector.py   orchestration
  normalize.py   legacy EGID field picking (preserved)
  provider.py    legacy EGID Swagger client (preserved)
  swagger.py     Swagger discovery (preserved)
```

The collector remains read-only transport/normalization. It does not make trading decisions.


## Forward validation and Funnel 2.8

BRIDGE = FACTS + SNAPSHOTS + VALIDATION. SCHEDULE LLM = TACTICAL / NEWS / MARKET INTERPRETATION. FUNNEL v2.8 LLM = ECONOMIC / EXPECTATIONS / VALUATION REASONING. WEEKLY LLM = VALIDATION INTERPRETATION + CHANGE PROPOSALS. USER = FINAL CAPITAL DECISION.

`analysis.forward_validation` owns enrollment and descriptive reports. Existing `schedule.identity` owns canonical identity; existing `schedule.outcomes` owns both selected and full-universe outcome arithmetic; `AnalysisStore` owns environment-scoped immutable persistence. `funnel.schema` describes imported LLM judgments, and the exact master prompt remains a Markdown asset. `ui.forward_validation` renders these owners and invokes their existing workflow actions.

Frozen source rows, append-only LLM classifications, mutable maturity outcomes and later Weekly event reviews are separate records. Legacy outcomes cannot become a new T0 sample, nor can old Funnel stages prove completion of an archived/new-version run. No scoring implementation or rule optimizer was added.

See [Forward validation contract](docs/FORWARD_VALIDATION.md) for table ownership, formulas, chronology, cohorts, rule/change controls and limitations.
