# Troubleshooting

## EGID returns HTTP 401 / 403

**Expected without a license.** Probe/dashboard will show **LICENSE/AUTH REQUIRED**.  
Obtain an official EGID token, set `EGID_TOKEN`, optionally `provider_mode: "feed"`, then re-run `python probe.py MASR`.

## Yahoo returns empty for a ticker

- Confirm alias in `symbol_aliases` (usually `SYMBOL.CA`).
- Some EGX tickers are missing on Yahoo.
- Try `COMI` first as a known working smoke test.

## TradingView provider status UNAVAILABLE

Optional dependency missing. Install one of:

```bash
pip install tradingview-datafeed
```

Then re-probe. If still failing, symbol mapping or anonymous limits may apply.

## Borsa disabled / errors

Enable only with your own instance:

```json
"enabled_providers": { "borsa": true },
"borsa_base_url": "http://localhost:8000"
```

Do not overload public demo servers.

## Conflicts in dashboard

Material cross-source disagreements are stored in SQLite `data_conflicts` and shown under **Source Conflicts**. Values are **not** averaged.

## Dashboard shows empty prices

1. Run `python probe.py --all`
2. Run `python collect.py --once`
3. Check Yahoo section of probe for `"ok": true`
4. Inspect `output/chatgpt_handoff.json` warnings

## pytest

```bash
pytest                 # unit tests only
pytest -m integration  # optional live Yahoo
```

## Rate limits

Increase `poll_seconds` and `rate_limit_seconds` if providers throttle you. Circuit breakers temporarily skip repeatedly failing providers.
