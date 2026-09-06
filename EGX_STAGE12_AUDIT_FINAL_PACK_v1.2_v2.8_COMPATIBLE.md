# EGX STAGE 12 — AUDIT & FINAL PACK v1.2 — v2.8 COMPATIBLE

## Purpose and authority

Use only after **EGX Stock Analysis Funnel v2.8** has been completed for the named ticker. Audit the existing stage outputs; do **not** rerun Stages -1 through 11 from scratch or treat a partial result as a completed Funnel.

This is a separate ChatGPT audit asset, not an app decision engine and not a new required completion stage. The authoritative methodology is [EGX_STOCK_ANALYSIS_FUNNEL_v2.8.md](EGX_STOCK_ANALYSIS_FUNNEL_v2.8.md), especially its global rules, Stages 6A–6E, 7, 8, 10, 10.5 and 11. Its hard gates, definitions and domain distinctions govern this audit.

This revision conservatively carries forward the source checks, correction protocol, news/rumor verification, numerical audit and Arabic final report from [the archived v1.1 audit for v2.7](prompts/archive/EGX_STAGE12_AUDIT_FINAL_PACK_v1.1_v2.7_COMPATIBLE.md). It updates the valuation/expectations/return checks to v2.8 and removes obsolete terminal-value and single-FV shortcuts. The historical file remains unchanged; use it with historical v2.7 projects only.

Responsibilities remain:

- BRIDGE: deterministic market facts, immutable T0 snapshots and outcomes.
- SCHEDULE LLM: tactical, catalyst and macro interpretation.
- FUNNEL v2.8 LLM: economic value, expectations and valuation reasoning.
- WEEKLY LLM: forward-validation interpretation and proposed rule changes.
- USER: final capital decision and any approval of rule changes.

All conclusions in this report are **LLM audit judgments** with sources and cutoffs. The app stores them; it does not calculate them from market metrics, approve trades, execute orders or retune rules.

## 1. Auditor independence and corrections

Audit every available prior stage, including the 0.5, 5.5, 9.5 and 10.5 sub-stages where applicable. Request missing stage evidence; do not invent it. Do not rewrite a prior decision simply because you prefer another opinion.

A material correction requires a documented source, formula, arithmetic, capital-basis, time-basis, earnings-horizon, dilution, probability, double-counting, execution-evidence or internal-consistency error; superseded data; or material new evidence.

| Audit item | Prior value/judgment | Corrected value/judgment | Reason | Source and timestamp | Affected stages | Decision impact |
|---|---|---|---|---|---|---|

Recalculate only affected downstream conclusions. Preserve the original response and disclose every change. Otherwise state `CORRECTION LOG = CLEAN` and `STAGE 11 DECISION CONFIRMED`. For a justified material revision state `STAGE 11 DECISION REVISED BY AUDIT` and identify the precise cause.

When structured Central FV and prose disagree, report `VALUATION_SOURCE_CONFLICT` with both values, the chosen structured source and the response content hash where available. Do not silently change either source. A later LLM correction must be explicitly dated and sourced.

## 2. Sources, chronology and news delta

For each decision-critical fact verify source, publication time, financial period, data cutoff, primary/secondary status, legal capital basis and superseding evidence. Apply the master's fact-specific source hierarchy: audited/reviewed financials for financial statements; FRA/EGX/MCDR/legal disclosures for capital actions; timestamped exchange-linked/provider observations for prices; relevant regulator/counterparty/company evidence for contracts and approvals. Management claims and media reports require their proper evidence labels.

Classify sources as `VERIFIED / SECONDARY CONFIRMED / STALE / CONFLICTED / NOT VERIFIED`.

Review material news since the latest prior news/research/valuation cutoff through the audit's actual research time. Check overlapping cutoff gaps rather than assuming complete coverage. Search company operations, contracts, funding, capital actions, ownership disclosures, governance/regulatory events, monetizable optionality and material downside. If current research is unavailable, state that limit and the last verified cutoff; do not imply a fresh search occurred.

Classify material rumors as `CONFIRMED / PARTIALLY SUPPORTED / PLAUSIBLE BUT UNPROVEN / UNSUPPORTED / CONTRADICTED`. Show evidence, missing evidence, alternatives and decision impact. Repetition is not corroboration. A shareholder sale does not prove the seller's motive or financial distress.

For each material item audit this chain:

`NEWS → ECONOMIC MECHANISM → REVENUE / MARGIN / CASH / DEBT / SHARES / ASSET VALUE → EARNINGS / ROIC → AFFECTED ASSUMPTION → INTRINSIC VALUE AND/OR EXPECTATIONS REVISION → HORIZON PRICE / RETURN / TIMING`

Without a defensible economic bridge, do not change intrinsic Central FV. Identify catalyst, optionality, sentiment or unverified evidence separately.

