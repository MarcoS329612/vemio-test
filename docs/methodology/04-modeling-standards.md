# Standard 04 — Modeling standards

Goal: models that are justified, temporally honest, and no more complex than the
decision requires.

## 1. Baseline first (non-negotiable)

Every modeling task starts with a naive baseline evaluated on the same splits as any
candidate model:

- Forecasting: seasonal naive (last equivalent week) and/or moving average.
- Elasticity: constant-elasticity intuition from a simple log-log scatter before any regression.
- Uplift: pre-period average as the counterfactual before anything fancier.

A candidate model earns its complexity only by **beating the baseline out-of-sample by a
margin that matters for the decision**. Report the baseline's score in every comparison.

## 2. Temporal validation (no future leakage)

- Train/test splits are strictly chronological. For forecasts, use **rolling-origin
  (expanding window) evaluation** across several origins, not a single split.
- The holdout horizon matches the decision horizon (e.g., 8–12 weeks ahead if that is
  what the business will consume).
- Features must be computable at prediction time: no same-period aggregates, no
  full-series statistics (means, scalers) fit on data that includes the test period.
- Hierarchies (SKU × warehouse): decide the modeling level explicitly (bottom-up vs
  top-down) and record it in a DR.

## 3. Model selection — argue trade-offs, then decide

Selection is recorded in a decision record with a table like:

| Candidate | Pros | Cons | When it wins |
|---|---|---|---|
| Seasonal naive / MA | Free, robust, interpretable | No covariates, no trend adaptation | Short, stable series |
| ETS / ARIMA family | Handles trend/seasonality, well understood, works on short series | Univariate (basic forms), per-series fitting | 1–2 years of weekly data, few series |
| Gradient boosting on lag features | Covariates (promos, calendar), one model across series | Needs careful leakage control, more data-hungry, less transparent | Many related series + drivers |
| Deep learning (N-BEATS, etc.) | SOTA at scale | Data-hungry, opaque, heavy for the payoff here | Hundreds+ of series |

Rule of thumb for this repo's scale (few SKUs, ~74 weekly points each): start
statistical (ETS/ARIMA-class or regression with seasonal features + promo covariates);
justify anything heavier.

## 4. Metric selection — chosen for the business, then defended

- Report at least one **scale metric** (MAE, RMSE) and one **relative metric**
  (WAPE preferred over MAPE — MAPE explodes on low-volume weeks and rewards
  under-forecasting; WAPE weights by actual volume, matching replenishment cost).
- MASE is useful to express "how much better than naive".
- State the asymmetry if it exists (is under-stocking worse than over-stocking?) and
  discuss the metric choice in one paragraph in the report.

## 5. Elasticity & causal estimates — extra care

- **Identification before regression**: ask where the price variation comes from
  (promos? list changes? mix?). Elasticity from promo-driven variation measures
  promo response, not pure price response — say so.
- Prefer log-log demand specification for interpretability; control for seasonality,
  trend, and promo flags so the price coefficient isn't absorbing them.
- **Never extrapolate outside the observed price range** — the simulator must refuse or
  warn out-of-range inputs.
- Uplift: define the counterfactual explicitly (pre/post baseline, matched non-promo
  weeks, or control segments), state its assumptions, and check for pantry-loading
  (post-promo dip) and cannibalization across SKUs.
- Every causal claim carries its threats to validity in the same paragraph.

## 6. Reproducibility

- Seeds fixed where randomness exists; environment pinned in `requirements.txt`.
- Modeling logic lives in `src/analysis/`; `scripts/NN_*.py` are thin entry points that
  run a stage end-to-end and emit its report ([DR-0003](../decisions/DR-0003-scripts-over-notebooks.md)).
- Final numbers in reports are produced by a script, never hand-edited — every figure in a
  deliverable is traceable to the code that generated it.
- Leakage-sensitive helpers (temporal splits, panel construction, feature lags) get unit
  tests; they are the cheapest place for a silent error to destroy the whole result.
