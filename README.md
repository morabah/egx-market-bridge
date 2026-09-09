# EGX Market Bridge v0.7.1 — Funnel v2.8 and Forward Validation Lab

A **read-only** Egyptian Exchange market-data aggregation layer plus **ChatGPT handoff** analysis workflows (no paid LLM API required):

**Market Bridge evidence → (A) Full Funnel value analysis | (B) Next-day Explorer**

It does **not** place orders, log into Thndr, scrape authenticated broker pages, store broker passwords, or bypass provider licensing.

> **Source-available repository; the owner has not selected a software license.** Upstream providers have their own terms. Delayed/public data is for research, not execution timing, unless a licensed live feed is configured and verified.

## What changed in v0.7.1

Application/workflow **0.7.1** · Funnel **2.8** · Scanner **0.5.1 / HEURISTIC_UNCALIBRATED** · Data layer **0.3.1** · AI mode **CHATGPT_HANDOFF**.

- Corrected configured cash-session boundaries and the completed-session cutoff.
- Valid normalized Funnel v2.8 valuation fields now feed valuation history, date/status and existing valuation readers. Structured/prose disagreements remain visible as `VALUATION_SOURCE_CONFLICT`.
- Archived the unchanged v2.7 Stage-12 audit and added a separate v2.8-compatible audit. See [asset ownership](prompts/README.md).
- Added offline fixture CI for Python 3.11/3.12 and `python scripts/acceptance_v071.py`.

See [operational integrity](docs/OPERATIONAL_INTEGRITY.md) for precedence, provenance, clock bands and acceptance outputs. The evidence/LLM/user responsibilities and forward-validation architecture remain unchanged.

## What changed in v0.7.0

Application 0.7.0 · Funnel Framework 2.8 · Scanner 0.5.1 / HEURISTIC_UNCALIBRATED · AI Mode CHATGPT_HANDOFF.

- Automatic immutable T0 snapshots and full eligible-universe retention on Explorer runs.
- A first-class **Forward Validation Lab** with +1/+2/+5/+10/+20 session returns, MFE/MAE, supplied friction, expectations/FV/setup comparisons and missed-winner audits.
- Partial v2.8 structured imports with exact LLM provenance; historical v2.7 runs remain preserved. New full runs use the uploaded v2.8 master.
- Weekly X-Ray owns validation interpretation and stored change proposals. Rules are never retuned or activated automatically.
- Production validation begins at the actual first new Explorer enrollment. Historical discoveries and synthetic acceptance examples are excluded.

The app prepares evidence and tracks results. It does not make the final investment decision. Scanner weights and canonical identity remain unchanged.

See [the forward-validation contract](docs/FORWARD_VALIDATION.md) for responsibilities, timing rules, data limitations, CLI commands and acceptance outputs.

## What changed in v0.4

- Dual workflows: **Full Funnel** (company/value) and **Next-day Explorer** (tactical discovery).
- Default AI mode: **CHATGPT_HANDOFF** only — no `OPENAI_API_KEY` / paid API required.
- Funnel prompt `EGX_STOCK_ANALYSIS_FUNNEL_v2.7.md` preserved as authoritative LLM reasoning (not reimplemented in Python).
- Stage-by-stage / full / delta Funnel handoff ZIPs + result import with append-only corrections.
- Explorer handoff with five schedule context files + Funnel status linkage (context only; never mutates Fair Value).
- Dashboard section **Analysis Workflows**.
- Market-data provider layer remains **v0.3.1-compatible**.

## What changed in v0.3

- Multi-provider architecture: **Yahoo**, optional **TradingView** (tvDatafeed/TradeGlob), optional **borsa** HTTP, optional **investor-egx** universe import, plus preserved **EGID** (licensed/optional).
- Canonical symbol registry (`MASR` ↔ `MASR.CA` ↔ `EGX:MASR`).
- SQLite persistence with provenance on every observation.
- Freshness classes: LIVE / FRESH / DELAYED / STALE / UNKNOWN.
- Explicit conflict engine (never averages conflicting prices).
- Separate **research** vs **execution** data-quality scores.
- Upgraded probe, collector CLI, Streamlit dashboard, scanner handoff.

EGID DelayedFeed returning HTTP 401 without credentials is **expected** and reported as **LICENSE/AUTH REQUIRED**, not an application crash.

## Install

