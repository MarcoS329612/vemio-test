# Standard 02 — Exploratory data analysis

Goal: EDA ends in **findings and hypotheses**, not a pile of plots. Every section of the
EDA report closes with findings written as sentences with evidence attached.

## 1. Structure the exploration around the business questions

Do not explore uniformly — explore in service of the decisions at stake. For a
forecast/elasticity/uplift case, the minimum program is:

### a. Levels and composition
- Volume and revenue by SKU, category, warehouse over the full period.
- Concentration: how much volume do the top SKUs/clients/warehouses carry?

### b. Temporal structure (feeds forecasting)
- Weekly aggregation of units per SKU: trend, seasonality (within-month, holiday effects),
  structural breaks, entry/exit of SKUs or warehouses.
- Calendar effects: business days per week, month boundaries, known events.
- Stability check: does the recent regime resemble the history the model will learn from?

### c. Price structure (feeds elasticity)
- Realized unit price per SKU (`amount / quantity`) over time: how much variation exists,
  and where does it come from (list price changes vs discounts vs mix)?
- Identify SKUs with enough price variation to support elasticity estimation — this is a
  *selection decision*, record it.

### d. Promotional structure (feeds uplift)
- Promo calendar reconstruction: when did each combo run, on which SKUs/warehouses,
  at what depth (discount %)?
- Baseline vs promo period volumes; visual inspection of pre/during/post windows.

### e. Segment heterogeneity
- Do warehouses/routes/client segments behave differently enough to matter for the
  chosen questions? (If yes → hypothesis; if no → justified pooling.)

## 2. Rules

- **Aggregate to the decision grain early.** Transaction-level plots rarely answer
  weekly-forecast questions; build the weekly SKU panel once in `src/analysis/panels.py`
  and reuse it across all three challenges.
- **Plot before summarizing.** Means hide bimodality; always look at distributions and
  time series before trusting aggregates.
- **Findings format**: each finding is one sentence with its supporting figure or number
  referenced. Verified ones go to `docs/FINDINGS.md`; anything that still needs testing
  goes to `docs/HYPOTHESES.md` with a rejection condition.
- **Negative results count.** "No weekly seasonality detectable for SKU X" is a finding,
  and it changes the modeling plan.

## 3. Artifacts

- `scripts/02_eda.py` — sections mirror (a)–(e) above; runnable standalone.
- `reports/02_eda.md` — the findings, tables and numbers, with figure references.
- Figures exported to `reports/figures/`, each with a takeaway in its caption.
- Registry updates in `FINDINGS.md` and `HYPOTHESES.md`.
