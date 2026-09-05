# EGX STOCK ANALYSIS FUNNEL — v2.8 EXPECTATIONS-AWARE ECONOMIC VALUE, EXPECTATIONS-REVISION, REQUIRED-RETURN & BEHAVIORAL EXECUTION FRAMEWORK

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

# v2.8 CHANGE SUMMARY

This version updates v2.7 without rebuilding the full funnel:

- Adds EPS Reconciliation as a hard accounting gate.
- Makes Intrinsic Value, Price-Implied Expectations, Expectations Revision, and Expected Return co-equal.
- Separates Economic Terminal Value from Expected Horizon Market Price.
- Adds value-creating-growth / incremental-ROIC logic.
- Adds rerating attribution.
- Converts Catalyst analysis into Catalyst → Expectations Revision mapping.
- Removes any need for nationality-based herd assumptions; uses observed EGX information-reaction regimes instead.
- Rebuilds Fresh Capital Test and Final Decision around multiple independent pillars.
- Resolves v2.7 internal conflict over the meaning of OVERVALUED.

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

### Price-Is-Information Rule — v2.8 REQUIRED

السعر الحالي ليس Fair Value، لكنه أيضًا ليس رقمًا يجب تجاهله حتى نهاية التقييم.

اعتبر Current Price **forecast جماعيًا يحمل معلومات عن توقعات السوق**.

لذلك في كل LONG-TERM INVESTMENT / FULL HYBRID REVIEW يجب أن يعمل التحليل عبر أربعة عدسات مستقلة:

1. **INTRINSIC / ECONOMIC VALUE** — ماذا تستحق الشركة تحت سيناريوهات اقتصادية قابلة للدفاع؟
2. **PRICE-IMPLIED EXPECTATIONS** — ما النمو/الهامش/ROIC/المدة/المضاعف الذي يحتاجه السعر الحالي؟
3. **EXPECTATIONS-REVISION OUTLOOK** — هل الأدلة القادمة مرجح أن ترفع توقعات السوق أم تخفضها؟
4. **EXPECTED RISK-ADJUSTED RETURN** — هل Expected Horizon Market Price والعوائد النقدية يقدمان عائدًا أفضل من البدائل؟

### Hard Rule

`Price > Central Fair Value` لا يكفي وحده لإصدار `AVOID` أو `OVERVALUED`.

و`Price-Implied Expectations = REASONABLE` لا يكفي وحده لإصدار `BUY`.

القرار النهائي يجب أن يدمج العدسات الأربع مع جودة النشاط والمخاطر والتنفيذ.

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

## 2.5A EPS Reconciliation Hard Gate — REQUIRED

قبل استخدام أي P/E أو Sustainable EPS أو Reverse-Valuation EPS، يجب بناء جسر محاسبي صريح:

### EPS Numerator Bridge

Net Profit attributable to parent/common equity
→ Employee profit share / statutory worker distribution
→ Board remuneration
→ Preferred / non-common distributions إن وجدت
→ Other common-share adjustments
→ **Earnings attributable to common shares for EPS**

### EPS Denominator Bridge

Opening shares
→ issuances/cancellations weighted by time
→ treasury-share treatment
→ split/bonus retrospective adjustment where accounting rules require
→ **Weighted-Average Shares used for EPS**

ثم تحقق:

Reconstructed EPS ≈ Published EPS

صنف:

EPS RECONCILIATION =

PASS / SMALL UNEXPLAINED DIFFERENCE / FAIL / NOT RELIABLE

### Hard Gate

إذا `EPS RECONCILIATION = FAIL / NOT RELIABLE` وكان P/E أو EPS-per-share جوهريًا للتقييم:

- لا تستخدم Published EPS أو reconstructed EPS بصورة انتقائية.
- P/E-based valuation = BLOCKED حتى حل الجسر أو استخدام منهج لا يعتمد على EPS.
- Sustainable Earnings يجب أن تكون على **نفس common-share economic basis** المستخدمة لاحقًا في EPS/FV.

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
- EPS Reconciliation = PASS / SMALL UNEXPLAINED DIFFERENCE / FAIL / NOT RELIABLE.
- EPS Numerator Basis المستخدمة.
- Weighted-Average Shares المستخدمة.
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

## Value-Creating Growth Bridge — v2.8 REQUIRED

لا تعامل Revenue Growth أو EPS Growth كقيمة اقتصادية تلقائيًا.

لكل Driver مادي قدّر قدر الإمكان:

Growth Driver
→ Incremental Revenue
→ Incremental Operating Profit / FCF
→ Incremental Capital Required
→ Incremental ROIC / ROE
→ Cost of Capital / Required Return
→ **Economic Value Creation**

صنف:

VALUE-CREATING GROWTH =

STRONG / POSITIVE / NEUTRAL / VALUE-DESTROYING / NOT RELIABLE

وحدد أيضًا:

GROWTH FUNDING DEPENDENCE =

LOW / MODERATE / HIGH / NOT RELIABLE

### Rule

Growth لا يرفع Bull/Base probability لمجرد أن الإيرادات ترتفع.

إذا Incremental ROIC ≤ Cost of Capital بصورة مستدامة، خفض قيمة النمو حتى لو Revenue CAGR مرتفع.

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

Value-Creating Growth =

STRONG / POSITIVE / NEUTRAL / VALUE-DESTROYING / NOT RELIABLE

Growth Funding Dependence =

LOW / MODERATE / HIGH / NOT RELIABLE

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

## 5.5.9 Rerating Attribution — v2.8 REQUIRED

إذا تغير P/E / P/B / EV-EBITDA أو سعر السهم ماديًا خلال الفترة، افصل قدر الإمكان بين:

1. **EARNINGS-REVISION RERATING** — توقعات الأرباح/FCF ارتفعت أو انخفضت.
2. **DISCOUNT-RATE RERATING** — الفائدة/التضخم/ERP/risk perception تغيرت.
3. **QUALITY / ROIC RERATING** — السوق أعاد تقييم جودة النمو أو الميزانية أو الإدارة.
4. **LIQUIDITY / FLOW RERATING** — تدفقات/سيولة/index/positioning.
5. **BEHAVIORAL RERATING** — FOMO/overreaction/underreaction without adequate economic bridge.

صنف:

RERATING ATTRIBUTION =

EARNINGS-LED / RATE-LED / QUALITY-LED / FLOW-LED / BEHAVIORAL-LED / MIXED / NOT RELIABLE

### Rule

لا تعاقب السهم آليًا لأن multiple ارتفع إذا كان الارتفاع ناتجًا بدرجة قابلة للدفاع من نمو earnings أو انخفاض normalized discount rate.

ولا تعتبر rerating دائمًا rational؛ يجب ربطه بالدليل.

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

Rerating Attribution =

EARNINGS-LED / RATE-LED / QUALITY-LED / FLOW-LED / BEHAVIORAL-LED / MIXED / NOT RELIABLE