```bash
cd egx_market_bridge
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Optional TradingView backend (pick one):

```bash
pip install tradingview-datafeed
# or: pip install git+https://github.com/rongardF/tvdatafeed.git
```

Copy `.env.example` → `.env` if you have optional tokens/credentials.

## First commands

```bash
# Probe every provider for one symbol
python probe.py MASR
python probe.py --all

# One hybrid snapshot (Yahoo + any available providers)
python collect.py --once

# Single symbol / single provider
python collect.py --symbol COMI --provider yahoo --once
python collect.py --provider tradingview --symbol MASR --interval 5m --once

# Universe discovery (seed / borsa / investor-egx import)
python collect.py --refresh-universe

# Continuous collection (respects poll_seconds; default 120s)
python collect.py

# Dashboard
streamlit run dashboard.py
```

Or double-click `run_mac.command` / `run_windows.bat`.

## Using the dashboard

Start on **Daily Operator**. Its **Next** panel names the current action and explains whether to continue in the app or in ChatGPT.

1. **Update data and scan.** This checks all known equities and builds the shortlist. A partial collection stays clearly marked and can continue to the next step.
2. **Prepare ChatGPT ZIP.** The app checks the scan against the expected completed session and the latest collection before packaging it.
3. **Download ZIP for ChatGPT.** Check the data date, coverage and collection time beside the download. Attach the ZIP in ChatGPT and save each analysis reply as `.md`, `.txt` or `.json`.
4. **Import saved ChatGPT replies.** Import each reply on Daily Operator or **Schedule Analysis Center**. The form advances to the next missing job and clears the previous upload.

The home page groups the shortlist, imported analysis and outcome tracking into tabs. The full workflow checklist, optional tools and technical diagnostics are collapsed until needed.

Manual collection retries are under **Data details and manual refresh**. Finishing a partial collection does not keep sending you back to Scan. A newly completed session requires a new check; a newer scan, collection or intraday refresh makes the old ZIP out of date. Company Funnel analysis and future outcome tracking remain available in the full workflow.

Daily collection stops starting provider requests after a five-minute budget; requests already in flight finish under their provider timeouts. Every skipped company remains in the report as a data gap.

The [EGXpilot public bulk API](https://www.egxpilot.com/developers.html) adds a supplementary market snapshot with one request per collection, bounded timeout and no automatic retry. It is included in `common/supplemental_market_snapshot.json`. Per-record `CreatedAt` is preserved separately from batch `updatedAt` and collection time. It is not a verified exchange trade timestamp. Inconsistent OHLC or percentage changes, missing/future timestamps and duplicate symbols are quarantined. These snapshots never replace daily candles, history or scanner scores. Set `enabled_providers.egxpilot` to `false` to disable the source. Licensed [EGID](https://ticker.egidegypt.com/index.html) remains supported; the live check returned HTTP 401 without a licensed token.

## Collection coverage and download status

**Scan market** reconciles the full known equity catalog before collecting daily data. Discovery merges the public TradingView EGX catalog, configured Borsa/import sources, the reference registry, configuration and stored symbols. Successful discovery is cached for 24 hours; failures retain the last-good catalog and wait 15 minutes before another automatic attempt. `python collect.py --refresh-universe` explicitly refreshes discovery. Catalog refresh is a single bounded request per source; truncated TradingView catalogs are rejected.

Known equities remain visible when prices are missing. Retained historical names are not assumed active, and provider catalogs do not establish official exchange completeness. Indices, funds and other known non-equities remain listed with their exclusions. The configured session calendar still excludes Friday/Saturday but does not know exchange holidays.

Daily freshness compares each company with the expected completed session. In-progress bars are not final closes. History counts distinct sessions from the selected provider; short histories receive a full history request, while sufficient histories use an overlap window. Current sufficient histories are reused. Recent provider corrections are audited and applied; older captures cannot overwrite newer ones.

Transient daily failures get at most two attempts per provider, with rate limiting and separate provider circuits. Missing symbols are not immediately retried and do not disable collection for other companies. Stale/failed requests have a 15-minute retry cooldown, recorded as `retry_after`; a new expected session or explicit `--refresh` bypasses it. SQLite workers use separate connections and commit each returned batch together. TradingView socket history requests are serialized and close after a 30-second deadline, including streams that only emit heartbeats.

The **Collection report** on Daily Operator lists every requested company, status, source, history range, collection start/end, original data capture time, request attempts and errors. Its JSON is saved beside the market database as `daily_collection_report.json`. Cache reuse preserves original data timestamps. Failures and partial coverage are reported rather than labeled a successful full refresh.

Every new evidence ZIP includes `DATA_STAMP.json` and `DATA_STAMP.md`, with daily coverage and per-company sessions/capture times. Downloads show contents, file size, package time, data state and intraday age at download time. The newest bar's delay is measured against package time, separately from fetch time. Preparing a schedule ZIP packages existing evidence; use the explicit Intraday refresh to obtain newer candles. Downloading an existing ZIP preserves its original evidence and timestamps. ZIP replacement is atomic.

The plain collector CLI remains an explicitly continuous mode until Ctrl+C, with the configured pause **after** each run; `--once` exits after one run. `session_only` is honored in continuous mode. The dashboard performs collection on request; it does not promise a continuously live feed.

## Configure

Edit `config.json` (see `config.example.json`):

- `symbols` / `focus_symbols`
- `enabled_providers`
- `provider_priority` (per capability)
- `symbol_aliases`
- `freshness` thresholds
- `database_path`, `output_dir`, `raw_retention_days`
- `borsa_base_url` (optional self-hosted borsa)

Secrets via environment / `.env` only:

- `EGID_TOKEN`
- `TRADINGVIEW_USERNAME` / `TRADINGVIEW_PASSWORD`
- `BORSA_BASE_URL`

## Outputs

- `output/chatgpt_handoff.json` / `.md` — compact research handoff
- `output/scanner_handoff.json` — scanner-oriented fields (no BUY labels)
- `output/<SYMBOL>/quote.json`, `candles_*.csv`, …
- `output/raw/<provider>/<date>/<symbol>/…`
- `output/egx_bridge.sqlite` — normalized tables + conflicts + provider status
- `output/probe.json`

## Tests

```bash
pytest
# optional live network tests:
pytest -m integration
```

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DATA_SOURCES.md](DATA_SOURCES.md)
- [PROVIDERS.md](PROVIDERS.md)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Privacy / safety

Read-only. No broker automation. No order placement. No embedded passwords.
# Daily data and download audit corrections

Overnight intraday collection retains valid bars from earlier sessions and marks
them historical. The default request set is 1m, 5m and 15m, with at most one
immediate retry for transient failures. Empty responses and rate limits receive
no immediate retry. Per-bar provider and capture timestamps survive export.

OHLC prices must be finite, positive and consistent with their high/low bounds;
volume must be nonnegative when supplied. Invalid source corrections cannot
overwrite good cached rows. Rejected observations stay in the audit exports,
and indicators use the continuous valid history after the last rejected session.
This validates the collector's OHLCV contract; it does not independently certify
exchange prices or reconcile different upstream price conventions.

Daily bars qualify as completed only when their capture timestamp proves they were
collected after that session closed. Legacy pre-close captures remain provisional
until refetched, even on later days. Missing capture provenance is unconfirmed
unless the source explicitly marked the bar final. The latest completed session
uses the configured Cairo market hours; an official holiday calendar is still unavailable.

The current scanner and market breadth require the expected completed session and
enough history from one provider. All other known companies remain in the exported
registry with stale, missing, or insufficient-history reasons. Provider selection
uses the freshest completed session, then history length, with Yahoo breaking ties.

Downloads include the collection report, its start/end times, actual network
attempts and cache/deferred results, every selected intraday target's diagnostics,
and available completed daily histories. Reports are frozen from the same database
at package creation; packaging makes no network requests. Intraday `NOT_REQUESTED`
and circuit `SKIPPED` outcomes are separate from attempted failures. Cached bars
keep their source dates and do not become current movers through repackaging.

Custom-output and nonproduction Explorer runs keep their ZIPs outside the production
download directory and do not publish the dashboard's latest-run pointer. The dashboard
selects the newest production snapshot by generation time, including scans with zero
candidates; acceptance packages are never a fallback. Schedule exports and intraday
refreshes recheck daily evidence, expected session, reconciled eligibility, and newer
collection reports. If needed, they rebuild the Explorer snapshot once from the local
database before proceeding. This rebuild does not fetch market data. A database is
required to repair missing or outdated evidence.

Combined downloads include daily source bars, rejected observations, per-company
daily status and the frozen collection report. Cached ticker summaries select the
newest source timestamp across intervals. Cache availability does not reset the
timeout/rate-limit circuit breaker, and interval diagnostics preserve each provider's
attempt count, outcome and start/end attempt timestamps.

Single-candle high, low and volume are exported as bar fields. Session-volume
summaries use one session and deduplicated bar volumes, disclose the observed
window, and leave unknown or cumulative volume unaggregated. Full-session coverage
and official exchange listing completeness are not inferred from the local cache.
