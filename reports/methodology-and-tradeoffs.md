# Methodology, assumptions and trade-offs

Technical companion to the three challenges. Written for a reviewer who wants to know
what was assumed, why each method was chosen, and what would be done differently with
more time. Every number cited here is produced by a script in `scripts/` and reproduced
in the stage reports; nothing is hand-entered.

Reproduce everything with `uv sync && uv run scripts/run_all.py`.

---

## 1. What the data turned out to be

The extract holds **358,775 transactions**, 6 SKUs, 12 warehouses, 52,555 clients and
79 combos, spanning **74 complete weeks** (2025-01-02 to 2026-05-30) with no missing weeks.
The stated grain — day × client × product × ticket × promotion — holds exactly: zero
duplicate rows. Dates are `dd/mm/yyyy`, verified against the independent `year`/`month`
columns rather than assumed.

Three things about the data changed how the case had to be answered. All three are
documented as findings with evidence in [`docs/FINDINGS.md`](../docs/FINDINGS.md) and
raised as questions to VEMIO in [`docs/ROADMAP.md`](../docs/ROADMAP.md), each with a
fallback so no question blocked progress.

**`product_cost` exceeds gross revenue on every single row (F-003).** The ratio
`product_cost / bruto` is *exactly* constant within each SKU — standard deviation 0.0 to
nine decimals — and equals 1.22, 1.24, 1.26, 1.27 and 1.30. Subtract one and you get
0.22–0.30: precisely the band the data dictionary attributes to the missing
`product_margin` column. Read literally, the client loses 18–23% on every transaction,
which is not a business. The file has `cost = price × (1 + margin)` where a markup over
cost implies `cost = price ÷ (1 + margin)` — the same factor, applied backwards.

> **Assumption adopted**: `margin = product_cost/bruto − 1`, and `unit cost = list price ÷
> (1 + margin)`. It is isolated in one module (`src/analysis/economics.py`) so it can be
> switched in a single place if VEMIO answers otherwise. Every margin figure in this
> deliverable inherits it; **no volume figure does.** The sensitivity is shown rather than
> asserted: under the literal reading, every price ever charged is loss-making and no
> pricing recommendation is possible at all.

**`product_margin` is absent from the delivered file (F-001)** although Challenge B names
it. The evidence above makes it exactly recoverable, which is why the challenge is
answerable at all.

**`discount` is a fraction, not percentage points, and reconciles only at bundle level
(F-004).** On the 128,977 promoted rows that show a gross/net gap, reading `discount` as a
currency amount matches **zero** rows; reading it as `(gross − net)/gross` matches 48%
within 0.001 — close but never exact, exactly as the dictionary's "calculated as bundle"
note predicts. It is also negative on 2.81% of rows, which is a surcharge and is
unexplained.

> **Consequence**: effective price is always computed as `sell_in_amount ÷
> sell_in_quantity`. Applying `discount` to `bruto` would be wrong on more than half the
> promoted rows — silently, and in the one variable Challenge B depends on.

**Cleaning** follows one rule: flag, never delete. Six boolean columns carry the reasons
(zero quantity, zero amount, missing money, incomplete metadata, negative discount, promo),
and each stage picks its own selector. 99.86% of rows are usable for demand and 96.9% for
price work. Zero-amount rows keep their units — shipping stock free of charge is real
demand, and dropping it would bias a units forecast downward — but are excluded from price
work, because a realised price of zero is not a point on a demand curve. The single
incomplete-metadata record the case warns about was located exactly (one row, 2026-02-18)
rather than filtered away as a symptom.

---

## 2. Challenge A — Demand forecasting

**Approach.** Weekly units for three SKUs chosen to span the failure modes rather than for
convenience: **1857** (largest volume, unpromoted for most of the history — the clean
case), **1283** (26-fold swing between trough and peak months — the seasonal case), and
**1665** (promoted in ~95% of weeks — the promo-saturated case). Horizon 12 weeks.

