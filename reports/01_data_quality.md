# Stage 01 — Data quality audit

> **Generated artifact — do not edit by hand.** Produced by `scripts/01_data_audit.py`; re-run the script to regenerate.

Verification of the delivered dataset against the data dictionary, and quantification of every quality issue **before** any cleaning decision (methodology standard 01).

| Run metadata | Value |
|---|---|
| Stage | `scripts/01_data_audit.py` |
| Generated (UTC) | 2026-08-04 02:35:58 |
| Source file | `20260701_Prueba_tecnica_AI Engineer.csv` |
| Source SHA-256 | `a8a9b8a3d5c91955…` |
| Param · nrows | all |

## 1. Shape and schema

| Item | Value |
|---|---|
| Rows | 358,775 |
| Columns | 21 |
| Columns documented but not delivered | product_margin |

| column | delivered | dtype | note |
|---|---|---|---|
| year | 1 | Int64 |  |
| month | 1 | Int64 |  |
| warehouse | 1 | string |  |
| route | 1 | string |  |
| client_code | 1 | string |  |
| client_name | 1 | string |  |
| product_code | 1 | string |  |
| product_name | 1 | string |  |
| date | 1 | datetime64[us] |  |
| ticket_code | 1 | string |  |
| sell_in_quantity | 1 | float64 |  |
| sell_in_amount | 1 | float64 |  |
| basket | 1 | string |  |
| category | 1 | string |  |
| brand | 1 | string |  |
| id_combo | 1 | string |  |
| combo | 1 | string |  |
| bruto | 1 | float64 |  |
| subcategory | 1 | string |  |
| discount | 1 | float64 |  |
| product_cost | 1 | float64 |  |
| product_margin | 0 | — | documented in the dictionary but NOT delivered (F-001) |

> `product_margin` is described in the data dictionary and explicitly required by Challenge B, but it is not in the delivered file — finding **F-001**, open question **Q1**. Section 7 tests whether it can be reconstructed (**H-001**).

## 2. Entity counts vs. the case statement

| column | distinct |
|---|---|
| product_code | 6 |
| warehouse | 12 |
| route | 228 |
| client_code | 52,555 |
| ticket_code | 273,779 |
| id_combo | 79 |
| combo | 79 |
| category | 3 |
| subcategory | 3 |
| brand | 4 |
| basket | 2 |

The case states 6 SKUs, 12 warehouses, ~52,500 clients, ~359,000 transactions and 79 combos. Divergences here are findings, not rounding.

## 3. Date parsing — verified, not assumed

| Item | Value |
|---|---|
| rows_parsed | 358,775 |
| rows_failed_to_parse | 0 |
| rows_agreeing_with_year_month | 358,775 |
| rows_disagreeing_with_year_month | 0 |
| days_above_12_present | 1 |

> Dates are read as `dd/mm/yyyy`. The `year` and `month` columns are an independent witness: under a `mm/dd` misreading they would disagree with the parsed date wherever the true day exceeds 12. Full agreement plus the presence of days above 12 is what makes the format claim evidence rather than assumption.

## 4. Temporal coverage

| Item | Value |
|---|---|
| first_date | 2025-01-02 |
| last_date | 2026-05-30 |
| distinct_days | 438 |
| weeks_spanned | 74 |
| weeks_observed | 74 |
| weeks_missing | 0 |

## 5. Grain verification

| Item | Value |
|---|---|
| keys | date × client_code × product_code × ticket_code × id_combo |
| rows | 358,775 |
| rows_with_null_in_key | 169,493 |
| rows_in_duplicate_groups | 0 |
| grain_is_unique | 1 |

| Item | Value |
|---|---|
| rows_in_exact_duplicate_groups | 0 |

> The dictionary *claims* the grain is day × client × product × ticket × promo. A non-unique result is not necessarily a defect — it may mean the same SKU appears twice on a ticket under different promo lines — but it changes how the weekly panel must be aggregated, so it is resolved before modelling.

## 6. Completeness and validity

