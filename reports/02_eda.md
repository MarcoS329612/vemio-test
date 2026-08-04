# Stage 02 — Cleaning, weekly panel and EDA

> **Generated artifact — do not edit by hand.** Produced by `scripts/02_eda.py`; re-run the script to regenerate.

Cleaning decisions applied as flags, the weekly SKU panel the three challenges share, and the exploration that selects SKUs and promotions.

| Run metadata | Value |
|---|---|
| Stage | `scripts/02_eda.py` |
| Generated (UTC) | 2026-08-03 03:49:24 |
| Source file | `20260701_Prueba_tecnica_AI Engineer.csv` |
| Source SHA-256 | `a8a9b8a3d5c91955…` |
| Param · nrows | all |

## 1. Cleaning decision log

Each rule adds a boolean column; nothing is deleted. Downstream stages pick a selector, so every exclusion stays visible and reversible (standard 01).

| flag | rule | rows | rows_% | units | rationale |
|---|---|---|---|---|---|
| is_zero_quantity | sell_in_quantity <= 0 | 515 | 0.144 | 0 | No units moved, so the row carries no demand signal. Kept for revenue reconciliation but excluded from any units-based model. |
| is_zero_amount | sell_in_amount <= 0 while units moved | 593 | 0.165 | 4,291 | Units shipped at no charge — free goods or a fully-discounted combo leg. Real demand, so kept for forecasting; excluded from price work because a zero realised price is not a point on a demand curve. |
| is_missing_money | bruto or product_cost is null | 107 | 0.03 | 0 | Cannot compute list price or margin. Excluded from elasticity; harmless for unit forecasting. |
| is_incomplete_metadata | category, brand or basket is null | 1 | 0 | 0 | The record the case statement warns about (F-005). Isolated rather than deleted so its footprint stays visible. |
| is_negative_discount | discount < 0 | 10,084 | 2.811 | 2.298e+04 | A negative discount is a surcharge, which the dictionary does not describe (F-004, open question Q6). Excluded from price work pending an answer; the units are still real, so they stay in the demand panel. |
| is_promo | id_combo is not null | 189,282 | 52.76 | 3.165e+05 | Not a defect — the promo marker every challenge depends on. |
| usable_for_demand | derived selector | 358,260 | 99.86 | 6.844e+05 | Rows entering the demand panel. |
| usable_for_price | derived selector | 347,660 | 96.9 | 6.577e+05 | Rows entering price/elasticity work. |

> Zero-amount rows keep their units: shipping stock at no charge is still demand, and dropping it would bias a units forecast downwards. They are excluded from price work instead, because a realised price of zero is not a point on a demand curve.

## 2. The weekly SKU panel

| Item | Value |
|---|---|
| SKU-weeks (all) | 444 |
| SKU-weeks (complete weeks only) | 432 |
| Partial weeks excluded from modelling | 2 |
| First complete week | 2025-01-06 |
| Last complete week | 2026-05-18 |
| Complete weeks per SKU | 72 |

> The first and last calendar weeks are truncated by the extract boundaries. They are flagged rather than dropped, because a truncated week looks like a demand collapse to any model that sees it — and like a real data point to any reader who does not know it was cut.

## 3. Volume and price structure per SKU

| product_code | product_name | weeks | total_units | median_weekly_units | cv_weekly_units | median_price | price_p10 | price_p90 | median_promo_share | price_spread_p90/p10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1283 | Cubito de pollo c/50 | 72 | 1.458e+05 | 1,869 | 0.701 | 196.1 | 175.2 | 201.2 | 0.3496 | 1.15 |
| 1665 | Antitranspirante 150 ml C | 72 | 1.008e+05 | 1,302 | 0.462 | 51.32 | 45.92 | 60.52 | 0.9251 | 1.32 |
| 1857 | Shampoo Rizos 135 ml | 72 | 1.995e+05 | 2,747 | 0.343 | 19.71 | 19.46 | 20.87 | 0 | 1.07 |
| 1858 | Shampoo 135 ml Azul | 72 | 1.16e+05 | 1,556 | 0.378 | 19.7 | 19.6 | 20.87 | 0 | 1.06 |
| 1875 | Desodorante 150 ml A | 72 | 9.033e+04 | 1,202 | 0.445 | 51.51 | 46.28 | 59.71 | 0.9281 | 1.29 |
| 9304 | Shampoo 180ml Verde | 72 | 2.002e+04 | 279 | 0.3 | 17.24 | 15.84 | 17.28 | 0.07191 | 1.09 |

> `cv_weekly_units` (coefficient of variation) is the forecastability signal: a low value means a naive baseline will already be hard to beat. `price_spread_p90/p10` is the elasticity signal — a SKU whose weekly price barely moves cannot identify a price response (**H-004**).

![Weekly units per SKU across the 74-week history. Promo-dominated weeks are marked; the level shifts they produce are what Challenge C must separate from underlying demand.](figures/02_weekly_units_by_sku.png)

*Weekly units per SKU across the 74-week history. Promo-dominated weeks are marked; the level shifts they produce are what Challenge C must separate from underlying demand.*

## 4. Promotion calendar