---

# Stage 6 — Valuation, Price-Implied Expectations & Expectations-Revision Gate — v2.8

نفذ Stage 6 باستخدام نتائج Stages 0–5.5.

هذه المرحلة لا تنتج رقم Fair Value فقط. يجب أن تنتج **أربعة محركات قرار متساوية الأهمية**:

1. INTRINSIC / ECONOMIC VALUE.
2. PRICE-IMPLIED EXPECTATIONS.
3. EXPECTATIONS GAP + REVISION OUTLOOK.
4. EXPECTED HORIZON MARKET PRICE + RISK-ADJUSTED RETURN.

لا تعتمد على Reported P/E وحده.

---

## 6.0 Freshness, EPS & Capital-Basis Checkpoint — REQUIRED

قبل أي حساب:

- PRICE INTEGRITY.
- VALUATION STATUS.
- CAPITAL STRUCTURE BASIS.
- Current / scenario share counts.
- EPS RECONCILIATION status.
- Latest material disclosure/news delta.

### Hard Rules

- إذا EPS RECONCILIATION = FAIL/NOT RELIABLE → لا تستخدم P/E valuation إلا بعد حل الجسر أو استبداله بمنهج لا يعتمد على EPS.
- Price / Earnings / FV / Terminal Value يجب أن تكون على نفس capital-structure basis.
- Material news delta غير bridged → valuation = NEEDS DELTA.

---

## 6.0A Valuation-Time Basis — REQUIRED

افصل بين ثلاثة أشياء:

### PRESENT INTRINSIC FAIR VALUE @ VALUATION DATE
قيمة اقتصادية اليوم.

### ECONOMIC TERMINAL VALUE @ HORIZON
القيمة الاقتصادية للشركة في نهاية الأفق إذا تحققت economics السيناريو.

### EXPECTED HORIZON MARKET PRICE @ HORIZON — v2.8 NEW
السعر الذي يُرجح أن يدفعه السوق عند الأفق، ويعتمد على:

- horizon earnings / FCF,
- likely market multiple / discount rate at that date,
- expectations state,
- sector/market regime,
- realized evidence,
- and scenario probability.

### Critical Rule

`Economic Terminal Value` ≠ `Expected Horizon Market Price` تلقائيًا.

Expected Return يجب أن يستخدم **Expected Horizon Market Price** عندما يمكن تقديره، وليس افتراض convergence كامل إلى intrinsic value.

صنف:

VALUATION TIME-BASIS CONSISTENCY = CLEAN / ADJUSTMENT REQUIRED / NOT RELIABLE

---

# Stage 6A — Intrinsic / Economic Value Engine

## 6A.1 Valuation Architecture

اختر المنهج الملائم للنشاط:

- Sustainable / Forward P/E.
- DCF / FCFF / FCFE.
- EV/EBITDA.
- P/B + ROE.
- P/FCF.
- RNAV / SOTP.
- Mid-cycle valuation للسلع/الدوريات.

### Multiple / Discount-Rate Calibration

Reasonable multiple/rate يجب أن يربط:

- forward sustainable growth,
- ROIC/ROE,
- reinvestment runway,
- payout,
- balance-sheet risk,
- cyclicality,
- governance,
- sector peers,
- market regime,
- normalized—not spot—rates,
- historical multiple only after regime adjustment.

صنف:

MULTIPLE CALIBRATION = WELL SUPPORTED / REASONABLE / WEAK / NOT RELIABLE

### Prohibitions

- Fair P/E = 1 / Spot Cash Yield كـdefault.
- Fair P/E = 1 / User Required Return.
- Historical mean reversion بلا regime check.

---

## 6A.2 Sector / Asset Adapters

احتفظ بقواعد v2.7 للقطاعات:

- Real Estate → RNAV / collections / land economics.
- Banks → P/B + sustainable ROE + asset quality/capital.
- NBFS → P/B/P-E + funding spread + credit cost + asset quality.
- Holdings → SOTP / NAV + parent cash/debt + holding discount.
- Cyclicals → mid-cycle economics.
- Capital-action companies → scenario share count + accretion economics.

### RNAV Double-Count Guard

إذا future development profits داخلة في earnings/DCF، لا تضف full asset value مرة ثانية.

RNAV / EARNINGS OVERLAP CHECK = CLEAN / PARTIAL OVERLAP ADJUSTED / MATERIAL OVERLAP / NOT RELIABLE / NOT APPLICABLE

---

## 6A.3 Scenario Intrinsic Values

استخدم Stage 4 Bear/Base/Bull أو scenario tree الأكثر granular.

لكل Scenario اعرض:

| Scenario | Probability | Earnings/FCF @ horizon | Present Intrinsic FV | Economic Terminal Value | Key assumptions |
|---|---:|---:|---:|---:|---|
| Bear | | | | | |
| Base | | | | | |
| Bull | | | | | |

إذا السيناريوهات مترابطة مع dilution/funding/optionality استخدم Conditional Probabilities.

تأكد أن probabilities ≈100%.

### Probability-Weighted Intrinsic Value

PW Intrinsic FV = Σ Scenario Present FV × Probability

### Probability-Supported Region

إذا tree coarse، لا تدّعِ quantiles دقيقة.

PROBABILITY-SUPPORTED FV QUALITY = HIGH / MEDIUM / COARSE / NOT RELIABLE

---

## 6A.4 Intrinsic Value Position — v2.8 NEW CLASSIFICATION

بدل جعل هذه النتيجة وحدها Final Investment Verdict، صنف فقط **موضع السعر بالنسبة للقيمة الاقتصادية**:

INTRINSIC VALUE POSITION =

DEEP DISCOUNT / DISCOUNT / NEAR CENTRAL VALUE / PREMIUM TO CENTRAL VALUE / BEYOND CREDIBLE ECONOMIC RANGE / UNRELIABLE

ثم اعرض:

- Central / PW Present FV.
- Base Present FV.
- Robust FV Range.
- Highest Credible Bull FV.
- Margin of Safety.
- Upside to Central FV.
- FDR إن كان مفيدًا.

### FDR

Base FDR = Current Price ÷ Base Present FV

Optimistic FDR = Current Price ÷ Highest Credible Bull Present FV

FDR يظل descriptive فقط، وليس Buy/Sell Gate.

---

# Stage 6B — Price-Implied Expectations Engine — REQUIRED

بدل سؤال "هل السعر أعلى من Fair Value؟" فقط، اعكس السعر الحالي لمعرفة ما يجب أن يتحقق اقتصاديًا.

## 6B.1 Reverse-Valuation Method

استخدم أفضل منهج ملائم:

### P/E-based reverse valuation

Current Price → Required Forward EPS → Required common-share earnings

لكن لا تتوقف هنا.