| column | nulls | null_rate_% |
|---|---|---|
| id_combo | 169,493 | 47.24 |
| combo | 169,493 | 47.24 |
| discount | 19,742 | 5.503 |
| bruto | 107 | 0.03 |
| product_cost | 107 | 0.03 |
| brand | 1 | 0 |
| basket | 1 | 0 |
| category | 1 | 0 |
| client_code | 0 | 0 |
| year | 0 | 0 |
| route | 0 | 0 |
| warehouse | 0 | 0 |
| month | 0 | 0 |
| sell_in_amount | 0 | 0 |
| sell_in_quantity | 0 | 0 |
| ticket_code | 0 | 0 |
| date | 0 | 0 |
| product_code | 0 | 0 |
| product_name | 0 | 0 |
| client_name | 0 | 0 |
| subcategory | 0 | 0 |

Implausible-but-structurally-valid records, with the volume and revenue they carry — the second and third columns are what decide whether excluding them is material:

| check | rows | rows_% | units_affected | amount_affected |
|---|---|---|---|---|
| sell_in_quantity == 0 | 515 | 0.144 | 0 | 0 |
| sell_in_quantity < 0 | 0 | 0 | 0 | 0 |
| sell_in_amount == 0 | 1,108 | 0.309 | 4,291 | 0 |
| sell_in_amount < 0 | 0 | 0 | 0 | 0 |
| product_cost is null | 107 | 0.03 | 0 | 0 |
| product_cost <= 0 | 587 | 0.164 | 1,399 | 0 |
| discount is null | 19,742 | 5.503 | 2.133e+04 | 3.916e+06 |
| discount < 0 | 10,084 | 2.811 | 2.298e+04 | 4.371e+06 |
| date failed to parse | 0 | 0 | 0 | 0 |
| sold in a combo | 189,282 | 52.76 | 3.165e+05 | 2.322e+07 |

> Nothing is dropped by this stage. Records are quantified here and handled in stage 02 by flag columns with a logged rationale, so downstream steps choose their own filters (standard 01, anti-pattern: over-cleaning).

## 7. The incomplete-metadata record

The case statement warns of a record with incomplete metadata. Rows matching that description: **1**.

| date | warehouse | client_code | product_code | ticket_code | id_combo | sell_in_quantity | sell_in_amount | bruto | product_cost | discount | category | subcategory | brand | basket | product_name |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-02-18 00:00:00 | bodega n. 6 | 981302 | 1857 | 3437-1771431484 | 10793 | 0 | 0 | — | — | 0.3333 | <NA> | Cabello | <NA> | <NA> | Shampoo Rizos 135 ml |

## 8. Reconciliation of monetary columns

How `bruto`, `sell_in_amount` and `discount` relate, by segment. Organic rows match every reading trivially (no discount, no gap), so the rightmost column — promo rows that actually show a gross/net gap — is the discriminating one:

| reconciliation test | all rows (%) | organic (no combo) (%) | promo (in combo) (%) | promo AND bruto≠net (%) |
|---|---|---|---|---|
| bruto == sell_in_amount (no discount applied) | 63.96 | 100 | 31.68 | 0 |
| discount == bruto − net  (currency reading) | 50.12 | 100 | 5.46 | 0 |
| discount == (bruto − net)/bruto  (fraction reading) | 67.48 | 100 | 38.37 | 48.21 |
| discount == 100·(bruto − net)/bruto  (percent-points) | 50.13 | 100 | 5.47 | 0.02 |

Value distribution of `discount`, which settles its unit of measure:

| statistic | value |
|---|---|
| null | 1.974e+04 |
| exactly zero | 1.765e+05 |
| negative | 1.008e+04 |
| positive | 1.524e+05 |
| min | -0.9606 |
| max | 1 |
| median (non-zero) | 0.1591 |
| p95 (non-zero) | 0.3315 |
| values above 1.0 | 0 |

> `discount` determines the effective unit price, which is the independent variable of Challenge B — hypothesis **H-002**, open question **Q2**.

## 9. Cost and margin structure (the missing `product_margin`)

