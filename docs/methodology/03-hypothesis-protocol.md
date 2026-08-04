# Standard 03 — Hypothesis protocol

Goal: no claim about the data reaches a report without passing through the registry
(`docs/HYPOTHESES.md`) with evidence. This keeps the analysis honest and makes it
reviewable by humans and AI assistants alike.

## 1. What counts as a hypothesis

Any statement that (a) could be false, and (b) would change a decision if true. Examples:

- "SKU 1283 demand has month-end seasonality."
- "Combo X generated incremental volume rather than pulling forward future purchases."
- "Price sensitivity for SKU Y is high enough that a 5% discount is margin-negative."

Purely descriptive facts (row counts, date ranges) don't need entries.

## 2. Entry format (in `docs/HYPOTHESES.md`)

```markdown
### H-007 — Short name
- **Statement**: falsifiable claim, with direction and rough magnitude when possible.
- **Why it matters**: the decision it affects.
- **Test plan**: data, method, and what result would *reject* it.
- **Status**: proposed | testing | supported | rejected | inconclusive
- **Evidence**: link to the report section/figure that shows it + one-sentence result with numbers.
- **Verdict date / by**: 2026-08-02 / initials or "AI-assisted, reviewed by <name>"
```

## 3. Lifecycle and rules

```
proposed → testing → supported | rejected | inconclusive
```

- **Falsifiable or it doesn't enter.** "Promos matter" is not testable; "Combo X lifted
  weekly units of SKU Y by >10% vs its pre-promo baseline" is.
- **Write the rejection condition before running the test.** This is the cheapest defense
  against confirmation bias and post-hoc rationalization.
- **Inconclusive is a valid verdict** — record why (insufficient data, confounding) rather
  than torturing the data.
- **Supported ≠ proven.** Note the strength of evidence and the main confounder you could
  not rule out.
- Reports may only cite hypotheses in `supported` (with caveats) or describe `rejected` /
  `inconclusive` ones as such.

## 4. Practical evidence bar

This is a business analytics context, not a clinical trial. The bar is:
**effect visible in a plot + robust to the obvious confounder + magnitude reported with
uncertainty**. Formal tests (e.g., a regression coefficient's CI) are used where cheap,
but a well-constructed counterfactual comparison beats a p-value on a bad design.
