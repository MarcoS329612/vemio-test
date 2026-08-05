# Stage 06 — Warehouse allocation

> **Generated artifact — do not edit by hand.** Produced by `scripts/06_allocation.py`; re-run the script to regenerate.

The stage-03 forecast is national because that is the grain the data supports. Stock ships per warehouse, so it is split by historical share — simple, auditable, and wrong in a way a planner can see.

| Run metadata | Value |
|---|---|
| Stage | `scripts/06_allocation.py` |
| Generated (UTC) | 2026-08-05 02:09:06 |
| Source file | `20260701_Prueba_tecnica_AI Engineer.csv` |
| Source SHA-256 | `a8a9b8a3d5c91955…` |
| Param · lookback_weeks | 52 |
| Param · dead_warehouse_weeks | 8 |

## 1. Share basis

| Item | Value |
|---|---|
| Forecast origin | 2026-05-25 |
| Lookback window | 52 weeks before the origin |
| Dead-warehouse silence period | 8 weeks |
| (SKU, warehouse) pairs in the share base | 64 |
| (SKU, warehouse) pairs excluded | 6 |
| Distinct warehouses receiving stock | 11 |

> Shares are fitted strictly before the forecast origin. A share computed over the forecast window is the same future leakage the modelling standard forbids, and it would be invisible in the output.

## 2. Shares by SKU and warehouse

