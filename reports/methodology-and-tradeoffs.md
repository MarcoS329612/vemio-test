# Methodology, assumptions and trade-offs

Assumptions, method per challenge, trade-offs. Every number comes from a script in `scripts/`
and is reprinted in a stage report; reproduce with `uv sync && uv run scripts/run_all.py`.
**The full reasoning — how each method works and why it was chosen — is in
[`technical-walkthrough.md`](technical-walkthrough.md).**

**Provenance.** This repository's baseline was imported from a prior, independent solution to
the same VEMIO case (credited in the initial commit). The break-even discount, price band,
combo-level uplift (H-007), commercial-context EDA and warehouse allocation were ported in
from a **second**, separately authored solution to the same dataset — see the 2026-08-04
entry in [`docs/WORKLOG.md`](../docs/WORKLOG.md) for the full statement. Every ported number
was re-derived on this repository's own cleaned data before being reported, and two were
corrected rather than adopted as-is (DR-0007's pricing fix, H-007's concurrency-controlled
re-estimate).

---

## Assumptions, across all three challenges

**The cost column is inverted (F-003).** `product_cost / bruto` is *exactly* constant within
each SKU — standard deviation 0.0 to nine decimals — at 1.22 to 1.30, so read literally the
client loses 22–30% of gross revenue on every transaction. The file carries
`cost = price × (1 + margin)` where a markup implies `cost = price ÷ (1 + margin)`: the same
factor, backwards. It also recovers `product_margin`, which the file omits (F-001) and
Challenge B needs. **Assumed**: `margin = product_cost/bruto − 1`, `unit cost = list price ÷
(1 + margin)`, isolated in `src/analysis/economics.py` so one edit reverses it. The
recovered rates are markups **over cost**, as the dictionary documents; every money *outcome*
is stated **over revenue**, `(price − cost)/price` — the same rates as 18.0%–23.1%. Every
currency figure inherits this; **no volume figure does.**

**`discount` is a fraction and reconciles only at bundle level (F-004).** Across the 128,977
promoted rows with a gross/net gap, reading it as a currency amount matches **zero** rows and
as a fraction matches 48% — never exact, as the dictionary's "calculated as bundle" note
predicts. Effective price is therefore always `sell_in_amount ÷ sell_in_quantity`; applying
`discount` to `bruto` would be wrong on more than half those rows, in the one variable
Challenge B rests on.

**Cleaning flags, never deletes.** Six boolean columns carry the reasons; each stage picks
its own selector: 99.86% of rows usable for demand, 96.9% for price. Zero-amount rows keep
their units — free stock is real demand — but leave the price panel.

## Challenge A — demand forecasting

Weekly units, 12-week horizon, three SKUs spanning the failure modes: **1857** (large, mostly
unpromoted), **1283** (26-fold seasonal swing), **1665** (promoted in ~95% of weeks).
Validated on five rolling origins three weeks apart, expanding window; no feature is
computable from the period it is scored on. Scored on **WAPE**: MAPE divides by each week's
actual and so structurally rewards under-forecasting, the wrong incentive when being short
costs as much as being long.

Of seven models, **nothing beat the naive baselines on two of three SKUs**: a 4-week moving
average wins on 1857 (WAPE 0.257) and 1665 (0.291). Only 1283 earned a candidate, damped
drift at 0.272 against the best baseline's 0.322. That is the finding, not a failure to find
one.

**Trade-offs.** Annual seasonality was not modelled — a 52-week period needs two cycles and
this history has ~1.4. Promotional pressure is not a covariate, since the future promo plan
is not in the data, so the forecast assumes *a promotional pattern resembling the recent
past*. Point forecasts, not intervals.

## Challenge B — price elasticity

SKU chosen on a criterion fixed **before** estimating — widest observed price support, which
bounds the simulator's valid domain; 1665 won on range and volume. Log-log demand with a
linear trend and annual Fourier terms, so the price coefficient does not absorb "March
is a strong month", with Newey-West (HAC) errors for autocorrelation: elasticity **−4.73**,
95% CI **[−5.71, −3.76]**, R² 0.76 over 72 weeks.

The simulator is bounded to the p5–p95 band (**45.32–61.45**), not the raw range
(42.87–64.20), whose tails are bundle-accounting artefacts rather than prices anyone set;
`predict_units` raises rather than extrapolating. Break-even is **46.41**, and 10% of the
history sat below it. Demand this elastic gives revenue no interior optimum, so averaging it
into a "balanced" objective would just vote for the grid's cheapest price
(**DR-0007**); the recommendation is the margin-maximising price, **58.71**.

## Challenge C — promotional uplift

Two layers, reported side by side (**DR-0005**). *Episodes* — contiguous runs of weeks where
more than half a SKU's units sell under a combo — measure total promotional pressure, immune
to combo overlap by construction; twelve detected, nine baselineable. *Combo-level
regression* enters every combo active on the SKU simultaneously alongside a trend, giving one
mechanic's contribution net of the others.

Each episode carries two counterfactuals resting on different assumptions — a pre-period
baseline from six preceding *quiet* weeks, and a difference-in-differences adjustment — plus
an evidence grade on baseline cleanliness, controls and post-window observability. Six
post-weeks of pull-forward are subtracted. Incremental margin counts only the units created,
while the discount is paid on every unit sold: that asymmetry is why several episodes with
real uplift still destroyed margin.

## Warehouse allocation

The national forecast is split by each warehouse's historical share: auditable, not opaque.
Shares are fitted strictly before the forecast origin, and a dead-warehouse check runs per
(SKU, warehouse), excluding bodega n. 11 (F-013). Reconciliation holds for the SKU total;
each warehouse line adds its own share-estimation error.

## Honest limitations

- **The baselines won on two of three SKUs** (above).
- **This is sell-in, not sell-out.** An elasticity near −5 absorbs distributor forward-buying
  as well as demand response: it says how much distributors load in, not how many units reach
  shoppers.
- **Parallel trends cannot be tested.** No client-level control group exists — everyone was
  offered the promotion — so the controls are other SKUs across three categories.
- **H-007's significance is fragile.** The point estimate is stable across covariance
  estimators; the p-value moves from 0.012 to 0.087 depending on the choice
  (`reports/05_uplift.md` §4.7).
- **The cost convention is an inference**, not a confirmed fact (F-003, open question Q5).
- **Cannibalisation is not measured**, and discount depth is realised, not offered.

## What I would do differently with more time or data

1. **Ask VEMIO the five open questions first** ([ROADMAP](../docs/ROADMAP.md)). Q5 — the cost
   direction — moves every margin number here.
2. **Get sell-out, not just sell-in**: it separates consumer response from forward-buying.
3. **Prediction intervals and a service level**, turning the forecast into a reorder quantity.
4. **A promo-plan-aware forecast**: legitimate in production, leakage in a backtest.
5. **Cross-SKU cannibalisation and a warehouse-level *demand* model** (F-012).
6. **A longer history.** Seventeen months observes each annual cycle roughly once.

AI use and the corrections made to AI output are documented in
[`docs/AI_USAGE_LOG.md`](../docs/AI_USAGE_LOG.md).