### Reverse DCF / Value-Driver valuation — PREFERRED WHEN FEASIBLE

استخرج قدر الإمكان:

- Implied Revenue CAGR.
- Implied operating / EBITDA / net margin.
- Implied FCF margin.
- Implied ROIC / ROE.
- Implied reinvestment rate.
- Implied growth duration.
- Implied terminal multiple / discount rate.
- Implied dilution/funding requirement.

### Horizon Matching Rule

Required assumptions يجب أن تطابق نفس horizon للـmultiple/DCF.

REVERSE-VALUATION HORIZON MATCH = CLEAN / ADJUSTMENT REQUIRED / NOT RELIABLE

---

## 6B.2 Price-Implied Expectations Profile — REQUIRED OUTPUT

| Driver | Current/Normalized | Price-Implied | Company History | Base Scenario | Bull Scenario | Burden |
|---|---:|---:|---:|---:|---:|---|
| Revenue CAGR | | | | | | |
| Margin | | | | | | |
| EPS / FCF | | | | | | |
| ROIC / ROE | | | | | | |
| Reinvestment | | | | | | |
| Growth Duration | | | | | | |
| Multiple / discount-rate state | | | | | | |

صنف:

PRICE-IMPLIED EXPECTATIONS =

UNDemanding / REASONABLE / DEMANDING / VERY DEMANDING / ECONOMICALLY IMPLAUSIBLE / NOT RELIABLE

### Critical Rule

لا تستخدم `Price > Central FV` كبديل لهذا الاختبار.

إذا السعر يحتاج assumptions قابلة للتحقق ضمن Base/Bull بصورة معقولة، لا تصفه ميكانيكيًا بأنه غير اقتصادي.

---

# Stage 6C — Expectations Gap & Revision Engine — v2.8 REQUIRED

هذه المرحلة تسأل:

> أين تختلف توقعات السوق الحالية عن الاحتمالات التي تشير إليها الأدلة، وهل هذا الفرق مرشح أن يتسع أو ينغلق؟

## 6C.1 Expectations Gap

لكل value driver:

Expectations Gap = Our probability-weighted expectation − Price-implied expectation

استخدم qualitative أو quantitative output حسب جودة البيانات.

صنف:

EXPECTATIONS GAP =

STRONGLY POSITIVE / POSITIVE / NEUTRAL / NEGATIVE / STRONGLY NEGATIVE / NOT RELIABLE

### Interpretation

- Positive = السوق يطلب أقل مما تشير إليه economics المتوقعة.
- Negative = السوق يطلب أكثر مما تشير إليه economics المتوقعة.

---

## 6C.2 Expectations Revision Outlook

استخدم evidence الحالي وليس السعر وحده:

- Earnings revisions / margin trend.
- New contracts / backlog / utilization.
- ROIC evidence.
- Funding/capital constraints.
- Management delivery history.
- Regulatory resolution.
- Sector demand.
- Rate/discount-rate direction.
- Catalyst map from Stage 7 when later available; Stage 6 يعطي provisional view ثم Stage 7 يحدثه.

صنف:

EXPECTATIONS REVISION OUTLOOK =

STRONG UPWARD / UPWARD / STABLE / DOWNWARD / STRONG DOWNWARD / UNCERTAIN

و:

EXPECTATIONS-REVISION CONFIDENCE = HIGH / MEDIUM / LOW / NOT RELIABLE

### Hard Rule

Momentum price action وحده لا يثبت Upward Fundamental Revision.

وضعف السعر وحده لا يثبت Downward Fundamental Revision.

---

## 6C.3 Rerating Attribution

استخدم Stage 5.5:

RERATING ATTRIBUTION =

EARNINGS-LED / RATE-LED / QUALITY-LED / FLOW-LED / BEHAVIORAL-LED / MIXED / NOT RELIABLE

حدد ما إذا كان استمرار rerating يحتاج:

- earnings delivery,
- further rate normalization,
- new liquidity,
- or behavioral continuation.

---

# Stage 6D — Expected Horizon Market Price & Return Engine — v2.8 REQUIRED

## 6D.1 Expected Horizon Market Price

لكل Scenario:

Expected Horizon Market Price =

Scenario Horizon Earnings/FCF
×
Likely Horizon Multiple / valuation rule

أو DCF/RNAV/SOTP equivalent.

Likely Horizon Multiple يجب أن يراعي:

- normalized rate environment at horizon,
- sector/market valuation regime,
- realized expectations state,
- business quality/ROIC,
- and evidence available today.

لا تفترض convergence كامل إلى economic terminal value بلا justification.

اعرض:

| Scenario | Economic Terminal Value | Expected Horizon Market Price | Why different? |
|---|---:|---:|---|
| Bear | | | |
| Base | | | |
| Bull | | | |

ثم:

PW Expected Horizon Market Price = Σ Scenario Market Price × Probability

EXPECTED-HORIZON-PRICE CONFIDENCE = HIGH / MEDIUM / LOW / NOT RELIABLE

---

## 6D.2 Expected Total Return

RETURN HORIZON = [T]

Expected Total Return =

(PW Expected Horizon Market Price + Expected Cash Dividends − Current Price)
÷ Current Price

Expected Annualized Total Return =

((PW Expected Horizon Market Price + Expected Cash Dividends) ÷ Current Price)^(1/T) − 1

إذا horizon قصير جدًا، اعرض absolute return أولًا.

---

## 6D.3 Investable Opportunity Cost

استخدم investable benchmark فعليًا قدر الإمكان:

1. actual money-market/cash instrument available,
2. representative net MMF/fixed-income return,
3. expected path over same horizon,
4. policy rate فقط كـmacro reference.

INVESTABLE CASH BENCHMARK = [ ]

EXPECTED NET CASH RETURN OVER HORIZON = [ ] / NOT RELIABLE

EXPECTED RETURN SPREAD =

STRONGLY POSITIVE / POSITIVE / MARGINAL / NEGATIVE / NOT RELIABLE

RETURN ATTRACTIVENESS =

EXCEEDS HURDLE / MEETS HURDLE / BELOW HURDLE / INFERIOR CAPITAL USE / NOT RELIABLE

### Critical Rule

`Return Attractiveness = INFERIOR` لا يعني تلقائيًا `Intrinsic Value Position = BEYOND RANGE`.

---

# Stage 6E — Sensitivity, Robustness & Decision Ladder

## 6E.1 Sensitivity

اختبر أهم 2–3 drivers:

- EPS/FCF × multiple.
- growth × margin.
- ROIC × reinvestment.
- WACC × terminal growth.
- RNAV haircut / holding discount.

حدد:

ROBUST FAIR-VALUE RANGE = [ ]

FV RANGE QUALITY = NARROW / MODERATE / WIDE / VERY WIDE / NOT RELIABLE

KEY DECISION PIVOT = [ ]

VALUATION MODEL RISK = LOW / MEDIUM / HIGH / NOT RELIABLE

