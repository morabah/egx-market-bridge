# EGX STOCK ANALYSIS FUNNEL — v2.7 PROBABILITY-SUPPORTED ECONOMIC VALUE, REQUIRED-RETURN & BEHAVIORAL EXECUTION FRAMEWORK

Execute this master prompt for [TICKER] according to the selected RUN MODE and ANALYSIS OBJECTIVE.

Do not silently change previously established numbers.

If a later stage discovers a material error in an earlier-stage number, explicitly:

1. Identify the old number.
2. Identify the corrected number.
3. Explain the source/reason.
4. State which downstream conclusions must be recalculated.

Use plain Arabic to explain every new financial term when first introduced.

                     EGX / EGID
                  OFFICIAL MARKET TRUTH
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
        FRA            MCDR         Company IR
 capital/legal      distributions   financials
          │              │              │
          └──────────────┼──────────────┘
                         ▼
              MUBASHER + ARAB FINANCE
               fast aggregation/mirror
                         │
                  ┌──────┴──────┐
                  ▼             ▼
             TradingView   Research houses
            candles/flow   Pharos/EFG/CI
                  │             │
                  └──────┬──────┘
                         ▼
                 OUR EGX SCANNER

---

# Stage -1 — Analysis Mandate, Run Mode & Horizon Gate — REQUIRED

Before Stage 0, define the decision problem.

## -1.1 Run Mode

RUN MODE =

INTERACTIVE_STAGE_BY_STAGE / FULL_AUTOMATED_RUN / DELTA_ONLY

### Run-Mode Rules

**INTERACTIVE_STAGE_BY_STAGE**

- Execute one stage only.
- Stop after its Stage Result.
- Continue only when the user requests the next stage.

**FULL_AUTOMATED_RUN**

- Execute all applicable stages sequentially.
- Do not stop merely because an individual stage contains the phrase “لا تنتقل للمرحلة التالية”.
- Stop only when a Hard Gate makes downstream analysis materially unreliable or impossible.

**DELTA_ONLY**

- Reuse the latest reliable funnel.
- Search for new financial, company-news, capital-action, ownership, market and price information.
- Recalculate only affected stages plus downstream dependencies.
- Preserve old values in the Correction / Delta Log.

---

## -1.2 Analysis Objective

ANALYSIS OBJECTIVE =

LONG-TERM INVESTMENT / SWING-POSITION TRADE / SHORT-TERM SPECULATION / OWNED-POSITION REVIEW / FULL HYBRID REVIEW

حدد أيضًا:

- OWNERSHIP STATE = NOT OWNED / OWNED / OWNED & OVERWEIGHT / OWNED & UNDERWEIGHT.
- INTENDED HORIZON = [sessions / months / years].
- PERSONAL / PORTFOLIO REQUIRED RETURN = [ ] إن كان معروفًا.
- CAPITAL AVAILABLE / PROPOSED POSITION VALUE = [ ] إن كان معروفًا.
- PRIMARY BENCHMARK = [Money Market / EGX100 / EGX30 / Sector / Other].
- DATA CUTOFF DATE/TIME = [ ].

### Objective Weighting Rule

**LONG-TERM INVESTMENT**

- Stages 0–7 and 10–11 dominate.
- Stage 9 is used for entry efficiency, not to override the investment thesis.

**SWING-POSITION TRADE**

- Fundamental survivability, catalysts, valuation context, market structure and execution all matter.

**SHORT-TERM SPECULATION**

- Stages 0/0.5 must still eliminate hidden corporate-action, disclosure, liquidity and tradability landmines.
- Stages 7–9 dominate the entry decision.
- Weak long-term valuation does not automatically veto a trade, but Universal No-Trade Gates always apply.

**OWNED-POSITION REVIEW**

- Reassess the position as if its current market value were cash today.
- Cost basis and break-even desire are not investment reasons.
- Explicitly allow ADD / HOLD / TRIM / EXIT outcomes.

**FULL HYBRID REVIEW**

- Produce separate investment and speculative conclusions before the final action.

### Horizon Consistency Rule

Do not compare a 3-session target with a 3-year Fair Value as if they were the same decision variable.

Every expected-return calculation, catalyst window, valuation horizon and technical setup must state its relevant horizon.



### Required-Return Independence Rule — CRITICAL

`PERSONAL / PORTFOLIO REQUIRED RETURN` هو **hurdle للمستثمر** وليس Fair-Value assumption للشركة.

ممنوع:

- استخدام required return الشخصي مباشرة لاشتقاق Reasonable P/E.
- القول إن السهم `OVERVALUED` فقط لأنه لا يحقق required return المطلوب.
- خلط Required-Return Entry Price مع Economic Fair Value.

يمكن أن يكون:

- Economic Valuation = FAIR
- Return Attractiveness = BELOW HURDLE

في نفس الوقت، ولا يوجد تناقض.

### Three-Decision-Domains Rule — REQUIRED

احتفظ بثلاثة أحكام مستقلة طوال الـFunnel:

1. **ECONOMIC VALUATION**  
   هل السعر مبرر بالقيمة الاقتصادية للشركة؟

2. **INVESTOR RETURN ATTRACTIVENESS**  
   هل العائد المتوقع من السعر الحالي يحقق hurdle / opportunity cost للمستخدم؟

3. **TRADING / BEHAVIORAL ATTRACTIVENESS**  
   هل السعر قد يتحرك إيجابيًا على المدى التكتيكي رغم valuation مرتفعة؟

لا تسمح لأي Domain بإلغاء الآخر بصمت.

---


# GLOBAL RULES

## 0. Reuse Before Rebuild — REQUIRED

قبل Stage 0، ابحث أولًا عمّا إذا كان هناك Funnel سابق مكتمل أو جزئي لنفس [TICKER].

صنّف:

PROJECT FUNNEL STATUS =

NEW / FOUND / PARTIAL / NOT FOUND

إذا وُجد Funnel سابق، استخرج واحفظ على الأقل:

- Valuation date.
- Latest financial period used.
- Current / Fully Diluted share-count basis.
- Bear / Base / Bull Fair Value.
- Probability-Weighted / Blended Fair Value.
- Sustainable Earnings / EPS.
- Required Earnings at Current Price.
- Capital-action assumptions.
- Correction log.
- Latest company-news cutoff.
- Open catalysts / projects / contracts.
- Major-holder activity.
- Management promises still open.
- Valuation status.
- Capital structure basis.

ثم حدد:

UPDATE MODE =

FULL REBUILD / DELTA UPDATE / NO MATERIAL UPDATE

### Hard Rule

إذا لم تظهر معلومات جوهرية جديدة، لا تعِد بناء Fair Value من الصفر لمجرد تشغيل الـPrompt مرة أخرى.

إذا ظهرت معلومة جديدة جوهرية، حدّث فقط المراحل المتأثرة وكل المراحل downstream التي تعتمد عليها، مع الحفاظ على الأرقام القديمة في سجل واضح.

### Company-News Delta Rule — REQUIRED

في كل Delta Update، البحث عن الأخبار والإفصاحات الجديدة إلزامي حتى لو لم تتغير القوائم المالية؛ لأن:

- Operating Evidence.
- Contracts.
- Project Progress.
- Ownership Activity.
- Related-Party Developments.
- Regulatory Approvals.
- Funding Changes.
- New Optionality.

قد تصبح Material قبل ظهورها في النتائج المالية.

لا تعتبر "لا توجد نتائج مالية جديدة" مساويًا لـ"لا توجد معلومات جوهرية جديدة".

---

## 1. Evidence Hierarchy — FACT-SPECIFIC

لا تستخدم ترتيبًا واحدًا بصورة ميكانيكية لكل نوع من الحقائق.

استخدم **أفضل مصدر للواقعة المحددة** كما يلي:

### A. Capital Actions / Listing / Legal Share Count

1. FRA / EGX official decisions and disclosures.
2. MCDR عند الحاجة.
3. Company official legal disclosure.
4. Audited statements only as supporting evidence when the legal action is already reflected.

### B. Historical Financial Results / Earnings / Balance Sheet / Cash Flow

1. Audited financial statements.
2. Reviewed interim financial statements.
3. EGX-filed official results / company official filing.
4. Reliable specialized financial databases only as cross-checks.
5. Financial media only as secondary evidence.

### C. Current Corporate / Operating Events

1. EGX / FRA / official company disclosure.
2. Official government / regulator / contract-counterparty source when relevant.
3. Company IR / official statement.
4. Reliable specialized financial media.
5. Management interview, clearly attributed and classified as guidance/claim rather than audited fact.

### D. Market Price / Trading / Rights Price

1. Official or exchange-linked market data with timestamp/session state.
2. Reliable market-data provider with timestamp.
3. Other sources only as cross-checks.

### E. Management Guidance / Narrative

- Company statement or management interview is the primary source for **what management said**.
- It is not primary evidence that the economic outcome actually occurred.
- Execution must be verified separately through operating, financial or regulatory evidence.

### General Conflict Rule

إذا وجدت تضاربًا:

- اذكر الرقمين أو الادعاءين.
- مصدر كل واحد.
- تاريخ / timestamp كل واحد.
- حدد أي مصدر هو authoritative **لهذه الواقعة تحديدًا**.
- اشرح سبب اختيار الرقم المستخدم.
- لا تختَر رقمًا بصمت.

---

## 1.5 Uncertainty, Sensitivity & False-Precision Control — REQUIRED

كل رقم نهائي يجب أن يعكس جودة مدخلاته.

### Precision Rule

- لا تعرض Fair Value أو Expected Return أو Position Size بدقة زائفة إذا كانت المدخلات تقريبية.
- إذا كانت الافتراضات الجوهرية غير مستقرة، اعرض Range + Central Estimate بدل رقم واحد فقط.
- لا تستخدم منزلتين عشريتين في Fair Value لمجرد أن الآلة الحاسبة تستطيع ذلك.
- عندما تكون البيانات ناقصة بصورة جوهرية، استخدم `NOT RELIABLE` بدل ملء الفراغ بافتراض غير موثق.

### Uncertainty Propagation

لكل Assumption جوهري يؤثر على القرار، حدد:

- Base assumption.
- Reasonable low / high range.
- Source / evidence.
- Which outputs it changes.
- Whether the uncertainty is independent or correlated with other assumptions.

### Decision-Robustness Test

اسأل:

> هل القرار النهائي يبقى نفسه عبر نطاق معقول من الافتراضات؟

صنف:

DECISION ROBUSTNESS =

ROBUST / MODERATELY SENSITIVE / HIGHLY SENSITIVE / NOT RELIABLE

إذا تحول القرار من BUY إلى AVOID بسبب تغيير صغير ومعقول في افتراض واحد:

- لا تعطِ Confidence = HIGH.
- أبرز هذا الافتراض باعتباره `DECISION PIVOT`.

---

## 1.6 Symmetric Evidence Treatment — REQUIRED

عامل عدم اليقين الإيجابي والسلبي بصورة متناظرة.

إذا كان Event غير مؤكد:

- لا تدخل Positive upside كاملًا في Base لمجرد أنه محتمل.
- ولا تخصم Negative downside كاملًا من Base لمجرد أنه plausible.

استخدم:

Expected Impact ≈
Probability
×
Economically Defensible Impact

عندما يمكن تقدير الاثنين بصورة معقولة.

### Symmetry Test

لكل Material Uncertain Positive / Negative Event اسأل:

- ما Evidence level؟
- ما Probability؟
- ما Economic magnitude؟
- هل هو داخل Base أم Bull/Bear أم Optionality؟
- هل عومل حدث معاكس بدرجة إثبات مماثلة بنفس المنطق؟

### Hard Rule

`POSITIVE REQUIRES PROOF / NEGATIVE REQUIRES PLAUSIBILITY` = BIASED.

إذا ظهر هذا النمط:

فعّل:

ASYMMETRIC EVIDENCE BIAS = YES

وصحح السيناريوهات قبل valuation.

---

## 2. No Double Counting of Risk — REQUIRED

كل Risk يجب أن يؤثر على التقييم مرة واحدة بصورة أساسية.

مثال:

إذا تم بالفعل خفض Sustainable Earnings بسبب FX risk أو governance issue،
فلا تخفض Fair P/E مرة ثانية لنفس السبب ثم تضيف Margin of Safety ثالثة لنفس السبب إلا إذا شرحت أن كل Adjustment يعكس خطرًا مختلفًا.

أنشئ عند التقييم:

| Risk | Where reflected? |
|---|---|
| Earnings scenario | |
| Valuation multiple / discount rate | |
| Margin of Safety | |
| Position sizing only | |

إذا وجدت نفس الخطر مكررًا:

صحح التقييم.

---

## 3. Separate Four Things

فرق دائمًا بين:

### Company Quality
جودة النشاط نفسه.

### Stock Valuation
هل السعر الحالي مناسب؟

### Timing
هل التوقيت الفني مناسب؟

### Portfolio Fit
هل السهم مناسب لمحفظتي وبأي وزن؟

شركة ممتازة قد تكون سهمًا سيئًا عند سعر مرتفع.

وشركة متوسطة قد تصبح فرصة جيدة عند سعر منخفض جدًا.

---

## 4. Current Price Is Not Fair Value

لا تستخدم ارتفاع أو هبوط السعر كدليل على أن القيمة العادلة تغيرت إلا إذا ظهر:

- New earnings information.
- Capital action.
- New debt/equity structure.
- New material catalyst with an economic bridge.
- Major macro change.
- New operating evidence.
- Material asset-value evidence.

---

## 5. Valuation Freshness & Delta Rule — REQUIRED

كل Fair Value أو Quick Fair Value يجب أن يحمل:

- VALUATION DATE.
- FINANCIAL DATA CUTOFF.
- COMPANY NEWS CUTOFF.
- CAPITAL STRUCTURE BASIS.
- VALUATION STATUS.

صنّف:

VALUATION STATUS =

CURRENT / NEEDS DELTA / STALE / NOT RELIABLE

اعتبر التقييم NEEDS DELTA إذا ظهر بعد تاريخ التقييم أي من التالي وكان ماديًا اقتصاديًا:

- New annual / half-year / quarterly results.
- Profit warning.
- Major contract مع Earnings/Cash bridge موثوق.
- Acquisition / disposal.
- Rights issue / capital increase / merger / share issue.
- New material debt / refinancing.
- Large dividend / capital return.
- Material FX/rate exposure change specific to the company.
- Stock split / bonus shares / share-count change.
- Regulatory event.
- Material data error discovered later.
- Material project-progress update.
- Material capacity / utilization update.
- New export / customer / supply agreement.
- Material related-party development.
- Major shareholder activity that changes ownership/control or supply materially.
- New monetizable asset / carbon-credit / concession / license / optionality evidence.

### Required Delta Protocol

1. Old valuation number.
2. New fact.
3. Which assumption changed.
4. Updated number or Quick Delta estimate.
5. Which downstream conclusions must be recalculated.

### Hard Rule

لا تحسب FDR أو Margin of Safety أو Required Earnings بدقة باستخدام Valuation = STALE / NOT RELIABLE.

---

## 6. Point-in-Time / No-Look-Ahead Rule — REQUIRED FOR HISTORICAL TESTS

إذا كان التحليل يعيد بناء حالة تاريخية عند تاريخ T، استخدم فقط المعلومات التي كانت منشورة ومتاحة للسوق بحلول T.

ممنوع إدخال:

- Earnings ظهرت بعد T.
- Contracts أو capital actions ظهرت بعد T.
- Later analyst forecasts.
- Later peer multiples.
- Revised share counts known only later.
- Later macro data.
- Hindsight knowledge about whether the breakout succeeded.

سجل:

DATA CUTOFF DATE/TIME = [ ]

VALUATION VINTAGE =

CONTEMPORANEOUS / RECONSTRUCTED POINT-IN-TIME / HINDSIGHT-DESCRIPTIVE / NOT RELIABLE

فقط CONTEMPORANEOUS و RECONSTRUCTED POINT-IN-TIME يمكن استخدامهما لاختبار predictive validity.

إذا تعذر بناء نقطة زمنية موثوقة:

HISTORICAL SIGNAL / FDR = NOT RELIABLE

ولا تدخل الحالة في hit-rate / precision / threshold calibration.

---

# Stage 0 — Data Integrity & Share-Count Gate

حلل [TICKER] في البورصة المصرية.

هذه المرحلة فقط للتحقق من البيانات وبناء أساس عددي موثوق.

ممنوع:

- تقييم جودة الشركة.
- تحديد سعر عادل.
- إعطاء توصية استثمارية.
- استخدام الشارت للحكم على الشركة.

---

## 0.1 Company Identity

حدد:

- الاسم القانوني للشركة.
- Ticker.
- النشاط الرئيسي.
- القطاع.
- الصناعة الفعلية Industry.
- الشركات التابعة الرئيسية إن كانت مؤثرة في التقييم.

---

## 0.2 Share Count Bridge — REQUIRED

أنشئ Share Count Bridge كاملًا:

| Item | Shares |
|---|---:|
| Shares before latest capital action | |
| New shares announced | |
| New shares subscribed | |
| New shares allocated | |
| New shares registered/listed | |
| Current legally outstanding shares | |
| Treasury shares | |
| Current net outstanding shares | |
| Potential additional shares | |
| Fully Diluted Shares | |
| Weighted-average shares used for latest EPS | |

فرق بوضوح بين:

### Current Shares
عدد الأسهم القانوني الحالي.

### Weighted-Average Shares
متوسط عدد الأسهم المستخدم محاسبيًا لحساب EPS خلال الفترة.

### Fully Diluted Shares
عدد الأسهم الاقتصادي المحتمل بعد جميع الأدوات/الزيادات/التحويلات المحتملة.

إذا توجد:

- Rights Issue.
- Capital Increase.
- Options.
- Convertible instruments.
- Bonus shares.
- Share split.
- Merger consideration shares.

أدخل أثرها صراحة.

---

## 0.3 Market Data

حدد:

- آخر سعر إغلاق موثوق.
- تاريخ الإغلاق.
- Market Capitalization.

تحقق:

Market Cap =
Share Price × Current Shares

وعند وجود Dilution:

Fully Diluted Market Cap =
Share Price × Fully Diluted Shares

إذا اختلف Market Cap المنشور عن الحساب:

- اذكر الفرق.
- ابحث عن السبب.
- لا تستخدم الرقم المنشور تلقائيًا.

---

## 0.3A Price Integrity Gate — REQUIRED

لكل سعر جوهري مستخدم في الحسابات حدد:

- Price.
- Source.
- Timestamp.
- Session state.
- Whether adjusted for corporate action.

صنف Session State عند الإمكان:

CONTINUOUS TRADING / CLOSING AUCTION / TRADING-AT-LAST / OFFICIAL CLOSE / PRE-OPEN INDICATIVE / HISTORICAL ADJUSTED

ثم صنف:

PRICE INTEGRITY =

CLEAN / CONFLICT / STALE / NOT RELIABLE

إذا وجدت سعرين مختلفين من مصادر موثوقة:

- اذكر السعرين.
- اذكر timestamp لكل منهما.
- حدد هل الاختلاف نتيجة حركة intraday، closing mechanics، adjusted history أو corporate action.
- لا تختَر سعرًا بصمت.

### Hard Rule

PRICE INTEGRITY = CONFLICT / NOT RELIABLE يمنع استخدام Exact Market Cap / Exact FDR / Exact Entry economics بثقة عالية حتى يتم حل التضارب.

---

## 0.3B Capital-Structure Basis — REQUIRED

حدد الأساس الذي ينتمي إليه السعر وEPS وFair Value per share:

CAPITAL STRUCTURE BASIS =

CURRENT-NORMAL / CUM-RIGHTS / EX-RIGHTS / POST-DILUTION / SPLIT-ADJUSTED / BONUS-ADJUSTED / MERGER-ADJUSTED / NOT RELIABLE

### Same-Basis Rule

يجب أن تكون المقارنة بين Price وEPS وFair Value على نفس Capital Structure Basis.

ممنوع مثلًا:

- Post-right price ÷ Pre-right FV/share.
- Split-adjusted price ÷ unadjusted EPS.
- Pre-merger shares مع post-merger earnings دون bridge.

في Rights Issue، عند الحاجة قارن القيمة الاقتصادية للمساهم كالتالي:

Ex-right share value + Right value

واستخدم TERP وFully Diluted economics بدل اعتبار الهبوط الميكانيكي Loss اقتصاديًا.

---

## 0.4 Ownership & Liquidity Data

حدد إن توفر:

- Free Float.
- كبار المساهمين.
- Strategic shareholders.
- Ownership concentration.
- Treasury shares.
- أي قيود مؤثرة على التداول.

فرق بين:

Legal Free Float

و

Economic Tradable Float

إذا كان هناك مساهمون غير مصنفين استراتيجيًا لكن تداولهم الفعلي محدود.

---

## 0.5 Financial Statements

حدد أحدث:

- Annual financial statements.
- Half-year results.
- Quarterly results.
- Standalone statements.
- Consolidated statements.

اذكر:

- تاريخ الفترة.
- تاريخ النشر.
- هل القوائم audited أم reviewed أم management accounts.

إذا كانت الشركة Holding أو لديها Subsidiaries مؤثرة:

فرق بين:

Standalone

و

Consolidated.

---

## 0.6 Latest Corporate Actions

راجع:

- Capital increase/decrease.
- Rights issue.
- Bonus shares.
- Stock split.
- Dividends.
- Treasury shares.
- Acquisitions.
- Disposals.
- Mergers.
- Tender offers.
- Share swaps.
- Major shareholder transactions.
- Strategic investor entry/exit.

---

