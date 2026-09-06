# EGX Market Bridge v0.7.1 — forward-validation contract

Application/workflow **0.7.1**, Funnel prompt **2.8**, scanner scoring **0.5.1 / HEURISTIC_UNCALIBRATED**, handoff schema **1.1**, market-data schema **0.3.1**, AI mode **CHATGPT_HANDOFF** are separate versions.

The app prepares evidence and tracks results. It does not make the final investment decision.

## Responsibility matrix

| Owner | Responsibility |
|---|---|
| Bridge | Provider data/provenance, deterministic OHLCV metrics, breadth, eligible universe, canonical identity, immutable snapshots, future session returns, MFE/MAE, supplied-cost arithmetic, target/stop arithmetic, sample counts and descriptive reports |
| Schedule LLM | Tactical, news and macro interpretation; promotion/downgrade; selective Funnel routing |
| Funnel v2.8 LLM | Economic quality, valuation, expectations burden/gap/revisions, catalyst interpretation, information reaction, rerating, expected horizon prices/returns, Fresh Capital Test and final analysis decision |
| Weekly LLM | Interpret forward evidence, later event reviews, KEEP_RULE / INVESTIGATE_RULE / PROPOSE_CHANGE |
| User | Final capital decision and external review/approval of proposed changes |
| Developer | Implement approved, versioned rule changes; accumulate a later chronological sample |

The matching executable matrix is `RESPONSIBILITY_MATRIX` in `egxbridge.analysis.forward_validation`. No Funnel or Schedule label enters scanner scoring. No broker execution, optimization, machine learning, or nationality-based psychology model is added.

## Daily workflow

1. Refresh market data and run Broad Explorer (APP).
2. Explorer automatically freezes the prescreen/final candidates and **every scanner-eligible stock**, including unselected stocks (APP). Serious-candidate enrollment uses the existing prescreen or final-handoff selection; it does not add a score gate.
3. Prepare/export the independent Schedule handoffs (APP), then run them in ChatGPT (CHATGPT).
4. Import Schedule results; selectively continue a Funnel, start a full v2.8 Funnel or run an eligible delta (APP / CHATGPT).
5. Wait for actual future market sessions, refresh market data and update outcomes (WAIT / APP).
6. Open Forward Validation Lab and prepare Weekly Validation X-Ray. Import its dated reviews and proposals (APP / CHATGPT).

`FORWARD_VALIDATION_START` is immutable and set to the actual production timestamp on the first new production Explorer enrollment, or explicitly using the Lab's start form. Installing the code or generating acceptance examples does not start a production sample. No historical discovery records are enrolled automatically.

The Lab's start form supports interpretation bands and explicit friction inputs. Additional initial settings (pullback bounds, round-number increments/proximity, audit top-N/fraction and poor-outcome cutoffs) are available through `start_validation(..., config=...)` before enrollment. The selected configuration and rule definitions are frozen. The app has no rule-activation or tuning action.

## Immutable ownership and identity

The existing `canonical_signals`, `analysis_observations` and `canonical_signal_outcomes` remain the identity/observation/outcome owners. Their v0.5.1 scoring and identity hashing are unchanged.

Additional environment-scoped tables:

- `forward_test_runs`: actual start and initial configuration.
- `forward_signal_snapshots`: one immutable extension per canonical signal, with exact metrics, selection state, clock, price basis, source metadata and rule versions.
- `universe_snapshots`, `universe_snapshot_members`: immutable run and normalized stock feature records, including all unselected eligible stocks. Full candle histories are not copied per member.
- `forward_signal_classifications`: immutable imported classifications and import/research/market-data cutoffs, linked by validated canonical ID and ticker.
- `universe_member_outcomes`: future outcomes for the retained eligible universe, using the same math as selected signals.
- `rule_definitions`, `rule_change_proposals`, `later_event_reviews`: separate immutable rules/proposals and outcome-time evidence.

Frozen tables reject SQL UPDATE and DELETE. Replayed inserts keep the first payload. Schedule views reuse existing canonicals; repeated observations do not become additional scanner samples. Canonical family counts disclose dependence, and ticker concentration is shown separately.

Production, acceptance and unit-test environments remain isolated. Acceptance uses temporary databases and labels every exported example as synthetic.

## Timing, classifications and no look-ahead