DECISION ROBUSTNESS = ROBUST / MODERATELY SENSITIVE / HIGHLY SENSITIVE / NOT RELIABLE

---

## 6E.2 Required-Return Entry Price

إذا required return معروف:

Max Entry Price =

(PW Expected Horizon Market Price + Expected Cash Dividends)
÷ (1 + Required Return)^T

هذا **Return Entry Price** وليس Fair Value.

---

## 6E.3 Price Decision Ladder

افصل:

- Deep / Strong Value Zone.
- Attractive Intrinsic Value Zone.
- Required-Return Entry Price.
- Central/PW Intrinsic FV.
- Highest Credible Bull FV.
- Current Price.

لا تنشئ zones بنسب 10%/20% اعتباطية.

---

# Stage 6F — Final Economic Classification — v2.8

Stage 6 لا يصدر Buy/Sell نهائيًا.

أعطِ **ثلاثة أحكام اقتصادية منفصلة**:

## 1. INTRINSIC VALUE POSITION

DEEP DISCOUNT / DISCOUNT / NEAR CENTRAL VALUE / PREMIUM TO CENTRAL VALUE / BEYOND CREDIBLE ECONOMIC RANGE / UNRELIABLE

## 2. PRICE-IMPLIED EXPECTATIONS

UNDemanding / REASONABLE / DEMANDING / VERY DEMANDING / ECONOMICALLY IMPLAUSIBLE / NOT RELIABLE

## 3. EXPECTATIONS REVISION OUTLOOK

STRONG UPWARD / UPWARD / STABLE / DOWNWARD / STRONG DOWNWARD / UNCERTAIN

ثم أعطِ Legacy/summary label فقط للتواصل:

ECONOMIC VALUATION SUMMARY =

CHEAP / ATTRACTIVE / FAIR / RICH BUT PLAUSIBLE / OVERVALUED / SEVERE FUNDAMENTAL DETACHMENT / UNRELIABLE

### v2.8 Overvaluation Rule — REQUIRED

لا تستخدم `OVERVALUED` لمجرد Price > Base/Central FV.

OVERVALUED يتطلب **تركيبة** من:

- Premium واضح إلى probability-supported intrinsic region,
- Price-Implied Expectations = DEMANDING/VERY DEMANDING أو أسوأ,
- Expectations Gap سلبي,
- وعدم وجود Upward Revision edge كافٍ يبرر premium الحالي.

يمكن أن يكون Price أقل من Highest Credible Bull FV ومع ذلك Overvalued إذا السعر يسعّر مقدارًا غير متناسب من Bull economics مع احتمالها.

ويمكن أن يكون Price أعلى من Central FV لكنه `RICH BUT PLAUSIBLE` إذا:

- implied expectations معقولة,
- revision outlook إيجابي/مستقر,
- والـreturn profile ما زال قابلًا للدفاع.

### Severe Fundamental Detachment

يتطلب:

- price beyond credible economic range أو expectations economically implausible,
- مع غياب credible revision/funding path.

---

# Stage 6 Result — REQUIRED OUTPUT

Valuation Status = CURRENT / NEEDS DELTA / STALE / NOT RELIABLE

Valuation Date = [ ]

Financial Data Cutoff = [ ]

Company News Cutoff = [ ]

Capital Structure Basis = [ ]

EPS Reconciliation = PASS / SMALL UNEXPLAINED DIFFERENCE / FAIL / NOT RELIABLE

Intrinsic Value Position = [ ]

Central / PW Present Intrinsic FV = [ ] / NOT RELIABLE

Robust FV Range = [ ] / NOT RELIABLE

Highest Credible Bull FV = [ ] / NOT RELIABLE

Probability-Supported FV Quality = HIGH / MEDIUM / COARSE / NOT RELIABLE

Price-Implied Expectations = [ ]

Implied Revenue CAGR = [ ] / NOT RELIABLE

Implied Margin = [ ] / NOT RELIABLE

Implied EPS/FCF = [ ] / NOT RELIABLE

Implied ROIC/ROE = [ ] / NOT RELIABLE

Implied Growth Duration = [ ] / NOT RELIABLE

Expectations Gap = STRONGLY POSITIVE / POSITIVE / NEUTRAL / NEGATIVE / STRONGLY NEGATIVE / NOT RELIABLE

Expectations Revision Outlook = STRONG UPWARD / UPWARD / STABLE / DOWNWARD / STRONG DOWNWARD / UNCERTAIN

Expectations-Revision Confidence = HIGH / MEDIUM / LOW / NOT RELIABLE

Rerating Attribution = [ ]

Economic Terminal Value @ Horizon = [ ] / NOT RELIABLE

Expected Horizon Market Price @ Horizon = [ ] / NOT RELIABLE

Expected-Horizon-Price Confidence = HIGH / MEDIUM / LOW / NOT RELIABLE

Expected Total Return = [ ] / NOT RELIABLE

Expected Annualized Total Return = [ ] / NOT RELIABLE

Expected Return Spread = STRONGLY POSITIVE / POSITIVE / MARGINAL / NEGATIVE / NOT RELIABLE

Return Attractiveness = EXCEEDS HURDLE / MEETS HURDLE / BELOW HURDLE / INFERIOR CAPITAL USE / NOT RELIABLE

Investable Cash Benchmark = [ ] / NOT RELIABLE

Expected Net Cash Return Over Horizon = [ ] / NOT RELIABLE

Base FDR = [ ] / NOT RELIABLE

Optimistic FDR = [ ] / NOT RELIABLE

Margin of Safety = [ ] / NOT RELIABLE

Upside to Central FV = [ ] / NOT RELIABLE

Multiple Calibration = WELL SUPPORTED / REASONABLE / WEAK / NOT RELIABLE

Nominal/Real Consistency = CLEAN / FAIL / NOT APPLICABLE

Valuation Time-Basis Consistency = CLEAN / ADJUSTMENT REQUIRED / NOT RELIABLE

Reverse-Valuation Horizon Match = CLEAN / ADJUSTMENT REQUIRED / NOT RELIABLE

RNAV / Earnings Overlap Check = [ ]

Valuation Model Risk = LOW / MEDIUM / HIGH / NOT RELIABLE

Decision Robustness = ROBUST / MODERATELY SENSITIVE / HIGHLY SENSITIVE / NOT RELIABLE

Key Decision Pivot = [ ]

Required-Return Entry Price = [ ] / NOT APPLICABLE / NOT RELIABLE

Economic Valuation Summary = CHEAP / ATTRACTIVE / FAIR / RICH BUT PLAUSIBLE / OVERVALUED / SEVERE FUNDAMENTAL DETACHMENT / UNRELIABLE

Confidence = HIGH / MEDIUM / LOW

لا تنتقل للشارت.

---

# Stage 7 — Catalyst & Expectations-Revision Gate — v2.8

