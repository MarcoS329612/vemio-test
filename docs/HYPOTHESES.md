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
- **Evidence**: Of the seven episodes with an observable six-week post window, **two show a
  clear dip**: SKU 1283's February–April 2025 episode gave back **8,828 units** afterwards
  (reducing its measured uplift from 14,983 to 6,155 net), and its June 2025 episode gave
  back **4,414 units**, turning a small positive into a **net −4,244**. The remaining five
  returned to baseline or above.
- **What this changes**: pull-forward is material enough that ignoring it would have
  reversed the sign of one recommendation, which is why net uplift subtracts it throughout
  rather than reporting gross uplift.
- **Limitation acknowledged**: six weeks may be too short for a product bought monthly, so
  this is a lower bound on displacement. Two of the largest episodes were still running when
  the extract ended and could not be checked at all.
- **Verdict date / by**: 2026-08-03 / AI-assisted, reviewed by the author
  (see `reports/05_uplift.md` §3, `post_delta_units`)
