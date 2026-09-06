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

1. **Scan and review.** Run the suggested market scan, then open **Explorer Candidates** to search the shortlist and inspect a company. Extra filters and source details are available when needed.
2. **Send evidence to ChatGPT.** Prepare and download the package. Attach the ZIP in ChatGPT, then save each analysis reply as `.md`, `.txt` or `.json`.
3. **Import and review company analysis.** Import each saved reply on Daily Operator or **Schedule Analysis Center**. The form advances to the next missing job and clears the previous upload. For company valuation, use **Analysis Workflows** to prepare a Funnel stage, full analysis or eligible update, then import its reply there.
4. **Track what happened.** After future market sessions, update outcomes and use **Signal Outcomes** or **Forward Validation Lab**. Select a trading-session horizon to compare matching returns and price excursions. Pending or unavailable outcomes remain missing, never zero.

The home page groups the shortlist, imported analysis and outcome tracking into tabs. The full workflow checklist, optional tools and technical diagnostics are collapsed until needed.

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