حدد Catalysts خلال 3–12 شهرًا، لكن لا تكتفِ بالسؤال "هل يوجد Catalyst؟".

السؤال الأهم:

> **أي توقع مضمن في السعر يمكن لهذا الحدث أن يرفعه أو يخفضه؟**

فرق بين:

Fundamental Catalyst

Trading Catalyst

Structural Catalyst

Optionality Catalyst

Expectations-Revision Catalyst

---

## 7.1 Catalyst Inventory

لكل Catalyst حدد:

- Event.
- Confirmed / estimated date.
- Source.
- Status.
- Economic channel.
- Is it new?
- Is it priced in?
- Remaining repricing potential.
- What KPI proves success/failure?
- Included in Base/Bull FV?

---

## 7.2 Expectations-Revision Map — REQUIRED

لكل حدث مادي:

EVENT
→ Which price-implied expectation changes?
→ Revenue / Margin / ROIC / Growth Duration / Funding / Risk / Multiple
→ Direction
→ Magnitude
→ Evidence needed

| Catalyst | Price-Implied Driver Affected | Current Market Expectation | Revision If Successful | Revision If Failed | Probability | Revision Potential |
|---|---|---|---|---|---:|---|
| | | | | | | |

صنف:

CATALYST REVISION POTENTIAL =

HIGH POSITIVE / MODERATE POSITIVE / NEUTRAL / MODERATE NEGATIVE / HIGH NEGATIVE / TWO-SIDED / NOT RELIABLE

### Rule

Catalyst قد يكون قويًا إخباريًا لكنه ضعيف اقتصاديًا إذا لا يغير expectations بصورة مادية.

وCatalyst صغير ظاهريًا قد يكون قويًا إذا يحسم Decision Pivot مثل margin normalization أو regulatory clearance.

---

## 7.3 Priced-In Test

لا تستخدم "Priced In" كحكم انطباعي.

قارن:

- Event economics versus Price-Implied Expectations from Stage 6B.
- Reaction already observed.
- Remaining execution milestones.
- Whether market price already requires success.

صنف:

OPEN / PARTLY PRICED / MOSTLY PRICED / FULLY PRICED / FAILED / EXPIRED / UNCERTAIN

---

## 7.4 Negative Catalysts

راجع بنفس القوة:

- Earnings deterioration.
- Margin miss.
- Funding/dilution.
- Regulatory issue.
- Debt/refinancing.
- Major-holder selling.
- Project delay.
- Contract cancellation.
- Failure to monetize optionality.
- Discount-rate shock.

---

## 7.5 Event Calendar & Horizon Collision — REQUIRED

راجع:

- Earnings/results.
- AGM/EGM.
- Rights/capital-action dates.
- Dividends.
- Tender/M&A deadlines.
- Debt maturities.
- Regulatory decisions.
- Project commissioning.
- Lock-up releases.
- Any event capable of gap or tradability change.

| Event | Date | Evidence | Inside Horizon? | Gap/Structural Risk | Expected-Revision Effect | Action Implication |
|---|---|---|---|---|---|---|
| | | | YES/NO | LOW/MEDIUM/HIGH/BINARY | | |

HORIZON EVENT COLLISION = NONE / MANAGEABLE / MATERIAL / BINARY / NOT RELIABLE

إذا Binary Event داخل horizon:

- لا تعتمد على stop وحده.
- عدّل size/timing.
- اذكر Gap Through Stop.

---

# Stage 7 Result

Catalyst Strength = STRONG / MODERATE / WEAK

Catalyst Revision Potential = HIGH POSITIVE / MODERATE POSITIVE / NEUTRAL / MODERATE NEGATIVE / HIGH NEGATIVE / TWO-SIDED / NOT RELIABLE

Expectations Revision Outlook — Updated = STRONG UPWARD / UPWARD / STABLE / DOWNWARD / STRONG DOWNWARD / UNCERTAIN

Horizon Event Collision = NONE / MANAGEABLE / MATERIAL / BINARY / NOT RELIABLE

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

## Information-Reaction Regime — v2.8 REQUIRED WHEN EVENT-DRIVEN

لا تستخدم افتراضًا عامًا عن "نفسية المستثمر المصري".

صنف السلوك الحالي من الأدلة point-in-time:

INFORMATION-REACTION REGIME =

UNDERREACTION / CONTINUATION / OVERREACTION / REVERSAL / MIXED / INCONCLUSIVE / NOT APPLICABLE

استخدم:

- event return,
- +1/+2/+5 follow-through,
- volume/value ratios,
- RS,
- price-limit behavior,
- earnings/catalyst revisions,
- participant flows إذا توفرت بصورة موثوقة.

### Rule

لا تضف `Egyptian Herd Premium` أو `Behavioral Fair Value`.

السلوك يؤثر على timing / expected revision / horizon market price عند وجود evidence، لكنه لا يغير intrinsic cash flows بلا economic bridge.

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

Information-Reaction Regime = UNDERREACTION / CONTINUATION / OVERREACTION / REVERSAL / MIXED / INCONCLUSIVE / NOT APPLICABLE

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

# Stage 10 — Portfolio Fit & Fresh-Capital Allocation Gate — v2.8

استخدم أحدث بيانات المحفظة المتاحة.

إذا قديمة:

PORTFOLIO DATA STALE

---

## 10.1 Exposure

افحص:

- Direct exposure.
- Indirect exposure via funds/indexes.
- Industry/sector exposure.
- Economic-driver concentration.
- Correlation.
- Duplication.
- Liquidity.
- Speculation allocation.

---

## 10.2 Fresh Capital Test — v2.8 FOUR-PILLAR REQUIRED

لا تجعل `Price > Central FV` يحدد النتيجة تلقائيًا.

اسأل أربعة أسئلة مستقلة:

### Pillar A — Economic Quality

هل النشاط والأرباح والميزانية وROIC يسمحون بخلق قيمة؟

ECONOMIC QUALITY = STRONG / ACCEPTABLE / WEAK

### Pillar B — Expectations Burden

هل Price-Implied Expectations من Stage 6B:

UNDemanding / REASONABLE / DEMANDING / VERY DEMANDING / IMPLAUSIBLE؟

### Pillar C — Expectations Revision Edge

هل Stage 6C + Stage 7 تشير إلى:

UPWARD / STABLE / DOWNWARD revision edge؟

### Pillar D — Risk-Adjusted Return

هل Expected Horizon Market Price + cash dividends ينتجان Expected Return Spread مناسبًا مقابل cash/benchmark؟

---

## Fresh Capital Decision

بعد الأعمدة الأربعة، اسأل:

> لو لم أملك السهم اليوم، هل هو من أفضل استخدامات رأس المال **بالسعر الحالي وتوقعات السوق الحالية**؟

FRESH CAPITAL TEST = YES / BORDERLINE / NO

