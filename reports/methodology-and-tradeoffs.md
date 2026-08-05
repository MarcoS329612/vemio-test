# Methodology, assumptions and trade-offs

Technical companion to the three challenges. Written for a reviewer who wants to know
what was assumed, why each method was chosen, and what would be done differently with
more time. Every number cited here is produced by a script in `scripts/` and reproduced
in the stage reports; nothing is hand-entered.

Reproduce everything with `uv sync && uv run scripts/run_all.py`.

**Provenance.** This repository's baseline was imported from a prior, independent solution
to the same VEMIO case (credited in the initial commit). The break-even discount, price
band, combo-level uplift (H-007), commercial-context EDA and warehouse allocation described
below were ported in from a **second**, separately authored solution to the same dataset —
see `docs/WORKLOG.md`'s 2026-08-04 entry for the full provenance statement. Every ported
number was re-derived on this repository's own cleaned data before being reported here, and
two of them were corrected rather than adopted as-is (DR-0007's pricing fix, H-007's
concurrency-controlled re-estimate).

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

**The simulator is bounded to the observed p5–p95 price band (45.32–61.45), not the raw
min/max (42.87–64.20) — and the raw range is not usable.** Its tails are not prices anyone
set: the floor is free bonus product shipped inside a combo (zero revenue, real units), and
the ceiling is a handful of weeks where net exceeds gross because of how a combo's discount
reconciles (F-004) — both artefacts of bundle accounting, not evidence of a price the
business would charge. Bounding to the p5–p95 band and refusing to extrapolate outside it
(`predict_units` raises rather than answering) removes that artefact tail from the
simulator's domain entirely, rather than leaving it in and hoping a reader notices.

Its most actionable output is a **break-even price of 46.41**: below that, every extra unit
is sold at a loss, and **10% of the 72-week history (7 weeks)** sat below that line. The same
break-even identity, restated as a discount *depth* rather than a price, generalises to all
six SKUs and is directly comparable across them even though their list prices differ by an
order of magnitude: three SKUs — Shampoo 180ml Verde, Shampoo 135 ml Azul and Shampoo Rizos
135 ml — already run a mean promotional discount deeper than their own break-even depth, a
standing structural loss on the ordinary promotional cadence, not an occasional deep-discount
week. Desodorante 150 ml A is a near-miss (cushion 0.68%).

Demand this elastic (|elasticity| = 4.73 > 1) means revenue scales as
price^(1 + elasticity) with a negative exponent — it has **no interior optimum anywhere in
the positive price domain**, not only outside the observed band. Averaging a term with no
optimum into a "balanced" objective would silently vote for the cheapest price in the grid
on every comparison regardless of what the margin curve looks like (**DR-0007**), so the
degenerate revenue term is dropped rather than averaged in whenever this condition holds.
The recommendation is therefore the margin-maximising price outright: **58.71**, giving
~707 units/week, ~41,485 revenue and ~8,771 margin (21.1%) — fewer units and less revenue
than the previous balanced-rule figure (54.34; ~1,019 units, ~55,390 revenue, ~8,196 margin)
but more profit and a materially higher margin rate. The balanced rule itself is unchanged
and still applies automatically to any SKU whose fitted elasticity lands in [−1, 0], where
revenue does have a genuine interior optimum.

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

**Two layers, not one (DR-0005).** Episodes answer "how much did promotional pressure move
volume on this SKU" and are immune to combo overlap by construction — but averaging away
that overlap also averages away any single mechanic's effect. A second layer,
combo-level regression, enters every combo active on the SKU simultaneously (as its share
of that week's units) alongside a linear trend, so one specific mechanic's contribution net
of every other combo running the same weeks can be read directly. The two layers are
reported side by side in `reports/05_uplift.md` §4, each labelled with what it measures.

**H-007, tested and supported.** The port's headline combo-level claim — SKU 1857's combo
11115 reads roughly +50% uplift where the episode layer sees only +1% (not significant) —
was re-estimated on this repository's own pipeline with concurrent combos and trend as
controls: **+989.0 units/week (+48.4%, p = 0.0352)**, against **+1,064.8 (+51.4%,
p = 0.0046)** uncontrolled — 92.9% of the uncontrolled point estimate retained. The
rejection condition (loses significance at p < 0.05, or the point estimate falls below half
the uncontrolled reading) does not fire on either clause. The point estimate is stable
across choices of standard error; the significance call is not — refitting the same model
under classical and HAC estimators at lags 0–8 moves the p-value from 0.012 to 0.087, and
that sensitivity is disclosed in full (`reports/05_uplift.md` §4.7) rather than only in the
headline number. SKU 1283's combo-level design is close to collinear (53 of 57 promoted
weeks concurrent) and its coefficients are reported only to illustrate the identification
problem, not as usable point estimates.

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

## 5. Warehouse allocation

Stage 03's forecast is national, because that is the grain the data supports for a
model. Stock ships per warehouse, so the national total is split by each warehouse's
historical share of a SKU's recent sales — simple and auditable: a planner can see exactly
why a given warehouse received its number, rather than trusting an opaque optimisation.

**Two guards, both there to catch the same failure mode: allocating stock to a warehouse
that is no longer live.**

1. **Shares are fitted strictly before the forecast origin.** A share computed using weeks
   inside the forecast window is the same future leakage the modelling standard forbids
   throughout this project — it would be invisible in the output, since the allocation
   would still reconcile to the forecast total, but it would be reconciling against
   information the planner does not have yet.
2. **The dead-warehouse check runs per (SKU, warehouse), not network-wide.** A warehouse
   can stop selling one SKU while remaining active for another, so a single network-wide
   silence threshold would either miss a genuine per-SKU exit or wrongly zero out a
   warehouse that is merely quiet on one product. Bodega n. 11 fails the check on every SKU
   it carries — F-013 shows its shutdown is an 8-month wind-down sitting inside the training
   window, not an edge case — and is excluded from the share base for all of them.

Allocated totals reconcile to the stage-03 SKU forecast to within two units by construction,
so the allocation inherits the forecast's own error rather than adding a new one. What it
cannot do is discover a warehouse-level demand shift the national forecast does not contain
— it is a way of *splitting* the existing forecast, not a second, independent one.

---

## 6. What I would do differently with more time or data

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
5. **Cross-SKU cannibalisation and a warehouse-level *demand* model.** Both were scoped out
   explicitly, not overlooked; 228 routes across 12 warehouses is enough to test whether
   promotional response differs by region. Stage 06's allocation splits the existing
   national forecast by historical share — it is not a substitute for modelling demand at
   the warehouse level, which would let the network react to a shift the top-down split
   cannot see (F-012).
6. **A longer history.** Seventeen months shows each annual pattern roughly once. Two more
   years would make the seasonal question answerable rather than merely acknowledged.

---

## 7. How AI was used

Documented in full in [`docs/AI_USAGE_LOG.md`](../docs/AI_USAGE_LOG.md), including the
corrections made to AI output. In summary: Claude Code drafted the methodology, the library
and the stage scripts; every number reaching this document was re-derived through an
independent query path before being written up; and two AI-introduced defects were caught
and recorded rather than quietly fixed — a reconciliation test that pooled rows where every
hypothesis matched trivially and looked conclusive at ~64%, and a code comment asserting
something false about pandas null handling. Both are the failure mode worth watching for:
plausible, fluent, and wrong.