T0 market evidence, LLM classification availability and future outcomes have separate clocks. Actual application import time is authoritative; an LLM cannot backdate when its judgment became available.

Default predictive reports admit only `sample_role=FORWARD_VALIDATION`, `point_in_time_kind=CONTEMPORANEOUS`, enrolled after the recorded start. DISCOVERY, HINDSIGHT_DESCRIPTIVE, HOLDOUT and discovery for a changed rule are excluded. Reconstructed observations are opt-in through the reporting API and require explicit verified-provenance metadata; they are not admitted by default.

An imported classification enters a T0 comparison only if its declared research and supplied market-data cutoffs are valid and it was available before the next possible future session opens. Friday/Saturday are excluded; without a verified holiday calendar, a possible holiday conservatively closes the classification window too. Missing provider bars never extend that window or admit later opinions. Late or missing-cutoff classifications remain stored and are disclosed as excluded. Import clocks are compared as timestamps across time zones. The earliest eligible value for each field is retained; later revisions cannot restate T0.

Partial Funnel imports retain provenance per structured field. Importing a new stage does not change an earlier valuation or expectations field's import timestamp, research cutoff, market-data cutoff or source hash. Explorer carries these separate source records into the immutable classification table; handoffs include the field provenance alongside the current imported state.

A Funnel may be partial and need not exist for every scanner candidate. Unanalyzed fields stay unavailable. LLM value-add uses one canonical plus imported analysis observation, separately from scanner denominators. Later catalyst outcomes and realized expectations revisions are stored separately; share-price movement never generates either judgment.

## Outcomes and execution limitations

Horizons are **1, 2, 5, 10 and 20 observed completed trading sessions**, with optional 60. Legacy +3 fields remain available for existing consumers. Calendar weekends/holidays are not counted as sessions. No official exchange holiday calendar is fabricated; missing provider bars can limit horizon reliability. Friday/Saturday are weekend clock labels, and Sunday is a possible session day.

Daily windows exclude sessions already underway when T0 evidence was frozen. A `through-session` cutoff cannot include future or unfinished daily sessions. The baseline price/timestamp and its reference-price integrity remain visible. These are observation returns, not a claimed executable fill or total-shareholder-return series.

Normal cash-session clock bands in Africa/Cairo: PRE_OPEN before 10:00; CONTINUOUS 10:00–14:15; CLOSING AUCTION 14:15–14:25; TRADING AT LAST 14:25–14:30; POST CLOSE from 14:30. These are configured normal clock bands, not a live exchange calendar/feed. The current day's observed bar may be considered completed from 14:30; before that, `completed_through()` excludes it. The app does not guess holidays.

- Gross return (%) = `(future close / baseline - 1) * 100`.
- MFE (%) = maximum future high relative to baseline; MAE (%) = minimum future low relative to baseline. Both require the complete horizon and reliable high/low; closes are not substituted for missing extremes.
- Discontinuity warnings are evaluated per horizon. Raw returns remain visible, while unreliable horizons do not enter empirical summary denominators.
- Targets/stops require a T0 user/imported source. If both are touched on the same daily bar, order is `SAME_SESSION_AMBIGUOUS`. No ordering is guessed.
- Friction inputs are explicit **round-trip percentage-point costs**. Net return = gross return minus their sum. Brokerage, exchange/regulatory fees, taxes, spread and slippage must all be known for a full net estimate; a known zero must be explicitly supplied. Optional entry/exit extras must not duplicate another component.
- Missing spread/slippage never become zero. Status is OBSERVED, ESTIMATED, PARTIAL or NOT_AVAILABLE. Partial known costs remain visible, with full net return unavailable.
- Mature outcomes survive bounded reruns. Legacy outcome payloads with a different T0 cutoff cannot contaminate a newly frozen validation snapshot.

No broad bid/ask, depth, aggressor tape, absorption, fill probability or execution capacity is inferred from candles.

## Reports and rules

Reports show N, independent-family N, ticker/sector/regime diversity, date span, horizon maturity, medians/means, **EMPIRICAL POSITIVE-RETURN RATE**, MFE/MAE and net medians where available. Missing outcomes are never treated as losses or zero returns.