### Examples

- Premium to Central FV + REASONABLE expectations + UPWARD revision + POSITIVE return spread → يمكن أن يكون YES/BORDERLINE.
- Discount to FV + DOWNWARD revision + weak economics → قد يكون NO.
- Cheap but unfinanceable growth → NO/BORDERLINE.

### Prohibition

Cost basis / break-even desire / average-down desire لا تدخل في Fresh Capital Test.

---

## 10.3 Opportunity-Cost Test

قارن مع:

- Investable cash/MMF.
- Broad EGX exposure.
- Best comparable stocks.
- Same-sector alternatives.

استخدم Stage 6D Expected Annualized Return عندما يكون موثوقًا.

Expected Return Spread vs Cash = Stock Expected Annualized Return − Expected Cash Return

Expected Return Spread vs Benchmark = Stock Expected Annualized Return − Benchmark Expected Return

صنف:

OPPORTUNITY COST = TOP-TIER CAPITAL USE / ACCEPTABLE / INFERIOR / NOT RELIABLE

---

## 10.4 Ownership State

NOT OWNED / OWNED / OWNED & OVERWEIGHT / OWNED & UNDERWEIGHT

إذا OWNED، قيّم المركز كما لو تحول إلى Cash اليوم.

OWNED POSITION ACTION = ADD / HOLD / TRIM / EXIT / NOT APPLICABLE

---

## 10.5 Position Sizing

افصل:

Investment Position

Speculation Position

استخدم:

- Stage 9 exit capacity.
- Max executable position.
- Fundamental risk.
- Expectations risk.
- Event risk.
- Valuation risk.
- correlation/duplication.

Liquidity Weight Cap = Maximum Executable Position ÷ Total Portfolio Value

Maximum Allowed Weight = min(Portfolio Risk Limit, Liquidity Cap, Concentration Limit, Fundamental/Event Limit)

إذا البيانات ناقصة: Range أو NOT RELIABLE.

---

# Stage 10 Result

Portfolio Fit = PASS / PASS WITH SIZE LIMIT / FAIL

Economic Quality = STRONG / ACCEPTABLE / WEAK

Expectations Burden = UNDemanding / REASONABLE / DEMANDING / VERY DEMANDING / IMPLAUSIBLE / NOT RELIABLE

Expectations Revision Edge = UPWARD / STABLE / DOWNWARD / UNCERTAIN

Risk-Adjusted Return = SUPERIOR / ADEQUATE / INFERIOR / NOT RELIABLE

Fresh Capital Test = YES / BORDERLINE / NO

Opportunity Cost = TOP-TIER CAPITAL USE / ACCEPTABLE / INFERIOR / NOT RELIABLE

Owned Position Action = ADD / HOLD / TRIM / EXIT / NOT APPLICABLE

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

## B. Valuation / Expectations Risk

- Intrinsic Value Position.
- Price-Implied Expectations burden.
- Expectations Gap.
- Expectations Revision Outlook.
- FDR / Margin of Safety where useful.
- Degree of execution already priced in.
- Risk that Expected Horizon Market Price fails to converge to economic value.

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

# Stage 11 — Final Decision Engine — v2.8

اجمع نتائج جميع المراحل السابقة.

لا تعيد التحليل من البداية.

لا تغير رقمًا سابقًا إلا بسبب موثق.

---

# 11.1 Five-Pillar Investment Decision — v2.8 REQUIRED

لـLONG-TERM INVESTMENT / FULL HYBRID REVIEW، اعرض خمسة أعمدة قبل الحكم:

| Investment Pillar | Result |
|---|---|
| 1. Business / Earnings / Financial Quality | |
| 2. Intrinsic Value Position | |
| 3. Price-Implied Expectations | |
| 4. Expectations Revision Outlook | |
| 5. Expected Risk-Adjusted Return / Opportunity Cost | |

### Decision Principle

لا يوجد Pillar منفرد يحدد القرار تلقائيًا ما لم يكن Hard Gate.

أمثلة مسموحة:

- Premium to Central FV + Reasonable expectations + Upward revisions + Superior expected return → ACCUMULATE ممكن.
- Discount to FV + Downward revisions + broken economics → WATCH/AVOID ممكن.
- Strong company + Very Demanding expectations + Negative return spread → WATCH/AVOID.

---

# 11.2 Decision Matrix

| Gate | Result |
|---|---|
| Analysis Objective / Horizon | |
| Run Mode | |
| Project Funnel Status / Update Mode | |
| Data Integrity | |
| EPS Reconciliation | |
| News Delta | |
| Price Integrity | |
| Capital Structure Basis | |
| Valuation Freshness | |
| Business Quality | |
| Earnings Quality | |
| Financial Strength | |
| Growth / Value-Creating Growth | |
| Corporate Action / Dilution | |
| Market Valuation Regime | |
| Rerating Attribution | |
| Market Tape Regime | |
| Event Calendar / Horizon Collision | |
| Intrinsic Value Position | |
| Central / PW Intrinsic FV | |
| Price-Implied Expectations | |
| Expectations Gap | |
| Expectations Revision Outlook | |
| Economic Terminal Value | |
| Expected Horizon Market Price | |
| Expected Total / Annualized Return | |
| Expected Return Spread | |
| Return Attractiveness | |
| Catalyst Revision Potential | |
| Speculation Classification | |
| Information-Reaction Regime | |
| Behavioral Repricing Family | |
| Psychological Price Map / PLSS | |
| Signal Calibration Status | |
| Breakout Acceptance | |
| Timing Quality / Execution | |
| Exit Capacity / Max Executable Position | |
| Portfolio Fit | |
| Fresh Capital Test | |
| Opportunity Cost | |
| Integrated Risk | |
| Universal No-Trade Gate | |

---

# 11.3 Unified Price Map — REQUIRED

| Price Layer | Level / Zone | Source | Meaning |
|---|---:|---|---|
| Current Executable Price | | Market | current executable price |
| Deep / Strong Value Zone | | Intrinsic | if defensible |
| Required-Return Entry Price | | Return | hurdle-based, not FV |
| Attractive Intrinsic Entry Zone | | Intrinsic | valuation sensitivity |
| Central / PW Intrinsic FV | | Intrinsic | economic center |
| Highest Credible Bull FV | | Intrinsic | credible upper economics |
| Nearest Psychological Support | | Behavioral | memory/clustering |
| Nearest Psychological Resistance | | Behavioral | memory/clustering |
| Breakout Trigger | | Technical | setup trigger, not FV |
| Do-Not-Chase | | Execution | poor trade economics |
| Invalidation | | Execution | setup invalidation, not guaranteed fill |
| First Trading Target | | Technical | short horizon |
| Price-Limit Boundary | | Market Rule | when relevant |
| Rights-Implied Share Cost | | Capital Action | when relevant |

لا تدمج هذه المستويات في رقم واحد.