**Validation.** Five rolling origins spaced three weeks apart, expanding window. Each model
sees only weeks 1…t and is scored on t+1…t+12. No feature is computable from the period it
is scored on. A single holdout would measure how a model did on one particular quarter,
which is a claim about that quarter and not about the model.

**Metric.** WAPE, and the reasoning matters more than the choice. MAPE divides by each
week's actual, so a quiet 20-unit week can contribute a 300% error and dominate the
average; worse, it structurally rewards under-forecasting, because an over-forecast's error
is unbounded while an under-forecast caps at 100%. For replenishment, cost is incurred per
unit and being short is at least as expensive as being long. WAPE weights every unit
equally. MASE is reported alongside as a sanity check against doing nothing.

**Result — and an honest one.** Seven models were compared. On two of the three SKUs
**nothing beat the naive baselines**: a 4-week moving average wins on 1857 (WAPE 0.257) and
on 1665 (0.291). Only on the seasonal SKU did a candidate earn its place — damped drift on
1283 at WAPE 0.272 against the best baseline's 0.322, a 15.5% improvement.

That candidate exists because of a diagnostic, not a hunch: a first pass showed *every*
level-only model under-forecasting by 13–30%, which meant the series were drifting upward
and flat forecasts could not follow. Damped drift extrapolates the recent slope while
damping it, so a 12-week horizon does not run away. Reporting that two of three SKUs are
best served by a moving average is the finding, not a failure to find one.

**Trade-offs taken.**
- **Seasonality was deliberately not modelled inside ETS.** A 52-week period needs at least
  two full cycles to estimate; this history has ~1.4. Fitting it would have produced a
  confident-looking season built from noise.
- **Promotional pressure is not a covariate.** It drives a large share of weekly variation,
  but future promo plans are not in the dataset. Including one would require assuming the
  plan is known — entirely defensible in production, where trade marketing sets the
  calendar months ahead, and leakage in a backtest. The forecast is therefore a demand
  expectation *under a promotional pattern resembling the recent past*, and that condition
  should travel with the number.
- **Point forecasts, not intervals.** A replenishment decision needs a service level, which
  needs a distribution. This is the first thing to add with more time.

---

## 3. Challenge B — Price elasticity

**SKU selection was a criterion fixed before estimating**, not a result: the widest observed
price support, because that is exactly what bounds the simulator's valid domain. Two SKUs
qualified (F-006); **1665** has both the wider range and the larger volume.

**Identification before regression.** This SKU is on promotion in nearly every week, so its
price moves through changes in *discount depth*, not list price. What is estimated is the
response to realised price under promotion. That is the right input for a trade-promotion
decision — the actual question being asked — but it is not evidence about a permanent
list-price change.

**Specification.** Log-log demand with a linear trend and second-order annual Fourier
terms, so the price coefficient does not quietly absorb "March is a strong month".
Newey-West (HAC) standard errors, because weekly demand is autocorrelated and plain OLS
errors would report more confidence than the evidence supports.

**Result.** Elasticity **−4.73**, 95% CI **[−5.71, −3.76]**, R² 0.76 over 72 weeks.

An elasticity near −5 is high for a household staple, and that is informative rather than
suspicious: **this is sell-in, not sell-out.** Distributors buy ahead when a discount
appears, so sell-in absorbs genuine demand response *and* forward-buying, and is routinely
several times more elastic than consumer demand. The practical reading is that this number
tells you how much distributors will load in — not how many extra units reach shoppers.

**The simulator** spans the observed price range (42.87–64.20) and cannot be queried outside
it. Its most actionable output is a **break-even price of ≈47**: below that, every extra
unit is sold at a loss, and roughly a third of the history sat below the line. Revenue
peaks at the boundary of the observed range — a corner solution, meaning the true revenue
optimum may lie below anything the data has seen, which is precisely where the simulator
correctly refuses to answer. The recommendation is therefore built on the margin curve,
which peaks *inside* the evidence at 58.78; the balanced price is **55.16**, giving ~949
units/week, ~52,400 revenue and ~16.1% margin.