## 0.7 EPS Integrity Check

تحقق قدر الإمكان:

Published EPS ≈

Net Profit attributable to common shareholders
÷
Weighted-Average Shares

إذا يوجد:

- Employee profit share.
- Board remuneration.
- Preferred distributions.
- Treasury-share adjustment.
- Restatement.

فسر أثره.

إذا يوجد اختلاف:

- اذكره.
- حاول تفسيره.
- لا تستخدم EPS المنشور بصورة آلية.

---

## 0.8 Source Hierarchy Check

لكل رقم جوهري حدد أفضل مصدر.

إذا كان مصدر مالي متخصص يستخدم Share Count قديم:

لا تستخدم Market Cap أو EPS أو P/E منه بدون تصحيح.

---

# Stage 0 Result

DATA QUALITY =

HIGH / MEDIUM / LOW

ثم أعطني:

- أهم البيانات المؤكدة.
- أهم البيانات الناقصة.
- Current Shares المستخدم.
- Weighted-Average Shares.
- Fully Diluted Shares المستخدم.
- PRICE INTEGRITY.
- CAPITAL STRUCTURE BASIS.
- PROJECT FUNNEL STATUS.
- UPDATE MODE.
- أي uncertainty تؤثر على valuation.
- أي Capital Action يحتاج مراجعة أعمق.

### Hard Rule

إذا DATA QUALITY = LOW بسبب نقص جوهري في:

- عدد الأسهم.
- Capital Action.
- القوائم.
- الأرباح.
- الملكية.

فلا تسمح لاحقًا بحكم استثماري عالي الثقة.

لا تنتقل إلى Business Quality.

---

# Stage 0.5 — Company Intelligence, News & Narrative Verification Gate — REQUIRED

نفذ هذه المرحلة بعد Stage 0 وقبل Business Quality.

في كل Full Build أو Delta Update، نفذ بحثًا عميقًا عن أحدث أخبار وإفصاحات [TICKER].

الهدف ليس جمع الأخبار فقط، بل اكتشاف معلومات اقتصادية قد لا تظهر بعد في القوائم المالية.

---

## 0.5.1 Search Scope — REQUIRED

راجع على الأقل:

- آخر 90 يومًا بصورة عميقة.
- آخر 12 شهرًا للأحداث المفتوحة وغير المكتملة.
- فترات أقدم عند الحاجة لفهم مشروع أو وعد إداري أو Capital Action ما زال مؤثرًا.

يجب أن يتضمن البحث:

- Official disclosures.
- Company statements.
- Regulatory approvals.
- Reliable specialized financial press.
- Management interviews only when clearly attributed.
- Historical announcements relevant to open projects.

لا تعتمد على Headlines فقط؛ افتح التفاصيل عندما يكون الخبر ماديًا.

---

## 0.5.2 News Categories — REQUIRED

ابحث صراحة عن:

### Operating News

- New contracts.
- Contract renewals.
- Contract cancellations.
- Orders / backlog.
- Production increases/decreases.
- Capacity additions.
- Utilization changes.
- New factories / farms / branches.
- New wells / equipment / machinery.
- New products.
- Export activity.
- New markets.
- Pricing changes.
- Customer wins/losses.
- Supplier issues.
- Raw-material changes.
- Operational disruptions.

### Investment / Expansion News

- New projects.
- Land acquisition/allocation.
- Reclamation progress.
- Construction progress.
- Capacity expansion.
- Project commissioning.
- Project delays.
- Capex plans.
- Revised project budgets.
- Funding requirements.
- Asset monetization.

### Financial / Funding News

- New loans.
- Shareholder loans.
- Refinancing.
- Debt repayment.
- Debt restructuring.
- Creditor balances.
- Debt-to-equity conversion.
- Grants.
- Subsidies.
- Capital raises.
- Rights issues.
- Bond / sukuk issuance.

### Ownership / Insider News

- Major shareholder buying.
- Major shareholder selling.
- Insider transactions.
- Strategic investor entry/exit.
- Block trades.
- Ownership changes.
- Related-party transactions.

### Management / Governance News

- Board changes.
- CEO/CFO changes.
- Management guidance.
- Guidance revisions.
- Auditor changes.
- Auditor qualifications.
- Legal disputes.
- Regulatory investigations.
- Minority-shareholder issues.

### Regulatory / Government News

- Licenses.
- FRA decisions.
- EGX decisions.
- Government contracts.
- Land allocations.
- Pricing regulations.
- Subsidies.
- Tax changes.
- Export/import rules.

### Optionality / Hidden Upside

ابحث عن مصادر قيمة لم تظهر بعد بوضوح في الأرباح:

- Carbon credits.
- Land revaluation potential.
- New concessions.
- Patents/licenses.
- Export licenses.
- Government approvals.
- Monetizable unused assets.
- New subsidiaries.
- Strategic partnerships.
- M&A discussions.
- Tax assets.
- Renewable-energy credits.
- Insurance recoveries.
- Claims / settlements.

### Hidden Downside

ابحث بنفس القوة عن:

- Project delays.
- Customer disputes.
- Contract cancellations.
- Cost overruns.
- Environmental liabilities.
- Regulatory fines.
- Litigation.
- Related-party leakage.
- Asset impairment.
- Liquidity strain.
- Repeated shareholder selling.
- Promises not delivered.

---

## 0.5.3 Rumor & Claim Verification — REQUIRED

إذا وجدت ادعاءً شائعًا مثل:

- "المالك يبيع لأنه مديون."
- "المساهم الرئيسي يخرج."
- "الشركة تجمع الأموال لسداد الديون."
- "هناك مستثمر استراتيجي قادم."
- "عقد ضخم سيُعلن."
- "السهم يتم التلاعب به."
- "المالك يبيع ثم يعيد المال للشركة."
- "زيادة رأس المال هدفها تغطية خسائر فقط."

صنف الادعاء:

CONFIRMED

PARTIALLY SUPPORTED

PLAUSIBLE BUT UNPROVEN

UNSUPPORTED

CONTRADICTED

ثم اذكر:

- Exact claim.
- Evidence found.
- Evidence missing.
- Alternative explanations.
- What disclosure would prove/disprove it.

### Hard Rule

لا تحول rumor أو تفسير سلوك المساهم إلى Fact بدون دليل.

Major-holder selling يثبت البيع فقط.

لا يثبت سبب البيع ما لم يوجد disclosure أو evidence موثوق.

Related-party creditor balance لا يعني تلقائيًا أن المساهم نفسه مديون.

Shareholder loan to company لا يعني تلقائيًا أن الشركة في distress.

---

## 0.5.4 News Economic Bridge — REQUIRED

لكل خبر مادي أنشئ:

| News / Event | Status | Economic Channel | Evidence | Valuation Impact |
|---|---|---|---|---|
| | | Revenue / Margin / Cash / Debt / Shares / ROIC / Optionality | | |

وصنف حالة الخبر:

ANNOUNCED

APPROVED

FUNDED

UNDER EXECUTION

OPERATING

REVENUE GENERATING

CASH GENERATING

DELAYED

CANCELLED

UNCERTAIN

### Required Economic Bridge

NEWS
→ Operating / Financial Mechanism
→ Revenue / Margin / Cash / Debt / Share Count / Asset Value
→ Incremental Sustainable Profit / ROIC
→ Valuation Assumption
→ Fair Value Impact

إذا لم يمكن بناء هذا الـBridge:

لا تدخل الخبر في Base Fair Value.

---

## 0.5.5 Narrative vs Economics Test — REQUIRED

فرق بين:

### Narrative
قصة تبدو إيجابية أو سلبية.

و

### Economic Evidence
دليل يمكن ربطه بالأرباح أو التدفقات النقدية أو رأس المال.

مثال:

"الشركة ستزرع 1,000 فدان إضافي"

لا يكفي وحده.

ابحث عن:

- Required capital.
- Planting schedule.
- Expected yield.
- Selling price.
- Customer/offtake.
- Operating cost.
- Incremental profit.
- Cash conversion.
- Expected ROIC.

مثال آخر:

"مشروع Carbon Credits بقيمة 3m USD"

لا تعامل 3m USD كأرباح تلقائيًا.

افحص:

- Registration.
- Verification.
- Credits issued.
- Sale agreement.
- Gross proceeds.
- Company share.
- Timing.
- Cash received.

---

## 0.5.6 Optionality Register — REQUIRED

أنشئ قائمة منفصلة للأحداث التي قد تضيف قيمة لكنها غير ناضجة بما يكفي للدخول في Base Case.

صنف كل Optionality:

HIGH-PROBABILITY

MEDIUM-PROBABILITY

LOW-PROBABILITY

SPECULATIVE

مثال:

| Optionality | Potential Value | Probability | Included in Base? |
|---|---:|---:|---|
| Carbon credits | | | NO / PARTIAL / YES |
| New export contract | | | |
| New project | | | |

### Rule

لا تدخل Optionality غير مثبتة بالكامل في Sustainable Earnings.

يمكن إدخالها في Bull Case أو Probability-Weighted valuation إذا كان هناك Economic Bridge معقول.

---

## 0.5.7 Management Promise Tracker — REQUIRED

احتفظ بسجل للوعود والتصريحات السابقة:

| Management Statement | Date | Target | Actual Outcome | Status |
|---|---|---|---|---|
| | | | | |

صنف:

DELIVERED

PARTLY DELIVERED

DELAYED

MISSED

TOO EARLY

UNKNOWN

استخدم هذا السجل لاحقًا في:

- Management Quality.
- Growth Probability.
- Bull/Base probability.
- Fair Multiple عند الحاجة.

### Rule

لا ترفع Growth Probability بسبب تكرار Management Guidance فقط.

يجب مقارنة الوعود السابقة بالتنفيذ الفعلي.

---

## 0.5.8 News Freshness Test — REQUIRED

لكل Delta Update:

ابحث عن أي خبر ظهر بعد:

LAST FUNNEL DATA CUTOFF

و

LAST VALUATION DATE

ثم صنف:

NEWS DELTA =

NO MATERIAL NEWS

POSITIVE MATERIAL NEWS

NEGATIVE MATERIAL NEWS

MIXED MATERIAL NEWS

UNVERIFIED MATERIAL CLAIM

---

## 0.5.9 Valuation Impact Rule — REQUIRED

لا تغير Fair Value لمجرد وجود خبر إيجابي أو سلبي.

يجب تحديد:

NEWS → ECONOMIC BRIDGE → ASSUMPTION CHANGE → VALUATION CHANGE

مثال:

New Contract
→ +Revenue
→ Expected margin
→ Incremental profit
→ Sustainable EPS change
→ Fair Value change.

إذا لا يمكن بناء Bridge معقول:

سجل الخبر كـCatalyst / Optionality فقط.

لا تدخله في Base Fair Value.

---

## 0.5.10 Balanced Search / Confirmation-Bias Control — REQUIRED

إذا طلب المستخدم البحث عن أخبار متفائلة أو سلبية فقط:

- ابحث عن المطلوب.
- لكن نفّذ أيضًا Counter-Search مختصرًا عن الأدلة العكسية.

مثال:

إذا طلب:

"ابحث عن أخبار إيجابية تجعلني أتمسك بالسهم"

يجب البحث أيضًا عن:

- Negative disclosures.
- Project delays.
- Insider selling.
- Funding strain.

والعكس صحيح.

### Hard Rule

لا تستخدم News Gate لتغذية Confirmation Bias.

---

# Stage 0.5 Result

أعطني:

NEWS DELTA =

NO MATERIAL NEWS / POSITIVE / NEGATIVE / MIXED / UNVERIFIED

ثم:

- حتى 5 أخبار إيجابية **Material** فقط؛ إذا كان العدد أقل، اذكر العدد الفعلي ولا تملأ القائمة بأخبار ضعيفة.
- حتى 5 أخبار سلبية **Material** فقط؛ إذا كان العدد أقل، اذكر العدد الفعلي.
- حتى 3 Rumors / market claims **فقط إذا وُجدت فعليًا**؛ لا تنشئ Rumor لاستكمال القالب.
- إذا لم توجد عناصر مادية، اكتب NONE / NO MATERIAL ITEMS FOUND.
- Open Projects.
- Open Contracts.
- Optionality Register.
- Major-holder activity.
- Related-party developments.
- Management Promise Tracker.
- أي خبر يستدعي إعادة حساب Stage 1–6.
- أي خبر يؤثر فقط على Catalyst/Timing وليس Fair Value.

### Hard Rule

إذا ظهر خبر مادي يمكنه تغيير:

- Sustainable Earnings.
- Debt.
- Cash.
- Share Count.
- ROIC.
- Asset Value.
- Growth Probability.

فعّل:

VALUATION STATUS = NEEDS DELTA

وحدد المراحل التي يجب إعادة حسابها.

أما إذا كان الخبر يؤثر على sentiment أو trading فقط:

لا تغير Fair Value.

حدّث Stage 7–9 فقط.

لا تنتقل إلى Business Quality قبل إنهاء Stage 0.5.

---

# Stage 1 — Business Quality Gate

نفذ فقط Business Quality Gate على [TICKER].

لا تستخدم سعر السهم أو الشارت للحكم على جودة النشاط.

---

## Business Model

حدد:

- الشركة تكسب أموالها من أين؟
- Revenue Mix.
- Segment Mix.
- أهم الشركات التابعة.
- أهم Revenue Drivers.
- أهم Cost Drivers.

---

## Business Quality

افحص:

- Sustainability of demand.
- Market Position.
- Market Share إذا توفر.
- Moat.
- Pricing Power.
- Customer concentration.
- Supplier concentration.
- Product concentration.
- Geographic concentration.
- Cyclicality.
- Seasonality.
- Capital Intensity.
- Regulatory Risk.

---

## Macro Sensitivity

حدد حساسية النشاط لـ:

- Interest rates.
- USD/EGP.
- Inflation.
- Energy prices.
- Commodity prices.
- Consumer demand.
- Credit cycle.

فرق بين:

### Revenue sensitivity

و

### Margin sensitivity

و

### Balance-sheet sensitivity.

---

## Holding Companies — REQUIRED IF APPLICABLE

إذا كانت الشركة Holding:

حلل:

- ما الأصول/الشركات التي تولد القيمة؟
- أي Subsidiary تحقق معظم الأرباح؟
- هل Parent نفسها تولد Cash؟
- هل توجد Holding-company costs كبيرة؟
- هل يوجد اعتماد على توزيعات الشركات التابعة؟

---

## Management

قيّم الإدارة فقط عند وجود أدلة موضوعية:

- Capital allocation record.
- Execution against guidance.
- Related-party behavior.
- Dilution history.
- Governance record.
- Acquisition record.
- Return generated on previous capital raises.
- Management Promise Tracker from Stage 0.5.

---

# Stage 1 Result

Business Gate =

PASS / PASS WITH CAUTION / FAIL

Business Quality =

STRONG / ACCEPTABLE / WEAK

اذكر أهم 3 أسباب للحكم.

لا تنتقل للمرحلة التالية.

---

# Stage 2 — Earnings Quality Gate

نفذ Earnings Quality Gate على [TICKER].

ابدأ من Revenue أو Operating Income المناسب لطبيعة الشركة وابنِ Earnings Bridge حتى Net Profit وEPS.

---

## 2.1 Core Earnings Bridge

افحص:

- Revenue.
- Revenue Growth.
- Gross Profit عند ملاءمته.
- Gross Margin.
- Operating Profit.
- Operating Margin.
- Net Profit attributable to shareholders.
- Net Margin.
- EPS.

قارن:

1. Latest period vs comparable prior period.
2. آخر سنتين أو ثلاث سنوات.

---

## 2.2 Holding / Financial Company Adjustment

إذا كانت الشركة Holding أو Financial Services فلا تطبق Gross Margin بصورة ميكانيكية.

استخدم حسب الملاءمة:

- Profit by subsidiary.
- Profit by segment.
- Interest income.
- Finance income.
- Investment income.
- Share of associates.
- Dividend income.
- Realized investment gains.
- Unrealized/Fair-value gains.
- Finance costs.
- Holding-company expenses.
- Minority Interest / NCI.

---

## 2.3 One-Off Audit

حدد أثر:

- Asset sales.
- Revaluation.
- FX gains/losses.
- Debt settlement gains.
- Provision reversals.
- Investment disposal gains.
- Exceptional income.
- Fair-value movements.
- Accounting changes.
- Government grants.
- Restatements.

فرق بين:

Reported Earnings

و

Recurring Operating Earnings.

---

## 2.4 Earnings Bridge

إذا Net Profit ارتفع أسرع كثيرًا من Revenue:

فسر اقتصاديًا مصدر الفرق.

Revenue
→ Gross Margin
→ Operating Expenses
→ EBIT
→ Finance Cost
→ Investment/FX/One-offs
→ Tax
→ Minority Interest
→ Attributable Net Profit.

---

## 2.5 Cash Conversion

افحص:

- Operating Cash Flow.
- Net Profit.
- Cash Conversion.
- Working-capital changes.
- Free Cash Flow.

حدد:

هل الأرباح تتحول إلى Cash؟

أم تذهب إلى:

- Receivables.
- Inventory.
- Capitalized costs.
- Other working capital.

---

## 2.6 Sustainable Earnings

قدّر:

Sustainable Earnings

أي الأرباح التي يمكن اعتبارها قابلة للتكرار اقتصاديًا.

### Share-Count Scenario Rule — REQUIRED

لا تستخدم `Maximum Theoretical Fully Diluted Shares` تلقائيًا في Base EPS.

احسب حسب الحالة:

### Current-Share Sustainable EPS

Current Sustainable EPS =

Sustainable Earnings
÷
Current Net Outstanding Shares

### Base-Case Sustainable EPS

Base-Case Sustainable EPS =

Base Sustainable Earnings
÷
Most Probable Share Count for the Base Scenario

### Dilution-Scenario Sustainable EPS

لكل سيناريو dilution:

Scenario EPS =

Scenario Sustainable Earnings
÷
Scenario Share Count

إذا شروط Capital Action غير محسومة:

- Limited dilution.
- Partial dilution.
- Large dilution.
- Full stress dilution.

ثم Probability-Weight **the scenario outcomes** عند الحاجة.

### Hard Rule

Fully Diluted Shares = maximum theoretical shares

لا تعني تلقائيًا:

Base Share Count = maximum theoretical shares.

استخدم maximum/full dilution كـBase فقط إذا أصبح هذا فعليًا السيناريو الأكثر احتمالًا.


### News Optionality Rule

لا تدخل Optionality من Stage 0.5 في Sustainable Earnings إلا إذا أصبحت:

REVENUE GENERATING أو CASH GENERATING بدرجة موثوقة.

وإلا:

ضعها في Bull / Probability-Weighted scenario فقط.

---

# Stage 2 Result

Earnings Gate =

PASS / PASS WITH CAUTION / FAIL

Earnings Quality =

STRONG / ACCEPTABLE / WEAK

اذكر:

- Reported Earnings.
- Sustainable Earnings.
- Reported EPS.
- Current-share Sustainable EPS.
- Fully Diluted Sustainable EPS أو السيناريوهات.
- أهم One-Off.
- أهم accounting uncertainty.
- أي News Optionality تم إدخالها أو استبعادها ولماذا.

لا تنتقل للمرحلة التالية.

---

# Stage 3 — Financial Strength Gate

نفذ Financial Strength Gate على [TICKER].

---

## Balance Sheet

احسب حسب الملاءمة:

- Cash.
- Total Debt.
- Net Debt.
- Debt/Equity.
- Net Debt/EBITDA.
- Interest Coverage.
- Current Ratio.
- Quick Ratio.
- Working Capital.
- Operating Cash Flow.
- Free Cash Flow.

راجع الاتجاه خلال آخر 3 سنوات.

---

## Sector-Specific Financial-Strength Adapter — REQUIRED

لا تطبق Net Debt/EBITDA أو Current Ratio أو Quick Ratio ميكانيكيًا على كل قطاع.

### Banks

استخدم حسب التوفر:

- Capital Adequacy Ratio / CAR.
- CET1 / Tier 1 عند التوفر.
- NPL ratio.
- NPL coverage.
- Cost of Risk.
- Loan-to-Deposit / funding mix.
- Liquidity ratios.
- Deposit concentration.
- FX funding mismatch.
- Regulatory capital headroom.

### NBFS / Consumer Finance / Leasing / Factoring / Mortgage Finance

راجع:

- Receivables / loan-book growth.
- Asset quality / arrears / NPLs.
- Provisioning / coverage.
- Funding spread and cost of funds.
- Leverage.
- Maturity mismatch.
- Securitization dependence.
- Collections quality.
- Regulatory capital where applicable.

### Real Estate

راجع:

- Net debt and maturity schedule.
- Collections vs construction cash needs.
- Presales quality and cancellations.
- Customer receivables.
- Land-payment obligations.
- Project-level funding commitments.

### Holdings

افصل Parent liquidity عن subsidiary liquidity كما هو موضح أدناه.

### Cyclicals / Commodity Producers

- لا تعتمد على peak-cycle EBITDA وحده.
- استخدم mid-cycle / normalized cash generation.
- Stress-test commodity price, FX, energy and working-capital requirements.

### Rule

إذا كان metric غير مناسب لطبيعة النشاط:

اكتب NOT APPLICABLE بدل إجبار الحساب.

---

## Funding Structure

افحص:

- الاعتماد على القروض.
- Capital Increases.
- Related-party financing.
- Debt maturity.
- Cost of debt.
- Refinancing risk.
- Capex funding.
- Covenant compliance.
- Creditor balances from related parties.
- Debt-to-equity conversion plans.

---

