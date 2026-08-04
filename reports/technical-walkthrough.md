# Technical walkthrough

How each challenge was actually solved, with the technical terms explained as they appear.

This is the long companion to
[methodology-and-tradeoffs.md](methodology-and-tradeoffs.md), which the case asks to keep
to 1–2 pages. That document states *what* was assumed and decided; this one explains *how*
the methods work and *why* each was chosen, for a reader who wants the reasoning without
having to already know the vocabulary.

Every number here is produced by a script in [`scripts/`](../scripts/) and appears in a
generated stage report. Reproduce all of it with `uv sync && uv run scripts/run_all.py`.

---

# Phase 1 — Data audit

## Verifying the grain instead of believing it

The **grain** is what one row represents. The data dictionary claimed:
day × client × product × ticket × promotion. That is a claim, not a fact, so it was tested
— those five columns were taken as a key and duplicates counted. Result: **zero duplicates
across 358,775 rows.** The grain holds.

One detail nearly got documented wrong. 169,493 rows have a null in that key, because
`id_combo` is empty on every organic sale. An early code comment asserted that pandas
treats nulls as *non-matching* during duplicate detection. **That is false** — pandas
treats them as equal. Had it been true, the duplicate count would have been understated and
the conclusion invalid. It was corrected and logged, because an explanation that sounds
reasonable and is wrong is worse than no explanation at all.

## Proving the date format instead of inferring it

The CSV writes dates as `02/01/2025`. Is that 2 January or 1 February? Parse it the wrong
way and 17 months of history is silently reordered — nothing errors, every result is simply
wrong.

The fix was an **independent witness**: `year` and `month` arrive as separate columns. If
`dd/mm` is parsed and correct, they must agree with the parsed date on every row. Under an
`mm/dd` misreading they would disagree on every row whose true day exceeds 12. Result:
**358,775 of 358,775 agree**, and days above 12 are present in the data. That turns the
format from an assumption into evidence. It is pinned in `config.py` and re-verified on
every run.

## The inverted cost finding

The ratio `product_cost / bruto` was computed per SKU, along with its **dispersion** — how
much it varies within each product:

| SKU | cost/bruto | standard deviation | implied margin |
|---|---|---|---|
| 1283 | 1.24 | 0.0 | 0.24 |
| 1665 | 1.30 | 0.0 | 0.30 |
| 1857 | 1.27 | 0.0 | 0.27 |
| 1858 | 1.26 | 0.0 | 0.26 |
| 1875 | 1.22 | 0.0 | 0.22 |
| 9304 | 1.22 | 0.0 | 0.22 |

A standard deviation of **exactly 0.0 to nine decimals** means this is not an approximate
relationship, it is a formula. And `cost/bruto − 1` lands on 0.22–0.30, precisely the band
the dictionary attributes to `product_margin`.

The logic: if margin is a **markup over cost** (a surcharge applied to cost), then
`price = cost × (1 + margin)`, and therefore `cost = price ÷ (1 + margin)`. The file has
`cost = price × (1 + margin)` — the same factor, applied backwards. That is why every
transaction reads as an 18–23% loss.

The correction is isolated in a single module (`economics.py`) so that one edit switches it
if VEMIO answers otherwise. And the sensitivity is shown rather than merely asserted: under
the literal reading, unit cost would be 78.25 against a median realised price of 51.55,
meaning **no price ever charged was profitable and no pricing recommendation would be
possible at all.** That the literal reading produces an impossible business is the argument
for correcting it.

## Decoding `discount` by segmenting

This exposed a methodological error in the first pass. Four readings of the column were
tested across *all* rows and scored between 50% and 67% — indistinguishable.

The problem: on organic sales there is no discount and gross equals net, so **every**
hypothesis matches trivially (0 = 0). Those rows are ~64% of the file and were adding the
same floor to every test, hiding the answer behind a uniform number.