---

# 11.4 Universal No-Trade / Investment Hard Gates

احتفظ بقواعد v2.7 التالية:

## Universal No-Trade

NEW ENTRY / ADD / ENTER SPECULATION = NO TRADE إذا كان بصورة مادية وغير محلولة:

- trading/suspension status يمنع التنفيذ الطبيعي,
- strategy requires rapid exit but account/segment rules prevent it,
- FILLABILITY = NOT EXECUTABLE,
- material fraud/auditor/regulatory event يجعل المخاطر غير قابلة للتقدير,
- capital-action entitlement mechanics غير مفهومة ومادية,
- PRICE INTEGRITY = NOT RELIABLE للتنفيذ الدقيق,
- rights/share bases/timestamps غير قابلة للمقارنة,
- EXIT CAPACITY = POOR للحجم ولا يمكن خفضه,
- market/trading data متناقضة جوهريًا,
- share/economic rights structure غير قابلة للنمذجة.

إذا OWNED، NO TRADE لا يمنع TRIM/EXIT risk-reducing إذا كان قابلًا للتنفيذ.

## Investment-Buy Hard Gates

Investment Buy غير مسموح إذا:

- Data Quality منخفضة بشكل يمنع valuation,
- Earnings/Financial/Governance Gate = material FAIL,
- EPS/share count/capital basis جوهري وغير قابل للمصالحة,
- valuation stale/not reliable بلا delta,
- unbridged material company-news delta.

Speculation قد تظل ممكنة فقط إذا لا يوجد Universal Gate وشروط Stage 9 صالحة.

---

# 11.5 State-Specific Decision Hierarchy

## NOT OWNED — Investment

STRONG BUY / ACCUMULATE / WATCH / AVOID / REJECT

## OWNED

ADD / HOLD / TRIM / EXIT

## Speculation

ENTER SPECULATION / WAIT FOR SPECULATION / TAKE PROFIT / EXIT SPECULATION / NO TRADE

## FULL HYBRID

أعطِ:

- Investment View.
- Speculation View.
- ثم Final Action واحد فقط حسب ownership/objective.

---

# 11.6 v2.8 Conclusion Calibration Checklist — REQUIRED

قبل القرار النهائي اسأل:

1. هل EPS reconciled على numerator/denominator صحيحين؟ إذا لا، block P/E logic.
2. هل السعر أعلى من Central FV فقط، أم أن Price-Implied Expectations نفسها demanding؟
3. هل Expectations Gap إيجابي أم سلبي؟
4. هل Revision Outlook Upward أم Downward؟ وما evidence؟
5. هل Expected Horizon Market Price تم خلطه مع Economic Terminal Value؟ إذا نعم صحح.
6. هل rerating الحالي earnings-led أم rate-led أم flow/behavioral؟
7. هل growth يخلق قيمة عبر ROIC > cost of capital أم مجرد يزيد الحجم؟
8. هل required return الشخصي اختلط بFair Value؟
9. هل Spot CBE rate استخدمت كـperpetual discount anchor؟
10. هل same risk خُصم أكثر من مرة؟
11. هل positive/negative uncertainty treated symmetrically؟
12. هل Base/Bull probabilities تعتمد على execution/funding مترابط وتم استخدام conditional probabilities؟
13. هل current price needs Bull economics أكبر من Bull probability/evidence؟
14. هل Price-Implied Expectations يمكن تحقيقها داخل Base/Bull من غير heroic assumptions؟
15. هل catalyst القادم يغيّر أي implied expectation ماديًا؟
16. هل market reaction يبدو underreaction/continuation أم overreaction/reversal؟
17. هل sample selection momentum-biased؟
18. هل technical signal heuristic وغير calibrated؟
19. هل horizon event يمكن أن يعمل gap through stop؟
20. هل trade executable فعليًا؟
21. هل Fresh Capital Test يعتمد على الأربعة أعمدة أم على Central FV وحدها؟
22. هل Expected Return يتفوق على investable cash/benchmark بعد risk؟
23. هل final decision robust عبر sensitivity معقولة؟
24. هل current price itself treated as information-bearing forecast—not truth and not noise؟

---

# 11.7 Final Explanation — REQUIRED

اشرح باختصار منظم:

1. Objective + horizon + ownership.
2. Investment thesis في 3 جمل.
3. Business/Earnings quality.
4. Intrinsic Value Position.
5. Central/PW FV + robust range + highest credible Bull FV.
6. Price-Implied Expectations: growth/margin/ROIC/duration.
7. Expectations Gap.
8. Expectations Revision Outlook + confidence.
9. Rerating Attribution.
10. Economic Terminal Value vs Expected Horizon Market Price.
11. Expected Total/Annualized Return.
12. Investable cash benchmark + return spread.
13. Growth value creation / incremental ROIC.
14. Catalyst Revision Potential.
15. Fresh Capital Test.
16. Opportunity Cost.
17. Timing / execution / fillability.
18. Event calendar/horizon collision.
19. Integrated Risk + key risk driver.
20. Universal No-Trade Gate.
21. Unified Price Map.
22. Price/event/KPI that would change the decision.

---

# Final Decision Summary — v2.8

Analysis Objective: [ ]

Run Mode: [ ]

Intended Horizon: [ ]

Ownership State: [ ]

Primary Benchmark: [ ]

Project Funnel Status: [ ]

Update Mode: [ ]

Data Confidence: HIGH / MEDIUM / LOW

EPS Reconciliation: PASS / SMALL UNEXPLAINED DIFFERENCE / FAIL / NOT RELIABLE

News Delta: [ ]

Price Integrity: [ ]

Capital Structure Basis: [ ]

Valuation Status / Date / Cutoffs: [ ]

Business Quality: STRONG / ACCEPTABLE / WEAK

Earnings Quality: STRONG / ACCEPTABLE / WEAK

Financial Strength: STRONG / ACCEPTABLE / WEAK

Growth Strength: STRONG / MODERATE / WEAK

Value-Creating Growth: STRONG / POSITIVE / NEUTRAL / VALUE-DESTROYING / NOT RELIABLE

Capital Action Economics: ACCRETIVE / NEUTRAL / DILUTIVE / TOO EARLY TO KNOW

Market Regime: [ ]

Rerating Attribution: [ ]

Market Tape Regime: [ ]

Intrinsic Value Position: DEEP DISCOUNT / DISCOUNT / NEAR CENTRAL VALUE / PREMIUM TO CENTRAL VALUE / BEYOND CREDIBLE ECONOMIC RANGE / UNRELIABLE

Central / PW Intrinsic FV: [ ]

Robust FV Range: [ ]

Highest Credible Bull FV: [ ]

Price-Implied Expectations: UNDemanding / REASONABLE / DEMANDING / VERY DEMANDING / ECONOMICALLY IMPLAUSIBLE / NOT RELIABLE