| product_code | warehouse | units | excluded_reason | share |
|---|---|---|---|---|
| 1283 | bodega n. 3 | 20,990 | — | 0.2558 |
| 1283 | bodega n. 6 | 20,785 | — | 0.2533 |
| 1283 | bodega n. 9 | 10,215 | — | 0.1245 |
| 1283 | bodega n. 2 | 5,894 | — | 0.07183 |
| 1283 | bodega n. 4 | 5,313 | — | 0.06475 |
| 1283 | bodega n. 12 | 5,061 | — | 0.06168 |
| 1283 | bodega n. 10 | 4,421 | — | 0.05388 |
| 1283 | bodega n. 5 | 2,874 | — | 0.03503 |
| 1283 | bodega n. 8 | 2,282 | — | 0.02781 |
| 1283 | bodega n. 1 | 2,274 | — | 0.02771 |
| 1283 | bodega n. 7 | 1,946 | — | 0.02372 |
| 1283 | bodega n. 11 | 188 | no sales in the 8 weeks before the origin | 0 |
| 1665 | bodega n. 3 | 18,416 | — | 0.2406 |
| 1665 | bodega n. 9 | 12,058 | — | 0.1575 |
| 1665 | bodega n. 2 | 12,053 | — | 0.1574 |
| 1665 | bodega n. 6 | 9,013 | — | 0.1177 |
| 1665 | bodega n. 4 | 5,268 | — | 0.06881 |
| 1665 | bodega n. 5 | 4,673 | — | 0.06104 |
| 1665 | bodega n. 12 | 4,202 | — | 0.05489 |
| 1665 | bodega n. 7 | 3,393 | — | 0.04432 |
| 1665 | bodega n. 10 | 3,237 | — | 0.04228 |
| 1665 | bodega n. 1 | 2,376 | — | 0.03104 |
| 1665 | bodega n. 8 | 1,866 | — | 0.02438 |
| 1665 | bodega n. 11 | 90 | no sales in the 8 weeks before the origin | 0 |
| 1857 | bodega n. 9 | 39,436 | — | 0.2535 |
| 1857 | bodega n. 6 | 26,339 | — | 0.1693 |
| 1857 | bodega n. 3 | 19,503 | — | 0.1254 |
| 1857 | bodega n. 4 | 14,224 | — | 0.09144 |
| 1857 | bodega n. 12 | 11,731 | — | 0.07541 |
| 1857 | bodega n. 2 | 10,107 | — | 0.06497 |
| 1857 | bodega n. 10 | 9,489 | — | 0.061 |
| 1857 | bodega n. 5 | 9,414 | — | 0.06052 |
| 1857 | bodega n. 7 | 5,772 | — | 0.0371 |
| 1857 | bodega n. 8 | 4,971 | — | 0.03195 |
| 1857 | bodega n. 1 | 4,577 | — | 0.02942 |
| 1857 | bodega n. 11 | 95 | no sales in the 8 weeks before the origin | 0 |
| 1858 | bodega n. 9 | 23,836 | — | 0.2656 |
| 1858 | bodega n. 6 | 17,469 | — | 0.1946 |
| 1858 | bodega n. 4 | 10,333 | — | 0.1151 |
| 1858 | bodega n. 3 | 9,447 | — | 0.1052 |
| 1858 | bodega n. 2 | 5,450 | — | 0.06072 |
| 1858 | bodega n. 12 | 4,864 | — | 0.05419 |
| 1858 | bodega n. 5 | 4,830 | — | 0.05381 |
| 1858 | bodega n. 10 | 4,315 | — | 0.04807 |
| 1858 | bodega n. 7 | 3,854 | — | 0.04294 |
| 1858 | bodega n. 8 | 3,475 | — | 0.03871 |
| 1858 | bodega n. 1 | 1,887 | — | 0.02102 |
| 1875 | bodega n. 6 | 14,214 | — | 0.2086 |
| 1875 | bodega n. 3 | 11,937 | — | 0.1752 |
| 1875 | bodega n. 4 | 8,484 | — | 0.1245 |
| 1875 | bodega n. 2 | 8,297 | — | 0.1218 |
| 1875 | bodega n. 9 | 7,227 | — | 0.1061 |
| 1875 | bodega n. 5 | 4,673 | — | 0.06859 |
| 1875 | bodega n. 12 | 3,293 | — | 0.04833 |
| 1875 | bodega n. 7 | 3,284 | — | 0.0482 |
| 1875 | bodega n. 8 | 2,845 | — | 0.04176 |
| 1875 | bodega n. 10 | 2,048 | — | 0.03006 |
| 1875 | bodega n. 1 | 1,828 | — | 0.02683 |
| 1875 | bodega n. 11 | 56 | no sales in the 8 weeks before the origin | 0 |
| 9304 | bodega n. 3 | 3,169 | — | 0.2387 |
| 9304 | bodega n. 6 | 2,704 | — | 0.2037 |
| 9304 | bodega n. 4 | 2,180 | — | 0.1642 |
| 9304 | bodega n. 9 | 2,146 | — | 0.1617 |
| 9304 | bodega n. 5 | 898 | — | 0.06765 |
| 9304 | bodega n. 10 | 631 | — | 0.04753 |
| 9304 | bodega n. 2 | 566 | — | 0.04264 |
| 9304 | bodega n. 8 | 523 | — | 0.0394 |
| 9304 | bodega n. 1 | 458 | — | 0.0345 |
| 9304 | bodega n. 12 | 127 | no sales in the 8 weeks before the origin | 0 |
| 9304 | bodega n. 7 | 131 | no sales in the 8 weeks before the origin | 0 |

## 3. Excluded warehouses

| product_code | warehouse | units | excluded_reason |
|---|---|---|---|
| 1283 | bodega n. 11 | 188 | no sales in the 8 weeks before the origin |
| 1665 | bodega n. 11 | 90 | no sales in the 8 weeks before the origin |
| 1857 | bodega n. 11 | 95 | no sales in the 8 weeks before the origin |
| 1875 | bodega n. 11 | 56 | no sales in the 8 weeks before the origin |
| 9304 | bodega n. 12 | 127 | no sales in the 8 weeks before the origin |
| 9304 | bodega n. 7 | 131 | no sales in the 8 weeks before the origin |

> A warehouse that stopped selling still carries historical volume. Allocating it stock on that history is exactly the failure this stage exists to prevent. The check runs per (product_code, warehouse), not network-wide, because a warehouse can go dark for one SKU while staying active for another.

## 4. Weekly allocation

The planner-facing output: units to send, per SKU, per warehouse, per week. Full table in `06_allocation_by_warehouse.csv`.

