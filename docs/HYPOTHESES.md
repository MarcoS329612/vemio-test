# Hypothesis registry

Every claim about the data that could change a decision lives here, from proposal to
verdict. Protocol: [methodology/03-hypothesis-protocol.md](methodology/03-hypothesis-protocol.md).

**Rule**: the rejection condition is written *before* the test is run. Reports may only
cite hypotheses marked `supported` (with caveats), or describe `rejected` / `inconclusive`
ones as such.

## Status summary

| ID | Short name | Phase | Status |
|---|---|---|---|
| H-001 | `product_margin` is a constant per-SKU markup | 1 | **supported** (with caveat) |
| H-002 | `discount` reconciles only at combo level | 1 | **supported** |
| H-003 | Weekly SKU demand has exploitable seasonality | 2 | **rejected** |
| H-004 | At least one SKU has price variation sufficient for elasticity | 2 | **supported** (reframed) |
| H-005 | Promotional weeks show volume uplift vs. adjacent baseline | 2 | **partially supported** |
| H-006 | Promotions are followed by a post-promo demand dip (pantry loading) | 4 | **partially supported** |
| H-007 | Combo-level uplift survives control for concurrent combos | 4 | **supported** |

---

### H-001 — `product_margin` is a constant per-SKU markup

- **Statement**: For each `product_code`, the implied markup derived from `bruto` and
  `product_cost` is constant across the whole period and falls within 0.20–0.30, as the
  data dictionary describes.
- **Why it matters**: Challenge B requires margin in $ and %; the column is absent from the
  delivered CSV (open question Q1). If the markup is constant per SKU we can reconstruct it
  defensibly; if it drifts, margin results need a different treatment and a caveat.
- **Test plan**: Compute implied markup per row per SKU; check dispersion within SKU
  (coefficient of variation) and drift over time.
- **Rejection condition**: markup varies more than ~1% within a SKU, or trends over time,
  or falls outside 0.20–0.30 for a material share of rows.
- **Status**: **supported**, with a caveat that changes its meaning
- **Evidence**: `product_cost / bruto` is exactly constant within each SKU (std = 0.0 to
  nine decimals) and `cost/bruto − 1` lands on 0.22, 0.24, 0.26, 0.27 and 0.30 — inside the
  documented 0.20–0.30 band for all six SKUs. The constancy claim passes decisively.
  **Caveat**: the ratio's *direction* is inverted relative to the dictionary's "markup over
  cost" — see finding **F-003**. The margin is recoverable; whether the delivered
  `product_cost` should be read as cost is a separate, open question (Q5).
- **Verdict date / by**: 2026-08-02 / AI-assisted, evidence re-derived independently and
  reviewed by the author (see `reports/01_data_quality.md` §9)

### H-002 — `discount` reconciles only at combo level

- **Statement**: `bruto − sell_in_amount` matches `discount` for combo transactions at the
  ticket/combo level but not row by row, consistent with the dictionary's note that
  discount is computed as a bundle.
- **Why it matters**: Determines whether effective price per unit can be computed per row
  (needed for elasticity, challenge B) or must be aggregated to combo level first. Getting
  this wrong silently corrupts the price variable.
- **Test plan**: For combo tickets, compare row-level and ticket-level reconciliation of
  `bruto`, `sell_in_amount`, `discount`. Quantify the share reconciling at each level.
- **Rejection condition**: row-level reconciliation holds for ≥95% of combo rows (in which
  case per-row price is usable directly).
- **Status**: **supported**
- **Evidence**: On the 128,977 promo rows with an actual gross/net gap, the currency
  reading matches **0** rows and the fraction reading `(bruto − net)/bruto` matches
  **48.3%** within 0.001 — far below the 95% that would have rejected the hypothesis.
  `discount` is a fraction (range −0.96 to 1.0, nothing above 1.0), not percent-points.
  Consequence adopted: **effective unit price is computed as
  `sell_in_amount / sell_in_quantity`**, never by applying `discount` to `bruto`.
  See finding **F-004**; the negative values (2.81% of rows) remain unexplained (Q6).