## Parent vs Subsidiary Debt — REQUIRED WHEN APPLICABLE

فرق بين:

### Parent/Holding Debt

و

### Operating/Subsidiary Funding

لا تعامل الاثنين بنفس الطريقة.

---

## Standalone Parent Liquidity — REQUIRED WHEN APPLICABLE

حدد:

- Parent cash.
- Parent debt.
- Parent operating expenses.
- Dividends received.
- Ability to service parent obligations.

لا تعتبر Consolidated Cash تلقائيًا متاحًا للأم.

---

## Funding Classification

حدد:

SELF-FUNDED

أو

EXTERNAL-FUNDING DEPENDENT

أو

MIXED

واربط التمويل بـ:

- Asset growth.
- Revenue growth.
- Earnings.
- OCF.
- Incremental Return on Capital.

---

# Stage 3 Result

Financial Strength Gate =

PASS / PASS WITH CAUTION / FAIL

Financial Strength =

STRONG / ACCEPTABLE / WEAK

لا تنتقل للمرحلة التالية.

---

# Stage 4 — Growth Gate

نفذ Growth Gate على [TICKER].

افصل بين:

Historical Growth

و

Future Growth.

---

## Historical Growth

حلل:

- Revenue growth.
- Sustainable Earnings growth.
- Fully Diluted EPS growth.
- Volume/unit growth.
- Margin progression.

فرق بين:

Nominal Growth

و

Real / FX-adjusted Growth

عندما يكون التضخم أو انخفاض الجنيه مؤثرًا جدًا.

---

## Future Growth Drivers

حسب طبيعة الشركة:

- Backlog.
- Presales.
- Orders.
- Capacity.
- Utilization.
- New branches.
- New products.
- New subsidiaries.
- Acquisitions.
- Geographic expansion.
- Market share.
- Management guidance.
- Open Projects from Stage 0.5.
- Open Contracts from Stage 0.5.
- Optionality Register from Stage 0.5.

---

## Growth Runway

حدد:

Growth Runway =
مساحة النمو المتبقية اقتصاديًا.

---

## Growth Proof

صنف:

PROVEN

PARTLY PROVEN

STORY ONLY

### Evidence Rule

ANNOUNCED أو MANAGEMENT GUIDANCE وحدها لا تكفي لـPROVEN.

الأفضل:

APPROVED → FUNDED → UNDER EXECUTION → OPERATING → REVENUE GENERATING → CASH GENERATING.

---

## Funding Bridge

كيف سيمول النمو؟

- Operating Cash Flow.
- Existing Cash.
- Debt.
- Rights Issue.
- Capital Increase.
- Asset Sales.
- Grants.
- Combination.

---

## Incremental Return on New Capital — REQUIRED

إذا جمعت الشركة رأس مال جديد:

احسب قدر الإمكان:

Incremental Sustainable Profit
÷
New Capital Raised

وسمه:

Incremental ROE / ROIC on New Capital

قارن العائد بـ:

- Cost of debt.
- Cost of equity.
- Normalized risk-free rate.
- Historical company ROIC.

صنف العائد:

VALUE CREATING

ADEQUATE

WEAK

VALUE DESTROYING

UNKNOWN

---

## Growth Scenarios

أنشئ:

### Bear
### Base
### Bull

خلال 1–3 سنوات.

لكل سيناريو:

- Revenue.
- Sustainable Net Profit.
- Fully Diluted EPS.
- أهم الافتراضات.
- Economic Bridge.
- Funding requirement.
- Which Stage 0.5 news/options are included.

---

## Probability — REQUIRED

حدد Probability تقريبية لكل سيناريو.

مثال:

Bear 25%

Base 55%

Bull 20%

لا تستخدم احتمالات شكلية فقط؛ اشرح سببها.

### Conditional-Probability / Dependence Rule — REQUIRED

لا تضرب احتمالات Operating Scenario × Dilution Scenario × Optionality بصورة آلية إلا إذا كان افتراض الاستقلال Independence معقولًا اقتصاديًا.

إذا كانت الأحداث مترابطة، استخدم Conditional Probability.

مثال:

P(Large Dilution | Bear Operating Case)

قد تكون أعلى بكثير من:

P(Large Dilution | Bull Operating Case)

لأن ضعف التشغيل نفسه قد يرفع الحاجة للتمويل.

عند وجود ترابط:

- ابنِ Scenario Tree مشروطًا.
- اذكر العلاقة الاقتصادية بين الفروع.
- تأكد أن مجموع probabilities النهائية = 100% تقريبًا.

إذا يوجد Capital Action غير محسوم:

أنشئ Scenarios منفصلة له عند الحاجة:

- Limited dilution.
- Partial dilution.
- Large dilution.
- Full stress dilution.

ولا تحول Full Stress Case تلقائيًا إلى Base Case.

### Management Credibility Adjustment

استخدم Management Promise Tracker لتعديل احتمالات السيناريوهات:

- DELIVERED history → يمكن رفع probability عند وجود دليل.
- MISSED / DELAYED repeatedly → خفض probability.

---

# Stage 4 Result

Growth Gate =

PASS / PASS WITH CAUTION / FAIL

Growth Strength =

STRONG / MODERATE / WEAK

Growth Proof =

PROVEN / PARTLY PROVEN / STORY ONLY

لا تنتقل للمرحلة التالية.

---

# Stage 5 — Corporate Action, Dilution & Governance Gate

نفذ هذه المرحلة قبل Valuation.

راجع أحدث EGX/FRA/company disclosures ونتائج Stage 0.5.

---

## 5.1 Corporate Actions

راجع:

- Rights Issues.
- Capital increases/decreases.
- Bonus shares.
- Treasury shares.
- Stock splits.
- Major shareholder transactions.
- Insider transactions.
- Related-party transactions.
- Large shareholder loans.
- Convertible shareholder funding.
- Creditor balances.
- Acquisitions.
- Disposals.
- Ownership/control changes.

---

## 5.2 Economic Bridge

لكل حدث اسأل:

- لماذا يحدث؟
- كم Capital سيتم جمعه؟
- أين ستذهب الأموال؟
- ماذا ستحصل الشركة اقتصاديًا؟
- هل الأموال للنمو أم لسد فجوة تمويل؟
- ما الأثر المحتمل على Revenue؟
- Net Profit؟
- Cash Flow؟
- Debt؟
- EPS؟
- Ownership؟
- Free Float؟

### Use-of-Proceeds Audit — REQUIRED

لا تكتفِ بعبارة "زيادة رأس مال للنمو".

أنشئ قدر الإمكان:

| Use of Proceeds | Amount | Status | Expected Economic Output |
|---|---:|---|---|
| Capex | | | |
| Working Capital | | | |
| Debt Conversion | | | |
| Debt Repayment | | | |
| Related Party Settlement | | | |
| Other | | | |

إذا كان مجموع البنود لا يطابق إجمالي الزيادة:

اذكر التعارض ولا تختر رقمًا بصمت.

---

# Dilution Economics — REQUIRED

إذا توجد زيادة رأس مال:

حدد:

Old Shares

New Shares

Fully Diluted Shares

Subscription Price

Capital Raised

ثم:

Dilution Ratio =
New Shares ÷ Old Shares

---

## Dilution Scenario Classification — REQUIRED

إذا شروط الزيادة لم تُحسم:

لا تستخدم رقمًا واحدًا على أنه Fully Diluted Base.

أنشئ:

### Scenario A — No / Limited Dilution

### Scenario B — Partial Dilution

### Scenario C — Large Dilution

### Scenario D — Full Stress Conversion

حدد Probability تقريبية لكل حالة حيثما أمكن.

---

## EPS Dilution Breakeven Test — REQUIRED

Pre-Action EPS =

Pre-Action Sustainable Earnings
÷
Old Shares

Required Post-Action Earnings =

Pre-Action EPS
×
Fully Diluted Shares

Required Earnings Growth =

Required Post-Action Earnings
÷
Pre-Action Sustainable Earnings
− 1

اشرح:

كم يجب أن ترتفع الأرباح فقط لمنع انخفاض EPS؟

---

## Capital Return Test

احسب:

Incremental Profit Required
÷
New Capital Raised

وقارنه مع:

- Expected ROIC.
- Cost of capital.
- Comparable investment returns.

---

## Classify Capital Action

ACCRETIVE

NEUTRAL

DILUTIVE

TOO EARLY TO KNOW

ولا تعتبر زيادة إجمالي Net Profit دليلًا على Accretion.

Accretive يعني:

> Economic value / EPS per share improves sufficiently after the new capital.

---

## TERP

إذا توجد Rights Issue وكان الحساب مناسبًا:

TERP =
Theoretical Ex-Rights Price

فرق بين:

Mechanical price adjustment

و

Economic value creation/destruction.

### Rights Reflexivity Cross-Check — ENTITLEMENT-RATIO ADJUSTED

عندما يكون الحق متداولًا، لا تفترض تلقائيًا أن Right واحد = سهم جديد واحد.

حدد أولًا:

- Rights entitlement ratio.
- Number of Rights required per new share.
- Subscription Price per new share.
- Right Market Price.
- Relevant execution friction.

احسب تقريبًا:

Right-Implied New Share Cost =

Subscription Price
+
(Rights Required per New Share × Right Market Price)
+
Execution Friction

ثم قارن مع:

Ordinary Share Price على نفس timestamp/session basis قدر الإمكان.

وحدد هل يوجد:

- Arbitrage-like pressure.
- Rights discount/premium.
- Temporary mechanical pressure on ordinary shares.

### Hard Rule

إذا entitlement ratio أو rights-needed-per-share غير محسوم:

RIGHTS RELATION = NOT RELIABLE

ولا تستخدم المقارنة لاتخاذ قرار تنفيذ دقيق.

لا تعتبر هذا Fair Value.

---

## Supply Overhang

افحص:

- أسهم جديدة تدخل التداول.
- تمويل المساهمين للاكتتاب.
- احتمالية البيع بعد الإدراج.
- Major-holder selling.
- Free Float expansion.

صنف:

NONE

LOW

MODERATE

HIGH

فرق بين:

### EPS Dilution Risk

و

### Market Supply Overhang

قد يكون Dilution كبيرًا لكن Supply Overhang منخفضًا إذا ظل المساهم المسيطر محتفظًا بالأسهم.

---

## Governance

راجع:

- Related parties.
- Insider transactions.
- Major-holder selling.
- Auditor issues.
- Disclosure quality.
- Capital allocation history.
- Repeated dilution.
- Ownership concentration.
- Minority shareholder protection.
- Rumors verified in Stage 0.5.

### Major-Holder Intent Rule

لا تستنتج سبب البيع من البيع نفسه.

صنف:

SALE CONFIRMED

USE OF PROCEEDS CONFIRMED / UNKNOWN

PERSONAL DEBT CLAIM CONFIRMED / UNSUPPORTED / CONTRADICTED

---

# Stage 5 Result

Corporate/Governance Gate =

PASS / CAUTION / FAIL

وأعطني:

- Dilution Ratio.
- Fully Diluted scenarios.
- Capital Raised.
- Use-of-Proceeds table.
- EPS Breakeven Profit.
- Required Earnings Growth.
- Incremental return on new capital.
- Supply Overhang.
- Capital Action classification.
- Major-holder activity interpretation with evidence limits.

---

# Stage 5.5 — Market & Valuation Calibration Layer — REQUIRED

هذه المرحلة لا تحدد Fair Value.

هدفها منع الـValuation من أن تكون محافظة أو متفائلة بصورة منفصلة عن ظروف السوق.

---

## 5.5.1 Market Valuation

حدد قدر الإمكان:

- EGX30 Forward P/E.
- EGX100 valuation.
- Market P/B.
- Earnings Yield.
- Historical valuation range.

صنف السوق:

CHEAP

NORMAL

RE-RATED

FROTHY

BUBBLE-LIKE

لا تستخدم ارتفاع المؤشر وحده كدليل على Bubble.

---

## 5.5.2 Sector Valuation

حدد Peer Group مناسب.

احسب Median / Range قدر الإمكان:

- Forward P/E.
- P/B.
- EV/EBITDA.
- ROE/ROIC.
- Growth.

لا تقارن شركة نمو عالية مع شركة راكدة بدون Adjustment.

---

## 5.5.3 Historical Valuation

حدد:

- Current multiple.
- 3–5Y median إن أمكن.
- Historical range.
- Current percentile تقريبًا.

هل الشركة:

Below history

Normal

Above history

Extreme

---

### Historical Multiple Regime-Shift Guard — REQUIRED

Historical median multiple ليس Fair Multiple تلقائيًا.

قبل استخدام 3–5Y historical median، اسأل هل تغير بصورة مادية:

- inflation/rate regime,
- FX convertibility / currency stress,
- leverage,
- ROE/ROIC,
- growth quality,
- governance,
- liquidity/free float,
- business mix,
- accounting/capital structure.

إذا حدث structural regime shift:

HISTORICAL MULTIPLE RELEVANCE =

HIGH / MEDIUM / LOW / NOT RELIABLE

واخفض وزن historical anchor عند الحاجة بدل إجبار الشركة على العودة إلى multiple تاريخي من بيئة اقتصادية مختلفة.

---

## 5.5.4 Interest-Rate Calibration

لا تستخدم Spot CBE Rate فقط كأنها ستستمر للأبد.

حدد:

### Current Policy Rate

و

### Normalized 2–3 Year Rate Assumption

و، إذا valuation horizon أطول:

### Long-Run Nominal Rate / Discount Assumption

استنادًا إلى:

- Inflation path.
- Forward expectations.
- Monetary-policy direction.
- Country risk.
- Market-implied / credible professional expectations when available.
- Historical real-rate regime only as a cross-check, not an anchor by itself.

استخدم Spot Rate كـnear-term condition.

واستخدم Normalized Rate لتقييم الأصول طويلة الأجل عندما يكون ذلك اقتصاديًا أنسب.

### Anti-Spot-Rate Bias Rule — CRITICAL

ممنوع تحويل Spot Policy / Deposit Rate مباشرة إلى Fair P/E مثل:

`Fair P/E ≈ 1 / Spot Rate`

إلا في حالة اقتصادية خاصة جدًا مع شرح كامل.

السبب:

- equity has growth,
- reinvestment,
- dividends,
- duration,
- risk premium,
- and changing rates.

Spot cash yield هو **opportunity-cost reference**، وليس perpetual equity valuation formula.

### Required-Return Separation

Personal Required Return لا يستخدم كـmarket discount rate تلقائيًا.

فرق بين:

- Market / company-specific required return used for valuation.
- User portfolio hurdle used for capital-allocation decision.

---

## 5.5.5 Inflation Calibration & Nominal/Real Consistency — REQUIRED

فرق بين:

Nominal Earnings Growth

و

Real Earnings Growth.

إذا Revenue +20% بينما inflation +15%:

لا تصفها تلقائيًا بأنها Growth 20% اقتصاديًا.

### Consistency Rule

استخدم أحد النظامين بوضوح:

#### NOMINAL MODEL
- Nominal revenue / earnings.
- Nominal growth.
- Nominal discount rate / required return.
- Nominal terminal value.

#### REAL MODEL
- Real revenue / earnings.
- Real growth.
- Real discount rate.
- Real terminal value.

### Hard Rule

ممنوع:

- خفض growth إلى real growth،
- ثم استخدام nominal discount rate المرتفع،
- ثم إضافة inflation penalty مرة أخرى في multiple/MOS،

إلا إذا كانت كل adjustment تعكس خطرًا مختلفًا ومفسرًا.

إذا حدث mixing:

NOMINAL/REAL CONSISTENCY = FAIL

وصحح valuation.

---

## 5.5.6 FX Calibration

للشركات الحساسة للدولار:

راجع:

- Earnings in EGP.
- Earnings in USD إن كان مفيدًا.
- Import costs.
- Export revenues.
- FX debt.

استخدم USD/real-earnings cross-check عندما يكون انخفاض الجنيه سببًا كبيرًا للنمو الاسمي.

---

## 5.5.7 Risk Duplication Audit — REQUIRED

راجع كل المخاطر المستخدمة سابقًا.

أنشئ:

| Risk | Earnings | Multiple | MOS | Position Size |
|---|---:|---:|---:|---:|
| FX | | | | |
| Governance | | | | |
| Liquidity | | | | |
| Debt | | | | |
| Dilution | | | | |
| Country risk | | | | |
| Optionality | | | | |

إذا نفس الخطر تم خصمه عدة مرات بدون مبرر مختلف:

صحح التقييم.

إذا Optionality أضيفت إلى Bull Earnings:

لا تضفها مرة ثانية كAsset Value مستقلة إلا إذا كان ذلك يعكس مكونًا مختلفًا اقتصاديًا.

---

## 5.5.8 EGX Market-Tape Regime — TIMING CONTEXT ONLY

افصل **Market Valuation Regime** عن **Market Tape Regime**.

راجع عند توفر البيانات:

- EGX30 direction.
- EGX70 direction.
- EGX100 direction.
- Advance/Decline breadth.
- Total market turnover vs recent normal.
- Number/ratio of successful vs failed breakouts.
- Sector leadership.
- Risk-on / Risk-off behavior.
- Small-cap vs large-cap participation.
- Foreign / institutional flow إذا توفر بصورة موثوقة.

صنف:

MARKET TAPE REGIME =

RISK-ON / NEUTRAL / RISK-OFF / DISLOCATED / NOT RELIABLE

### Rule

Market Tape Regime يؤثر على:

- Timing.
- Breakout probability.
- Position size.
- Execution threshold.

ولا يغير Fair Value مباشرة إلا إذا كان يعكس معلومة اقتصادية جديدة مستقلة.

---

# Stage 5.5 Result

Market Regime =

CHEAP / NORMAL / RE-RATED / FROTHY / BUBBLE-LIKE

Sector Valuation =

CHEAP / NORMAL / RICH

Rate Environment =

RESTRICTIVE / NORMALIZING / NORMAL

Risk Double-Count Check =

CLEAN / ADJUSTMENT REQUIRED

Market Tape Regime =

RISK-ON / NEUTRAL / RISK-OFF / DISLOCATED / NOT RELIABLE

---

# Stage 6 — Valuation Gate

نفذ Valuation Gate باستخدام نتائج Stages 0–5.5.

استخدم:

- Sustainable Earnings.
- Fully Diluted EPS scenarios.
- Fully Diluted Shares.
- Capital-action economics.
- Market calibration.
- Sector calibration.
- Normalized rates.
- Stage 0.5 Optionality only according to its evidence level.

لا تعتمد على Reported P/E وحده.

---

## 6.0 Valuation Freshness Checkpoint — REQUIRED

قبل أي Fair Value calculation، أعد فحص:

- PRICE INTEGRITY.
- VALUATION STATUS.
- CAPITAL STRUCTURE BASIS.
- Fully Diluted Shares.
- Latest material disclosure after prior valuation date.
- Latest material company-news delta.

إذا VALUATION STATUS = NEEDS DELTA:

نفذ Delta Update أولًا ولا تستبدل التقييم القديم بصمت.

إذا CAPITAL STRUCTURE BASIS بين Price وFV غير متطابق:

صحح الأساس قبل الحساب.

---

## 6.0A Valuation-Time Basis Rule — REQUIRED

كل قيمة سيناريو يجب أن تحمل **زمنها الاقتصادي** بوضوح.

صنف كل رقم valuation إلى واحد من:

### PRESENT FAIR VALUE @ VALUATION DATE

قيمة السهم اليوم بعد خصم/معايرة التدفقات أو الأرباح المستقبلية إلى تاريخ التقييم.

تُستخدم في:

- Economic Valuation classification.
- Margin of Safety.
- Upside to Fair Value.
- Base / Optimistic FDR.
- Current Price vs Fair Value.

### TERMINAL VALUE @ RETURN HORIZON

قيمة السهم المتوقعة في نهاية Horizon محدد مستقبلًا، قبل إرجاعها إلى Present Value.

تُستخدم في:

- Expected Total Return.
- Expected Annualized Total Return.
- Required-Return Entry Price.

### Hard Rule — NO TIME-BASIS MIXING

ممنوع:

- استخدام Terminal FV في FDR / Margin of Safety / Current Economic Valuation.
- استخدام Present FV كأنه Future Terminal Value في Expected Return.
- مقارنة Current Price مع Scenario Values من تواريخ مختلفة دون discount/bridge واضح.

لكل Scenario عند الحاجة اعرض:

| Scenario | Present FV @ Valuation Date | Terminal Value @ Horizon | Horizon Date | Bridge / Discount Basis |
|---|---:|---:|---|---|
| Bear | | | | |
| Base | | | | |
| Bull | | | | |

صنف:

VALUATION TIME-BASIS CONSISTENCY =

CLEAN / ADJUSTMENT REQUIRED / NOT RELIABLE

---

## 6.1 Three Independent Outputs — REQUIRED

Stage 6 يجب أن ينتج **حكمين منفصلين**، بينما Stage 9 ينتج الحكم الثالث:

### A. ECONOMIC VALUATION
هل Current Price مبرر اقتصاديًا بالنسبة إلى defensible Fair-Value range؟

### B. INVESTOR RETURN ATTRACTIVENESS
هل Expected Return من Current Price يحقق `PERSONAL / PORTFOLIO REQUIRED RETURN` والـOpportunity Cost؟

### C. TRADING / BEHAVIORAL ATTRACTIVENESS
يُحسم لاحقًا في Stage 9 بصورة مستقلة.

### Hard Separation

`Below Required-Return Hurdle` لا يعني `Overvalued`.

`Overvalued` لا يعني أن Short-Term Trade مستحيل.

---