Default interpretation bands: fewer than 20 independent mature signals = DESCRIPTIVE_ONLY; 20–49 = PROVISIONAL; 50+ = CALIBRATION_REVIEW_ELIGIBLE. Neither VALIDATED nor PROVISIONALLY_CALIBRATED is granted automatically. Tiny cross-groups remain insufficient samples.

The Lab compares expectations burden and gap against revision outlook; premiums/discounts to imported Central FV; catalyst/reaction/rerating groups; breakouts; pullbacks; psychological levels; and tape/day/liquidity/cap/catalyst/sector/lane/setup splits. No comparison generates a BUY/SELL or Fresh Capital judgment.

CLV = `(2*close-high-low)/(high-low)` for consistent, nonzero-range OHLC. It is stored continuously; displayed bins are HEURISTIC_INITIAL. Breakout volume bins are INITIAL_ANALYSIS_BINS. Pullback v1 freezes trend/support/3–8% pullback/volume/reclaim conditions before outcomes. Missing volume is disclosed. PLSS stays HEURISTIC; raw scores, available maximum, coverage and supplied components are retained without treating missing evidence as negative. Round anchors use configurable 1/2/5-style increments scaled to price; encounters track touch/rejection/breakout/close-above and future returns without assuming resistance. A round-level breakout requires a crossing from a previous close at/below the anchor to a close above it; remaining above is only a close-above observation. Inconsistent OHLC cannot establish these events.

False negatives rank the retained universe at +5/+10/+20 and show original selection/rank/state plus matured-vs-missing coverage. A rejection reason is attributed only when supported by stored evidence; otherwise it is UNEXPLAINED. False positives are review candidates, not automatic conclusions that a rule is wrong.

Weekly X-Ray receives a dedicated **FORWARD VALIDATION AUDIT** in its independent Schedule job. Proposals are stored, never applied. Their motivating window is labeled discovery for a changed rule, which must collect a later independent chronological sample. There is no optimizer or automatic threshold promotion.

Final-handoff flags identify package selection; the app cannot observe whether a user subsequently uploads a downloaded file into an external ChatGPT session.

## Funnel asset and historical continuity

The exact user-supplied root `EGX_STOCK_ANALYSIS_FUNNEL_v2.8.md` is the current master asset. The unchanged `prompts/EGX_STOCK_ANALYSIS_FUNNEL_v2.7.md` serves historical projects. Continuation and delta retain their baseline version. Starting a new full run for an older-version project archives its exact workspace under `_history/<ticker>/<timestamp>` and creates a v2.8 project; old database rows remain intact and cannot satisfy the new run's completion boundary.

Structured fields and provenance are kept in project state for subsequent deltas and in immutable classification records for validation. Raw response text is always retained. Partial fields or claimed metadata do not establish complete status; existing verified-stage/full-tag safeguards remain. Direct DELTA_ONLY handoff also checks baseline eligibility. Version-mismatched imports are retained outside verified stage files.

The v0.7.1 [valuation persistence contract](OPERATIONAL_INTEGRITY.md) makes validated structured Central FV authoritative in history and existing readers. Expected Horizon Market Price remains separate. Audit assets are explicitly [versioned](../prompts/README.md); the archived v2.7 audit is not a current v2.8 workflow requirement.

## Commands and acceptance

The dashboard is the primary workflow. Optional commands:

```bash
python -m egxbridge.analysis.update_outcomes --horizons 1,2,5,10,20 --pending-only --forward-validation-only --dry-run
python -m egxbridge.analysis.update_outcomes --horizons 1,2,5,10,20 --through-session YYYY-MM-DD --forward-validation-only
python -m egxbridge.analysis.forward_validation --summary
python -m egxbridge.analysis.forward_validation --expectations --false-negatives
python -m egxbridge.analysis.forward_validation --weekly-package
python scripts/acceptance_v070.py
python scripts/acceptance_v071.py
```

The acceptance script runs the full configured pytest suite and generates `output/acceptance/v070/forward_validation_acceptance.md` plus JSON, schema, CSV and rule/proposal examples. All examples are synthetic and never become production evidence. The repository's pytest configuration excludes its external-network integration test by default.

The v0.7.1 script additionally checks operational integrity and writes `output/acceptance/v071/operational_integrity_acceptance.md` and its JSON reports. CI runs it after the configured test suite, without exchange, broker or LLM credentials.
