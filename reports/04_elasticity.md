# Stage 04 — Price elasticity and simulator (Challenge B)

> **Generated artifact — do not edit by hand.** Produced by `scripts/04_elasticity.py`; re-run the script to regenerate.

SKU 1665 — Antitranspirante 150 ml C. Demand response to realised price, and a simulator bounded to the observed price range.

| Run metadata | Value |
|---|---|
| Stage | `scripts/04_elasticity.py` |
| Generated (UTC) | 2026-08-03 03:52:35 |
| Source file | `20260701_Prueba_tecnica_AI Engineer.csv` |
| Source SHA-256 | `a8a9b8a3d5c91955…` |
| Param · sku | 1665 |

## 1. Where the price variation comes from

SKU 1665 was selected on a criterion fixed before estimating: the widest observed price support, since that is exactly what bounds the simulator's valid domain. Two SKUs qualified (finding F-006); this one has the wider range and the larger volume.

| Item | Value |
|---|---|
| Weeks in the price panel | 72 |
| Realised price range | 42.87 – 64.20 |
| Median realised price | 51.55 |
| Median list price | 60.19 |
| Median promo share of units | 0.925 |

> **This matters more than the coefficient.** This SKU is on promotion in nearly every week of the history, so its price moves through changes in *discount depth*, not through list-price changes. What is estimated is therefore the response to realised price under promotion. That is the right input for a trade-promotion decision — the actual question being asked — but it is not evidence about how demand would respond to a permanent list-price change, and it should not be quoted as such.

## 2. Elasticity estimate

Log-log demand regression with a linear trend and annual Fourier terms, so the price coefficient is not absorbing seasonality or drift. Standard errors are Newey-West (HAC), because weekly demand is autocorrelated and plain OLS errors would report more confidence than the evidence supports.

| Item | Value |
|---|---|
| Price elasticity of demand | -4.734 |
| Standard error (HAC) | 0.498 |
| 95% confidence interval | [-5.709, -3.759] |
| p-value | 0.0000 |
| R² | 0.76 |
| Weeks used | 72 |

A 1% increase in realised price is associated with a 4.73% change in weekly units, in the opposite direction. Demand is elastic: a price cut raises revenue, because volume grows faster than price falls.

> **An elasticity near −5 is high for a household staple, and that is informative rather than suspicious.** This is *sell-in* — shipments to distributors, not purchases by shoppers. Distributors buy ahead when a discount is offered, so sell-in absorbs both genuine demand response and forward-buying, and it is routinely several times more elastic than sell-out. The practical reading: this number tells you how much distributors will load in when you discount. It does **not** tell you how many extra units reach consumers, and treating it as consumer demand would substantially overstate the benefit of a price cut.

![1665 (Antitranspirante 150 ml C): each point is one week. The downward slope on log-log axes is what a constant-elasticity model assumes; the visible scatter is the uncertainty the confidence interval quantifies.](figures/04_price_quantity_1665.png)

*1665 (Antitranspirante 150 ml C): each point is one week. The downward slope on log-log axes is what a constant-elasticity model assumes; the visible scatter is the uncertainty the confidence interval quantifies.*

## 3. Unit economics used by the simulator

Margin cannot be read off the file: `product_margin` is absent and `product_cost` exceeds gross revenue on every row (findings F-001 and F-003, open question Q5). The adopted reading is stated here so every number below can be re-derived — or rejected — on its own terms.

| product_code | product_name | margin_rate | rows | in_documented_band |
|---|---|---|---|---|
| 1283 | Cubito de pollo c/50 | 0.24 | 118,944 | 1 |
| 1665 | Antitranspirante 150 ml C | 0.3 | 54,879 | 1 |
| 1857 | Shampoo Rizos 135 ml | 0.27 | 66,935 | 1 |
| 1858 | Shampoo 135 ml Azul | 0.26 | 45,725 | 1 |
| 1875 | Desodorante 150 ml A | 0.22 | 59,025 | 1 |
| 9304 | Shampoo 180ml Verde | 0.22 | 12,573 | 1 |

| Item | Value |
|---|---|
| Assumption | cost = bruto / (1 + margin), with margin = product_cost/bruto - 1 |
| Recovered margin rate for 1665 | 0.3 |
| List price anchor (median) | 60.19 |
| Implied unit cost | 46.3 |