Segmenting down to promotional rows that actually show a gross/net gap (128,977 rows) made
the answer obvious:

| Reading of `discount` | Match rate |
|---|---|
| Currency amount (`bruto − net`) | **0%** |
| Fraction (`(bruto − net)/bruto`) | 48.21% |
| Percentage points (×100) | 0.02% |

The value range is −0.96 to 1.0 with **nothing above 1.0**, which independently confirms it
is a fraction rather than percentage points. The 48% — close but never exact — is precisely
what the dictionary's "calculated as bundle" note predicts: the discount is computed at
combo level and allocated across lines without reconciling row by row.

**Operational consequence:** effective price is always computed as
`sell_in_amount / sell_in_quantity`. Applying `discount` to `bruto` would have been wrong
on more than half the promotional rows — in the one variable Challenge B depends on.

## Cleaning as flags

No row is deleted. Six boolean columns carry the reason, and each stage picks its own
filter:

| Flag | Rows | Decision |
|---|---|---|
| quantity ≤ 0 | 515 | Out of every units-based model |
| amount ≤ 0 with units > 0 | 593 (4,291 units) | **In** the forecast, out of price work |
| bruto or cost null | 107 | Out of elasticity |
| incomplete metadata | 1 | Isolated, not deleted |
| negative discount | 10,084 (2.81%) | Out of price work, in the demand panel |
| sold under a combo | 189,282 (52.76%) | Not a defect — the promo marker |

That leaves **99.86% usable for demand** and **96.9% usable for price**.

The zero-amount rows are the interesting case: shipping stock free of charge *is* real
demand, and removing it would bias a units forecast downward — but a realised price of zero
is not a point on a demand curve. So they belong in one panel and not the other. This is
what the standard means by not over-cleaning: the same row is valid evidence for one
question and invalid for another, and a single global filter cannot express that.

---

# Challenge A — Demand forecasting

## Leakage

**Leakage** is when a model sees, directly or indirectly, information from the period it is
being scored on. It inflates apparent accuracy and then vanishes in production. The common
forms: a statistic computed over the whole series including the test period, a scaler fitted
on future data, or a feature that will not actually be known at prediction time.

## Rolling origins

A single train/test split measures how a model did *in that particular quarter* — a claim
about the quarter, not about the model. This used **rolling origins with an expanding
window**: five cut points spaced three weeks apart, where at each one the model sees weeks
1…t and is scored on t+1…t+12. The window expands rather than slides because on a short
series, discarding old history costs more than it gains.

## Why WAPE rather than MAPE

**MAPE** (mean absolute percentage error) divides each week's error by that week's actual.
Two serious problems here:

1. A quiet 20-unit week with an error of 60 contributes 300%, and dominates the average over
   an entire quarter.
2. It **structurally rewards under-forecasting.** Forecast 0 against an actual of 100 and
   the error caps at 100%; forecast 200 and it is also 100%; forecast 400 and it is 300%.
   The penalty for being short is bounded, the penalty for being long is not. A model tuned
   on MAPE learns to be timid.

**WAPE** (weighted absolute percentage error) is `Σ|error| / Σ|actual|` — one division at
the end. Every unit weighs the same, which is how stock-out and overstock costs are actually
incurred.

**MASE** (mean absolute scaled error) is reported alongside: the error divided by a naive
forecast's error on the training set. It answers "is this better than doing nothing?", with
the caveat that the denominator here is the **one-step** naive, so values above 1 are
unremarkable at a 12-week horizon. It compares models against each other; it does not
certify adequacy on its own.

## The seven models

- **Naive** — repeat last week.
- **Moving average (4 weeks)** — flat forecast at the recent level.
- **Seasonal naive (52 weeks)** — repeat the same week of last year.
- **ETS with damped trend** — exponential smoothing, where the weight of past observations
  decays going backwards. "Damped" means the slope fades rather than extrapolating forever.
  **Seasonality was switched off deliberately**: a 52-week period needs at least two full
  cycles to estimate and this history has ~1.4. Requesting it would fit noise and label the
  result a season.