- **Verdict date / by**: 2026-08-02 / AI-assisted, reviewed by the author
  (see `reports/01_data_quality.md` §8)

### H-003 — Weekly SKU demand has exploitable seasonality

- **Statement**: For the selected forecasting SKUs, weekly unit demand shows a repeating
  intra-month or calendar pattern strong enough that a seasonal-naive baseline beats a
  flat mean.
- **Why it matters**: Determines whether the forecast baseline should be seasonal-naive or
  a simple moving average, and whether seasonal features belong in the candidate model.
- **Test plan**: Weekly panel per SKU; visual inspection plus autocorrelation; compare
  seasonal-naive vs. mean/MA baseline on rolling-origin splits.
- **Rejection condition**: seasonal-naive does not improve on a moving-average baseline
  out-of-sample.
- **Status**: **rejected**
- **Evidence**: The rejection condition was met on all three forecasting SKUs. Seasonal
  naive scored WAPE 0.330 against the moving average's 0.257 on SKU 1857, 0.436 against
  0.358 on 1283, and 0.481 against 0.291 on 1665 — worse in every case, and on 1283 it was
  the second-worst model of seven despite that SKU showing a 26-fold swing between its
  trough and peak months.
- **Why it failed, which matters more than that it failed**: the seasonal pattern is
  visible in the monthly medians but cannot be *exploited*, because 17 months observes each
  annual cycle roughly once. A 52-week lag therefore carries one noisy observation rather
  than an estimated season. This is a data-quantity limit, not evidence that the business
  has no seasonality — an important distinction for the report, and the reason a longer
  history is the top data request.
- **Consequence adopted**: seasonality is excluded from the forecasting models; a damped
  drift term captures the recent level shift instead and wins on the seasonal SKU.
- **Verdict date / by**: 2026-08-03 / AI-assisted, reviewed by the author
  (see `reports/03_forecast.md` §2)

### H-004 — At least one SKU has price variation sufficient for elasticity

- **Statement**: At least one SKU shows realized unit-price variation (across time and/or
  promo depth) wide enough — and not perfectly confounded with a single promo period — to
  identify a price coefficient.
- **Why it matters**: Challenge B is only answerable for such a SKU; the selection must be
  justified, not arbitrary.
- **Test plan**: Distribution of realized unit price (`sell_in_amount / sell_in_quantity`)
  per SKU over time; count distinct price levels and their support in weeks.
- **Rejection condition**: every SKU's price variation comes from a single promo window, in
  which case the estimate measures promo response, not price response — and must be
  reported as such.
- **Status**: **supported**, but the confound resolved *against* the broader reading
- **Evidence**: Two SKUs carry an order of magnitude more realised price variation than the
  rest — `1875` (74 distinct list / 494 net prices) and `1665` (78 / 493) against 9–20 list
  prices for the others (**F-006**). On SKU 1665 the log-log regression yields a
  well-determined coefficient: **−4.73**, 95% CI [−5.71, −3.76], R² 0.76 over 72 weeks.
  Sufficient variation to identify a price response: confirmed.
- **The confound was not ruled out — it was characterised.** SKU 1665 is promoted in ~95%
  of weeks, so its price moves through changes in *discount depth*, not list price. The
  rejection condition anticipated a single promo window; the reality is a near-permanent
  one. The estimate is therefore a **promotional price response**, not a structural
  list-price elasticity, and it is labelled that way everywhere it appears.
- **A second qualification, discovered during estimation**: because this is *sell-in*,
  the coefficient absorbs distributor forward-buying as well as demand. That is why −4.73
  is far above a plausible consumer elasticity for a household staple, and why it must not
  be quoted as one.
- **Verdict date / by**: 2026-08-03 / AI-assisted, reviewed by the author
  (see `reports/04_elasticity.md` §1–2)

### H-005 — Promotional weeks show volume uplift vs. adjacent baseline

- **Statement**: For the selected combos, weekly units during the promo window exceed the
  pre-promo baseline by a margin larger than normal week-to-week variation.