| week_start | product_code | warehouse | units |
|---|---|---|---|
| 2026-05-25 | 1283 | bodega n. 1 | 74 |
| 2026-05-25 | 1283 | bodega n. 10 | 143.8 |
| 2026-05-25 | 1283 | bodega n. 12 | 164.6 |
| 2026-05-25 | 1283 | bodega n. 2 | 191.7 |
| 2026-05-25 | 1283 | bodega n. 3 | 682.7 |
| 2026-05-25 | 1283 | bodega n. 4 | 172.8 |
| 2026-05-25 | 1283 | bodega n. 5 | 93.5 |
| 2026-05-25 | 1283 | bodega n. 6 | 676.1 |
| 2026-05-25 | 1283 | bodega n. 7 | 63.3 |
| 2026-05-25 | 1283 | bodega n. 8 | 74.2 |
| 2026-05-25 | 1283 | bodega n. 9 | 332.3 |
| 2026-06-01 | 1283 | bodega n. 1 | 74.8 |
| 2026-06-01 | 1283 | bodega n. 10 | 145.4 |
| 2026-06-01 | 1283 | bodega n. 12 | 166.5 |
| 2026-06-01 | 1283 | bodega n. 2 | 193.9 |
| 2026-06-01 | 1283 | bodega n. 3 | 690.4 |
| 2026-06-01 | 1283 | bodega n. 4 | 174.8 |
| 2026-06-01 | 1283 | bodega n. 5 | 94.5 |
| 2026-06-01 | 1283 | bodega n. 6 | 683.7 |
| 2026-06-01 | 1283 | bodega n. 7 | 64 |
| 2026-06-01 | 1283 | bodega n. 8 | 75.1 |
| 2026-06-01 | 1283 | bodega n. 9 | 336 |
| 2026-06-08 | 1283 | bodega n. 1 | 75.5 |
| 2026-06-08 | 1283 | bodega n. 10 | 146.8 |
| 2026-06-08 | 1283 | bodega n. 12 | 168 |
| 2026-06-08 | 1283 | bodega n. 2 | 195.7 |
| 2026-06-08 | 1283 | bodega n. 3 | 696.8 |
| 2026-06-08 | 1283 | bodega n. 4 | 176.4 |
| 2026-06-08 | 1283 | bodega n. 5 | 95.4 |
| 2026-06-08 | 1283 | bodega n. 6 | 690 |
| 2026-06-08 | 1283 | bodega n. 7 | 64.6 |
| 2026-06-08 | 1283 | bodega n. 8 | 75.8 |
| 2026-06-08 | 1283 | bodega n. 9 | 339.1 |
| 2026-06-15 | 1283 | bodega n. 1 | 76.1 |
| 2026-06-15 | 1283 | bodega n. 10 | 147.9 |
| 2026-06-15 | 1283 | bodega n. 12 | 169.3 |
| 2026-06-15 | 1283 | bodega n. 2 | 197.2 |
| 2026-06-15 | 1283 | bodega n. 3 | 702.2 |
| 2026-06-15 | 1283 | bodega n. 4 | 177.7 |
| 2026-06-15 | 1283 | bodega n. 5 | 96.1 |

## 5. Reconciliation

| product_code | allocated_total | forecast_total | difference |
|---|---|---|---|
| 1283 | 33,272 | 33,272 | 0.1 |
| 1665 | 14,185 | 14,184 | 1.2 |
| 1857 | 51,168 | 51,168 | 0 |

> Allocated totals reconcile to the SKU forecast by construction — shares for the live warehouses sum to 1.0, so splitting and re-summing returns the forecast total up to rounding to one decimal place.

## 6. What this assumes

- Warehouse mix is stable over the horizon — the wind-down inside the training window shows that is not guaranteed.
- Top-down cannot discover warehouse-level demand shifts the national forecast does not contain.
- Allocated totals reconcile to the SKU forecast by construction, so they inherit its error, roughly a quarter of volume per week.