- **Harmonic ridge** — regression on a linear trend plus **Fourier terms**: sines and
  cosines of the week-of-year, which represent a smooth annual cycle with a handful of
  parameters instead of 52 dummy variables. **Ridge** is regression with a penalty that
  shrinks coefficients, used because 72 observations against 5 correlated seasonal
  regressors overfits readily. It is deterministic in the future, so there is nothing to
  feed back recursively and by construction no path for leakage.
- **Damped drift** and **ensemble** — added afterwards, which is the interesting part.

## The diagnostic that added two models

The first run showed **every** model carrying a negative bias between −13% and −30%. **Bias**
is the signed error: negative means systematic under-forecasting. That it was systematic
*and* common to all models is not bad luck — it is a signal that the series are drifting
upward and no flat forecast can follow them.

Hence **damped drift**: recent level plus the recent slope, damped geometrically so it does
not run away over 12 weeks. And an **ensemble**, the mean of three forecasts that fail
differently — the cheapest reliable improvement in forecasting practice, because no single
component has to be right on its own.

## Results

| SKU | Winner | WAPE | Best baseline |
|---|---|---|---|
| 1857 Shampoo Rizos | moving average (4w) | **0.257** | — (is a baseline) |
| 1283 Cubito de pollo | **damped drift** | **0.272** | 0.322 → 15.5% improvement |
| 1665 Antitranspirante | moving average (4w) | **0.291** | — (is a baseline) |

Forward 12-week volumes: **51,170** units (1857), **33,270** (1283), **14,180** (1665).

Seasonal naive ranked **among the worst on all three**, even though SKU 1283 swings 26-fold
between its trough and peak months. That rejects hypothesis H-003, and the reason matters
more than the verdict: **the seasonality is visible but not exploitable**, because 17 months
observes each annual cycle roughly once. A 52-week lag therefore carries one noisy
observation rather than an estimated season. This is a data-quantity limit, not evidence
that the business has no seasonality — which is why a longer history is the top data request.

## Why promotions are not a feature

Promotional pressure drives a large share of weekly variation, but the future promotional
plan is not in the dataset. Including it would require assuming the calendar is known —
entirely defensible in production, where trade marketing sets it months ahead, and **pure
leakage in a backtest**.

The forecast is therefore a demand expectation *under a promotional pattern resembling the
recent past*, and that condition must travel with the number. If the client shares next
quarter's calendar, the promo-driven variance currently sitting in the residual becomes
predictable, and the range narrows materially.

---

# Challenge B — Price elasticity

## Identification before regression

**Identification** is the question of where the variation the model will use actually comes
from. Before running anything: why does SKU 1665's price move? Answer — it is promoted in
~95% of weeks, so its price moves through **changes in discount depth**, not through
list-price changes.

That does not invalidate the estimate, but it changes what the estimate *is*. It is a
**promotional price response**, which happens to be exactly what a trade-promotion decision
needs — but it is not evidence about what a permanent list-price change would do.

## The specification

A **log-log** regression: `log(units) = a + b·log(price) + trend + Fourier terms`.

The point of log-log is that the coefficient `b` **is** the elasticity directly, with no
transformation: it measures the percentage change in units for a 1% change in price. It is
equivalent to assuming constant elasticity across the whole range.

Trend and Fourier terms are included as **controls** so the price coefficient does not
quietly absorb "March is a strong month". Without them, if discounts coincide with high
season, the model credits price with what was really seasonality.

**HAC (Newey-West) standard errors**: a standard error measures the uncertainty around a
coefficient. Ordinary regression assumes residuals are independent, and in weekly series
they are not — a week that runs above expectation tends to be followed by another
(**autocorrelation**). Ignoring it produces confidence intervals narrower than the evidence
supports, which is how an elasticity gets over-sold. HAC corrects for it.