## 6.2 Reasonable Multiple / Discount-Rate Calibration — REQUIRED

إذا استخدمت P/E أو EV/EBITDA أو P/B أو DCF discount rate:

لا تختَر multiple أو rate من الانطباع.

أنشئ Bridge واضحًا:

### For P/E

Reasonable P/E should be calibrated from:

- sustainable / forward growth,
- ROE / ROIC,
- reinvestment runway,
- payout/dividend profile,
- balance-sheet risk,
- earnings cyclicality,
- governance/disclosure quality,
- sector peer range,
- current market regime,
- normalized—not merely spot—rates,
- historical multiple only after regime adjustment.

### Required Cross-Checks

قارن:

1. Absolute / fundamentals-implied multiple.
2. Sector / peer multiple.
3. Historical-regime-adjusted multiple.
4. Market-implied multiple.

إذا Base P/E أقل كثيرًا من peer/historical/market anchors:

اشرح لماذا.

إذا السبب الوحيد هو:

`cash yield is high today`

فهذا غير كافٍ.

### Equity-Yield Shortcut Guard

`Fair P/E = 1 / User Required Return`

أو

`Fair P/E = 1 / Spot Cash Yield`

ممنوع كـdefault valuation method.

يمكن استخدام earnings yield كـcross-check فقط مع:

- growth,
- payout,
- duration,
- reinvestment,
- and risk adjustments.

### Multiple Calibration Status

MULTIPLE CALIBRATION =

WELL SUPPORTED / REASONABLE / WEAK / NOT RELIABLE

---

## Valuation Methods

حسب النشاط:

- Sustainable P/E.
- Forward P/E.
- Earnings Yield.
- P/B.
- ROE.
- EV/EBITDA.
- P/FCF.
- PEG.
- Dividend Yield.
- DCF إذا كان مناسبًا.
- Asset/NAV cross-check إذا كانت الأصول المادية جوهرية.

---

## Asset / RNAV Cross-Check — REQUIRED WHEN MATERIAL

إذا كانت الشركة تمتلك أو تتحكم في:

- Land.
- Concessions.
- Usufruct rights.
- Farms.
- Factories.
- Investment properties.
- Other material tangible assets.

حاول بناء Asset/NAV cross-check.

فرق بين:

- Legal ownership.
- Usufruct / concession rights.
- Book value.
- Independent appraised value.
- Management-estimated value.

إذا لا يوجد appraisal موثوق:

صنف:

ASSET VALUE = UNCONFIRMED

ولا تستخدم Asset Story لرفع Fair Value بلا أساس.

لكن إذا:

- legal ownership / economic rights موثقة،
- asset materially affects equity value،
- وتتوفر comparable transactions / market evidence معقولة،

يمكن بناء:

CONSERVATIVE RNAV RANGE

باستخدام:

- verified area/ownership/right,
- conservative comparable value,
- development / monetization haircut,
- tax/cost/debt adjustments,
- time-to-realization discount,
- probability of monetization.

صنف:

RNAV CONFIDENCE =

HIGH / MEDIUM / LOW / NOT RELIABLE

لا تحول lack of formal appraisal إلى Asset Value = ZERO تلقائيًا.

### RNAV / Earnings Double-Count Guard — REQUIRED

خصوصًا في Real Estate / Asset-Heavy companies، لا تضف قيمة الأرض أو المشروع مرتين.

افصل قدر الإمكان بين:

1. **Operating / Development Franchise Value** — قيمة النشاط وقدرته على توليد أرباح متكررة.
2. **Projects / Land already embedded in forecast earnings** — أصول ستولد الأرباح المستخدمة بالفعل في P/E / DCF / scenario earnings.
3. **Surplus / Undeveloped / Non-operating Assets** — أصول غير داخلة بصورة جوهرية في earnings forecast ويمكن أن تستحق Asset Value مستقلة.
4. **Investment / Recurring Assets** — أصول ذات cash flow مستقل يمكن تقييمها منفصلًا إذا لم تكن أرباحها محسوبة بالفعل.

### Hard Rule

إذا كانت future development profits من أرض/مشروع داخلة في Sustainable / Forward Earnings:

- لا تضف Full RNAV لنفس الأرض فوق Earnings Value.
- استخدم RNAV كـcross-check، أو قيّم فقط Surplus / Residual Asset Value غير الملتقط في earnings.

إذا تعذر فصل overlap بصورة موثوقة:

RNAV / EARNINGS OVERLAP CHECK = NOT RELIABLE

ولا تستخدم RNAV كوزن مستقل داخل Blended FV.

صنف:

RNAV / EARNINGS OVERLAP CHECK =

CLEAN / PARTIAL OVERLAP ADJUSTED / MATERIAL OVERLAP / NOT RELIABLE

---

## Holding Companies — SOTP REQUIRED WHEN FEASIBLE

SOTP = Sum of the Parts.

قيّم:

- Subsidiaries.
- Investments.
- Parent cash.
- Parent debt.
- Holding costs.
- Other assets/liabilities.

Equity Value =

Sum of subsidiary values
+ Parent Cash
− Parent Debt
− Other Adjustments

Fair Value per Share =

Equity Value
÷
Fully Diluted Shares

---

## Sector-Specific Valuation

### Real Estate

- RNAV.
- Price/RNAV.
- Presales quality.
- Collections.
- Land bank quality.

### Banks

- P/B.
- ROE.
- NIM.
- NPL.
- Coverage.
- CAR.
- Cost of Risk.
- Sustainable/normalized ROE across the rate cycle.

### NBFS / Financial Services

- P/B and ROE where economically meaningful.
- P/E on normalized earnings.
- Loan/receivables growth.
- Cost of funds / spread.
- Credit-cost normalization.
- Asset quality.
- Funding and securitization risk.

### Cyclicals / Commodity Companies

- Mid-cycle earnings / EBITDA.
- EV/EBITDA on normalized commodity assumptions.
- Replacement-cost / asset-value cross-check when appropriate.
- Do not value peak-cycle earnings as sustainable earnings without justification.

### Holdings

- SOTP/NAV.
- Holding discount.

### Capital Action Companies

- Fully Diluted Market Cap.
- Fully Diluted EPS.
- Incremental return on new capital.
- Probability-weighted dilution scenarios.
- Rights reflexivity as timing only, not FV.

---

# Three Valuation Anchors — REQUIRED

احسب قدر الإمكان:

## A. Absolute Fair Value

ما الذي تبرره أرباح الشركة اقتصاديًا؟

## B. Relative Fair Value

ما الذي تبرره Peer/sector multiples؟

## C. Historical-Normalized Fair Value

ما الذي يبرره تاريخ تقييم الشركة بعد ضبط اختلاف النمو؟

## D. Asset / Optionality Cross-Check — WHEN MATERIAL

استخدمه فقط إذا توفر Economic Bridge موثوق.

لا تجبره على الدخول في Blended FV إذا كان غير موثوق.

---

# Probability-Weighted Fair Value — REQUIRED

استخدم Bear/Base/Bull probabilities.

Expected / Probability-Weighted Fair Value =

Bear FV × P(Bear)

+

Base FV × P(Base)

+

Bull FV × P(Bull)

إذا يوجد Dilution uncertainty:

يمكن إنشاء Probability Tree تجمع Operating Scenario وDilution Scenario وOptionality realization عند الحاجة.

### Dependence Rule

لا تستخدم multiplication ميكانيكيًا إذا كانت الفروع مترابطة.

استخدم Conditional Probabilities مثل:

P(Dilution Scenario | Operating Scenario)

و

P(Optionality Realization | Funding / Execution State)

عند الحاجة.

ولا تستخدم Full Stress Case كأنه Base Case إلا إذا أصبح هو الأكثر احتمالًا فعليًا.

تحقق أن مجموع probabilities النهائية ≈ 100%.

---

# Blended Fair Value — REQUIRED

استخدم مزيجًا مبررًا من:

- Absolute FV.
- Relative FV.
- Historical FV.
- Probability-weighted FV.
- Asset/Optionality anchor إذا كان موثوقًا.

ثم استخرج:

# Blended Fair Value

اشرح وزن كل طريقة.

## Anti-Double-Count Rule — REQUIRED

Probability-Weighted FV ليس Valuation Method مستقلًا إذا كانت Bear/Base/Bull Fair Values نفسها مبنية بالفعل من Absolute / Relative / Historical anchors.

لا تعطِ Probability-Weighted FV وزنًا إضافيًا داخل Blended FV إذا كان ذلك سيعيد احتساب نفس evidence مرتين.

استخدم أحد الهيكلين بوضوح:

### Preferred Structure A

Operating Scenarios
→ Valuation anchors داخل كل Scenario
→ Scenario Fair Values
→ Probability-Weighted Fair Value
→ Relative/Historical/Asset values كـcross-checks.

### Alternative Structure B

Independent valuation anchors
→ justified blend
→ scenario adjustments
→ probability-weighted outcome.

لكن لا تخلط الهيكلين بطريقة تعيد احتساب نفس المعلومات.

---

# Fair-Value Detachment Ratio — FDR — REQUIRED

هدف FDR هو قياس مقدار انفصال السعر عن القيمة الاقتصادية، خصوصًا في الأسهم ذات Momentum أو Behavioral Extension.

احسب فقط عندما PRICE INTEGRITY وVALUATION STATUS وCAPITAL STRUCTURE BASIS تسمح بمقارنة موثوقة.

## Base FDR

Base FDR =

Current Price
÷
Base Fair Value

## Optimistic FDR

Optimistic FDR =

Current Price
÷
Highest Economically Defensible Bull / Optimistic Fair Value

## Premium Above Optimistic FV

Premium Above Optimistic FV =

Current Price
÷
Optimistic Fair Value
− 1

صنف:

### AT / BELOW OPTIMISTIC VALUE
Premium ≤ 0%

### MODEST EXTENSION
0–25% above

### EXTENDED
25–50% above

### STRONG DETACHMENT
50–100% above

### EXTREME DETACHMENT
100–200% above

### SEVERE BEHAVIORAL DETACHMENT
>200% above

### NOT RELIABLE
إذا price / valuation / capital-structure basis غير موثوق.

## Critical Interpretation Rule

FDR ليس Automatic Breakout Veto.

افصل دائمًا بين:

### Investment Attractiveness
هل السعر مبرر اقتصاديًا؟

و

### Breakout / Behavioral Probability
هل يمكن أن يستمر السعر في الحركة رغم الانفصال عن القيمة؟

قد يكون:

Investment = AVOID

وفي نفس الوقت:

Behavioral / Breakout Setup = STRONG

ولا يوجد تناقض بين الحكمين.

---

# Economic Valuation Classification — v2.7 PROBABILITY-SUPPORTED

صنف **Economic Valuation** فقط، وليس required-return attractiveness.

### CHEAP
Current Price materially below the lower / central probability-supported FV region with strong economic upside.

### ATTRACTIVE
Current Price below Central / Probability-Weighted Present Fair Value by a meaningful margin with acceptable downside asymmetry.

### FAIR
Current Price قريب من Central / Probability-Weighted Present FV **ومدعوم بمنطقة valuation ذات probability meaningful**.

وجود السعر داخل Robust FV Range واسع جدًا لا يكفي وحده لـFAIR.

### RICH BUT PLAUSIBLE
Current Price أعلى من Central/Base Present FV، لكنه ما زال مدعومًا اقتصاديًا بواسطة probability-supported upside scenarios، وBull Dependence / Market-Implied Expectations لا تتطلبان نجاحًا شبه كامل غير مدعوم.

### OVERVALUED
Current Price materially above the probability-supported economic region، أو يسعّر نسبة كبيرة جدًا من credible Bull economics مقارنة باحتمالها وأدلتها، حتى لو لم يتجاوز Highest Credible Bull FV بصورة طفيفة.

لا تستخدم OVERVALUED لمجرد:

- Price > Base FV.
- Expected return < user hurdle.
- Current multiple > historical median.
- Spot interest rate مرتفعة.

### SEVERE FUNDAMENTAL DETACHMENT
Current Price far above HIGHEST CREDIBLE FV / probability-supported range **and** Market-Implied Expectations appear economically implausible.

### UNRELIABLE
المعلومات أو valuation basis غير كافية.

## Bull-Credibility Guard — REQUIRED

`Highest Defensible Bull FV` لا يعني أعلى رقم يمكن تخيله.

حتى يُستخدم Bull FV كحد يمنع تصنيف السهم `OVERVALUED`، يجب أن يكون:

- evidence-backed,
- economically bridged,
- internally funded / financeable when funding is required,
- consistent with realistic capacity / margins / ROIC,
- and assigned a **non-trivial probability**.

### Bull Status

BULL CASE STATUS =

CREDIBLE / AGGRESSIVE BUT DEFENSIBLE / REMOTE-SPECULATIVE / NOT RELIABLE

إذا:

BULL CASE STATUS = REMOTE-SPECULATIVE

فلا تستخدم Bull FV وحده لتبرير Current Price أو لمنع `OVERVALUED`.

استخدم بدلًا منه:

HIGHEST CREDIBLE FV =

highest Fair Value from scenarios classified:

CREDIBLE
or
AGGRESSIVE BUT DEFENSIBLE

### Rule

Low-probability optionality يمكن أن يظهر منفصلًا، لكنه لا يحوّل سعرًا مرتفعًا إلى `RICH BUT PLAUSIBLE` ما لم يكن احتمال تحققه وتبريره الاقتصادي meaningful.

---

## Probability-Supported Fair-Value Region — REQUIRED

لا يكفي معرفة أعلى Bull FV؛ يجب معرفة **أين تتركز احتمالات القيمة**.

رتب Scenario Fair Values واحتمالاتها على نفس Present-Value date basis.

عندما يكون Scenario Tree granular بما يكفي، احسب/قدّر:

- PW / Expected FV.
- Median / P50 FV.
- P25 / P75 FV.
- P10 / P90 FV عند إمكان الدفاع عنها.

إذا كانت السيناريوهات قليلة جدًا (مثل Bear/Base/Bull فقط):

- لا تدّعِ quantiles دقيقة.
- اعرض `COARSE PROBABILITY-SUPPORTED RANGE` مع probabilities الصريحة لكل Scenario.

صنف:

PROBABILITY-SUPPORTED FV QUALITY =

HIGH / MEDIUM / COARSE / NOT RELIABLE

### Rule

`Current Price < Highest Credible Bull FV` **ليس وحده دليلًا** أن السعر economically plausible.

يجب أيضًا فحص:

- probability mass around Current Price,
- Bull probability,
- execution burden,
- financing capacity,
- and Market-Implied Expectations.

---

## Bull-Dependence Test — REQUIRED WHEN Price > Base FV

إذا كان:

Base Present FV < Current Price

ويوجد Highest Credible Bull Present FV أعلى من Base، احسب:

Bull Dependence =

(Current Price − Base Present FV)
÷
(Highest Credible Bull Present FV − Base Present FV)

### Interpretation — DESCRIPTIVE, NOT A HARD GATE

- ≤0%: Base أو أقل مسعّر.
- 0–25%: mild upside execution priced.
- 25–50%: meaningful Bull execution priced.
- 50–75%: substantial Bull economics priced.
- 75–100%: معظم/تقريبًا كامل credible Bull repricing مسعّر.
- >100%: السعر تجاوز Highest Credible Bull FV.

هذه الحدود **descriptive initialization** وليست قانونًا ثابتًا؛ يجب تفسيرها مع Bull probability والأدلة.

صنف:

BULL DEPENDENCE =

LOW / MODERATE / HIGH / VERY HIGH / BEYOND CREDIBLE BULL / NOT APPLICABLE / NOT RELIABLE

### Bull Probability Consistency Test

إذا Bull Dependence مرتفع جدًا بينما Bull probability منخفضة أو Bull execution يحتاج شروطًا كثيرة متزامنة:

لا تسمح لـHighest Credible Bull FV وحده بمنع `OVERVALUED`.

اسأل:

> هل Current Price يسعّر جزءًا من Bull economics أكبر بكثير مما تبرره probability/evidence؟

إذا نعم:

BULL-PRICING CONSISTENCY = WEAK

ويمكن أن يصبح `OVERVALUED` صحيحًا رغم أن Current Price ما زال أقل قليلًا من Bull FV.

صنف:

BULL-PRICING CONSISTENCY =

STRONG / REASONABLE / WEAK / NOT APPLICABLE / NOT RELIABLE

---

## Overvaluation Trigger Rule — v2.7 PROBABILITY-SUPPORTED

قبل `OVERVALUED` أو `SEVERE FUNDAMENTAL DETACHMENT`:

يجب أن تعرض:

- Central / PW Present FV.
- Probability-Supported FV Region / quality.
- Robust FV Range.
- Base Present FV.
- Highest Defensible Bull Present FV.
- Bull Case Status + probability.
- HIGHEST CREDIBLE FV.
- Bull Dependence.
- Bull-Pricing Consistency.
- Current Price vs HIGHEST CREDIBLE FV.
- Market-Implied Expectations.
- Why those expectations are or are not reasonably achievable.

### Classification Logic

**RICH BUT PLAUSIBLE** يكون مناسبًا عندما:

- Current Price > Central/Base FV،
- لكنه ما زال مدعومًا بمنطقة valuation ذات probability meaningful،
- أو Bull Dependence ليست مفرطة مقارنة باحتمال Bull وأدلته،
- وMarket-Implied Expectations لا تتجاوز execution يمكن الدفاع عنه.

**OVERVALUED** يمكن أن يكون صحيحًا حتى لو:

Current Price ≤ HIGHEST CREDIBLE FV

عندما:

- Current Price materially above probability-supported region، أو
- Bull Dependence = HIGH / VERY HIGH بينما Bull probability ضعيفة نسبيًا، أو
- السعر يسعّر تقريبًا كامل Bull outcome قبل تحقق الأدلة، أو
- Market-Implied Expectations = VERY DEMANDING ولا يدعمها execution record / funding / capacity.

### Critical Rule

`Price ≤ Highest Credible Bull FV` هو **necessary cross-check** لكنه **ليس sufficient condition** لمنع `OVERVALUED`.

---

# Margin of Safety & Upside — REQUIRED

فرق بين مقياسين مختلفين:

## A. Fair-Value Discount / Margin of Safety

Margin of Safety =

(Fair Value − Current Price)
÷
Fair Value

هذا يجيب:

> كم يقل السعر الحالي عن Fair Value كنسبة من Fair Value؟

## B. Upside to Fair Value

Upside to Fair Value =

(Fair Value − Current Price)
÷
Current Price

هذا يجيب:

> كم يمكن أن يرتفع السعر من Current Price حتى Fair Value؟

### Example

إذا Fair Value = 100 وCurrent Price = 50:

- Margin of Safety = 50%.
- Upside to Fair Value = 100%.

### Risk Rule

لا تجعل Margin of Safety عقوبة ثانية لنفس المخاطر التي خفضت بالفعل Earnings أو Fair Multiple.

---

# Market-Implied Expectations / Reverse Valuation — REQUIRED

بدل الاكتفاء بقول “غالي”، اعكس السعر الحالي لمعرفة ما الذي يسعره السوق.

استخدم **market-calibrated Reasonable Multiple / Discount Rate** من Stage 6.2، وليس personal hurdle.

## A. Implied EPS / Earnings

Required EPS =

Current Price
÷
Market-Calibrated Reasonable P/E

Required Sustainable Earnings =

Required EPS
×
Relevant Scenario Share Count

### Earnings-Horizon Matching Rule — REQUIRED

الـMultiple المستخدم في Reverse Valuation يجب أن يطابق أفق الأرباح التي تتم مقارنتها.

| Multiple Basis | Required Earnings Horizon |
|---|---|
| TTM P/E | TTM normalized earnings |
| Current Sustainable P/E | Current / near-term sustainable earnings |
| FY+1 Forward P/E | FY+1 expected earnings |
| FY+2 Forward / Terminal P/E | FY+2 earnings at the same horizon |
| DCF terminal multiple/value | Terminal-year normalized cash flow / earnings |

### Hard Rule

ممنوع:

- استخدام FY+1 Forward P/E لاشتقاق Required EPS ثم مقارنته مباشرة بـTTM EPS.
- استخدام Terminal P/E مع Current Earnings بدون growth bridge.
- مقارنة Required Earnings وScenario Earnings من تواريخ مختلفة دون reconciliation.

صنف:

REVERSE-VALUATION HORIZON MATCH =

CLEAN / ADJUSTMENT REQUIRED / NOT RELIABLE

## B. Implied Growth — WHEN FEASIBLE

احسب تقريبًا:

- Implied EPS CAGR.
- Implied Revenue CAGR.
- Implied sustainable margin.
- Implied ROE / ROIC.
- Implied terminal growth / FCF when DCF is used.

ثم قارن مع:

- company history,
- current capacity,
- backlog/contracts,
- sector growth,
- peer economics,
- management execution record,
- funding capacity.

## C. Market-Implied Expectations Classification

CURRENT PRICE IMPLIES:

EASY EXECUTION

PLAUSIBLE EXECUTION

DEMANDING EXECUTION

VERY DEMANDING EXECUTION

ECONOMICALLY IMPLAUSIBLE

### Interpretation

إذا Current Price يحتاج growth أعلى من Base لكن داخل credible Bull execution:

لا تستخدم `OVERVALUED` تلقائيًا.

استخدم:

RICH BUT PLAUSIBLE

إذا كان Bull scenario قابلًا للدفاع اقتصاديًا.

إذا السعر يحتاج assumptions تتجاوز حتى defensible Bull:

OVERVALUED أو SEVERE FUNDAMENTAL DETACHMENT حسب magnitude.