| Item | Value |
|---|---|
| Distinct combos | 110 |
| Combos above the materiality floor (500 units) | 63 |
| Units sold under a combo | 3.165e+05 |
| Median combo duration (days) | 30 |

The largest promotions by volume — Challenge C's candidate pool:

| id_combo | combo | product_code | first_date | last_date | duration_days | weeks | units | discount_depth | warehouses |
|---|---|---|---|---|---|---|---|---|---|
| 9810 | combo n. 38 | 1875 | 2025-04-11 00:00:00 | 2026-02-10 00:00:00 | 306 | 28 | 2.904e+04 | 0.1463 | 12 |
| 9810 | combo n. 38 | 1665 | 2025-04-11 00:00:00 | 2026-02-10 00:00:00 | 306 | 28 | 2.814e+04 | 0.1529 | 12 |
| 10400 | combo n. 21 | 1665 | 2025-10-01 00:00:00 | 2026-02-02 00:00:00 | 125 | 19 | 2.321e+04 | 0.1609 | 11 |
| 10400 | combo n. 21 | 1875 | 2025-10-01 00:00:00 | 2026-02-02 00:00:00 | 125 | 19 | 1.934e+04 | 0.161 | 11 |
| 11115 | combo n. 33 | 1857 | 2026-05-01 00:00:00 | 2026-05-30 00:00:00 | 30 | 5 | 1.657e+04 | 0 | 11 |
| 9728 | combo n. 71 | 1283 | 2025-03-14 00:00:00 | 2025-04-28 00:00:00 | 46 | 8 | 1.603e+04 | 0.001426 | 12 |
| 10856 | combo n. 41 | 1857 | 2026-03-02 00:00:00 | 2026-03-31 00:00:00 | 30 | 5 | 1.196e+04 | 0 | 11 |
| 8724 | combo n. 43 | 1283 | 2025-01-15 00:00:00 | 2026-05-12 00:00:00 | 483 | 18 | 1.099e+04 | -0.0001776 | 11 |
| 10811 | combo n. 56 | 1875 | 2026-02-11 00:00:00 | 2026-04-01 00:00:00 | 50 | 8 | 9,587 | 0.147 | 11 |
| 10811 | combo n. 56 | 1665 | 2026-02-11 00:00:00 | 2026-04-01 00:00:00 | 50 | 8 | 9,157 | 0.1611 | 11 |
| 11115 | combo n. 33 | 1858 | 2026-05-01 00:00:00 | 2026-05-30 00:00:00 | 30 | 5 | 8,645 | 0 | 11 |
| 2902 | combo n. 61 | 1283 | 2025-01-04 00:00:00 | 2025-03-31 00:00:00 | 87 | 12 | 6,662 | 0.1974 | 12 |

> A combo's `discount_depth` here is realised (1 − net/gross), not the nominal offer. Candidates for uplift estimation need enough duration to see a before and an after, and enough volume for the effect to clear week-to-week noise.

## 5. Seasonality and trend

Median weekly units by calendar month, per SKU:

| product_code | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1283 | 2,477 | 2,636 | 3,687 | 3,338 | 1,361 | 630 | 142 | 680 | 1,345 | 454 | 764 | 1,891 |
| 1665 | 1,428 | 872 | 1,090 | 1,526 | 1,689 | 1,244 | 1,216 | 1,270 | 1,216 | 1,595 | 1,328 | 1,248 |
| 1857 | 1,989 | 3,183 | 2,913 | 3,099 | 1,467 | 2,298 | 3,646 | 3,131 | 2,554 | 2,706 | 3,050 | 2,134 |
| 1858 | 1,166 | 1,902 | 1,416 | 1,764 | 954 | 413 | 2,256 | 1,922 | 1,515 | 1,586 | 1,890 | 1,177 |
| 1875 | 1,331 | 927 | 1,050 | 1,245 | 1,832 | 1,120 | 1,175 | 1,138 | 1,287 | 1,122 | 1,191 | 1,159 |
| 9304 | 309 | 322 | 266 | 314 | 365 | 341 | 223 | 235 | 198 | 215 | 99 | 239 |

> Read for shape, not level. A flat row means a seasonal-naive baseline has nothing to exploit and a moving average will be the one to beat (**H-003**).

## 6. Price–quantity relationship (Challenge B precondition)

![1665 (Antitranspirante 150 ml C): weekly realised price against units, both on log scales. Correlation -0.68 — a downward slope is the precondition for an elasticity estimate, not proof of one.](figures/02_price_qty_1665.png)

*1665 (Antitranspirante 150 ml C): weekly realised price against units, both on log scales. Correlation -0.68 — a downward slope is the precondition for an elasticity estimate, not proof of one.*

![1875 (Desodorante 150 ml A): weekly realised price against units, both on log scales. Correlation -0.71 — a downward slope is the precondition for an elasticity estimate, not proof of one.](figures/02_price_qty_1875.png)

*1875 (Desodorante 150 ml A): weekly realised price against units, both on log scales. Correlation -0.71 — a downward slope is the precondition for an elasticity estimate, not proof of one.*

## 7. Candidate findings for the registry

- **H-003** — Seasonality strength per SKU — §5.
- **H-004** — Price variation and its direction — §3, §6.
- **H-005** — Promotion windows available for uplift — §4.