## The result and how to read it

**−4.73**, 95% confidence interval **[−5.71, −3.76]**, standard error 0.498, R² 0.76 over 72
weeks.

An elasticity near −5 is very high for a household staple. Rather than accepting or
discarding it, it was interrogated — and the explanation is substantive: **this is sell-in,
not sell-out.**

- **Sell-in** = what the manufacturer ships to the distributor.
- **Sell-out** = what the end consumer buys at the point of sale.

When a discount appears, the distributor **buys ahead** to capture it. So sell-in absorbs
genuine demand response *plus* forward-buying, and is routinely several times more elastic
than sell-out. The practical reading: this number tells you how much distributors will load
in when you discount. It does **not** tell you how many extra units reach shoppers, and
treating it as consumer demand would substantially overstate the benefit of a price cut.

## The simulator

It spans the observed range (42.87 to 64.20) and **cannot be queried outside it by
construction**. A constant-elasticity curve extended past the data is arithmetic, not
evidence — and the further it goes, the more confident it looks.

Unit cost: `median list / (1 + 0.30)` = 60.19 / 1.30 = **46.30**.

| Price | Units | Revenue | Margin $ | Margin % |
|---|---|---|---|---|
| 42.87 | 3,131 | 134,200 | **−10,740** | **−8.0%** |
| 47.21 | 1,984 | 93,660 | 1,804 | 1.9% |
| 51.55 | 1,308 | 67,450 | 6,867 | 10.2% |
| 55.89 | 893 | 49,880 | 8,556 | 17.2% |
| 58.05 | 745 | 43,270 | **8,762** | 20.3% |
| 62.39 | 530 | 33,060 | 8,528 | 25.8% |

Two readings matter.

**Break-even ≈ 47.** Below it, every additional unit is sold at a loss. Roughly a third of
the 72 weeks sat below that line. The elastic demand is real; the volume it buys at those
prices is bought at a loss.

**Revenue peaks at the boundary of the range** (42.87). This is a **corner solution**: the
optimum sits on the edge of the data rather than inside it, which means the true revenue
maximum may lie *below* any price ever charged. That is exactly where the simulator refuses
to answer, and the refusal is correct behaviour. The recommendation is therefore built on
the margin curve, which **does** peak inside the evidence, at 58.78.

The balanced price of 55.16 maximises the average of revenue and margin, each normalised to
its own maximum. That weighting is arbitrary, so it is stated in the report rather than
hidden, with the margin-maximising alternative given alongside — the commercial team can
argue with the weighting instead of arguing with a black box.

---

# Challenge C — Promotional uplift

## The real problem is the counterfactual

A **counterfactual** is what would have sold without the promotion. It is never observed,
always estimated, and that is where all the difficulty lives. The rest is arithmetic.

## Episodes rather than combo codes

Several combos overlap on the same SKU, so what the business actually ran is the **combined
promotional pressure**, not any individual code. An episode is defined as a contiguous run
of weeks in which more than half of a SKU's units sold under a combo. Twelve were detected;
nine had enough preceding weeks to establish a baseline.

## Two counterfactuals, deliberately

**1. Pre-period baseline** — the median of the six preceding weeks, restricted to weeks that
were *themselves* quiet (under 20% promoted). Without that restriction you compare a
promotion against another promotion, which is the classic error.

**2. Difference-in-differences (DiD)** — the baseline is scaled by how much the SKUs *not*
promoted in the same weeks moved between the two windows. The idea is to absorb whatever the
market did on its own — seasonality, a strong month, a distribution push — that a raw
before/after comparison would credit to the promotion.

DiD requires an assumption called **parallel trends**: that the promoted SKU would have
moved in step with the controls had there been no promotion. With six SKUs across three
categories, that assumption is doing real work and cannot be tested. So it is declared
rather than buried.