---

# Expected Total Return & Horizon Bridge — REQUIRED FOR INVESTMENT / SWING

حدد Valuation / realization horizon المستخدم:

RETURN HORIZON = [T years or fraction of year]

احسب قدر الإمكان:

Expected Terminal Value =

Probability-weighted expected value at the selected horizon

ثم:

Expected Total Return =

(Expected Terminal Value + Expected Cash Dividends − Current Price)
÷
Current Price

و:

Expected Annualized Total Return =

((Expected Terminal Value + Expected Cash Dividends) ÷ Current Price)^(1 / T)
− 1

### Short-Horizon Rule

إذا T أقل بكثير من سنة:

- اعرض **Absolute Expected Return** أولًا.
- يمكن عرض annualized number كمرجع فقط.
- لا تستخدم annualization القصير لإظهار عائد مضلل أو مبالغ فيه.

### Required-Return / Opportunity Spread

#### Investable Benchmark Rule — REQUIRED

لـOpportunity Cost استخدم **العائد الذي يستطيع المستثمر الوصول إليه فعليًا**، وليس Policy Rate وحده.

ترتيب المرجع المفضل:

1. Actual cash / money-market instrument available to the portfolio.
2. Representative investable money-market / fixed-income fund return after material fees/taxes when known.
3. Expected path of that investable return over the same investment horizon.
4. CBE policy rate كـmacro reference فقط إذا لم يتوفر benchmark قابل للاستثمار.

لا تستخدم Current 1-day / current policy yield كأنه مضمون طوال 2–3 سنوات.

حدد:

INVESTABLE CASH BENCHMARK = [instrument / proxy]

EXPECTED NET CASH RETURN OVER HORIZON = [ ] / NOT RELIABLE

ثم قارن:

Expected Annualized Total Return
−
Expected Investable Money-Market / Cash Return

و

Expected Annualized Total Return
−
Relevant Benchmark Expected Return

صنف:

EXPECTED RETURN SPREAD =

STRONGLY POSITIVE / POSITIVE / MARGINAL / NEGATIVE / NOT RELIABLE

### Rule

Fair Value وحدها لا تكفي للحكم على جاذبية الاستثمار.

Upside 25% خلال 6 أشهر يختلف اقتصاديًا عن Upside 25% خلال 3 سنوات.



## Investor Return Attractiveness — REQUIRED

قارن Expected Annualized Total Return مع:

- PERSONAL / PORTFOLIO REQUIRED RETURN.
- Expected cash / money-market alternative.
- Relevant equity benchmark.
- Best comparable stock opportunities عند توفرها.

صنف:

RETURN ATTRACTIVENESS =

EXCEEDS HURDLE

MEETS HURDLE

BELOW HURDLE

INFERIOR CAPITAL USE

NOT RELIABLE

### Critical Semantic Rule

`RETURN ATTRACTIVENESS = BELOW HURDLE`

لا يغير Economic Valuation إلى OVERVALUED.

مثال مسموح:

- Economic Valuation = FAIR.
- Return Attractiveness = BELOW HURDLE.
- Trading Attractiveness = STRONG.

---


# Valuation Sensitivity Envelope & Decision Price Ladder — REQUIRED

Fair Value ليست نقطة سحرية واحدة.

حدد أهم 2–3 assumptions تحرك التقييم، ثم أنشئ Sensitivity مناسبًا لطبيعة الشركة.

## A. Earnings-Multiple Sensitivity — WHEN APPLICABLE

استخدم Matrix مثل:

Sustainable EPS scenario
×
Reasonable P/E scenario

مثال structure:

| Sustainable EPS | Low Multiple | Base Multiple | High Multiple |
|---|---:|---:|---:|
| Bear EPS | | | |
| Base EPS | | | |
| Bull EPS | | | |

لا تستخدم هذه المصفوفة إذا P/E غير مناسب اقتصاديًا.

## B. DCF Sensitivity — WHEN APPLICABLE

اختبر على الأقل:

- Discount rate / WACC.
- Terminal growth.
- Margin / FCF normalization عند الحاجة.

## C. RNAV / SOTP Sensitivity — WHEN APPLICABLE

اختبر:

- Asset-value haircut.
- Holding discount.
- Debt / parent adjustments.
- Monetization probability.

## Required Output

حدد:

ROBUST FAIR-VALUE RANGE = [ ]

CENTRAL / BLENDED FAIR VALUE = [ ]

### Fair-Value Range Width / Quality — REQUIRED

احسب عندما تكون الحدود موثوقة:

FV Range Width =

(High Robust FV − Low Robust FV)
÷
Central FV

ثم صنف بصورة **descriptive**:

FV RANGE QUALITY =

NARROW / MODERATE / WIDE / VERY WIDE / NOT RELIABLE

لا تستخدم thresholds عالمية ثابتة قبل calibration قطاعي؛ اشرح magnitude والسبب.

### Rule

إذا Robust Range واسع جدًا:

- لا تعتبر كل السعر داخل الـrange = FAIR تلقائيًا.
- أعطِ وزنًا أكبر لـPW/Central FV، scenario probabilities وMarket-Implied Expectations.
- اخفض Valuation Confidence عند الحاجة.

KEY DECISION PIVOT = [assumption]

VALUATION MODEL RISK =

LOW / MEDIUM / HIGH / NOT RELIABLE

### Required-Return Entry Price

إذا يوجد Target / Required Annual Return وReturn Horizon:

Max Entry Price for Required Return =

(Expected Terminal Value + Expected Cash Dividends)
÷
(1 + Required Annual Return)^T

هذا السعر يجيب:

> ما أعلى سعر يمكن دفعه اليوم مع بقاء العائد المتوقع مساويًا للعائد المطلوب؟

إذا Expected Terminal Value نفسه احتمالي:

استخدم Probability-Weighted terminal value على نفس horizon.

### Price Decision Ladder

أنشئ فقط من Economics الموثوقة، وليس من نسب ثابتة اعتباطية:

- Deep / Strong Value Zone = [if defensible].
- Required-Return Entry Price = [ ].
- Attractive Entry Zone = [ ].
- Central Fair Value = [ ].
- Optimistic / Bull Fair Value = [ ].
- Fundamental Overvaluation Zone = [ ].

### Hard Rule

لا تنشئ Buy Zone بإضافة أو طرح 10% أو 20% بصورة آلية.

كل Level يجب أن يرجع إلى:

- required return,
- scenario economics,
- valuation sensitivity,
- or defensible market/asset anchor.

---

# Cross-Sectional Valuation Calibration Audit — REQUIRED FOR BATCH / UNIVERSE USE

إذا تم تشغيل الـFunnel على عدة أسهم أو shortlist كبيرة:

احسب توزيع Economic Valuation classifications.

مثال:

- % CHEAP
- % ATTRACTIVE
- % FAIR
- % RICH BUT PLAUSIBLE
- % OVERVALUED
- % SEVERE FUNDAMENTAL DETACHMENT
- % UNRELIABLE

### Calibration Warning

إذا نسبة كبيرة بصورة غير معتادة من **representative diversified sample** خرجت:

OVERVALUED / SEVERE FUNDAMENTAL DETACHMENT

لا تغيّر النتائج آليًا، لكن فعّل:

VALUATION MODEL CALIBRATION WARNING = YES

ثم راجع:

- normalized rate assumption,
- Reasonable P/E / discount-rate logic,
- Sustainable Earnings haircuts,
- positive/negative evidence symmetry,
- dilution assumptions,
- nominal/real consistency,
- asset-value treatment,
- sample-selection bias.

### Selection Caveat

إذا العينة مأخوذة أساسًا من:

- top gainers,
- breakout scanner,
- unusual volume,
- momentum,
- hot catalysts,

فارتفاع نسبة RICH/OVERVALUED قد يكون طبيعيًا بسبب Selection Bias.

لا تستخدم هذه العينة للحكم على EGX بالكامل.

### Batch Audit Result

VALUATION MODEL CALIBRATION WARNING =

YES / NO / NOT APPLICABLE

SAMPLE REPRESENTATIVENESS =

HIGH / MEDIUM / LOW / NOT RELIABLE

---

# Stage 6 Result

ECONOMIC VALUATION =

CHEAP

ATTRACTIVE

FAIR

RICH BUT PLAUSIBLE

OVERVALUED

SEVERE FUNDAMENTAL DETACHMENT

UNRELIABLE

Confidence =

HIGH / MEDIUM / LOW

VALUATION STATUS =

CURRENT / NEEDS DELTA / STALE / NOT RELIABLE

VALUATION DATE = [ ]

FINANCIAL DATA CUTOFF = [ ]

COMPANY NEWS CUTOFF = [ ]

CAPITAL STRUCTURE BASIS = [ ]

Base FDR = [ ]

Optimistic FDR = [ ]

Premium Above Optimistic FV = [ ]

FDR Classification = [ ]

Margin of Safety = [ ] / NOT RELIABLE

Upside to Fair Value = [ ] / NOT RELIABLE

Return Horizon = [ ]

Expected Total Return = [ ] / NOT RELIABLE

Expected Annualized Total Return = [ ] / NOT RELIABLE

Expected Return Spread = STRONGLY POSITIVE / POSITIVE / MARGINAL / NEGATIVE / NOT RELIABLE

Return Attractiveness = EXCEEDS HURDLE / MEETS HURDLE / BELOW HURDLE / INFERIOR CAPITAL USE / NOT RELIABLE

Multiple Calibration = WELL SUPPORTED / REASONABLE / WEAK / NOT RELIABLE

Nominal/Real Consistency = CLEAN / FAIL / NOT APPLICABLE

Valuation Time-Basis Consistency = CLEAN / ADJUSTMENT REQUIRED / NOT RELIABLE

Reverse-Valuation Horizon Match = CLEAN / ADJUSTMENT REQUIRED / NOT RELIABLE

Asymmetric Evidence Bias = YES / NO

RNAV / Earnings Overlap Check = CLEAN / PARTIAL OVERLAP ADJUSTED / MATERIAL OVERLAP / NOT RELIABLE / NOT APPLICABLE

Robust Fair-Value Range = [ ] / NOT RELIABLE

FV Range Width = [PERCENT] / NOT RELIABLE

FV Range Quality = NARROW / MODERATE / WIDE / VERY WIDE / NOT RELIABLE

Probability-Supported FV Region = [ ] / NOT RELIABLE

Probability-Supported FV Quality = HIGH / MEDIUM / COARSE / NOT RELIABLE

Highest Defensible Bull FV = [ ] / NOT RELIABLE

Bull Case Status = CREDIBLE / AGGRESSIVE BUT DEFENSIBLE / REMOTE-SPECULATIVE / NOT RELIABLE

Bull Case Probability = [PERCENT] / NOT RELIABLE

Highest Credible FV = [ ] / NOT RELIABLE

Bull Dependence = [PERCENT] / LOW / MODERATE / HIGH / VERY HIGH / BEYOND CREDIBLE BULL / NOT APPLICABLE / NOT RELIABLE

Bull-Pricing Consistency = STRONG / REASONABLE / WEAK / NOT APPLICABLE / NOT RELIABLE

Central / Blended Fair Value = [ ] / NOT RELIABLE

Valuation Model Risk = LOW / MEDIUM / HIGH / NOT RELIABLE

Decision Robustness = ROBUST / MODERATELY SENSITIVE / HIGHLY SENSITIVE / NOT RELIABLE

Key Decision Pivot = [ ]

Required-Return Entry Price = [ ] / NOT APPLICABLE / NOT RELIABLE

Investable Cash Benchmark = [ ] / NOT RELIABLE

Expected Net Cash Return Over Horizon = [PERCENT] / NOT RELIABLE

Present FV Date Basis = [DATE] / NOT RELIABLE

Terminal Value Horizon / Date = [ ] / NOT APPLICABLE / NOT RELIABLE

Valuation Model Calibration Warning = YES / NO / NOT APPLICABLE

Sample Representativeness = HIGH / MEDIUM / LOW / NOT RELIABLE / NOT APPLICABLE

Market-Implied Expectations = EASY EXECUTION / PLAUSIBLE EXECUTION / DEMANDING EXECUTION / VERY DEMANDING EXECUTION / ECONOMICALLY IMPLAUSIBLE / NOT RELIABLE

لا تنتقل للشارت.

---

# Stage 7 — Catalyst Gate

حدد Catalysts خلال 3–12 شهرًا.

فرق بين:

Fundamental Catalyst

Trading Catalyst

Structural Catalyst

Optionality Catalyst

---

## For Each Catalyst

حدد:

- Event.
- Date.
- Source.
- Stage.
- Economic Impact.
- Is it new?
- Is it priced in?
- Remaining repricing potential.
- What future KPI proves success?
- Whether it is already included in Base/Bull FV.

---

## Open Catalyst Inventory

راجع المحفزات غير المنتهية خلال آخر 60 يومًا على الأقل، واستخدم Stage 0.5 Open Projects / Contracts / Optionality.

صنف كل Catalyst:

OPEN

PARTLY PRICED

FULLY PRICED

FAILED

EXPIRED

UNCERTAIN

---

## Negative Catalysts

راجع:

- Earnings deterioration.
- Dilution.
- Supply overhang.
- Regulatory risk.
- Debt/refinancing.
- Major-holder selling.
- Governance.
- Delisting/suspension.
- Weak return from capital raise.
- Project delay.
- Contract cancellation.
- Failure to monetize Optionality.

---

## Event Calendar & Horizon-Collision Gate — REQUIRED

حوّل Catalysts وCorporate Actions إلى Calendar زمني قابل للتنفيذ.

راجع قدر الإمكان:

- Earnings / financial-results dates.
- Board / AGM / EGM dates ذات الأثر المادي.
- Rights record / ex-right / subscription / allocation / listing dates.
- Dividend record / ex-dividend / payment dates.
- Tender-offer / acquisition deadlines.
- Debt maturity / refinancing milestones.
- Regulatory decisions / license expiries.
- Project commissioning / contract milestone dates.
- Lock-up / strategic-holder release dates إذا كانت موثقة ومادية.
- Any known event capable of causing a gap or changing tradability.

أنشئ:

| Event | Confirmed / Estimated Date | Evidence | Inside Intended Horizon? | Gap / Structural Risk | Action Implication |
|---|---|---|---|---|---|
| | | | YES / NO | LOW / MEDIUM / HIGH / BINARY | |

حدد:

HORIZON EVENT COLLISION =

NONE / MANAGEABLE / MATERIAL / BINARY / NOT RELIABLE

### Rule

إذا حدث Binary أو Capital-Structure Event يقع قبل الخروج المتوقع:

- لا تستخدم Stop/Invalidation وحده كأن التنفيذ مضمون.
- ارفع Event Risk.
- عدّل Position Size أو Entry Timing.
- اذكر صراحة احتمال Gap Through Stop.

---

# Stage 7 Result

Catalyst Strength =

STRONG / MODERATE / WEAK

Horizon Event Collision =

NONE / MANAGEABLE / MATERIAL / BINARY / NOT RELIABLE

---

# Stage 8 — Speculation Classification

صنف [TICKER] قبل Timing Analysis.

افحص:

- Average trading value.
- Volume.
- Trade count.
- Free Float.
- Liquidity concentration.
- ±10–20% sessions.
- Gaps.
- Reversal speed.
- Major-holder activity.
- Capital Actions.
- Price vs earnings.
- Fully Diluted valuation.
- Price/Volume behavior.
- FOMO behavior.
- Economic explainability.
- Rights-price interaction when applicable.

---

## Primary Classification

اختر واحدًا فقط:

INVESTMENT QUALITY

HYBRID

SPECULATIVE

HIGHLY SPECULATIVE

---

## Driver Classification — REQUIRED

حدد المحرك الرئيسي:

FUNDAMENTAL-LED

CATALYST-LED

FLOW-LED

CAPITAL-ACTION-LED

M&A-LED

MIXED

---

## Behavioral Repricing Family — REQUIRED WHEN APPLICABLE

إذا كان السهم في حالة Momentum / breakout / capital-action / NAV dislocation، صنف **النمط العام** أولًا، ثم اذكر historical analogue إن كان مفيدًا.

FLOW-DRIVEN BEHAVIORAL BUBBLE

- Historical analogue example: BIOC-type.

RIGHTS REFLEXIVITY

- Historical analogue example: LUTS-type.

DELAYED-CATALYST CONTINUATION / REPRICING

- Historical analogue example: KORA-type.

BREAKOUT REJECTION

- Historical analogue example: MPCI-type.

NAV DISLOCATION

- Historical analogue example: KASABF-type.

HIGH-BASE SECOND-LEG

- Historical analogue example: SWDY-type.

OTHER

INCONCLUSIVE

### Anti-Anchoring Rule

لا تبدأ بالسؤال “هل يشبه KORA/MPCI؟”.

ابدأ بالخصائص الموضوعية:

- catalyst state.
- impulse size.
- volume/turnover.
- breakout acceptance.
- base retention.
- rejection.
- rights relation.
- NAV relation.

ثم استخدم historical analogue كتوضيح فقط، لا كدليل.

### Rule

Behavioral Family هو Timing / Market-Structure descriptor فقط.

لا يرفع:

- Company Quality.
- Earnings Quality.
- Fair Value.
- Investment Quality.

ولا يمكنه إلغاء Fundamental FAIL أو Valuation FAIL.

---

## Selection-Bias Check — REQUIRED

اسأل:

هل السهم تم اختياره للتحليل لأنه:

- Top gainer؟
- عليه Catalyst؟
- ظهر في Scanner؟
- تحرك 20–100% بالفعل؟

إذا نعم:

اذكر أن العينة قد تكون منحازة نحو الأسهم التي **already rerated** أو ذات Momentum مرتفع.

### Mandatory Selection-Bias Output

SELECTION BASIS =

RANDOM / BROAD UNIVERSE / FUNDAMENTAL SCREEN / MOMENTUM SCREEN / TOP GAINER / CATALYST SCREEN / USER-SELECTED / OTHER

SELECTION-BIAS RISK =

LOW / MEDIUM / HIGH

### Hard Rule

لا تستنتج أن:

- "EGX كله غالي"
- "معظم الأسهم Overvalued"
- "لا توجد فرص"

من عينة اختيرت أساسًا بسبب:

- الصعود،
- breakout،
- unusual volume،
- أو الأخبار الساخنة.

إذا أردت market-wide inference:

استخدم representative cross-sectional sample أو universe scan.

---

# Stage 8 Result

Speculation Classification =

INVESTMENT QUALITY / HYBRID / SPECULATIVE / HIGHLY SPECULATIVE

Driver =

FUNDAMENTAL-LED / CATALYST-LED / FLOW-LED / CAPITAL-ACTION-LED / M&A-LED / MIXED

Behavioral Repricing Family =

FLOW-DRIVEN BEHAVIORAL BUBBLE / RIGHTS REFLEXIVITY / DELAYED-CATALYST CONTINUATION / BREAKOUT REJECTION / NAV DISLOCATION / HIGH-BASE SECOND-LEG / OTHER / INCONCLUSIVE / NOT APPLICABLE

Historical Analogue = [ ] / NOT APPLICABLE

Investment Attractiveness and Breakout Probability must remain separate.

---

# Stage 9 — Timing & Execution Gate

استخدم أحدث جلسة موثوقة.

لا تغير Fundamental Judgment بسبب الشارت.

---

## 9.0 Standardized Time Windows & Adjusted-History Rule — REQUIRED

استخدم نفس النوافذ قدر الإمكان لتقليل model drift:

- MICRO = 1–3 sessions.
- SHORT = 5 sessions.
- TACTICAL = 20 sessions.
- INTERMEDIATE = 60 sessions.
- STRUCTURAL = 120–250 sessions.

### Standard Comparisons

احسب/قدّر عند توفر البيانات:

- Volume Ratio 20D = Current Volume ÷ 20-session median volume.
- Value Ratio 20D = Current Trading Value ÷ 20-session median trading value.
- RS5 vs EGX100.
- RS20 vs EGX100.
- RS60 vs EGX100.
- Distance from 20D high/base.
- Distance from 60D high/base.
- ATR / realized volatility where useful.

### Corporate-Action Adjustment Rule

عند وجود split / bonus / rights / merger / major capital action:

- استخدم adjusted historical price/volume basis عندما يكون ذلك لازمًا للمقارنة.
- لا تقارن pre-action resistance أو moving average مع post-action price دون bridge.

إذا data provider adjustment غير موثوق:

TECHNICAL HISTORY INTEGRITY = NOT RELIABLE

---

## Market Structure

حلل:

- Trend.
- Support.
- Resistance.
- Volume vs normal.
- Trade count.
- Transaction velocity.
- Relative Strength vs EGX100.
- Moving averages.
- RSI إذا كان مفيدًا.
- Breakout.
- Failed Breakout.
- Failed Breakdown/Reclaim.
- Accumulation hypothesis.
- Distribution.
- Absorption.
- Executed order flow.
- Rights/share arbitrage pressure when applicable.

---

## 9.1 Psychological / Behavioral Price Map — REQUIRED FOR TIMING

Psychological Price هو **Behavioral / Market-Structure reference** وليس Fair Value.

لا تستخدمه لتغيير:

- Company Quality.
- Sustainable Earnings.
- Fundamental Fair Value.
- Investment Quality.

استخدمه لفهم:

- أين قد تتجمع الأوامر والانتباه؟
- أين توجد Market Memory أو trapped holders؟
- أين قد يظهر FOMO / profit-taking؟
- وما المسافة السلوكية المتاحة بعد breakout؟

### Candidate Psychological Anchors

ابحث عن:

