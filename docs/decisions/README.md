# Decision records

Non-obvious methodological choices, recorded with the alternatives that lost and why.
Written **before or at** the moment of deciding — not reconstructed afterwards, because
reasoning invented after seeing the result is rationalization and reads that way.

Use [DR-0000-template.md](DR-0000-template.md) for new records. Numbering is sequential;
a superseded record stays in place and points to its successor.

## When to write one

Write a DR when a choice (a) is not obvious to a reviewer, (b) had a credible alternative,
and (c) affects results or their interpretation. Model family, error metric, uplift
identification strategy, SKU selection, and cleaning rules that materially change volumes
all qualify. Routine choices (plot colors, variable names) do not.

## Index

| ID | Title | Phase | Status |
|---|---|---|---|
| [DR-0001](DR-0001-methodology-framework.md) | Adopt a phased CRISP-DM variant with explicit registries | 0 | accepted |
| [DR-0002](DR-0002-repository-and-data-handling.md) | Repository layout, raw-data immutability, and what gets committed | 1 | accepted |
| [DR-0003](DR-0003-scripts-over-notebooks.md) | Script-first analysis architecture (no notebooks) | 1 | accepted |
| [DR-0004](DR-0004-uv-and-pyproject.md) | `uv` + `pyproject.toml` as the environment and packaging contract | 1 | accepted |
| [DR-0007](DR-0007-pricing-recommendation-rule.md) | Drop the degenerate revenue objective from the pricing recommendation | 4 | accepted |

## Expected upcoming records

Placeholders, to be written when the decision is actually made — not pre-committed:

- Cleaning rules for zero-quantity/zero-amount and incomplete-metadata records (Phase 1)
- SKU selection for forecasting and for elasticity, with the selection criteria (Phase 2)
- Forecast model family and modeling grain, bottom-up vs top-down (Phase 4)
- Forecast error metric and why it fits replenishment decisions (Phase 4)
- Uplift identification strategy and its counterfactual assumptions (Phase 4)
