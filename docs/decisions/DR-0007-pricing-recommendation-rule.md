# DR-0007 — Drop the degenerate revenue objective from the pricing recommendation

- **Date**: 2026-08-04
- **Status**: accepted
- **Phase**: 4
- **Decided by**: Luis Angel Almazán López, on the case owner's ruling (AI-assisted: yes
  — Claude Code)
- **Corrects**: `elasticity.recommend_price`'s original balanced rule (average of
  normalised revenue and normalised margin), which round-1 review of Task 3 found
  produces an economically arbitrary number for SKU 1665

## Context

SKU 1665's fitted price elasticity of demand is −4.734. Under the constant-elasticity
form used throughout stage 04, revenue = price × units scales as
price^(1 + elasticity) = price^(−3.734). The exponent is negative whenever
elasticity < −1, and a negative exponent means revenue falls **monotonically** as price
rises across the *entire positive price domain* — not merely outside the p5–p95 observed
band Task 3 introduced. There is no interior revenue maximum anywhere to find; the grid's
revenue argmax is nothing but wherever the band's lower edge happens to sit, and it would
move to any other lower edge chosen.

`recommend_price`'s original rule recommended the price that maximises the average of
normalised revenue and normalised margin. Round-1 review of Task 3 found this rule is
contaminated when the revenue term is degenerate: normalised revenue decreases
monotonically across the band, so it votes for the cheapest price in the grid on *every*
comparison, regardless of what the margin curve looks like. For SKU 1665 this pulled the
recommendation from the margin optimum (58.71) down to 54.34 — a fixed 4.37 discount with
no economic content behind its size; it does not reflect any genuine revenue/margin
trade-off, only the shape of an objective that has no optimum to trade off against.

The question this decision answers: **what should `recommend_price` return when the
revenue objective is degenerate?**

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **Keep the revenue-weighted average as-is** | No code change; "balances" two objectives in one number | The revenue term is not a preference among prices, it is a constant vote for the band floor. Averaging it in produces a gap (4.37 here) with no economic meaning — it would be the same size regardless of how the margin curve actually looks, and would change arbitrarily with `n_points` or the band's exact edges |
| **Maximise margin subject to a volume (or revenue) floor** | Well-posed; gives the commercial team an explicit lever (protect at least X units/week or Y revenue) | Introduces a new parameter (the floor) that itself needs justifying from data this project does not have (no stated volume commitment, no stockout or capacity constraint uncovered in EDA) — trading one arbitrary number for another, just relocated into a constraint instead of a weight |
| **Drop the revenue term when it is degenerate; recommend the margin-maximising price outright** | No new parameter; the margin curve has a genuine interior optimum (58.71, comfortably inside the band) that needs no external justification beyond the cost model already adopted (F-001/F-003); the degenerate branch is made explicit (`recommendation_rule`) rather than silently absorbed; the well-posed branch (elasticity ≥ −1) keeps the original balanced rule, so the fix is scoped to exactly the case that is broken | Discards the informational content of the revenue curve's shape *as an input to the recommended price* — though it is still reported (`revenue_max_price`, `revenue_has_interior_optimum`) for the reader, just not averaged in |

## Decision

**When the revenue objective has no interior optimum (`1 + elasticity < 0`),
`recommend_price` recommends the margin-maximising price outright — 58.71 for SKU
1665, up from 54.34.** The revenue-weighted balanced price is still computed and
returned under `balanced_price` for disclosure, but it is no longer promoted to
`recommended_price`. `recommend_price` now takes the fitted `elasticity` and returns an
explicit `recommendation_rule` field (`"margin_only"` or `"revenue_margin_balance"`) so
a reader — or a future SKU with milder elasticity — sees which path fired rather than
having to infer it from which numbers happen to coincide.

## Rationale

An objective with no interior optimum anywhere cannot carry half the weight in a
compromise: averaging in a term that always prefers the cheapest price in the grid is not
"balancing revenue against margin", it is subtracting a fixed, grid-dependent amount from
the margin optimum and calling the result a trade-off. The margin-only rule wins on the
deciding constraint here — **no new parameter, and no new justification burden** — over
the volume-floor alternative, which is well-posed but only relocates the arbitrariness
into a number (the floor) this project has no data to set defensibly. Pragmatism (working
rule 9) favours the option that needs no new assumption over the option that is
"more sophisticated" but equally arbitrary in a different place.

The fix is scoped narrowly: SKUs whose fitted elasticity lands in [−1, 0] keep the
original balanced rule unchanged, so this is a correction of the broken case, not a
wholesale replacement of the recommendation logic.

## Consequences

- **The published headline number for SKU 1665 moves from 54.34 to 58.71.** Everything
  downstream that quoted the old balanced price — `reports/04_elasticity.md` and, per
  Task 3's fix-round-1 report, `reports/business-recommendations.md` — must be refreshed
  to the new figure. `reports/04_elasticity.md` was refreshed as part of this fix;
  `reports/business-recommendations.md` is explicitly out of this task's scope and is
  left for the task that owns that deliverable.
- At 58.71: **~706.6 units/week, ~$41,485 weekly revenue, ~$8,771 weekly margin (21.1%)**
  — versus the prior 54.34 recommendation's ~1,019 units/week, ~$55,390 revenue, ~$8,196
  margin (14.8%). The new recommendation trades roughly 312 units/week and ~$13,900 of
  revenue for ~$575 more weekly margin and 6.3 points of margin rate — a materially
  different commercial trade-off than the number it replaces.
  `reports/04_elasticity.md`'s new "Price / units / revenue / margin trade-off across the
  band" table lets a reader inspect other points on the same curve rather than trusting
  the argmax alone.
- `recommend_price`'s signature and return contract changed
  (`recommend_price(grid, elasticity)`, new `recommendation_rule`, `recommended_price`,
  `recommended_units`, `recommended_revenue`, `recommended_margin_value`,
  `recommended_margin_pct` fields); covered by
  `tests/test_elasticity.py::test_recommend_price_drops_the_revenue_term_when_degenerate`
  and `::test_recommend_price_uses_the_balanced_rule_when_revenue_is_well_posed`.
- Revisit trigger: if a future re-estimation lands SKU 1665 (or any SKU run through this
  stage) at an elasticity in [−1, 0], the balanced rule applies automatically via the same
  `recommendation_rule` branch — no code change needed, only re-running the stage. If the
  case owner later wants a volume-floor constraint instead (e.g. to protect distributor
  relationships at a minimum order size), that is a new decision superseding this one, not
  an extension of it — it needs its own justified floor value.