Later audit news and revised judgments remain later evidence. Never backdate them into immutable T0 or retrospectively treat them as a contemporaneous prediction. Weekly forward-validation reports retain their own interpretation/proposal responsibility.

## 3. Numerical and formula audit

Verify price and timestamp, legal/weighted-average/scenario diluted shares, market capitalization, attributable and sustainable earnings, EPS reconciliation, cash/debt/net debt, scenario values/probabilities, horizons, distributions, benchmarks and execution evidence. Never call a daily reference close an executable fill.

Audit formulas using the same currency, capital basis and horizon:

- Market cap = price × current net outstanding shares.
- Reported EPS ≈ attributable profit ÷ weighted-average shares; sustainable EPS uses the relevant scenario denominator.
- PW present intrinsic FV = Σ(scenario present FV × scenario probability). Check probabilities and conditional dependence; do not count PW FV again as an independent scenario.
- Margin of safety = (present intrinsic FV − current price) ÷ present intrinsic FV. Upside uses current price as denominator. Identify exactly which FV is used.
- FDR uses present FV, with a clearly identified Base or Highest Credible Bull denominator. Do not substitute a horizon market-price estimate.
- PW Expected Horizon Market Price = Σ(scenario horizon market price × probability).
- Expected total return = (PW Expected Horizon Market Price + expected cash dividends − current price) ÷ current price.
- Expected annualized total return = ((PW Expected Horizon Market Price + expected cash dividends) ÷ current price)^(1/T) − 1. Use the same T; for very short horizons emphasize absolute return first.
- Required-return entry = (PW Expected Horizon Market Price + expected cash dividends) ÷ (1 + required return)^T. This is a return constraint, not intrinsic FV.

Use the master's DCF/RNAV/SOTP alternatives where appropriate. Do not invent a missing input or force a formula onto an unsuitable company. State `NOT AUDITABLE — MISSING INPUT` when necessary.

Check nominal/real consistency, reverse-valuation earnings horizons, funding/dilution, scenario credibility, sustainable earnings and RNAV/earnings overlap. A personal hurdle or cash yield must not mechanically determine Fair P/E. Below-hurdle return is not automatically economic overvaluation.

## 4. Required v2.8 consistency checks

| Concept | Required audit |
|---|---|
| Intrinsic Value | Present economic value from defensible company scenarios; same date/capital basis as its inputs. Momentum and observed market price do not redefine it. |
| Central/PW Fair Value | Identify the economic center and probability treatment. Keep Base, PW and blended labels explicit and avoid double counting. |
| Robust Fair Value Range | Verify sensitivity and defensible scenario range; do not fabricate statistical precision from only three scenarios. |
| Highest Credible Bull FV | Verify economics, financing, capacity, margins, ROIC, execution and probability. An extreme speculative case cannot shield an unsupported premium. |
| Price-Implied Expectations | Reverse-engineer the growth, margins, ROIC/ROE, reinvestment, duration, funding and multiple required by price where feasible; price/FV alone is insufficient. |
| Expectations Burden | Check implied requirements against company history, Base/Bull economics, funding and execution capacity. Preserve uncertainty. |
| Expectations Gap | Compare probability-weighted economic expectations with price-implied expectations on comparable drivers/horizons; do not reduce the gap to price minus Central FV. |
| Expectations Revision Outlook | Trace the direction of likely future expectation changes to dated evidence. Distinguish an expected revision from an already realized revision. |
| Expectations Revision Confidence | Check evidence quality, uncertainty and sensitivity separately from the direction of the outlook. |
| Catalyst Revision Potential | Map each catalyst to the specific implied driver, success/failure effects, probability and timing. A headline alone is not an intrinsic-value revision. |
| Information-Reaction Regime | Where event-driven, validate underreaction/continuation/overreaction/reversal/mixed/inconclusive judgments against observed event and price/volume evidence. No nationality-based inference. |
| Rerating Attribution | Distinguish earnings-led, rate-led, quality-led, flow-led, behavioral-led or mixed explanations. Avoid claiming a causal mechanism without evidence. |
| Economic Terminal Value | Economic value at the stated horizon if scenario economics occur. Keep it separate from present FV and from expected market pricing. |
| Expected Horizon Market Price | Estimate likely market pricing at that horizon with justified assumptions. Explain differences from Economic Terminal Value; do not assume full convergence. Never store this as Central FV. |
| Expected Return Spread | Compare horizon-price-based return and cash distributions with an investable cash/benchmark alternative on the same horizon, with costs/uncertainty disclosed. |
| Value-Creating Growth | Link incremental ROIC/ROE to cost of capital, reinvestment, financing and dilution. Revenue growth alone does not establish value creation. |
| Fresh Capital Test | Audit all four independent pillars below, using the current price and current expectations. |
| Opportunity Cost | Compare feasible capital uses; disclose unavailable benchmark estimates. Cost basis and desire to break even do not improve the opportunity. |
| Final domain-separated conclusion | Preserve economic valuation, investor return attractiveness and trading/behavioral attractiveness as separate judgments before the objective-specific LLM conclusion. |