- **Why it matters**: This is challenge C's core claim; without it there is no uplift to
  report and the recommendation becomes "stop running these".
- **Test plan**: Reconstruct the promo calendar from `id_combo`; compare promo-window
  weekly units against a pre-period baseline and against non-promo weeks of the same SKU.
- **Rejection condition**: promo-window volume falls within the normal variation band of
  adjacent non-promo weeks.
- **Status**: **partially supported** — and the split is the interesting part
- **Evidence**: Across nine evaluable episodes the answer divides cleanly by product.
  Large uplift on the two personal-care SKUs running the long promotion (**+178%** on 1665,
  **+222%** on 1875) and on Cubito de pollo (**+47% to +51%**). Essentially none on the two
  shampoos: **+1.2%** on 1857 and **−10.2%** on 1858, despite those being the
  best-identified estimates in the dataset — both SKUs had gone 14 months with zero
  promotion, giving an uncontaminated baseline.
- **Why the split matters more than the average**: the hypothesis is true for some products
  and false for others, so a portfolio-level statement about promotional effectiveness
  would be wrong in both directions. The shampoo result is the strongest evidence available
  precisely because those SKUs had never been promoted before.
- **Caveat carried forward**: for the 1283 and long-running episodes no clean control SKU
  existed, so the difference-in-differences correction collapsed to the naive comparison and
  those estimates are graded `weak`. The recommendations do not rest on them.
- **Verdict date / by**: 2026-08-03 / AI-assisted, reviewed by the author
  (see `reports/05_uplift.md` §3)

### H-006 — Promotions are followed by a post-promo demand dip (pantry loading)

- **Statement**: In the weeks following a promo window, weekly units fall below the
  pre-promo baseline, indicating purchases were pulled forward rather than incremental.
- **Why it matters**: Decides whether reported uplift is genuine incremental volume or
  timing displacement — the difference between "repeat this promo" and "stop it".
- **Test plan**: Compare post-window weeks against the pre-promo baseline; net the dip
  against the measured uplift.
- **Rejection condition**: post-promo weeks return to baseline without a statistically
  visible dip.
- **Status**: **partially supported** — real, but not universal
- **Evidence**: Nine episodes are evaluable; **four** were still running when the extract
  ended (`post_weeks = 0`), leaving **five** with an observable six-week post window. Of
  those five, **two show a clear dip**: SKU 1283's February–April 2025 episode gave back
  **8,828 units** afterwards (reducing its measured uplift from 14,983 to 6,155 net), and
  its June 2025 episode gave back **4,414 units**, turning a small positive into a **net
  −4,244**. The remaining three returned to baseline or above. (Counts read from
  `reports/05_uplift_estimates.csv`'s `post_weeks` column; an earlier revision of this entry
  said "seven episodes with an observable post window", which no artifact supported.)
- **What this changes**: pull-forward is material enough that ignoring it would have
  reversed the sign of one recommendation, which is why net uplift subtracts it throughout
  rather than reporting gross uplift.
- **Limitation acknowledged**: six weeks may be too short for a product bought monthly, so
  this is a lower bound on displacement. **Four** episodes — including the two 60-week ones,
  which are the largest in the dataset — were still running when the extract ended and could
  not be checked at all.
- **Verdict date / by**: 2026-08-03 / AI-assisted, reviewed by the author
  (see `reports/05_uplift.md` §3, `post_delta_units`)

### H-007 — Combo-level uplift survives control for concurrent combos

- **Statement**: The ported analysis estimates uplift per `id_combo` and finds SKU 1857
  averaging +1% (not significant) while combo n.33 inside it reads +50% (p ≈ 0.011). The
  claim under test is that this combo-level effect is real, not an artefact of other
  combos running in the same weeks.
- **Why it matters**: This repository's episode approach (`uplift.detect_episodes`, see
  H-005/H-006) was chosen because several combos can overlap on the same SKU — combo-level
  estimates are exposed to exactly the confound episodes were built to avoid. If the
  +50% reading doesn't survive controlling for that confound, it cannot be reported as a
  combo-level finding, and only the episode layer (+1%, not significant) stands for SKU
  1857.