1. Round-number / price-clustering levels.
2. Prior major highs / lows.
3. 20D / 60D / 52-week extremes.
4. Repeated support / resistance reactions.
5. High Volume-at-Price nodes.
6. Anchored VWAP from a material event / impulse / disclosure.
7. IPO / placement / tender / rights subscription / TERP / capital-action reference prices.
8. Major gap origin / prior breakout / failed-breakout levels.
9. Trapped-holder / breakeven supply zones.
10. Historically important price levels with recent executed evidence.

### 52-Week Anchor

احسب عند الإمكان:

52W High Proximity =

Current Price
÷
52-Week High

استخدمه كـbehavioral anchor فقط، وليس Buy/Sell rule مستقلًا.

---

### Psychological Level Strength Score — PLSS

لكل Candidate Level أو Zone، قيّم:

| Component | Initial Max Score |
|---|---:|
| Round-number / observed price-clustering strength | 15 |
| Volume-at-Price concentration | 25 |
| Repeated reaction / market-memory evidence | 20 |
| Anchored VWAP proximity + anchor materiality | 15 |
| Corporate-action / official event price anchor | 15 |
| Recency / current relevance | 10 |
| **Total** | **100** |

PLSS = sum of the non-duplicative component scores.

### PLSS Evidence Coverage — REQUIRED

لا تعرض PLSS كأنه 0–100 كامل إذا بعض المكونات غير متاحة أصلًا.

احسب:

Available PLSS Maximum =

sum of maximum points for components with usable evidence

ثم:

PLSS Evidence Coverage =

Available PLSS Maximum
÷
100

واعرض النتيجة بصيغة مثل:

> PLSS Observed = 43 / 60 available points; Coverage = 60%

### Coverage Rule

- لا تملأ component مفقودًا بصفر وكأنه Negative Evidence.
- Missing evidence ≠ evidence of weakness.
- لا تقارن score 65 المبني على 95% coverage مع score 65 المبني على 50% coverage كأنهما متساويان.
- إذا Coverage منخفضة materially، اخفض Psychological Map Confidence.
- إذا Available PLSS Maximum غير كافٍ للحكم، استخدم `PLSS = NOT RELIABLE / INSUFFICIENT COVERAGE`.

يمكن عرض normalized 0–100 equivalent كمرجع فقط عندما coverage كافية، لكن يجب إظهار Raw/Available score بجانبه.

### Initial Classification

PLSS < 30 = WEAK

30–49 = MODERATE

50–69 = STRONG

70–84 = VERY STRONG

85–100 = DOMINANT

### Critical Calibration Rule

هذه weights والthresholds **HEURISTIC INITIALIZATION** وليست قانونًا علميًا ثابتًا.

المكونات الأساسية مثل round-number clustering وreference-price anchoring لها أساس سلوكي/تجريبي في الأدبيات، لكن **PLSS composite نفسه هو framework مخصص لهذا الـFunnel** ويحتاج EGX validation.

لا تحول PLSS إلى Hard Buy/Sell threshold قبل Historical EGX calibration في Stage 9.5.

---

### Component Guidance

#### A. Round-Number Strength

إذا تتوفر transaction/order data:

- اختبر هل trades/orders تتجمع حول round increment أكثر من nearby comparable increments.
- لا تعتمد على roundness البصري فقط.

إذا لا تتوفر:

- استخدم Round Number كـweak prior فقط.
- لا تمنحه score مرتفعًا دون confluence.

#### B. Volume-at-Price Concentration

حدد Zone حول المستوى.

احسب عند الإمكان:

VAP Concentration =

Volume traded inside Zone
÷
Total volume in selected lookback

ثم قارنها مع equal-width neighboring price bins أو percentile داخل distribution.

High absolute volume وحده لا يكفي إذا كان كل النطاق عالي الحجم.

#### C. Market-Memory / Reaction Evidence

احسب distinct sessions—not repeated prints in the same session—التي ظهر فيها:

- rejection,
- support,
- reclaim,
- acceleration,
- or heavy execution around the level.

استخدم recency weighting عندما يكون مناسبًا.

#### D. Anchored VWAP

اربط VWAP بحدث اقتصادي أو سلوكي واضح مثل:

- catalyst disclosure,
- first impulse,
- breakout,
- rights event,
- high-volume reversal.

Anchored VWAP بلا anchor مبرر لا يحصل على full score.

#### E. Event / Corporate Price Anchor

أمثلة:

- subscription price,
- TERP,
- placement price,
- IPO price,
- tender price,
- acquisition consideration reference.

لا تعتبر هذه الأسعار Fair Value تلقائيًا.

#### F. Recency

الـlevel القديم جدًا بدون current interaction يحصل على وزن أقل من level حديث أو تمت إعادة اختباره مؤخرًا.

---

### Psychological Zone Width

استخدم Zone بدل exact price.

ابدأ بصورة heuristic من:

Psychological Zone Half-Width =

MAX(
3–5 valid price ticks,
0.20 × ATR20,
normal spread allowance when material
)

إذا liquidity ضعيفة أو spread غير طبيعي:

- وسّع zone بصورة مبررة.
- لا تدّعي precision غير موجود.

---

### Confluence Independence / No Double Counting — REQUIRED

لا تجمع نفس الدليل مرتين.

مثال:

- “52-week high”
- “prior major high”
- “repeated resistance”

قد تكون كلها نفس historical price event.

إذا كانت الأدلة مترابطة:

- خفض combined contribution.
- اشرح أن confluence ليس independent.

Psychological confluence يصبح أقوى عندما تأتي anchors مستقلة اقتصاديًا، مثل:

Round number
+
High Volume-at-Price
+
Anchored VWAP
+
Official capital-action price.

---

### Level Function — DO NOT ASSUME EVERY ROUND NUMBER IS A WALL

لكل Level صنف الوظيفة من evidence:

LEVEL FUNCTION =

MAGNET / SUPPORT / RESISTANCE / BREAKOUT TRIGGER / SUPPLY-RELEASE LEVEL / MIXED / INCONCLUSIVE

Round-number clustering قد يجذب أوامر وانتباهًا دون أن يمنع السعر من المرور.

لا تستخدم `ROUND NUMBER = RESISTANCE` بصورة آلية.

---

### Trapped-Holder / Breakeven Supply Zone

ابحث عن منطقة:

- تداول عندها حجم كبير،
- ثم هبط السعر ماديًا،
- ثم عاد إليها لاحقًا.

صنف:

TRAPPED-HOLDER SUPPLY =

LOW / MODERATE / HIGH / NOT RELIABLE

إذا تجاوز السعر المنطقة مع:

- heavy executed volume,
- offer depletion,
- strong close,
- and follow-through,

فهذا قد يعني أن supply تم امتصاصه جزئيًا أو كليًا.

---

### Psychological Breakout Clearance — REQUIRED WHEN APPLICABLE

حدد:

Psychological Breakout Trigger = [ ]

Next Strong Psychological Resistance = [ ]

ثم:

Psychological Clearance =

(Next Strong Psychological Resistance − Breakout Trigger)
÷
Breakout Trigger

هذا يقيس المسافة السلوكية التقريبية حتى المقاومة النفسية/المرجعية القوية التالية.

### Rule

Clearance وحده لا يكفي للدخول.

يجب دمجه مع:

- breakout acceptance,
- liquidity,
- friction,
- market tape,
- valuation detachment,
- and exit capacity.

---

### Psychological Price Map — REQUIRED OUTPUT

اعرض:

| Behavioral Price Item | Level / Zone | PLSS | Function | Evidence |
|---|---:|---:|---|---|
| Nearest Psychological Support | | | | |
| Nearest Psychological Resistance | | | | |
| Dominant Psychological Level | | | | |
| Trapped-Holder Zone | | | | |
| Psychological Breakout Trigger | | | | |
| Next Strong Psychological Resistance | | | | |

ثم أعطِ:

PSYCHOLOGICAL MAP CONFIDENCE =

HIGH / MEDIUM / LOW / NOT RELIABLE

Psychological levels remain Timing/Execution evidence only.

---

## Breakout Acceptance Test — REQUIRED

A breakout is not confirmed by the intraday high alone.

عند توفر High/Low/Close صالحين، احسب:

Close Location Value — CLV =

(Close − Low)
÷
(High − Low)

ثم افحص:

- Close vs breakout level.
- Upper wick / rejection.
- هل قضى السعر وقتًا ذا معنى فوق breakout؟
- هل توجد executed transactions عند الأسعار الأعلى؟
- هل تحسن spread/depth أم تدهور؟
- +1 session follow-through.
- +2 session follow-through عندما تتوفر.

صنف:

BREAKOUT ACCEPTANCE =

STRONG / PARTIAL / WEAK / FAILED / NOT YET TESTED

### Interpretation

Delayed-catalyst continuation pattern: breakout + strong acceptance يمكن أن يدعم continuation.

Breakout-rejection pattern: high touch + weak close + no follow-through = rejection، وليس breakout ناجحًا.

---

## Price-Impact Compression Rule — REQUIRED

HIGH TURNOVER + LOW PRICE RESPONSE =

UNRESOLVED SUPPLY / DEMAND BATTLE

وليس Accumulation تلقائيًا.

لا تُرقِّ الإشارة إلى Accumulation إلا إذا ظهر لاحقًا دليل مثل:

- Higher lows.
- Offer depletion.
- Buyers lifting offers.
- Acceptance at higher prices.
- Positive relative strength.
- Follow-through.

High activity + falling price = DISTRIBUTION-POSSIBLE حتى يثبت العكس.

---

## Trading-at-Last / Closing-Mechanism Exclusion — REQUIRED

Repeated identical-price executions خلال Closing Auction أو Trading-at-Last لا تثبت وحدها:

- Accumulation.
- Absorption.
- Distribution.
- Fresh price discovery.

لا تستخدمها في absorption score إلا إذا دعمها:

- Continuous-session executed evidence قبل الإغلاق.
- ثم subsequent ability to lift offers / accept higher prices.

---

## High-Base Second-Leg Test — REQUIRED WHEN APPLICABLE

بعد First Impulse قوي، اختبر هل السهم بنى Higher Base بدل انهيار الحركة.

احسب عند الإمكان:

Breakout Retention Ratio =

(Lowest Consolidation Close − Old Base Reference)
÷
(First Impulse Close − Old Base Reference)

ثم صنف:

OLD-BASE RE-ENTRY =

NO RE-ENTRY / BRIEF RE-ENTRY + RECLAIM / SUSTAINED RE-ENTRY

لا تستخدم Threshold ثابت للـRetention كقاعدة شراء بدون Validation.

صنف المسار:

### IMMEDIATE CONTINUATION
Delayed-catalyst continuation pattern.

### HIGHER-BASE / SECOND-LEG
High-base second-leg pattern.

### BREAKOUT REJECTION
Breakout-rejection pattern.

### INCONCLUSIVE
إذا البيانات غير كافية.

---

## Rights Reflexivity Test — REQUIRED WHEN APPLICABLE

إذا يوجد Right متداول:

حدد:

- Rights Required per New Share.
- Right Market Price.
- Subscription Price per New Share.
- Execution Friction.

احسب تقريبًا:

Right-Implied Share Cost =

Subscription Price
+
(Rights Required per New Share × Right Market Price)
+
Execution Friction

ثم قارن مع Ordinary Share Price على timestamp/session basis متقارب.

حدد:

RIGHTS RELATION =

RIGHT CHEAPER / APPROXIMATELY ALIGNED / ORDINARY SHARE CHEAPER / NOT RELIABLE

إذا entitlement ratio غير معروف أو الأسعار من أوقات مختلفة بصورة مادية:

RIGHTS RELATION = NOT RELIABLE

إذا Right-Implied Share Cost أقل ماديًا من السهم العادي:

قد يوجد ضغط مؤقت على السهم نتيجة التحول من Ordinary Share إلى Rights Strategy.

هذا:

- Timing factor.
- Flow factor.

وليس Fair Value proof.

---

## Order Book Rule

فرق بين:

Displayed Orders

و

Executed Trades.

لا تعتبر Bid كبير دليل شراء.

Absorption يحتاج:

- بيع فعلي كبير.
- عدم تدهور السعر.
- Bid replenishment.
- ثم قدرة المشترين على رفع السعر/أكل العروض.

---

## Tradability, Market-Segment, Price-Limit & Fillability Gate — REQUIRED

قبل إصدار أي Entry Action، تحقق من أن الصفقة **قابلة للتنفيذ فعليًا** تحت قواعد السوق والحساب المستخدمة في تاريخ التحليل.

راجع من أحدث EGX/FRA/broker evidence عند الحاجة:

- Current market board / segment classification.
- Current security trading status.
- Tick size.
- Current daily price limit / temporary-suspension threshold.
- Distance to upper/lower permitted price boundary.
- Intraday / T+1 eligibility where relevant.
- Settlement cycle.
- Short-selling eligibility only if relevant to the requested strategy.
- Broker/account restrictions that may prevent same-day exit or specific order types.
- Corporate-action temporary trading restrictions.
- Current suspension / resumption conditions.

### Fresh-Rules Requirement

لا hard-code قواعد EGX المتغيرة داخل التقييم وكأنها دائمة.

تحقق من القواعد الحالية عند كل حالة يكون فيها التنفيذ حساسًا لها.

---

### Price-Limit / Queue Risk

إذا السهم عند أو قرب Upper Price Limit أو Lower Price Limit:

لا تفترض أن displayed price = executable entry/exit.

افحص:

- Are there executable opposite-side orders?
- Executed trades at/near the limit.
- Queue size and depletion.
- New supply/demand entering.
- Time spent locked.
- Spread/depth after any resumption.
- Probability of adverse selection if fill occurs only when the queue starts reversing.

صنف:

FILLABILITY =

NORMAL / QUEUE-DEPENDENT / LOW FILL PROBABILITY / NOT EXECUTABLE / NOT RELIABLE

### Upper-Limit Chase Rule

إذا:

- price locked near upper boundary,
- offers absent/thin,
- and realistic fill probability منخفضة,

فلا تصدر Entry Price كما لو كان guaranteed.

استخدم:

`SETUP STRONG — ENTRY NOT CURRENTLY EXECUTABLE`

إذا كان ذلك هو الوصف الصحيح.

### Exit-Constraint Rule

إذا Intended Horizon يتطلب same-day أو rapid exit لكن:

- security/account rules,
- settlement constraints,
- price-limit lock,
- or market segment

تمنع ذلك عمليًا:

الاستراتيجية نفسها = NOT EXECUTABLE

حتى لو كان setup جذابًا نظريًا.

---

## Entry Framework

حدد:

Entry Zone

Confirmation Level

Do-Not-Chase Level

Invalidation Level

First Target

Reward/Risk after friction

---

## Trading Friction Model — REQUIRED FOR EXECUTION

قبل حساب Reward/Risk، قدّر أو سجل عند الإمكان:

- Bid/Ask spread.
- Expected slippage on entry.
- Expected slippage on exit.
- Brokerage/platform charges.
- Exchange/regulatory charges.
- Applicable taxes/levies.
- Rights-related execution/subscription friction when applicable.

TOTAL ROUND-TRIP FRICTION = [EGP and %]

NET REWARD = Gross Target Profit − Total Expected Friction

NET RISK = Gross Stop/Invalidation Loss + Total Expected Friction

Reward/Risk after friction =

Net Reward ÷ Net Risk

### Freshness Rule

أي fee/tax assumption متغير يجب أن يحمل source/date أو يصنف ESTIMATE / NOT VERIFIED.

---

## Entry Type — REQUIRED

حدد نوع الدخول:

VALUE ENTRY

PULLBACK ENTRY

BREAKOUT ENTRY

RECLAIM ENTRY

SPECULATION ENTRY

NO ENTRY

---

## Exit Capacity & Maximum Executable Position — REQUIRED

لا تبدأ بافتراض Position Size ثم تكتشف بعد ذلك أنها غير قابلة للخروج.

حدد أولًا:

- 20-session median Average Daily Trading Value / ADTV أو أفضل normal-liquidity estimate.
- Average Daily Volume.
- Near-touch executable liquidity.
- Spread.
- Expected slippage.
- Conservative Participation Rate = [state assumption].
- Acceptable Liquidation Days = [state assumption].

احسب تقريبًا:

Liquidity-Based Maximum Position =

ADTV
× Conservative Participation Rate
× Acceptable Liquidation Days

ثم عدّل لأسفل إذا near-touch depth / spread / volatility تفرض حدًا أكثر تحفظًا.

إذا Proposed Position Value معروف:

احسب أيضًا:

Proposed Position Value ÷ ADTV

و

Estimated Days to Liquidate at Conservative Participation.

صنف:

EXIT CAPACITY =

NORMAL / CONSTRAINED / POOR

MAXIMUM EXECUTABLE POSITION = [EGP] / NOT RELIABLE

### Rule

Stage 10 Maximum Weight لا يجوز أن يتجاوز Liquidity-Based Maximum Position دون مبرر واضح.

---

# Stage 9 Result

Psychological Map Confidence =

HIGH / MEDIUM / LOW / NOT RELIABLE

Dominant Psychological Level = [ ] / NOT RELIABLE

Dominant PLSS = [RAW / AVAILABLE MAX] / [0–100 equivalent if justified] / NOT RELIABLE

PLSS Evidence Coverage = [PERCENT] / NOT RELIABLE

Nearest Psychological Support = [ ] / NOT RELIABLE

Nearest Psychological Resistance = [ ] / NOT RELIABLE

Psychological Breakout Trigger = [ ] / NOT APPLICABLE / NOT RELIABLE

Psychological Clearance = [PERCENT] / NOT APPLICABLE / NOT RELIABLE

Fillability =

NORMAL / QUEUE-DEPENDENT / LOW FILL PROBABILITY / NOT EXECUTABLE / NOT RELIABLE

Timing Quality =

GOOD / NEUTRAL / POOR

Execution Action =

ENTER NOW / ACCUMULATE / WAIT FOR PULLBACK / WAIT FOR CONFIRMATION / NO ENTRY

Breakout Acceptance =

STRONG / PARTIAL / WEAK / FAILED / NOT YET TESTED / NOT APPLICABLE

Breakout Retention Ratio = [ ] / NOT APPLICABLE

Old-Base Re-Entry =

NO RE-ENTRY / BRIEF RE-ENTRY + RECLAIM / SUSTAINED RE-ENTRY / NOT APPLICABLE

Rights Relation =

RIGHT CHEAPER / APPROXIMATELY ALIGNED / ORDINARY SHARE CHEAPER / NOT APPLICABLE / NOT RELIABLE

Technical strength لا يستطيع إلغاء Investment Hard Gate.

لكن Fundamental weakness لا يمنع Speculation تلقائيًا إذا لم يوجد Universal No-Trade Gate وكانت شروط speculation مستوفاة.

---

# Stage 9.5 — Signal Calibration, Base-Rate & Model-Risk Gate — REQUIRED FOR REPEATED SCANNER USE

هذا الـStage يمنع تحويل patterns وscores إلى “قوانين” لمجرد أنها نجحت في أمثلة قليلة.

لكل Behavioral / Timing signal مستخدم بصورة متكررة، مثل:

- PLSS.
- Breakout Acceptance.
- High-Base Second-Leg.
- Delayed-Catalyst Continuation.
- Breakout Rejection.
- Price-Impact Compression.
- Psychological Clearance.
- Volume/Value Ratio thresholds.
- RS thresholds.

احتفظ بـSignal Calibration Register عندما تتوفر بيانات تاريخية كافية.

## Required Register

| Signal | Exact Definition | Sample Window | N | +1 / +2 / +5 Session Outcome | Hit Rate | Median Return | Median MAE | Friction Included? | Regime Split | Status |
|---|---|---|---:|---|---:|---:|---:|---|---|---|
| | | | | | | | | YES / NO | | |

MAE = Maximum Adverse Excursion.

### Signal Status

VALIDATED

PROVISIONALLY CALIBRATED

HEURISTIC

INSUFFICIENT SAMPLE

NOT RELIABLE

### Base-Rate Rule

قبل القول إن Setup “high probability”:

اسأل:

> ما معدل نجاح setups المشابهة قبل رؤية هذه الحالة الحالية؟

إذا Base Rate غير معروف:

- لا تستخدم probability دقيقة.
- استخدم qualitative confidence فقط.

### Anti-Overfitting Rule

لا تعدّل thresholds بعد كل winner/loser منفرد.

أي تغيير threshold يجب أن يذكر:

- old threshold,
- new threshold,
- calibration sample,
- out-of-sample / later-period check إن أمكن,
- whether costs/slippage were included.

### No-Look-Ahead / Survivorship Rule

Stage 9.5 يخضع بالكامل لـPoint-in-Time Rule.

لا تدخل:

- stocks selected only because they later became winners,
- delisted/failed names بصورة انتقائية,
- hindsight catalyst classification,
- later-known share counts,
- later-known outcomes.

### PLSS Rule

إلى أن يتم backtest على عينة EGX مناسبة:

PLSS STATUS = HEURISTIC

ولا يجوز أن يكون PLSS وحده Hard Buy/Sell Gate.

---

# Stage 9.5 Result

SIGNAL CALIBRATION STATUS =

VALIDATED / PROVISIONALLY CALIBRATED / HEURISTIC / INSUFFICIENT SAMPLE / NOT APPLICABLE

PLSS STATUS =

VALIDATED / PROVISIONALLY CALIBRATED / HEURISTIC / INSUFFICIENT SAMPLE / NOT APPLICABLE

KEY BASE-RATE LIMITATION = [ ]

---

# Stage 10 — Portfolio Fit Gate