> **Sensitivity to the assumption.** Taken literally, `product_cost` implies a unit cost of 78.25 against a median realised price of 51.55 — every price in the observed range would be loss-making and no pricing recommendation could be made at all. That the literal reading yields an impossible business is the argument for the correction, not a reason to hide it.

## 4. Simulator

Expected weekly demand, revenue and margin across the observed price range (42.87 – 64.20), holding season and trend at their average. Every tenth grid point:

| price | units | revenue | margin_value | margin_pct | unit_cost |
|---|---|---|---|---|---|
| 42.87 | 3,131 | 1.342e+05 | -1.074e+04 | -0.08 | 46.3 |
| 45.04 | 2,479 | 1.116e+05 | -3,123 | -0.028 | 46.3 |
| 47.21 | 1,984 | 9.366e+04 | 1,804 | 0.0193 | 46.3 |
| 49.38 | 1,604 | 7.92e+04 | 4,938 | 0.0623 | 46.3 |
| 51.55 | 1,308 | 6.745e+04 | 6,867 | 0.1018 | 46.3 |
| 53.72 | 1,077 | 5.783e+04 | 7,985 | 0.1381 | 46.3 |
| 55.89 | 892.6 | 4.988e+04 | 8,556 | 0.1715 | 46.3 |
| 58.05 | 745.3 | 4.327e+04 | 8,762 | 0.2025 | 46.3 |
| 60.22 | 626.5 | 3.773e+04 | 8,724 | 0.2312 | 46.3 |
| 62.39 | 529.9 | 3.306e+04 | 8,528 | 0.2579 | 46.3 |

![1665 (Antitranspirante 150 ml C): revenue and margin in currency against realised unit price, with expected units on the right axis. Where the two curves peak at different prices is precisely the trade-off the commercial team has to settle.](figures/04_simulator_1665.png)

*1665 (Antitranspirante 150 ml C): revenue and margin in currency against realised unit price, with expected units on the right axis. Where the two curves peak at different prices is precisely the trade-off the commercial team has to settle.*

> **The simulator refuses to extrapolate.** Its grid is constructed from the observed price range and cannot be queried outside it. A constant-elasticity curve extended past the data is arithmetic, not evidence — and the further it goes, the more confident it looks.

## 5. Recommended price

| Item | Value |
|---|---|
| Revenue-maximising price | 42.87 |
| Margin-maximising price | 58.78 |
| Balanced recommendation | 55.16 |
| Expected units/week at that price | 949 |
| Expected weekly revenue | 5.237e+04 |
| Expected weekly margin ($) | 8,414 |
| Expected margin (%) | 16.1 |

The balanced price maximises the average of revenue and margin, each normalised to its own maximum. The rule is stated rather than hidden so the commercial team can argue with the weighting instead of with a black box — if margin matters more this quarter, the margin-maximising price is the one to take.

> **The single most actionable number here is the break-even price: 46.49.** Below it, every additional unit sold loses money under the assumed cost of 46.30. 8 of the 72 weeks in the history — 11% — were priced below that line. The elastic demand is real, but the volume it buys at those prices is bought at a loss.

> **The revenue-maximising price sits on the boundary of the observed range**, which is a corner solution: it means revenue was still rising as price fell at the cheapest price ever charged, so the true revenue optimum may lie below anything the data has seen. That is precisely where the simulator refuses to answer, and the refusal is the correct behaviour — it is also why the recommendation is built on the margin curve, which does peak inside the evidence.

## 6. Risks and assumptions

- **Promotional confound.** Price variation comes from discount depth on an almost-always-promoted SKU. The estimate is a promotional price response, not a structural list-price elasticity.
- **Reconstructed margin.** Every margin figure rests on `cost = list / (1 + 0.3)`. If VEMIO answers Q5 differently, the revenue column survives unchanged and the margin column does not.
- **Constant elasticity is an approximation.** A single coefficient assumes the same percentage response at every price. Over a range this wide the true curve almost certainly bends; the estimate is most trustworthy near the middle of the observed range, which is where the recommendation sits.
- **Weekly aggregation hides mix.** A week's realised price averages across warehouses, clients and combo structures. Two weeks with the same average price can have very different underlying offers.
- **No competitor or stock data.** Demand shifts caused by rival pricing or out-of-stock weeks are absorbed into the residual, which widens the interval and could bias the coefficient if either correlates with discount timing.
- **72 weekly observations.** Enough for one coefficient with honest error bars, not enough for interaction effects or a flexible functional form.
