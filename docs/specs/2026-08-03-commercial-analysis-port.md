# Design — porting the commercial-analysis layer

**Date**: 2026-08-03 · **Status**: approved, not yet implemented

## Provenance

The five capabilities below originate in a **separate, independent solution to the same
VEMIO case**, authored outside this repository. They are ported here deliberately, not
rediscovered. Every artifact this work produces names that origin, and the worklog entry
does the same. Importing method without declaring where it came from would break the one
property that makes this repository worth reading.

The two solutions disagree on two substantive points. Neither disagreement is settled by
assertion here: one is resolved by a test written before it is run (§3), the other by an
executable check (§1).

## Goal

Add five capabilities this repository does not have, under full integration: where the
ported method is better, it replaces what is here and the affected figures are recomputed,
including in the two business deliverables.

Out of scope, explicitly: the StatsForecast/Nixtla model pool and the head-to-head
re-run of Challenge A. Adding a heavy automatic-model dependency contradicts the
pragmatism argument this repository makes and defends (DR-0001, working rule 9). The
Challenge A conclusion stands as reported.

## 1. Margin convention — verify what is currently only asserted

`economics.py` already adopts the correct reading: `unit_cost = bruto / (1 + margin)` with
`margin = product_cost/bruto - 1`. No change to the convention is required.

What is missing is verification. The reading is argued in a module docstring and defended
by the constancy of the ratio (F-003), but nothing in the code fails if it is wrong.

**Add** `quality.check_margin_convention(frame, rates)`, surfaced in stage 01:

Free-goods lines — units shipped at a realised price of zero inside a combo — are the
discriminating case. Under the adopted reading they carry a negative margin equal to their
cost, which is correct: giving product away costs money. Under the rejected reading
(`product_cost` as a distributor list price, margin = list − sell-in) the same lines carry
the **full reference price as positive margin**, making giveaways the most profitable
transactions in the dataset. The check computes margin on those lines under both readings
and fails the stage if the adopted one assigns them a non-negative margin.

This generalises: the rejected reading anchors margin to a fixed reference while revenue
falls with discount depth, so deeper discounts report *more* margin. That inverts the sign
of the break-even discount in §4, which is why the convention has to be settled first.

**Record** as DR-0006 (the convention has no decision record today) and keep Q5 open in
the roadmap — this is a defended inference, not a verified fact.

## 2. Commercial context — extend stage 02

Stage 02 covers levels, concentration, temporal and price structure per SKU. It does not
cover the network, the customer base, or the structure of the discount itself. Add to
`02_eda.py`, writing into `reports/02_eda.md`:

- **Warehouse network**: size dispersion (routes, clients, revenue per client), revenue
  concentration, and the top-product profile per warehouse.
- **Warehouse 11 shutdown**: last-sale date per warehouse, and the monthly ticket count
  showing the wind-down is gradual, not a data cut. This is a structural break inside the
  training window and it belongs in the forecast caveats.
- **Customer base**: frequency and basket-length distribution, and its consequence for
  Challenge C — a low-frequency customer makes promotional uplift a network-level effect,
  not a per-customer one.
- **Discount structure**: that realised discounts fall on discrete levels rather than a
  continuum, plus the 100% group that is bonus product; and that discount depth is not
  client-specific (within-client dispersion is near zero for clients with ≥10 discounted
  lines). Together these say the discount is a central decision applied network-wide.
- **No control group**: price drops are simultaneous across all twelve warehouses, not
  staggered. This is the identification diagnostic that rules out difference-in-differences
  for Challenge C, and stage 05 currently makes that choice without evidence.

New findings F-012 onward. The warehouse-11 break and the absence of a control group are
the two that change how existing results should be read.

## 3. Combo-level uplift — extend stage 05

Stage 05 estimates uplift over episodes derived from promotional intensity, on the grounds
that combos overlap on the same SKU. The ported analysis estimates per `id_combo` and finds
that SKU-level aggregation destroys the signal: one SKU averages +1% (not significant)
while a single combo inside it reads +50% (p ≈ 0.011).

Both arguments are correct, and how much the overlap objection bites varies by SKU: the
source analysis counts 31 combos across 57 promotional weeks on SKU 1283, where concurrency
is near-certain, but only 9 combos across 31 promotional weeks on SKU 1857, where the +50%
result lives. So the objection is real but not obviously fatal to that specific estimate —
which is exactly why it gets tested rather than argued. Either way it argues for controlling
concurrency, not for abandoning the combo as the unit.

**Add** `uplift.estimate_combo_effects(panel, product_code)`, fitting per SKU:

```
demand_t = γ₀ + γ₁·t + Σₖ γₖ·combo_k,t + ε
```

Each `γₖ` is net of secular trend and net of every other combo active in the same weeks.
Report each coefficient with its standard error, p-value and the number of weeks
identifying it. Keep a Welch t-test alongside for events that have a clean unpromoted
control window, as a non-parametric contrast that does not depend on the linear form.

Episodes stay. They answer a different question — total promotional pressure on a SKU —
and the report presents both layers with what each one measures.

**Register H-007 before running it**, with the rejection condition written first:

> H-007 — Combo-level uplift survives control for concurrent combos.
> **Rejected if** the combo that reads +50% uncontrolled loses significance at p < 0.05
> once concurrent combos and trend enter the model, or if its point estimate falls below
> half of the uncontrolled estimate.

A rejection is published as a finding. It would mean the headline result of the source
analysis was concurrency, and that is worth more than a silent removal.

**Record** as DR-0005: unit of analysis for uplift, naming the alternatives that lost —
episodes alone (masks mechanic-level heterogeneity) and uncontrolled combo-level
(contaminated by concurrency).

## 4. Price-range guards and break-even discount — extend stage 04

**Observed-range guard.** The brief forbids extrapolating outside the observed price range,
and the simulator must enforce that on evidence rather than on the raw min/max. The extremes
are not prices: the floor is free bonus product inside combos, and the ceiling is a handful
of broken records where net exceeds gross and the implied discount goes negative. Bound the
simulator by the **p5–p95 weekly price range per SKU**, computed in `elasticity.py`, and have
it refuse prices outside that band with the band stated in the refusal. Publish the per-SKU
band as a table in `reports/04_elasticity.md`.

**Break-even discount, all six SKUs.** `04_elasticity.md` reports a break-even *price* for
one SKU. The same unit economics give the maximum discount depth each SKU absorbs before its
realised price falls under cost — expressed in the lever the commercial team actually moves:

```
max_discount_k = 1 - unit_cost_k / list_price_k = margin_k / (1 + margin_k)
```

Add `economics.break_even_discount(rates)` and compare each SKU's break-even against its
observed mean discount. Any SKU whose average promotional depth already exceeds its own
break-even is a standing loss, not an occasional one, and that goes into the business
recommendations.

This reuses `unit_cost_from_list` and therefore inherits §1's verification.

## 5. Warehouse allocation — new stage 06

A SKU-level national forecast is not an order. Add `src/analysis/allocation.py` and
`scripts/06_allocation.py` → `reports/06_allocation.md`.

```
forecast_{sku,warehouse} = forecast_sku × share_{sku,warehouse}
```

with shares from the trailing 12 months of history. Top-down, interpretable, auditable.

Design constraints:

- **Stage 06, not inside stage 03.** It consumes the published forecast; it is a layer on
  top of the model, not part of it. `run_all.py` discovers `NN_*.py` by name, so no
  registration is needed.
- **Shares must respect the temporal rule.** They are computed on history strictly prior to
  the forecast origin. A share fitted over the forecast window is leakage of the same kind
  the modelling standard forbids.
- **Warehouse 11 is excluded from the share base** and the exclusion is stated. Its history
  is real but its future demand is zero (§2); allocating stock to a warehouse that stopped
  selling in 2025 is the exact failure this stage exists to prevent.
- Emit a weekly allocation table per SKU × warehouse, the format a planner can act on.

## Consequences outside this repository

The margin decision invalidates the source analysis's Challenge B, which computes margin as
`(unit_cost_ref − price) × demand` — the reading rejected in §1. That simulator needs
correcting before its numbers are comparable to anything here. Noted for completeness; it is
not work in this repository.

## Traceability checklist

Working rules 4, 5 and 6 apply in full:

- [ ] H-007 registered with its rejection condition **before** the combo model is run
- [ ] DR-0005 — unit of analysis for uplift
- [ ] DR-0006 — margin convention, with the free-goods test as its evidence
- [ ] F-012 onward in `FINDINGS.md`
- [ ] `WORKLOG.md` session entry, naming the origin declared under **Provenance**
- [ ] `AI_USAGE_LOG.md` entry
- [ ] `ROADMAP.md` updated; Q5 stays open
- [ ] `run_all.py` reproduces every figure end-to-end from raw data
- [ ] Both business deliverables updated wherever a ported result changed a number

## Definition of done

`uv run scripts/run_all.py` completes on a clean environment, stage 01 fails loudly if the
margin convention is violated, H-007 carries a verdict either way, and every currency figure
in `reports/` traces to `economics.py`.