استخدم أحدث بيانات المحفظة المتاحة.

إذا بيانات المحفظة قديمة:

اذكر:

PORTFOLIO DATA STALE

---

## Exposure

افحص:

- Direct exposure.
- Indirect exposure via funds/indexes.
- Industry exposure.
- Sector concentration.
- Economic-driver concentration.
- Correlation.
- Duplication.
- Liquidity.
- Speculation allocation.

---

## Fresh Capital Test — REQUIRED

اسأل:

> لو كنت لا أملك السهم نهائيًا اليوم، هل سأختاره كواحد من أفضل استخدامات رأس المال الجديد بالسعر الحالي؟

الإجابة:

YES

BORDERLINE

NO

ممنوع استخدام:

- Cost basis.
- Unrealized loss.
- Desire to average down.
- Desire to break even.

كسبب استثماري.

---

## Opportunity-Cost Test — REQUIRED

قارن السهم مع:

- Cash / money-market alternative.
- Broad EGX exposure.
- Best available stock candidates.
- Other opportunities in same sector.

استخدم Stage 6 Expected Annualized Total Return عندما يكون موثوقًا.

احسب/قدّر:

Expected Return Spread vs Cash =

Stock Expected Annualized Return − Expected Cash/Money-Market Return

Expected Return Spread vs Benchmark =

Stock Expected Annualized Return − Relevant Benchmark Expected Return

ثم اسأل:

هل الاستثمار في هذا السهم أفضل استخدام لرأس المال الجديد مقارنة بالبدائل بعد ضبط:

- Horizon.
- Risk.
- Liquidity.
- Friction.
- Diversification value.

صنف:

TOP-TIER CAPITAL USE

ACCEPTABLE

INFERIOR

NOT RELIABLE

---

## Ownership State — REQUIRED

حدد:

NOT OWNED

OWNED

OWNED & OVERWEIGHT

OWNED & UNDERWEIGHT

---

## Position Sizing

فرق بين:

Investment Position

و

Speculation Position.

اقترح:

Starter Weight

Target Weight

Maximum Weight

مع مراعاة:

- Exit Capacity.
- Stage 9 Maximum Executable Position.
- Fundamental risk.
- Valuation risk.
- Event risk.
- Dilution.
- Correlation.
- Existing exposure.
- Speculation budget.

احسب:

Liquidity Weight Cap =

Maximum Executable Position ÷ Total Portfolio Value

ثم:

Maximum Allowed Weight =

min(
Portfolio Risk Limit,
Liquidity Weight Cap,
Concentration Limit,
Fundamental/Event Limit
)

إذا أي مدخل غير معروف، لا تخترع precision؛ أعطِ range أو NOT RELIABLE.

### Owned-Position Rule

إذا OWNED:

لا تجعل سعر الشراء Anchor للقرار.

اعمل القرار كما لو أن قيمة المركز أصبحت Cash اليوم.

ثم اسأل:

هل سأعيد شراء نفس السهم بنفس القيمة الآن؟

إذا NO:

لا تستخدم Break-even desire كسبب للاحتفاظ.

حدد مبدئيًا:

OWNED POSITION ACTION =

ADD / HOLD / TRIM / EXIT / NOT APPLICABLE

### Trim / Exit Logic

TRIM يصبح منطقيًا عندما يكون السهم ما زال قابلًا للاحتفاظ جزئيًا لكن:

- الوزن زائد.
- Expected Return Spread ضعيف.
- valuation متقدم.
- event/liquidity risk مرتفع.

EXIT يصبح منطقيًا عندما:

- thesis انكسرت.
- Fresh Capital Test = NO بصورة واضحة.
- Opportunity Cost = INFERIOR مع ضعف expected return.
- أو يوجد Universal No-Trade / severe unresolved risk يتطلب الخروج عندما تكون السيولة متاحة.

---

# Stage 10 Result

Portfolio Fit =

PASS

PASS WITH SIZE LIMIT

FAIL

Fresh Capital Test =

YES / BORDERLINE / NO

Opportunity Cost =

TOP-TIER CAPITAL USE / ACCEPTABLE / INFERIOR / NOT RELIABLE

Owned Position Action =

ADD / HOLD / TRIM / EXIT / NOT APPLICABLE

Maximum Allowed Weight = [ ] / NOT RELIABLE

---

# Stage 10.5 — Integrated Risk Engine — REQUIRED

لا تستخدم LOW / MEDIUM / HIGH / EXTREME كحكم انطباعي فقط.

قيّم خمس طبقات منفصلة:

## A. Fundamental Risk

- Business fragility.
- Earnings quality.
- Balance-sheet stress.
- Governance.
- Execution credibility.

## B. Valuation Risk

- FDR.
- Required earnings at current price.
- Margin of Safety / downside asymmetry.
- Degree of execution already priced in.

## C. Market / Behavioral Risk

- Volatility.
- Momentum extension.
- Breakout acceptance/rejection.
- Psychological-map strength / detachment when relevant.
- Market Tape Regime.
- Gap/reversal behavior.

## D. Liquidity / Execution Risk

- ADTV.
- Spread.
- Near-touch depth.
- Slippage.
- Exit Capacity.
- Position size vs executable liquidity.
- Fillability / queue risk.
- Price-limit / suspension mechanics when material.

## E. Event / Structural Risk

- Rights/capital action.
- Results/event date.
- Regulatory action.
- Suspension/delisting possibility.
- Major-holder supply.
- Project/contract binary events.
- Horizon Event Collision from Stage 7.

صنف كل طبقة:

LOW / MEDIUM / HIGH / EXTREME / NOT RELIABLE

ثم صنف:

OVERALL RISK =

LOW / MEDIUM / HIGH / EXTREME / NOT RELIABLE

### Aggregation Rule

لا تستخدم average بسيط يخفي خطرًا كارثيًا.

- EXTREME liquidity/event risk يمكن أن يرفع Overall Risk حتى لو كانت fundamentals جيدة.
- Universal No-Trade trigger يتغلب على Overall Risk label.
- وضّح أهم risk driver.

---

# Stage 11 — Final Decision Engine

اجمع نتائج جميع المراحل السابقة.

لا تعيد التحليل من البداية.

لا تغير رقمًا سابقًا إلا بسبب موثق.

---

# Decision Matrix

| Gate | Result |
|---|---|
| Analysis Objective / Horizon | |
| Run Mode | |
| Project Funnel Status / Update Mode | |
| Data Integrity | |
| News Delta | |
| Price Integrity | |
| Capital Structure Basis | |
| Valuation Freshness | |
| Business Quality | |
| Earnings Quality | |
| Financial Strength | |
| Growth | |
| Corporate Action / Dilution | |
| Market Valuation Regime | |
| Market Tape Regime | |
| Event Calendar / Horizon Collision | |
| Economic Valuation | |
| Margin of Safety / Upside | |
| Expected Total / Annualized Return | |
| Expected Return Spread | |
| Return Attractiveness | |
| Market-Implied Expectations | |
| Base FDR / Optimistic FDR | |
| Catalyst | |
| Speculation Classification | |
| Behavioral Repricing Family | |
| Psychological Price Map / PLSS | |
| Signal Calibration Status | |
| Breakout Acceptance | |
| Rights Relation | |
| Timing Quality | |
| Execution Action | |
| Exit Capacity / Max Executable Position | |
| Portfolio Fit | |
| Fresh Capital Test | |
| Opportunity Cost | |
| Unified Price Map | |
| Integrated Risk | |

---

# Unified Price Map — REQUIRED

اعرض جميع مستويات السعر المهمة في جدول واحد مع فصل **مصدر كل Level**.

| Price Layer | Level / Zone | Source | Meaning |
|---|---:|---|---|
| Current Executable Price | | Market | السعر القابل للتنفيذ حاليًا، وليس مجرد last print |
| Deep / Strong Value Zone | | Fundamental | إن كان defensible |
| Required-Return Entry Price | | Fundamental / Return | أعلى سعر يحقق required return |
| Attractive Fundamental Entry Zone | | Fundamental | من valuation sensitivity |
| Central / Blended Fair Value | | Fundamental | القيمة المركزية |
| Optimistic / Bull Fair Value | | Fundamental | أعلى قيمة اقتصادية قابلة للدفاع |
| Nearest Psychological Support | | Behavioral | Market-memory / clustering zone |
| Nearest Psychological Resistance | | Behavioral | Market-memory / clustering zone |
| Dominant Psychological Level | | Behavioral | أعلى confluence / PLSS |
| Psychological Breakout Trigger | | Behavioral / Technical | trigger لا يساوي Fair Value |
| Next Strong Psychological Resistance | | Behavioral | يستخدم في clearance |
| Technical Confirmation Level | | Technical | level required for setup confirmation |
| Do-Not-Chase Level | | Execution | فوقه trade economics تسوء |
| Invalidation Level | | Execution / Technical | thesis invalidation، وليس guaranteed fill |
| First Trading Target | | Execution / Technical | short-horizon target |
| Price-Limit Boundary | | Market Rule | إذا كان relevant |
| Rights-Implied Share Cost | | Capital Action | إذا كان applicable |

### Separation Rule

لا تدمج هذه المستويات في رقم واحد.

خصوصًا:

- Psychological Level ≠ Fair Value.
- Breakout Trigger ≠ Buy Price تلقائيًا.
- Fundamental Fair Value ≠ short-term Target تلقائيًا.
- Invalidation Level ≠ guaranteed Stop execution.
- Current Last Price ≠ Executable Price إذا liquidity/queue ضعيفة.

### Conflict Interpretation

إذا Fundamental وPsychological وTechnical levels تتقارب:

سمِّ ذلك:

`MULTI-LAYER PRICE CONFLUENCE`

لكن لا تضاعف Confidence تلقائيًا إذا كانت الأدلة مشتقة من نفس price history.

إذا تتعارض:

مثال:

- Fair Value أعلى بكثير،
- لكن strong psychological/technical resistance قريب،

اشرح:

> long-term economic upside may remain while near-term execution path is obstructed.

---

# Hard-Gate Rules

## A. Universal No-Trade / Entry-Blocker Gates — APPLY TO INVESTMENT AND SPECULATION

إذا تحقق أحد البنود التالية بصورة مادية وغير محلولة:

NEW ENTRY / ADD / ENTER SPECULATION = NO TRADE

حتى يتم حل المشكلة:

- Trading status / suspension / delisting status غير واضح أو يمنع تنفيذًا طبيعيًا.
- Strategy depends on same-day / rapid exit but current security/account/segment rules make that execution impossible.
- FILLABILITY = NOT EXECUTABLE for the proposed entry/exit method.
- Material auditor / fraud / governance / regulatory event يجعل المخاطر غير قابلة للتقدير بصورة معقولة.
- Capital-action mechanics أو entitlement ratio غير مفهومة بينما هي جوهرية لسعر التنفيذ.
- PRICE INTEGRITY = NOT RELIABLE عندما يعتمد التنفيذ على السعر الحالي الدقيق.
- Rights/share price relation مبنية على timestamps أو bases غير قابلة للمقارنة ولا يمكن تصحيحها.
- EXIT CAPACITY = POOR بالنسبة للحجم المقترح ولا يمكن خفض الحجم إلى مستوى قابل للخروج.
- Market/trading data اللازمة للقرار التنفيذي متناقضة جوهريًا.
- Corporate action يمكن أن يغير عدد الأسهم/الحق الاقتصادي جذريًا ولا يمكن بناء scenario موثوق.

### Rule

Universal No-Trade Gate لا يتحول إلى SPECULATION ONLY ولا يسمح بإضافة رأس مال جديد.

إذا السهم **مملوك بالفعل**، لا تفسر NO TRADE على أنه منع البيع؛ اسمح بـTRIM / EXIT عندما يكون ذلك هو الإجراء المخفِّض للمخاطر وقابلًا للتنفيذ.

---

## B. Investment-Buy Hard Gates

Investment Buy غير مسموح إذا:

- DATA QUALITY = LOW بشكل يمنع valuation موثوق.
- Earnings Gate = FAIL جوهري.
- Financial Strength Gate = FAIL مع liquidity/going-concern risk.
- Corporate/Governance = FAIL جوهري.
- Fully Diluted Share Count غير معروف رغم وجود dilution كبير ولا يمكن بناء scenarios معقولة.
- Valuation غير موثوق بسبب Capital Action غير مفهوم.
- VALUATION STATUS = STALE / NOT RELIABLE مع غياب Delta bridge مناسب.
- Price وFair Value على Capital Structure Basis مختلف بصورة مادية.
- Material company-news delta exists but was not economically bridged.

لكن قد يسمح بـ:

ENTER SPECULATION

فقط إذا:

- لا يوجد Universal No-Trade Gate.
- Timing Quality = GOOD أو setup مبرر بوضوح.
- Execution Action يسمح بالدخول.
- liquidity/exit capacity مناسبة للحجم.
- Invalidation واضح.
- Reward/Risk after friction مقبول.
- المخاطر معروفة ومحدودة بالحجم.

---

# Decision Hierarchy — STATE-SPECIFIC

أعطني **حكمًا واحدًا فقط** مناسبًا لـANALYSIS OBJECTIVE وOWNERSHIP STATE.

## If NOT OWNED — Investment Decision

STRONG BUY / ACCUMULATE / WATCH / AVOID / REJECT

## If OWNED — Investment Position Decision

ADD / HOLD / TRIM / EXIT

## If Speculation Decision

ENTER SPECULATION / WAIT FOR SPECULATION / TAKE PROFIT / EXIT SPECULATION / NO TRADE

## If FULL HYBRID REVIEW

أعطِ أولًا:

- Investment View.
- Speculation View.

ثم اختر Final Action واحدًا فقط بناءً على ownership والحجم والهدف.

### Ownership Rule

OWNED وNOT OWNED قد يؤديان إلى حكم مختلف منطقيًا.

مثال:

NOT OWNED → WATCH

OWNED → HOLD أو TRIM

ولا تعتبر ذلك تناقضًا.

---

# Conclusion Calibration — REQUIRED

قبل القرار النهائي اسأل:

## 1.
هل السهم ظهر Expensive فقط لأن Spot Interest Rate مرتفعة؟

إذا نعم:
أعد الاختبار باستخدام Normalized 2–3Y Rate.

## 2.
هل نفس Risk تم خصمه عدة مرات؟

إذا نعم:
صحح Double Counting.

## 3.
هل Relative/Sector valuation تختلف جذريًا عن Absolute valuation؟

إذا نعم:
اشرح السبب ولا تختَر أحدهما بصمت.

## 4.
هل Worst-Case Dilution أصبح Base Case بدون دليل؟

إذا نعم:
استخدم Probability-Weighted Scenarios.

## 5.
هل السعر مرتفع لكن Growth يبرر ذلك اقتصاديًا؟

إذا نعم:
استخدم:

RICH BUT PLAUSIBLE

بدل OVERVALUED.

## 6.
هل السهم تم اختياره أصلًا بسبب Momentum؟

إذا نعم:
اذكر Selection Bias ولا تعمم النتيجة على EGX بالكامل.

## 7.
هل Price وFair Value على نفس Capital Structure Basis؟

إذا لا:
صحح المقارنة قبل أي FDR أو Margin of Safety.

## 8.
هل Valuation ما زال CURRENT أم يحتاج Delta؟

إذا NEEDS DELTA:
لا تستخدم الرقم القديم بصمت.

## 9.
هل Optimistic FDR مرتفع جدًا لكن الـBreakout قوي؟

إذا نعم:
افصل Investment Attractiveness عن Breakout Probability ولا تجعل أحدهما يلغي الآخر.

## 10.
إذا التحليل تاريخي: هل استخدمت فقط المعلومات المتاحة وقتها؟

إذا لا:
صنف النتيجة HINDSIGHT-DESCRIPTIVE ولا تستخدمها كدليل predictive.

## 11.
هل توجد أخبار إيجابية لم تدخل التقييم لأنها لم تتحول بعد إلى أرباح؟

إذا نعم:
ضعها في Optionality / Catalyst ولا تتجاهلها، لكن لا تدخلها في Base بلا Economic Bridge.

## 12.
هل توجد أخبار سلبية أو Insider Activity تم تفسير سببها بدون دليل؟

إذا نعم:
صححها إلى VERIFIED FACT + UNKNOWN MOTIVE حيث يلزم.

## 13.
هل Management Story مدعومة بتنفيذ سابق؟

إذا لا:
خفض Growth Probability بدل قبول Guidance كما هي.

## 14.
هل Probability Tree يفترض independence بين Operating / Dilution / Optionality رغم وجود ترابط اقتصادي؟

إذا نعم:
استخدم Conditional Probabilities وأعد حساب Expected FV.

## 15.
هل Blended FV يعيد احتساب Probability-Weighted FV مع نفس Absolute/Relative/Historical evidence؟

إذا نعم:
أزل double counting وحدد valuation architecture بوضوح.

## 16.
هل Margin of Safety اختلط مع Upside to Fair Value؟

إذا نعم:
استخدم الصيغتين المنفصلتين الصحيحـتين.

## 17.
هل Expected Return جذاب فقط لأن Horizon طويل أو غير محدد؟

إذا نعم:
احسب Expected Annualized Total Return وقارنه بالـCash والBenchmark.

## 18.
إذا يوجد Rights Issue: هل تم ضبط Rights Required per New Share وtimestamp وfriction؟

إذا لا:
RIGHTS RELATION = NOT RELIABLE.

## 19.
هل يوجد Universal No-Trade Gate؟

إذا نعم:
- New entry / add / speculation = NO TRADE حتى لو كان breakout قويًا.
- إذا المركز مملوك، قيّم TRIM / EXIT كإجراء risk-reducing عند إمكان التنفيذ.

## 20.
هل أسماء historical analogues أصبحت تقود التصنيف بدل البيانات؟

إذا نعم:
أعد التصنيف باستخدام generic behavioral pattern أولًا.

---

## 21.
هل القرار يعتمد على Psychological Level واحد لأنه round number فقط؟

إذا نعم:
اخفض Psychological Confidence واطلب confluence / executed evidence.

## 22.
هل PLSS أو أي behavioral threshold غير validated على EGX؟

إذا نعم:
صنفه HEURISTIC ولا تستخدمه Hard Gate.

## 23.
هل حدث مادي يقع داخل Intended Horizon ويمكن أن يسبب Gap Through Stop؟

إذا نعم:
فعّل Horizon Event Collision وعدّل size/timing.

## 24.
هل الـsetup قابل للتحليل لكنه غير قابل للتنفيذ بسبب price-limit queue أو account/segment restriction؟

إذا نعم:
استخدم `ENTRY NOT CURRENTLY EXECUTABLE` أو `NO TRADE` حسب شدة القيد.

## 25.
هل Fair Value decision يتغير جذريًا تحت Sensitivity معقولة؟

إذا نعم:
DECISION ROBUSTNESS ≠ ROBUST وConfidence لا يكون HIGH.

---

## 26.
هل `OVERVALUED` نتج فقط لأن Price > Base FV بينما Price ما زال داخل defensible Bull range؟

إذا نعم:
صحح إلى `RICH BUT PLAUSIBLE`.

## 27.
هل `BELOW HURDLE` تم تحويلها ضمنيًا إلى `OVERVALUED`؟

إذا نعم:
افصل Economic Valuation عن Return Attractiveness.

## 28.
هل Reasonable P/E تم اشتقاقه مباشرة من Spot Cash Yield أو Personal Required Return؟

إذا نعم:
أعد Multiple Calibration من Stage 6.2.

## 29.
هل تم خلط real growth مع nominal discount rate أو العكس؟

إذا نعم:
NOMINAL/REAL CONSISTENCY = FAIL وأعد الحساب.

## 30.
هل unproven negatives خُصمت من Base بينما comparable positives تم استبعادها بالكامل؟

إذا نعم:
ASYMMETRIC EVIDENCE BIAS = YES وأعد السيناريوهات بصورة متناظرة.

## 31.
هل Maximum Theoretical Dilution استُخدم كـBase Share Count بدون كونه السيناريو الأكثر احتمالًا؟

إذا نعم:
أعد EPS/FV باستخدام Probability-Weighted dilution scenarios.

## 32.
هل asset-heavy company تم تقييمها كأن غير-appraised assets = zero؟

إذا نعم:
ابنِ Conservative RNAV Range عند توفر evidence كافٍ.

## 33.
هل historical multiple من regime اقتصادي مختلف استُخدم كـmean-reversion anchor مباشر؟

إذا نعم:
اخفض Historical Multiple Relevance.

## 34.
إذا عدة أسهم خرجت Overvalued:
هل العينة representative أم momentum-selected؟

إذا غير representative:
لا تعمم.

إذا representative:
فعّل Cross-Sectional Valuation Calibration Audit.

## 35.
هل Current Price أقل من Bull FV لكن يسعّر معظم Bull economics رغم Bull probability منخفضة؟

إذا نعم:
لا تستخدم Highest Credible Bull FV وحده لمنع OVERVALUED؛ فعّل Bull-Dependence + Bull-Pricing Consistency.

## 36.
هل تم خلط Present Fair Value مع Terminal Value؟

إذا نعم:
VALUATION TIME-BASIS CONSISTENCY = ADJUSTMENT REQUIRED وأعد FDR/MOS/Expected Return على الأساس الصحيح.

## 37.
هل RNAV أو land value يعيد احتساب نفس future profits الموجودة بالفعل في Earnings/DCF؟

إذا نعم:
احذف overlap أو استخدم RNAV كـcross-check فقط.

## 38.
هل Required EPS مشتق من multiple لا يطابق نفس earnings horizon؟