**Risks.** Constant elasticity assumes the same percentage response at every price; over a
range this wide the true curve almost certainly bends, so the estimate is most trustworthy
near the middle — which is where the recommendation sits. Weekly aggregation hides mix: two
weeks at the same average price can have very different underlying offers. No competitor or
stock-out data exists, so those shifts sit in the residual.

---

## 4. Challenge C — Promotional uplift

**Episodes, not combo codes.** Combos overlap on the same SKU, so what the business
actually ran is the combined promotional pressure. Episodes are contiguous runs of weeks
where more than half of a SKU's units sold under a combo. Twelve were detected; nine had
enough preceding weeks to establish a baseline.

**Two counterfactuals, deliberately.** A clean pre-period baseline (median of six preceding
*quiet* weeks — comparing a promotion against another promotion is the classic error), and
a difference-in-differences adjustment scaling that baseline by how much SKUs *not*
promoted in the same weeks moved. They rest on different assumptions, and where they
diverge the divergence is itself the finding.

**Every episode is graded on identification** — clean baseline, controls available, post
window observable — because a well-measured small effect is worth more than a large one
that cannot be separated from the season. Only one episode grades `strong`. Where
`control_skus` reads *none available*, every other SKU was itself promoted and the
difference-in-differences correction collapses to the naive comparison; those rows are
marked `weak` and the recommendations do not rest on them.

**Pull-forward is always checked.** Six post-promotion weeks. Volume repaid by a later
slump was displaced in time, not created, and net uplift subtracts it.

**The economics are where the answer lives.** Incremental margin counts only the units a
promotion created; the discount is paid on *every* unit sold in the window, including those
that would have sold anyway. That asymmetry is why several episodes with genuinely positive
volume uplift still destroyed margin.

**Trade-offs and limits.**
- **No client-level control group exists.** Everyone was offered the promotion, so the
  control is other SKUs, which have their own demand drivers. Parallel trends across three
  product categories is an assumption doing real work and cannot be tested here.
- **Cannibalisation is not measured.** A promotion on one shampoo may move volume from
  another rather than growing the category. With more time this is the first extension:
  cross-SKU substitution during promoted weeks.
- **Six post-weeks may be too short** for a monthly-purchase product; payback landing
  outside the window makes a promotion look better than it was.
- **Discount depth is realised, not offered**, inferred from gross versus net — and F-004
  showed those reconcile only at bundle level. The true offer structure is not in the data.

---

## 5. What I would do differently with more time or data

1. **Ask VEMIO the five open questions first** ([ROADMAP](../docs/ROADMAP.md)). Q5 alone —
   the cost direction — moves every margin number in this deliverable. The case says it
   prefers questions to assumptions; these are the questions.
2. **Get sell-out, not just sell-in.** The −4.73 elasticity conflates consumer demand with
   distributor forward-buying, and the two imply very different promotional strategies.
   This is the single highest-value additional dataset.
3. **Prediction intervals and a service-level target**, turning a point forecast into a
   reorder quantity — the decision the commercial team actually has to make.
4. **A promo-plan-aware forecast.** With next quarter's promotional calendar as a known
   covariate, the promo-driven variance currently sitting in the residual becomes
   predictable. This is legitimate in production and only leakage in a backtest.
5. **Cross-SKU cannibalisation and warehouse-level heterogeneity.** Both were scoped out
   explicitly, not overlooked; 228 routes across 12 warehouses is enough to test whether
   promotional response differs by region.
6. **A longer history.** Seventeen months shows each annual pattern roughly once. Two more
   years would make the seasonal question answerable rather than merely acknowledged.

---

## 6. How AI was used

Documented in full in [`docs/AI_USAGE_LOG.md`](../docs/AI_USAGE_LOG.md), including the
corrections made to AI output. In summary: Claude Code drafted the methodology, the library
and the stage scripts; every number reaching this document was re-derived through an
independent query path before being written up; and two AI-introduced defects were caught
and recorded rather than quietly fixed — a reconciliation test that pooled rows where every
hypothesis matched trivially and looked conclusive at ~64%, and a code comment asserting
something false about pandas null handling. Both are the failure mode worth watching for:
plausible, fluent, and wrong.