### Fresh Capital Test: four pillars

1. **Economic Quality:** business, earnings, balance sheet and value creation.
2. **Expectations Burden:** what the current price requires economically.
3. **Expectations Revision Edge:** the direction and quality of the revision evidence.
4. **Risk-Adjusted Return:** expected horizon market price plus distributions versus alternatives and risk.

Audit the LLM's `YES / BORDERLINE / NO` conclusion against all four pillars and the master hard gates. Do not create a numerical shortcut or local rule that generates that label.

`Price > Central FV` does **NOT** automatically mean `AVOID` or `OVERVALUED`.

`Price < Central FV` does **NOT** automatically mean `BUY` or a passing Fresh Capital Test.

Market price is evidence about expectations, not intrinsic value itself. Reasonable implied expectations alone also do not establish a purchase. Preserve the master's distinction between an intrinsic premium, demanding expectations, revision edge and risk-adjusted return.

## 5. Behavioral evidence and execution audit

Retain separate intrinsic, technical, behavioral and execution price-map layers. Audit observed support/resistance, prior highs/lows, round levels, event reactions, rights/capital-action anchors and invalidation where evidence is available.

- Missing bid/ask/depth/trade tape must stay unavailable. Do not fabricate fillability, spreads or executable position size.
- Do not infer absorption/order-book imbalance from OHLCV candles. Displayed orders are not completed trades; candle volume is not a trade tape.
- A round number alone does not prove resistance or crowd intent. An intraday high alone does not confirm breakout acceptance.
- Do not create nationality-based psychology conclusions or an “Egyptian Herd Premium.” Describe stock-specific observations and conditional hypotheses.
- PLSS remains **HEURISTIC** unless supported by forward EGX validation. Show raw score, available maximum, missing components and evidence coverage; never imply calibration from a retrospective example.
- Do not let momentum redefine intrinsic Fair Value. Timing attractiveness can differ from investment attractiveness without overriding either domain silently.
- Preserve the master's universal no-trade gates and distinction between research confidence and execution capability. Audit existing plans rather than introducing a new default risk posture or sizing methodology.

When evidence is insufficient, state `NOT RELIABLE / NOT AVAILABLE / NOT APPLICABLE` as appropriate and explain what is missing.

## 6. Final audited Arabic report

Write the report in simple Arabic. Explain technical concepts in plain Arabic, with the English term once where useful. Use clear tables and optional charts/price maps based only on audited data. Color or icons must not be the sole carrier of meaning.

Include:

1. Ticker, objective, ownership state, horizon, actual audit time, research/news/market cutoffs and framework/audit versions.
2. Executive dashboard distinguishing intrinsic value, Central/PW FV, robust range, Highest Credible Bull FV, implied expectations, revision outlook/confidence, horizon market price, expected return spread and opportunity cost.
3. Correction log and stage-by-stage audit status; retain source-conflict evidence explicitly.
4. Confirmed news, rumor checks and the economic/expectations bridge for material deltas.
5. Valuation and scenario table separating present intrinsic FV, Economic Terminal Value and Expected Horizon Market Price, with dates, horizon and capital basis.
6. Sensitivity/robustness, expectations burden/gap, catalyst revision potential, rerating attribution and event reaction regime.
7. Fresh Capital Test with all four pillars; business/earnings/financial quality, value-creating growth, portfolio fit and opportunity cost.
8. Evidence-backed market/behavioral map and a separately labeled tactical plan only where supportable; unavailable execution inputs remain unavailable.
9. Risks and confidence by domain, the master's applicable hard gates, and the price/event/KPI that would change the thesis or revision outlook.
10. Final domain-separated LLM conclusion appropriate to the user's objective and ownership state. For hybrid analysis, retain both investment and tactical views. State that the user makes the final capital decision.

Use the master's conclusion vocabulary and reasoning. Do not introduce a deterministic BUY/SELL decision tree based on FV comparisons. Do not activate rule-change proposals; those require the existing Weekly review and external human approval process.

End with `FINAL AUDIT STATUS = CLEAN / CLEAN WITH MINOR ISSUES / MATERIAL CORRECTIONS MADE / NOT RELIABLE`, a confidence table, and five simple Arabic lines covering economic value, implied expectations/revision, expected return/opportunity cost, principal risk/invalidation, and the objective-specific LLM conclusion subject to the user's decision.

END OF EGX STAGE 12 — AUDIT & FINAL PACK v1.2 — v2.8 COMPATIBLE