The two estimates rest on different assumptions, so when they disagree, **the disagreement
is itself the finding.**

## Evidence grading — and the mistake that produced it

The most instructive error in the project. The first implementation required an observable
post-promotion window, and that silently excluded the two **best-identified** episodes in
the dataset: SKUs 1857 and 1858 had gone **14 months with no promotion at all** before March
2026 — the cleanest possible baseline. It was caught by asking why only 5 of 12 episodes
were being evaluated.

A clean baseline is what an estimate *needs*; an observable aftermath is a bonus. Relaxing
the filter took the evaluable set from 5 to 9 episodes, and that is what surfaced the
central finding.

An **evidence grade** was added at the same time, scoring three things that can invalidate
an estimate: is the baseline clean, were controls available, is the aftermath observable.
The `control_skus` column was also surfaced, because when it reads *none available* it means
every other SKU was promoted too, **the DiD adjustment collapses to 1.0, and the estimate is
really just the raw before/after comparison.** An estimate that silently degrades to a weaker
method is worse than one that admits it.

## Pull-forward

**Pull-forward** (or *pantry loading*) is volume the promotion did not create but merely
moved earlier, repaid by a slump afterwards. Six post-promotion weeks were checked on every
episode with an observable window. Two of seven showed a clear dip:

- 1283, Feb–Apr 2025: gave back **8,828 units**, cutting the uplift from 14,983 to
  **6,155 net**.
- 1283, Jun 2025: gave back **4,414**, turning a small positive into **−4,244 net**.

Ignoring pull-forward would therefore have **reversed the sign** of one recommendation.
That is why net uplift subtracts it throughout. Six weeks may still be too short for a
monthly-purchase product, so this is a lower bound on displacement.

## The asymmetry that decides everything

This is what turns volume into a decision:

> Incremental margin counts **only the units the promotion created**. The discount is paid
> on **every** unit sold in the window, including those that would have sold anyway.

That asymmetry is why several episodes with genuinely positive volume uplift still destroyed
margin.

## The central finding

| | SKU 1665 | SKU 1875 |
|---|---|---|
| Duration | 60 weeks | 60 weeks |
| Realised discount depth | 13.96% | 13.97% |
| Promoted price | 51.06 | 51.07 |
| Net incremental units | +56,313 | +54,372 |
| **Unit cost** | **45.65** | **48.70** |
| **Margin per unit** | **5.41** | **2.37** |
| **Net margin effect** | **+42,311** | **−76,315** |

The same promotion. Same duration, same depth, essentially the same final price, both with
large volume uplift. **One made money and the other lost it**, and the entire difference is
the cost base: 1875 carries a 22% margin against 1665's 30%, so it earns barely half per
unit. A discount the first can absorb, the second cannot afford.

Both estimates are graded `weak` because no clean controls existed in those weeks, so the
magnitudes carry error bars. But **the direction of the contrast does not depend on the
counterfactual**, because both SKUs share it.

## The second finding

The best episode of the entire period ran at a discount depth of **≈ 0%** — placement or
bundling with no price cut. It moved 6,126 incremental units and, because nothing was given
away, almost all of it dropped through to profit: **+235,626**, the best of the nine.
Discount-led episodes on **the same SKU** produced comparable volume (+6,155 and +2,736) but
lost 47,595 and 67,479.

And the two shampoos, which are the best-identified evidence available: after 14 months with
no promotion, 1857 sold **+1.2%** and 1858 sold **−10.2%**. Volume did not move. The
discount was given away regardless, costing roughly 35,000 and 33,000.

---

# What runs through all three

The cost assumption (finding F-003) touches every monetary figure in all three challenges.
That is why it is isolated in one module and declared in every report where a currency
number appears:

> **Every volume figure stands regardless of what VEMIO answers. Every currency figure
> depends on the reconstruction being right.**

That separation is what makes it possible to deliver actionable conclusions without hiding
that there is an open question underneath them.