إذا نعم:
صحح Reverse-Valuation Horizon Match.

## 39.
هل Robust FV Range واسع جدًا بحيث كلمة FAIR أصبحت غير informative؟

إذا نعم:
استخدم PW/Central FV + scenario probabilities + implied expectations، واخفض confidence.

## 40.
هل Opportunity Cost يستخدم CBE Policy Rate بدل عائد cash/fund يمكن للمستخدم استثماره فيه فعليًا على نفس horizon؟

إذا نعم:
استبدله بـInvestable Cash Benchmark أو صنف comparison NOT RELIABLE.

## 41.
هل PLSS يبدو دقيقًا رغم أن مكونات كثيرة غير متاحة؟

إذا نعم:
اعرض Raw / Available score + Evidence Coverage، ولا تستخدم 0–100 score وحده.

---

# Final Explanation

اشرح:

1. ANALYSIS OBJECTIVE + Horizon.
2. Investment Thesis في 3 جمل فقط.
3. أهم سبب يجعلني أشتري / أحتفظ / أبيع حسب الحالة.
4. أهم سبب قد يجعل التحليل خاطئًا.
5. أهم KPI أو رقم سأراقبه.
6. السعر أو الحدث الذي سيغير الحكم.
7. أثر Dilution على EPS.
8. هل رأس المال الجديد Accretive أم Dilutive؟
9. Fresh Capital Test.
10. Opportunity-Cost Test.
11. Margin of Safety وUpside to Fair Value — كل واحد منفصل.
12. Expected Total Return وExpected Annualized Total Return وهامش التفوق على Cash/Benchmark.
13. Return Attractiveness = EXCEEDS / MEETS / BELOW HURDLE / INFERIOR.
14. Economic Valuation = CHEAP / ATTRACTIVE / FAIR / RICH BUT PLAUSIBLE / OVERVALUED / SEVERE FUNDAMENTAL DETACHMENT.
15. Market-Implied Expectations: EPS/Growth/Margin/ROE assumptions التي يسعرها Current Price.
16. Multiple Calibration + normalized-rate basis.
17. Nominal/Real Consistency.
18. Asymmetric Evidence Bias = YES / NO.
19. Confidence = HIGH / MEDIUM / LOW.
20. Valuation Date وValuation Status.
21. Capital Structure Basis.
22. Base FDR وOptimistic FDR وPremium Above Optimistic FV.
23. Behavioral Repricing Family + historical analogue إن كان applicable.
24. Psychological Price Map: support / resistance / dominant level / breakout trigger / PLSS / clearance.
25. Signal Calibration Status + whether PLSS is validated or heuristic.
26. Selection Basis + Selection-Bias Risk.
27. Breakout Acceptance / Retention / Re-entry state إن كان applicable.
28. Timing Quality + Execution Action + Fillability.
29. Exit Capacity + Maximum Executable Position.
30. Event Calendar / Horizon Collision.
31. News Delta.
32. أهم Positive Optionality التي لم تدخل Base FV.
33. أهم Negative News / Governance evidence.
34. أهم Rumor تم التحقق منه ونتيجته.
35. Management Promise Tracker summary.
36. Valuation Sensitivity / Decision Robustness / key pivot assumption.
37. Present FV date basis vs Terminal Value horizon/date + Time-Basis Consistency.
38. Probability-Supported FV Region + FV Range Width / Quality.
39. Highest Defensible Bull FV + Bull Case Status/Probability + Highest Credible FV.
40. Bull Dependence + Bull-Pricing Consistency.
41. Reverse-Valuation Horizon Match.
42. RNAV / Earnings Overlap Check إذا applicable.
43. Investable Cash Benchmark + expected net cash return over the same horizon.
44. PLSS Raw/Available score + Evidence Coverage.
45. Valuation Model Calibration Warning + Sample Representativeness إذا applicable.
46. Unified Price Map مع فصل Fundamental / Behavioral / Technical / Execution levels.
47. Integrated Risk summary وأهم risk driver.
48. Universal No-Trade Gate = YES / NO.

---

# Final Decision Summary

Analysis Objective:
LONG-TERM INVESTMENT / SWING-POSITION TRADE / SHORT-TERM SPECULATION / OWNED-POSITION REVIEW / FULL HYBRID REVIEW

Run Mode:
INTERACTIVE_STAGE_BY_STAGE / FULL_AUTOMATED_RUN / DELTA_ONLY

Intended Horizon:
[ ]

Ownership State:
NOT OWNED / OWNED / OWNED & OVERWEIGHT / OWNED & UNDERWEIGHT

Primary Benchmark:
[ ]

Personal / Portfolio Required Return:
[PERCENT] / NOT SPECIFIED

Project Funnel Status:
NEW / FOUND / PARTIAL / NOT FOUND

Update Mode:
FULL REBUILD / DELTA UPDATE / NO MATERIAL UPDATE

News Delta:
NO MATERIAL NEWS / POSITIVE MATERIAL NEWS / NEGATIVE MATERIAL NEWS / MIXED MATERIAL NEWS / UNVERIFIED MATERIAL CLAIM

Price Integrity:
CLEAN / CONFLICT / STALE / NOT RELIABLE

Valuation Status:
CURRENT / NEEDS DELTA / STALE / NOT RELIABLE

Valuation Date:
[DATE]

Financial Data Cutoff:
[DATE]

Company News Cutoff:
[DATE/TIME]

Valuation Vintage:
CONTEMPORANEOUS / RECONSTRUCTED POINT-IN-TIME / HINDSIGHT-DESCRIPTIVE / NOT APPLICABLE

Capital Structure Basis:
CURRENT-NORMAL / CUM-RIGHTS / EX-RIGHTS / POST-DILUTION / SPLIT-ADJUSTED / BONUS-ADJUSTED / MERGER-ADJUSTED / NOT RELIABLE

Business Gate:
PASS / PASS WITH CAUTION / FAIL

Business Quality:
STRONG / ACCEPTABLE / WEAK

Earnings Gate:
PASS / PASS WITH CAUTION / FAIL

Earnings Quality:
STRONG / ACCEPTABLE / WEAK

Financial Strength Gate:
PASS / PASS WITH CAUTION / FAIL

Financial Strength:
STRONG / ACCEPTABLE / WEAK

Growth Gate:
PASS / PASS WITH CAUTION / FAIL

Growth Strength:
STRONG / MODERATE / WEAK

Growth Proof:
PROVEN / PARTLY PROVEN / STORY ONLY

Capital Action Economics:
ACCRETIVE / NEUTRAL / DILUTIVE / TOO EARLY TO KNOW

Market Regime:
CHEAP / NORMAL / RE-RATED / FROTHY / BUBBLE-LIKE

Sector Valuation:
CHEAP / NORMAL / RICH

Market Tape Regime:
RISK-ON / NEUTRAL / RISK-OFF / DISLOCATED / NOT RELIABLE

Horizon Event Collision:
NONE / MANAGEABLE / MATERIAL / BINARY / NOT RELIABLE

Economic Valuation:
CHEAP / ATTRACTIVE / FAIR / RICH BUT PLAUSIBLE / OVERVALUED / SEVERE FUNDAMENTAL DETACHMENT / UNRELIABLE

Margin of Safety:
[PERCENT] / NOT RELIABLE

Upside to Fair Value:
[PERCENT] / NOT RELIABLE

Return Horizon:
[ ]

Expected Total Return:
[PERCENT] / NOT RELIABLE

Expected Annualized Total Return:
[PERCENT] / NOT RELIABLE

Expected Return Spread:
STRONGLY POSITIVE / POSITIVE / MARGINAL / NEGATIVE / NOT RELIABLE

Return Attractiveness:
EXCEEDS HURDLE / MEETS HURDLE / BELOW HURDLE / INFERIOR CAPITAL USE / NOT RELIABLE

Multiple Calibration:
WELL SUPPORTED / REASONABLE / WEAK / NOT RELIABLE

Nominal/Real Consistency:
CLEAN / FAIL / NOT APPLICABLE

Valuation Time-Basis Consistency:
CLEAN / ADJUSTMENT REQUIRED / NOT RELIABLE

Reverse-Valuation Horizon Match:
CLEAN / ADJUSTMENT REQUIRED / NOT RELIABLE

Asymmetric Evidence Bias:
YES / NO

RNAV / Earnings Overlap Check:
CLEAN / PARTIAL OVERLAP ADJUSTED / MATERIAL OVERLAP / NOT RELIABLE / NOT APPLICABLE

Robust Fair-Value Range:
[ ] / NOT RELIABLE

FV Range Width:
[PERCENT] / NOT RELIABLE

FV Range Quality:
NARROW / MODERATE / WIDE / VERY WIDE / NOT RELIABLE

Probability-Supported FV Region:
[ ] / NOT RELIABLE

Probability-Supported FV Quality:
HIGH / MEDIUM / COARSE / NOT RELIABLE

Highest Defensible Bull FV:
[ ] / NOT RELIABLE

Bull Case Status:
CREDIBLE / AGGRESSIVE BUT DEFENSIBLE / REMOTE-SPECULATIVE / NOT RELIABLE

Bull Case Probability:
[PERCENT] / NOT RELIABLE

Highest Credible FV:
[ ] / NOT RELIABLE

Bull Dependence:
[PERCENT] / LOW / MODERATE / HIGH / VERY HIGH / BEYOND CREDIBLE BULL / NOT APPLICABLE / NOT RELIABLE

Bull-Pricing Consistency:
STRONG / REASONABLE / WEAK / NOT APPLICABLE / NOT RELIABLE

Valuation Model Risk:
LOW / MEDIUM / HIGH / NOT RELIABLE

Decision Robustness:
ROBUST / MODERATELY SENSITIVE / HIGHLY SENSITIVE / NOT RELIABLE

Required-Return Entry Price:
[ ] / NOT APPLICABLE / NOT RELIABLE

Investable Cash Benchmark:
[ ] / NOT RELIABLE

Expected Net Cash Return Over Horizon:
[PERCENT] / NOT RELIABLE

Present FV Date Basis:
[DATE] / NOT RELIABLE

Terminal Value Horizon / Date:
[ ] / NOT APPLICABLE / NOT RELIABLE

Base FDR:
[NUMBER] / NOT RELIABLE

Optimistic FDR:
[NUMBER] / NOT RELIABLE

Premium Above Optimistic FV:
[PERCENT] / NOT RELIABLE

FDR Classification:
AT/BELOW OPTIMISTIC VALUE / MODEST EXTENSION / EXTENDED / STRONG DETACHMENT / EXTREME DETACHMENT / SEVERE BEHAVIORAL DETACHMENT / NOT RELIABLE

Market-Implied Expectations:
EASY EXECUTION / PLAUSIBLE EXECUTION / DEMANDING EXECUTION / VERY DEMANDING EXECUTION / ECONOMICALLY IMPLAUSIBLE

Catalyst:
STRONG / MODERATE / WEAK

Speculation:
INVESTMENT QUALITY / HYBRID / SPECULATIVE / HIGHLY SPECULATIVE

Primary Driver:
FUNDAMENTAL-LED / CATALYST-LED / FLOW-LED / CAPITAL-ACTION-LED / M&A-LED / MIXED

Behavioral Repricing Family:
FLOW-DRIVEN BEHAVIORAL BUBBLE / RIGHTS REFLEXIVITY / DELAYED-CATALYST CONTINUATION / BREAKOUT REJECTION / NAV DISLOCATION / HIGH-BASE SECOND-LEG / OTHER / INCONCLUSIVE / NOT APPLICABLE

Historical Analogue:
[ ] / NOT APPLICABLE

Psychological Map Confidence:
HIGH / MEDIUM / LOW / NOT RELIABLE

Dominant Psychological Level:
[ ] / NOT RELIABLE

Dominant PLSS:
[RAW / AVAILABLE MAX] / [0–100 equivalent if justified] / NOT RELIABLE

PLSS Evidence Coverage:
[PERCENT] / NOT RELIABLE

Nearest Psychological Support:
[ ] / NOT RELIABLE

Nearest Psychological Resistance:
[ ] / NOT RELIABLE

Psychological Breakout Trigger:
[ ] / NOT APPLICABLE / NOT RELIABLE

Psychological Clearance:
[PERCENT] / NOT APPLICABLE / NOT RELIABLE

PLSS Status:
VALIDATED / PROVISIONALLY CALIBRATED / HEURISTIC / INSUFFICIENT SAMPLE / NOT APPLICABLE

Signal Calibration Status:
VALIDATED / PROVISIONALLY CALIBRATED / HEURISTIC / INSUFFICIENT SAMPLE / NOT APPLICABLE

Selection Basis:
RANDOM / BROAD UNIVERSE / FUNDAMENTAL SCREEN / MOMENTUM SCREEN / TOP GAINER / CATALYST SCREEN / USER-SELECTED / OTHER

Selection-Bias Risk:
LOW / MEDIUM / HIGH

Valuation Model Calibration Warning:
YES / NO / NOT APPLICABLE

Sample Representativeness:
HIGH / MEDIUM / LOW / NOT RELIABLE / NOT APPLICABLE

Breakout Acceptance:
STRONG / PARTIAL / WEAK / FAILED / NOT YET TESTED / NOT APPLICABLE

Breakout Retention Ratio:
[NUMBER] / NOT APPLICABLE

Old-Base Re-Entry:
NO RE-ENTRY / BRIEF RE-ENTRY + RECLAIM / SUSTAINED RE-ENTRY / NOT APPLICABLE

Rights Relation:
RIGHT CHEAPER / APPROXIMATELY ALIGNED / ORDINARY SHARE CHEAPER / NOT APPLICABLE / NOT RELIABLE

Timing Quality:
GOOD / NEUTRAL / POOR

Execution Action:
ENTER NOW / ACCUMULATE / WAIT FOR PULLBACK / WAIT FOR CONFIRMATION / NO ENTRY

Entry Type:
VALUE / PULLBACK / BREAKOUT / RECLAIM / SPECULATION / NO ENTRY

Unified Price Map:
[CURRENT / VALUE ZONE / REQUIRED-RETURN ENTRY / CENTRAL FV / BULL FV / PSYCH SUPPORT / PSYCH RESISTANCE / BREAKOUT / DO-NOT-CHASE / INVALIDATION / TARGET]

Round-Trip Friction:
[EGP / %] / NOT RELIABLE

Fillability:
NORMAL / QUEUE-DEPENDENT / LOW FILL PROBABILITY / NOT EXECUTABLE / NOT RELIABLE

Exit Capacity:
NORMAL / CONSTRAINED / POOR

Maximum Executable Position:
[EGP] / NOT RELIABLE

Portfolio Fit:
PASS / PASS WITH SIZE LIMIT / FAIL

Fresh Capital Test:
YES / BORDERLINE / NO

Opportunity Cost:
TOP-TIER CAPITAL USE / ACCEPTABLE / INFERIOR / NOT RELIABLE

Owned Position Action:
ADD / HOLD / TRIM / EXIT / NOT APPLICABLE

Maximum Allowed Weight:
[PERCENT] / NOT RELIABLE

Fundamental Risk:
LOW / MEDIUM / HIGH / EXTREME / NOT RELIABLE

Valuation Risk:
LOW / MEDIUM / HIGH / EXTREME / NOT RELIABLE

Market / Behavioral Risk:
LOW / MEDIUM / HIGH / EXTREME / NOT RELIABLE

Liquidity / Execution Risk:
LOW / MEDIUM / HIGH / EXTREME / NOT RELIABLE

Event / Structural Risk:
LOW / MEDIUM / HIGH / EXTREME / NOT RELIABLE

Overall Risk:
LOW / MEDIUM / HIGH / EXTREME / NOT RELIABLE

Universal No-Trade Gate:
YES / NO

Optionality Summary:
[KEY ITEMS + PROBABILITY]

Major-Holder Activity:
[SUMMARY + VERIFIED / MOTIVE UNKNOWN]

Rumor Verification Summary:
[CLAIM → CLASSIFICATION]

Management Promise Record:
STRONG / MIXED / WEAK / INSUFFICIENT HISTORY

Final Decision Domain:
INVESTMENT / OWNED-POSITION / SPECULATION / HYBRID

Final Decision:
STRONG BUY / ACCUMULATE / WATCH / AVOID / REJECT / ADD / HOLD / TRIM / EXIT / ENTER SPECULATION / WAIT FOR SPECULATION / TAKE PROFIT / EXIT SPECULATION / NO TRADE

Data Confidence:
HIGH / MEDIUM / LOW

Fundamental Confidence:
HIGH / MEDIUM / LOW / NOT APPLICABLE

Valuation Confidence:
HIGH / MEDIUM / LOW / NOT APPLICABLE

Timing Confidence:
HIGH / MEDIUM / LOW / NOT APPLICABLE

Execution Confidence:
HIGH / MEDIUM / LOW / NOT APPLICABLE

Behavioral-Signal Confidence:
HIGH / MEDIUM / LOW / NOT APPLICABLE

### Domain-Specific Confidence Rule

**LONG-TERM INVESTMENT**
- Final Confidence is primarily capped by Data / Fundamental / Valuation confidence.
- Weak intraday Timing confidence does not automatically cap the investment thesis.

**SHORT-TERM SPECULATION / SWING**
- Final Confidence is capped materially by Timing + Execution + Data confidence.
- `FILLABILITY = NOT EXECUTABLE` overrides confidence and blocks entry.

**PSYCHOLOGICAL / BEHAVIORAL SIGNALS**
- If PLSS STATUS = HEURISTIC, Behavioral-Signal Confidence cannot be HIGH solely because PLSS score is high.

Confidence:
HIGH / MEDIUM / LOW


---

# v2.7 Change-Control Principles

هذا الإصدار يرسخ القواعد التالية:

1. Intent and horizon before analysis.
2. Delta before rebuild.
3. Fact-specific evidence hierarchy.
4. Same capital-structure basis for Price/EPS/FV.
5. News requires an economic bridge before Base FV.
6. Conditional probabilities when scenarios are dependent.
7. Probability-weighted valuation must not be double-counted inside blended valuation.
8. Margin of Safety is distinct from Upside to Fair Value.
9. Fair Value must be converted into horizon-specific expected return.
10. Rights economics must respect entitlement ratio and execution friction.
11. Generic behavioral pattern first; historical analogue second.
12. Standardized technical windows reduce model drift.
13. Maximum executable position precedes portfolio position sizing.
14. Universal No-Trade Gates override investment/speculation attractiveness.
15. Owned positions explicitly allow ADD / HOLD / TRIM / EXIT.
16. Final risk classification must be decomposed, not impressionistic.
17. Psychological prices are behavioral zones, never Fundamental Fair Value.
18. Psychological levels require confluence; round numbers alone are weak evidence.
19. PLSS weights/thresholds remain heuristic until point-in-time EGX calibration validates them.
20. Event dates inside the intended holding horizon must be treated as gap/structural risk.
21. A theoretically attractive trade can still be rejected because it is not executable under current market/account rules.
22. Price-limit queues and displayed orders do not imply a fill.
23. Fair Value must include a sensitivity envelope and decision-robustness test.
24. Required-return entry price is derived from economics, not arbitrary percentage discounts.
25. Final confidence is decomposed and objective-specific.
26. All price outputs are consolidated into one Unified Price Map while keeping Fundamental, Behavioral, Technical and Execution meanings separate.
27. Economic Fair Value, Investor Required-Return Attractiveness, and Trading Attractiveness are three separate decision domains.
28. Personal required return must never be used mechanically as the company's Fair-Value discount rate or P/E anchor.
29. `BELOW HURDLE` is not synonymous with `OVERVALUED`.
30. OVERVALUED requires price to be materially above the highest economically defensible Bull/Optimistic FV, not merely above Base FV.
31. Market-Implied Expectations must be reverse-engineered before declaring severe overvaluation.
32. Reasonable P/E / discount rates require explicit multi-anchor calibration; spot cash yield shortcuts are prohibited.
33. Nominal growth must be matched with nominal discount rates; real models must remain internally real.
34. Positive and negative uncertainty must be treated symmetrically.
35. Maximum theoretical dilution is not the Base share count unless it is the most probable scenario.
36. Non-appraised but verified material assets may receive a conservative RNAV range rather than automatic zero value.
37. Historical valuation multiples must be regime-adjusted before mean-reversion use.
38. Batch results require a cross-sectional calibration audit before any market-wide “most stocks are overvalued” conclusion.
39. Momentum-selected samples are explicitly non-representative for market-wide valuation inference.
40. Remote/speculative Bull cases cannot shield a stock from OVERVALUED; only evidence-backed credible Bull economics count.
41. Price below a credible Bull FV is not sufficient to avoid OVERVALUED; valuation must be probability-supported.
42. Bull Dependence measures how much of the Base-to-Bull repricing is already embedded and must be interpreted with Bull probability/evidence.
43. Present Fair Value and Terminal Value are different time-basis objects and may never be mixed in FDR/MOS/Expected Return.
44. Reverse valuation must match the earnings horizon to the multiple horizon.
45. RNAV / land value cannot be added on top of earnings value when the same future development profits are already embedded.
46. Wide Fair-Value ranges reduce decision precision; being inside a very wide range does not automatically mean FAIR.
47. Opportunity cost should use an investable net cash/money-market benchmark over the same horizon, not policy rate alone.
48. PLSS must report evidence coverage; missing components are missing evidence, not zero-strength evidence.
49. Probability-supported FV regions / quantiles should be reported when scenario granularity supports them; coarse trees must be labeled coarse.
50. Overvaluation classification must consider central value, probability-supported region, Bull Dependence, Bull probability and market-implied execution together.

END OF MASTER FUNNEL — v2.7
