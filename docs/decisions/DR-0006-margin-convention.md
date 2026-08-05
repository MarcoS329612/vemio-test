# DR-0006 — Margin convention: `unit_cost = bruto / (1 + margin)`

- **Date**: 2026-08-04
- **Status**: accepted
- **Phase**: 1 (retroactively documented — the convention has been in force since the
  first modelling stage)
- **Decided by**: AI-assisted (Claude Code), reviewed by the author

## Context

`product_margin` is absent from the delivered CSV (F-001) although Challenge B requires it.
`product_cost` exceeds `bruto` on every one of the 358,775 rows, by a factor that is
exactly constant per SKU (std = 0.0 to nine decimals) and lands on 0.22–0.30 — precisely
the documented 0.20–0.30 margin band (F-003). Read literally, `product_cost` makes every
transaction loss-making, which is not a business VEMIO would be running.

This convention has been used to compute every margin figure in this repository since
stage 01 was first written, argued in `economics.py`'s module docstring and defended only
by the constancy of the ratio. It has never had its own decision record — this is that
record, written after the fact but before the convention is used any further. The question
this decision answers: **given `bruto` and `product_cost`, what is the unit cost, and is
the reading a defended inference or a verified fact?**

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **Take `product_cost` literally as unit cost** | No reconstruction, no assumption | Makes every transaction loss-making — contradicts the documented 20–30% margin band and is not a coherent business. Rejected on its face. |
| **`product_cost` as a distributor list price, margin = list − sell-in** | Also requires no direction change to the delivered column; margin still lands in a plausible range on ordinary discounted rows | Fails the free-goods test (below): a line shipped free of charge would book the full reference price as profit, and progressively deeper discounts would report *more* margin, the wrong sign for a discount. |
| **`unit_cost = bruto / (1 + margin)`, with `margin = product_cost/bruto − 1`** | Reproduces the documented 0.20–0.30 band exactly per SKU (F-003); passes the free-goods test (below); is the reading `economics.py` has used throughout | Still an inference, not a fact confirmed by VEMIO — Q5 stays open |

## Decision

**`unit_cost = bruto / (1 + margin)`**, with `margin = product_cost/bruto − 1` computed
per SKU. This is not a new choice — it is what `economics.py` has implemented since stage
01 — but it previously had no decision record naming the rejected alternatives.

## Rationale

The deciding evidence is `quality.check_margin_convention`, run against free-goods
lines — units shipped at a realised price of zero inside a combo, where `bruto == 0` but
`product_cost` is still populated. These lines are the discriminating case because the two
readings disagree on their *sign*, not just their magnitude:

- Under the adopted reading, a free-goods line's margin is `-unit_cost x units` — negative,
  because giving product away costs money and no revenue offsets it. **Correct behaviour.**
- Under the rejected reading (`product_cost` as list price, margin = list − sell-in), the
  same line's margin is the *full reference price* — the most profitable transaction in
  the dataset, for a unit that was given away. **Wrong sign**, and it generalises: because
  that reading anchors margin to a fixed reference while revenue falls with discount depth,
  deeper discounts report *more* margin throughout the dataset, not just on free goods. That
  would invert the sign of every break-even-discount figure in `reports/04_elasticity.md`
  §6, which is why this had to be settled before that analysis could be trusted.

On the full dataset (`scripts/01_data_audit.py` §9b, `reports/01_data_quality.md`): **414
free-goods lines**, 2,892 units. Adopted reading: **−420,300** aggregate margin (negative,
as required). Rejected reading: **+648,300** (positive, and larger in magnitude than the
correct answer's loss). Stage 01 computes both and aborts the run if the adopted reading
ever yields a non-negative margin on free goods — this is a check now, not only an
argument in a docstring (`quality.check_margin_convention`, verdict printed in
`reports/01_data_quality.md` §9b).

The runner-up (`product_cost` as list price) is not merely less elegant — it fails a test
that can be run against the data, while the adopted reading passes it. That asymmetry is
why this is a decision and not a coin flip between two equally-defensible readings.

## Consequences

- Every margin, break-even-discount, and margin-maximising-price figure in
  `reports/04_elasticity.md`, `reports/05_uplift.md`, and the business deliverables
  inherits this convention. No volume or units figure does.
- `quality.check_margin_convention` runs on every invocation of `scripts/01_data_audit.py`
  and **aborts the stage** if the adopted reading assigns a non-negative margin to
  free-goods lines — a silent regression to the rejected reading (e.g. a future edit to
  `economics.py` that flips the division) is caught at the source, not downstream in a
  business report.
- **This is a defended inference, not a verified fact — Q5 stays open.** If VEMIO confirms
  or corrects the direction, this decision is revisited, not merely footnoted: every
  currency figure in both deliverables would need to be regenerated. The revisit trigger is
  an answer to Q5; until then, every margin number in the deliverable carries this
  assumption on its face, per working rule 4 (register claims before testing them) and the
  disclosure already present in `reports/04_elasticity.md` and
  `reports/business-recommendations.md`.
- Applies uniformly across all six SKUs, since the constancy of `product_cost/bruto` was
  verified per SKU (F-003), not assumed globally.