Implied Revenue CAGR / Margin / ROIC / Growth Duration: [ ]

Expectations Gap: STRONGLY POSITIVE / POSITIVE / NEUTRAL / NEGATIVE / STRONGLY NEGATIVE / NOT RELIABLE

Expectations Revision Outlook: STRONG UPWARD / UPWARD / STABLE / DOWNWARD / STRONG DOWNWARD / UNCERTAIN

Expectations-Revision Confidence: HIGH / MEDIUM / LOW / NOT RELIABLE

Economic Terminal Value @ Horizon: [ ]

Expected Horizon Market Price @ Horizon: [ ]

Expected-Horizon-Price Confidence: HIGH / MEDIUM / LOW / NOT RELIABLE

Expected Total Return: [ ]

Expected Annualized Total Return: [ ]

Investable Cash Benchmark: [ ]

Expected Net Cash Return Over Horizon: [ ]

Expected Return Spread: STRONGLY POSITIVE / POSITIVE / MARGINAL / NEGATIVE / NOT RELIABLE

Return Attractiveness: EXCEEDS HURDLE / MEETS HURDLE / BELOW HURDLE / INFERIOR CAPITAL USE / NOT RELIABLE

Economic Valuation Summary: CHEAP / ATTRACTIVE / FAIR / RICH BUT PLAUSIBLE / OVERVALUED / SEVERE FUNDAMENTAL DETACHMENT / UNRELIABLE

Catalyst Strength: STRONG / MODERATE / WEAK

Catalyst Revision Potential: [ ]

Information-Reaction Regime: UNDERREACTION / CONTINUATION / OVERREACTION / REVERSAL / MIXED / INCONCLUSIVE / NOT APPLICABLE

Speculation Classification: [ ]

Timing Quality: GOOD / NEUTRAL / POOR

Execution Action: [ ]

Fillability / Exit Capacity / Max Executable Position: [ ]

Portfolio Fit: PASS / PASS WITH SIZE LIMIT / FAIL

Fresh Capital Test: YES / BORDERLINE / NO

Opportunity Cost: TOP-TIER CAPITAL USE / ACCEPTABLE / INFERIOR / NOT RELIABLE

Overall Risk: LOW / MEDIUM / HIGH / EXTREME / NOT RELIABLE

Universal No-Trade Gate: YES / NO

Final Decision Domain: INVESTMENT / OWNED-POSITION / SPECULATION / HYBRID

Final Decision: STRONG BUY / ACCUMULATE / WATCH / AVOID / REJECT / ADD / HOLD / TRIM / EXIT / ENTER SPECULATION / WAIT FOR SPECULATION / TAKE PROFIT / EXIT SPECULATION / NO TRADE

Final Confidence: HIGH / MEDIUM / LOW

---

# v2.8 Change-Control Principles

هذا الإصدار يحافظ على قواعد v2.7 ويضيف/يصحح ما يلي:

1. Intent and horizon before analysis.
2. Delta before rebuild.
3. Fact-specific evidence hierarchy.
4. Same capital-structure basis for Price/EPS/FV.
5. **EPS numerator/denominator reconciliation is a hard gate before EPS/P-E valuation.**
6. News requires an economic bridge before Base FV.
7. Growth must be linked to incremental ROIC/ROE and capital required; growth is not value by itself.
8. Conditional probabilities when scenarios are dependent.
9. Positive and negative uncertainty must be symmetric.
10. Probability-weighted intrinsic value must not be double-counted inside blended valuation.
11. Intrinsic Value, Price-Implied Expectations, Expectations Revision and Expected Return are **co-equal investment engines**.
12. Current Price is information-bearing forecast—not Fair Value and not noise.
13. `Price > Central FV` does not automatically mean OVERVALUED or AVOID.
14. Market-Implied Expectations must reverse-engineer value drivers, not only EPS when feasible.
15. Reverse valuation should estimate Revenue CAGR, margins, ROIC/ROE, reinvestment, growth duration and funding when possible.
16. **Economic Terminal Value and Expected Horizon Market Price are distinct objects.**
17. Expected Return should use Expected Horizon Market Price when feasible, not assume full convergence to intrinsic value.
18. Expectations Gap compares market-required economics with probability-weighted economics.
19. Expectations Revision Outlook asks whether future evidence is likely to move market expectations up or down.
20. Catalysts must map to the specific expectation they can revise.
21. Rerating should be attributed to earnings, rates, quality, flows or behavior where possible.
22. No arbitrary `Egyptian Herd Premium`, `Behavioral Fair Value`, or nationality-based psychology adjustment.
23. EGX behavior must be classified from observed reaction regime: underreaction, continuation, overreaction, reversal, mixed or inconclusive.
24. Required return remains separate from intrinsic value.
25. Spot policy/cash yield is not a perpetual Fair-P/E formula.
26. Nominal/real consistency remains mandatory.
27. Fair Value sensitivity and robustness remain mandatory.
28. Price below Highest Credible Bull FV is not sufficient to make price reasonable.
29. Price above Base/Central FV is not sufficient to make price overvalued.
30. **OVERVALUED requires a probability-supported intrinsic premium plus demanding/improbable implied expectations and/or negative expectations gap without sufficient positive revision edge.**
31. RICH BUT PLAUSIBLE can apply above Central FV when implied expectations are reasonable and revision/return evidence supports the premium.
32. Value-creating growth requires ROIC/ROE relative to cost of capital.
33. Market Tape remains timing context, not automatic intrinsic-value input.
34. PLSS remains heuristic until EGX calibration.
35. Event dates inside horizon remain gap/structural risk.
36. Maximum executable position precedes portfolio sizing.
37. Fresh Capital Test uses four pillars: economic quality, expectations burden, revision edge, risk-adjusted return.
38. Cheap stock can still fail Fresh Capital Test if revisions are downward or economics are deteriorating.
39. Premium stock can still pass/borderline if expectations are reasonable, revision edge positive and expected return superior.
40. Universal No-Trade Gates remain superior to all attractiveness labels.
41. Owned positions continue to allow ADD/HOLD/TRIM/EXIT independent of cost basis.
42. Final risk remains decomposed, not averaged mechanically.
43. Unified Price Map keeps intrinsic, behavioral, technical and execution levels separate.
44. Historical multiples remain regime-adjusted.
45. Selection bias must be disclosed for momentum/catalyst-selected samples.
46. Cross-sectional calibration warning remains required for batch/universe analysis.
47. Decision confidence must separately consider intrinsic valuation, implied expectations, revision outlook and horizon-price confidence.
48. Final decision must state what price/event/KPI would change the expectations gap or revision outlook.
49. No model component is allowed to become a hidden hard gate merely because it is numerically precise.
50. v2.8 prefers **expectations-aware capital allocation** over point-estimate fair-value anchoring.

END OF MASTER FUNNEL — v2.8