| product_code | product_name | rows | cost/bruto mean | cost/bruto std | distinct values | implied margin (cost/bruto − 1) | margin as literally delivered ((bruto−cost)/bruto) |
|---|---|---|---|---|---|---|---|
| 1283 | Cubito de pollo c/50 | 118,944 | 1.24 | 0 | 3 | 0.24 | -0.24 |
| 1665 | Antitranspirante 150 ml C | 54,879 | 1.3 | 0 | 3 | 0.3 | -0.3 |
| 1857 | Shampoo Rizos 135 ml | 66,935 | 1.27 | 0 | 3 | 0.27 | -0.27 |
| 1858 | Shampoo 135 ml Azul | 45,725 | 1.26 | 0 | 3 | 0.26 | -0.26 |
| 1875 | Desodorante 150 ml A | 59,025 | 1.22 | 0 | 20 | 0.22 | -0.22 |
| 9304 | Shampoo 180ml Verde | 12,573 | 1.22 | 0 | 3 | 0.22 | -0.22 |

> Tests **H-001**. Two readings at once: whether the per-SKU ratio is constant (deciding whether the missing column can be reconstructed), and whether its direction implies a positive commercial margin. See finding **F-003**.

## 9b. Margin-convention check (free-goods lines)

The reading adopted in `economics.py` — `cost = bruto / (1 + margin)` — is an inference, not a documented fact (F-003, open question Q5). Free-goods lines are the discriminating case: units shipped at a realised price of zero inside a combo. Under the adopted reading they carry a negative margin equal to their cost. Under the rejected reading (`product_cost` as a distributor list price) they carry the full reference price as positive margin, making giveaways the most profitable transactions in the dataset.

| Item | Value |
|---|---|
| free_goods_rows | 414 |
| free_goods_units | 2,892 |
| free_goods_null_cost_rows | 0 |
| adopted_margin | -4.203e+05 |
| rejected_margin | 6.483e+05 |
| applicable | 1 |
| passes | 1 |

**Verdict:** PASS — free goods lose money under the adopted reading, as they should.

## 10. Realised price variation per SKU (Challenge B selection input)

| product_code | product_name | rows | distinct list prices | distinct net prices | net price min | net price median | net price max | weeks observed | max/median |
|---|---|---|---|---|---|---|---|---|---|
| 1283 | Cubito de pollo c/50 | 118,944 | 19 | 125 | 0 | 198 | 408.4 | 74 | 2.06 |
| 1665 | Antitranspirante 150 ml C | 54,879 | 78 | 493 | 0 | 51.11 | 115.3 | 74 | 2.26 |
| 1857 | Shampoo Rizos 135 ml | 66,935 | 11 | 79 | 1.358 | 19.64 | 69.31 | 74 | 3.53 |
| 1858 | Shampoo 135 ml Azul | 45,725 | 12 | 62 | 1.358 | 19.64 | 69.31 | 74 | 3.53 |
| 1875 | Desodorante 150 ml A | 59,025 | 74 | 494 | 0 | 51.21 | 180 | 74 | 3.51 |
| 9304 | Shampoo 180ml Verde | 12,573 | 9 | 38 | 2.578 | 17.22 | 17.56 | 74 | 1.02 |

> Elasticity requires a SKU whose price actually moved (**H-004**). Counting distinct realised prices makes the SKU choice a documented criterion rather than a convenient one. `max/median` flags SKUs with extreme upper tails worth inspecting before they are treated as price signal.

## 11. Candidate findings for the registry

- **F-001** — `product_margin` absent from the delivered CSV — §1, §9.
- **F-003** — Direction of the cost/price relationship — §9.
- **F-004** — Unit and sign of `discount` — §8.
- **F-005** — The incomplete-metadata record — §7.
- **H-002** — Which reconciliation reading holds — §8.
- **H-004** — Which SKU supports an elasticity estimate — §10.

Promoting an observation to a registered finding is a human decision (standard 07). Update `docs/FINDINGS.md` and `docs/HYPOTHESES.md` from the numbers above before proceeding to stage 02.
