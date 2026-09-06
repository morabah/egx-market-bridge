# EGX Market Bridge v0.7.1 — operational integrity

Application/workflow 0.7.1; data layer 0.3.1; scanner 0.5.1 / HEURISTIC_UNCALIBRATED; Funnel 2.8; CHATGPT_HANDOFF. This patch corrects timing and persistence, versions audit assets and adds CI. It introduces no scoring, ranking, identity, provider, decision or forward-validation redesign.

## Configured normal cash-session clock

All bands use Africa/Cairo, with an inclusive start and exclusive end:

| Phase | Clock band |
|---|---|
| PRE_OPEN | before 10:00 |
| CONTINUOUS_TRADING | 10:00–14:15 |
| CLOSING_AUCTION | 14:15–14:25 |
| TRADING_AT_LAST | 14:25–14:30 |
| POST_CLOSE | 14:30 onward |

Friday and Saturday are POST_CLOSE; Sunday is a possible normal session day. These are configured normal cash-market clock bands, not a live exchange calendar/feed. The app still does not guess holidays.

`completed_through()` is a calendar cutoff for available observed bars, not proof that a session occurred. At 14:29:59 Cairo it excludes today's bar; at 14:30:00 it permits it. Freshness uses the same exclusive close. Provider availability, data quality and freshness-age thresholds retain their existing semantics.

The pre-edit repository search for 14:20/14:30/14:45 and equivalent time tuples found 252 matching lines: nine operational lines in `session.py`/`freshness.py` and 243 historical output lines. Operational boundaries and their generated-label source were corrected. Previously generated handoff/acceptance packages and historical candle/market-observation timestamps were preserved. Tests using 14:25 and 14:40 retain their timestamps with corrected phase expectations. The new 14:45 test verifies POST_CLOSE; it is not a retained operational boundary.

## Valuation persistence and source precedence

The existing importer remains the owner. Valid normalized v2.8 `central_fv` supplies Central FV in project state, `valuation_history.json` and the existing `Fair Value` database reader. An existing/extracted `Blended Fair Value` compatibility slot is synchronized to the authoritative structured center. It is not another independently calculated value.

Precedence is valid normalized structured valuation, then legacy text extraction where no valid structured value exists, then the previous persisted value when no new value is supplied. A later prose-only stage cannot silently overwrite an existing valid structured center. The source disagreement is recorded instead. Normalized envelope fields override equivalent text aliases; invalid fields remain in the raw response and produce schema issues.

Also retain supplied `highest_credible_bull_fv`, `robust_fv_range`, `valuation_date`, `economic_terminal_value`, `expected_horizon_market_price` and `expected_return_spread`. No value is inferred. In particular, Expected Horizon Market Price never becomes Central FV.

Dates must be real `YYYY-MM-DD` dates for v2.8. A Central FV and a valid imported valuation date establish valuation status through the existing status function. A date may arrive in a later partial stage without rewriting the earlier FV's field availability. Missing dates and missing FV remain missing. Valuation existence does not establish Funnel completion or delta eligibility.

Each appended history record includes the available valuation fields, recorded/import time, framework, source kind (`STRUCTURED_FUNNEL_V28` or `LEGACY_TEXT_EXTRACTION`), hash, stage, declared research/market cutoff, field provenance, original legacy extraction and diagnostics. `fair_value` remains a compatibility field. Old history records are retained; an unreadable history is not silently replaced with an empty list.

When structured/prose values differ, `VALUATION_SOURCE_CONFLICT` records the structured value, legacy text value/raw text, chosen source and content hash. It is returned by the importer, saved in stage metadata/current summary/history and surfaced in UI import feedback. The import remains successful; the complete raw LLM response is unchanged.

Fields retain their individual import/start times, research/source and market cutoffs, version and hash. A stage updating another field does not relabel earlier field availability. Later judgments remain later evidence. Existing verified-stage/full-result completion checks remain the only completion authority.

## Audit assets and verification

See [prompt ownership](../prompts/README.md). Stage-12 audit assets are manually selected; no automatic audit packaging is added. Both master prompts and the historical v2.7 audit have frozen pre-edit hashes.

`python scripts/acceptance_v071.py` runs the configured offline pytest suite and synthetic checks in temporary ACCEPTANCE_TEST databases, never production tables. Results are labeled `SYNTHETIC_ACCEPTANCE_NOT_PRODUCTION` under `output/acceptance/v071/`:

- `operational_integrity_acceptance.md` and `.json`
- `session_boundary_report.json`
- `funnel_v28_valuation_persistence_report.json`
- `stage12_versioning_report.json`
- `frozen_source_hashes.json`
- `pytest.txt`

The hash baseline is `tests/fixtures/v071_frozen_sources.json`. The four frozen scorer/identity sources must remain byte-identical. Existing fixed-fixture ranking and forward-validation regressions remain in the full suite. CI uses Python 3.11/3.12 and respects `pytest.ini`'s exclusion of live-network integration tests.

No LICENSE was present when this patch was prepared. `LICENSE_DECISION_REQUIRED = YES`; the owner must select it. The patch does not choose or grant a license.