- **Test plan**: Re-estimate combo n.33's uplift on SKU 1857 with concurrent combos and a
  linear trend entered as controls (DR-0005).
- **Rejection condition**: rejected if the combo that reads +50% uncontrolled loses
  significance at p < 0.05 once concurrent combos and a linear trend enter the model, or
  if its point estimate falls below half of the uncontrolled estimate.
- **Status**: **supported**
- **Concurrency context**: pressure differs sharply by SKU — 31 combos across 57
  promotional weeks on SKU 1283, but only 9 combos across 31 promotional weeks on SKU
  1857, where the result lives. The objection is real but not obviously fatal to this
  specific estimate.
- **Evidence**: `uplift.estimate_combo_effects` (`src/analysis/uplift.py`) confirms the
  identity of the combo first — `id_combo` 11115 on SKU 1857 matches the ported
  description on the details that do not depend on model choice: 5 active weeks, ending
  2026-05-25, mean 4,106.2 units/week during those weeks. Two estimates were then compared,
  both computed on this repo's own pipeline (`reports/05_uplift.md` §4.7):
  - **Uncontrolled** (single-combo OLS, HAC(4) errors, trend term, no concurrent-combo
    controls — computed fresh here, not the ported +49.9%/p=0.0106 figure): coefficient
    **1,064.8** units/week, **+51.4%** vs. intercept, **p = 0.0046**.
  - **Controlled** (DR-0005's design — every concurrent combo on SKU 1857 plus a linear
    trend entered simultaneously): coefficient **989.0** units/week, **+48.4%** vs.
    intercept, **p = 0.0352**.
  Applying the rejection condition exactly as registered: the controlled estimate stays
  significant (p = 0.0352 < 0.05), and its point estimate retains 92.9% of the uncontrolled
  reading (989.0 / 1,064.8), well above the 50% floor. Neither clause fires. Combo 11115
  shares only 1 of its 5 active weeks with another combo (`weeks_concurrent = 1`),
  consistent with SKU 1857's mild concurrency noted above — there was little contamination
  for the control to remove, which is why the estimate barely moves once it is added.
  SKU 1283's combo-level estimates (also in §4) are not part of this verdict: with 53 of
  57 promoted weeks concurrent, that SKU's design matrix is close to collinear and its
  coefficients are reported only to illustrate the identification problem, not as
  point estimates.
- **Significance fragility (disclosed, not hidden)**: the p = 0.0352 figure depends on the
  covariance estimator. `uplift.combo_p_value_sensitivity` (`src/analysis/uplift.py`)
  refits the identical controlled model under classical (non-robust) errors and HAC at
  lags 0, 1, 2, 3, 4, 6, 8 — full table in `reports/05_uplift.md` §4.7. Result: classical
  OLS p = 0.087 (not significant); HAC(0) 0.036; HAC(1) 0.057 (not significant); HAC(2)
  0.060 (not significant); HAC(3) 0.046; **HAC(4), the pre-registered estimator, 0.035**;
  HAC(6) 0.021; HAC(8) 0.012. HAC(4) was fixed in DR-0005 before the controlled model was
  fit — it follows the standard Newey-West T^(1/4) rule of thumb for ~74 weekly
  observations — so it is not a post-hoc pick, but the determination visibly flips at 1-2
  lags and is not close under classical errors, on a design with 74 observations, 8
  parameters, a 5-week treatment window, and non-normal residuals (Jarque-Bera skew 1.04,
  kurtosis 6.48). **What is stable and what is not are different claims**: the point
  estimate (sign and magnitude, 989.0 vs. 1,064.8 uncontrolled) does not move with the
  choice of standard errors; only the p-value does, and the rejection condition's
  significance clause is judged against the pre-registered estimator specifically, not
  against a consensus across estimators. Applied as written, the verdict is supported —
  but by a margin that is not wide.
- **Verdict date / by**: 2026-08-04 / AI-assisted, `estimate_combo_effects` implemented
  and run against this repo's cleaned data, reviewed by the author. Sensitivity disclosure
  added 2026-08-04 following review.
