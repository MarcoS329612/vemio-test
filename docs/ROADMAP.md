# Roadmap

Living document: current phase, what is done, what is next, and what is blocked.
Update at the end of every work session.

- **Current phase**: 6 — Communication. **All three challenges answered and both written
  deliverables drafted.** The full pipeline reproduces end-to-end from raw data via
  `uv run scripts/run_all.py`, six stages in order (`01_data_audit` → `02_eda` →
  `03_forecast` → `04_elasticity` → `05_uplift` → `06_allocation`).
- **Ported capabilities (2026-08-04)**: a second, independently authored analysis of the
  same VEMIO dataset was ported into this repository — see the provenance note in
  `docs/WORKLOG.md`'s 2026-08-04 entry. Landed: break-even discount per SKU (§Phase 4/B),
  a p5–p95 price band replacing the raw observed range (§Phase 4/B), combo-level uplift
  with concurrency controls alongside the existing episode layer (§Phase 4/C, H-007,
  DR-0005), commercial-context EDA — warehouse network, customer frequency, discount
  structure (§Phase 2, F-012…F-016), and top-down warehouse allocation of the SKU forecast
  (stage 06, `reports/06_allocation.md`). Explicitly left out: the StatsForecast/Nixtla
  model pool for Challenge A (would add a heavy dependency for no reported improvement over
  the existing seven-model comparison).
- **Last updated**: 2026-08-04
- **Deadline context**: take-home, 2–4 calendar days, ~4–6 effective hours of work

## Phase 0 — Business framing ✅

The commercial team of a CPG client needs input for next quarter's replenishment and
promotion plan. Three decisions must be supported:

| # | Decision to support | Analytical question | "Good enough" looks like |
|---|---|---|---|
| A | How much to stock, per SKU, per week, next quarter | Weekly unit demand, 2–3 SKUs, 8–12 weeks ahead | Beats seasonal-naive out-of-sample on a volume-weighted error metric; error stated in units the planner can act on |
| B | What price / discount depth to set | Demand sensitivity to price for 1 SKU + simulator over the observed price range | Elasticity with a stated sign, magnitude and uncertainty; simulator refuses out-of-range prices |
| C | Which promotions to repeat next quarter | Incremental units attributable to ≥2 past promotions | Incremental estimate with an explicit counterfactual and its assumptions; one promo to repeat, one to drop |

**Explicitly out of scope** (stated so reviewers know it was a choice, not an oversight):
sell-out / consumer-level modeling, cross-SKU cannibalization as a full model, client-level
segmentation models, production deployment, and any inventory optimization beyond the
demand forecast itself.

## Repository scaffolding ✅

- [x] Script-first architecture in place (DR-0003): `src/analysis/` library +
      `scripts/NN_*.py` stages, each emitting a markdown artifact into `reports/`
- [x] `config.py` resolves the dataset by original filename and verifies its SHA-256 on
      every run — a changed input is flagged in the report header, never silent
- [x] `uv` + `pyproject.toml` + committed `uv.lock` for a reproducible environment (DR-0004)
- [x] `.gitignore` and the `run_all.py` end-to-end reproducibility entry point
- [x] Unit tests for leakage-sensitive helpers (temporal splits, panel construction) —
      delivered with the warehouse-allocation port: `tests/test_allocation.py` covers the
      leakage guard directly (`test_history_after_the_origin_is_never_used`, "a share fitted
      over the forecast window is leakage") plus the dead-warehouse and per-SKU-total
      checks; `tests/test_economics.py`, `test_elasticity.py` and `test_uplift.py` cover the
      other model-facing helpers. 29 tests across four files, run via `uv run pytest -v`
      (measured directly from a fresh run, not copied from the implementation plan's
      expectation of 15 — that figure was stale before this stage's tests were finished).

## Phase 1 — Data intake & quality audit ✅

- [x] Originals preserved verbatim in `docs/case/original/` with SHA-256 provenance manifest (F-002)
- [x] Raw file in `data/raw/` under its original filename (immutable, git-ignored, 77 MB)
- [x] Column inventory vs. dictionary — **21 columns; `product_margin` is missing** (F-001 / Q1)
- [x] Grain verification — claimed grain holds, **0 duplicate rows** (F-007)
- [x] Coverage — 2025-01-02 → 2026-05-30, **74 weeks, none missing**; all 6 SKUs present in all 74 weeks (F-007)
- [x] Date format verified against the independent `year`/`month` columns, not assumed (F-007)
- [x] Quality quantification: nulls, zeros/negatives, duplicates, monetary reconciliation
- [x] **`product_cost` direction anomaly found** — every row reads as loss-making (F-003 / Q5)
- [x] **`discount` semantics settled** — a fraction, bundle-level, negative on 2.8% of rows (F-004 / Q6)
- [x] Incomplete-metadata record isolated — exactly 1 row (F-005)
- [x] Price variation profiled per SKU → elasticity candidates identified (F-006)
- [x] Cleaning decision log + flagged (not deleted) records — delivered in stage 02
      (`reports/02_eda.md` §1, six boolean flags with before/after counts, nothing deleted)
- [x] Weekly SKU panel built in `data/processed/` — delivered in stage 02
      (`weekly_sku_panel.parquet`, 432 complete SKU-weeks)
- **Artifacts**: `scripts/01_data_audit.py` → [`reports/01_data_quality.md`](../reports/01_data_quality.md) ✅

## Phase 2 — EDA ✅

- [x] Cleaning applied as six boolean flags with a logged rationale; nothing deleted
- [x] Weekly SKU panel (432 complete SKU-weeks) + promo calendar in `data/processed/`
- [x] Levels, concentration, temporal structure, price structure per SKU
- [x] Promo calendar reconstructed → uplift candidates identified
- **Artifacts**: `scripts/02_eda.py` → [`reports/02_eda.md`](../reports/02_eda.md)

## Phase 3 — Hypotheses ✅

- [x] Six hypotheses registered with rejection conditions written before testing
- [x] All six now carry verdicts: 2 supported, 1 rejected, 2 partially supported, 1 reframed

## Phase 4 — Modeling ✅

- [x] **A**: seven models, five rolling origins, 12-week horizon → `reports/03_forecast.md`
- [x] **B**: log-log demand model + range-guarded simulator, p5–p95 band, break-even
      discount per SKU → `reports/04_elasticity.md`
- [x] **C**: nine episodes, dual counterfactual, margin verdict, plus combo-level uplift
      with concurrency controls (H-007) → `reports/05_uplift.md`
- [x] **Allocation**: top-down warehouse split of the SKU forecast, dead-warehouse guard,
      reconciled to the forecast total → `reports/06_allocation.md` (stage 06)
- [x] Decision records for the model-family and uplift-strategy choices this phase's port
      touched: **DR-0005** (uplift unit of analysis), **DR-0006** (margin convention,
      retroactive), **DR-0007** (pricing recommendation rule). The original Challenge A
      model-selection reasoning remains in `reports/03_forecast.md` rather than its own DR —
      it was not touched by the port and stays where it was written.

## Phase 5 — Validation ✅

- [x] `uv run scripts/run_all.py` reproduces every number from raw data end-to-end
- [x] Sensitivity to the F-003 cost assumption shown explicitly in `reports/04_elasticity.md` §3
- [x] Post-promo dip checked for every episode with an observable window (H-006)
- [x] Limitations documented per challenge, in both the stage reports and the summary doc
- [x] Every estimate in Challenge C graded on identification strength

## Phase 6 — Communication ✅

- [x] [Methodology, assumptions & trade-offs](../reports/methodology-and-tradeoffs.md)
- [x] [Business recommendations](../reports/business-recommendations.md), non-technical
- [x] [`AI_USAGE_LOG.md`](AI_USAGE_LOG.md) updated with corrections made to AI output

## Open questions for VEMIO

The case states *"we prefer you ask rather than assume."* These are asked; each has a
documented fallback so work is never blocked.

| # | Question | Status | Fallback if unanswered |
|---|---|---|---|
| **Q5** | **`product_cost` exceeds `bruto` on every one of the 358,775 rows**, by a factor that is exactly constant per SKU (1.22–1.30) and matches the documented 0.20–0.30 margin band. Read literally, the client loses 22–30% of gross revenue on every transaction — each SKU's own margin rate with the sign flipped. Was the margin applied in the wrong direction on export — i.e. should cost be `bruto ÷ (1 + margin)` rather than `bruto × (1 + margin)`? | **open — critical** | Treat `product_margin = product_cost/bruto − 1` and unit cost as `bruto/(1 + margin)`. Every margin figure in the deliverable carries this assumption on its face. (F-003, **DR-0006** — now defended by an executable free-goods check, `quality.check_margin_convention`, not only an argument; the direction is still a defended inference, not a VEMIO-confirmed fact) |
| **Q6** | `discount` is **negative on 10,084 rows (2.81%)**, as low as −0.96. A negative discount is a surcharge — is that intended, an allocation artefact of bundle pricing, or a defect? | **open** | Flag, do not drop. Exclude from elasticity estimation; report the excluded share. (F-004) |
| Q1 | The delivered CSV has 21 columns and **no `product_margin`**, but the dictionary describes it and Challenge B requires it. Was it dropped from the export? | **mitigated** | Resolved in practice by Q5's evidence: `product_cost/bruto − 1` is constant per SKU and reproduces the documented 0.20–0.30 band exactly. Used as the reconstructed margin, disclosed as an assumption. (F-001) |
| Q2 | Is `discount` a percentage or a currency amount, and does it reconcile line by line? | **settled empirically** | Settled without needing an answer: it is a **fraction** (never above 1.0), and reconciles at bundle level only — the currency reading matches 0 of 128,977 promo rows with a gap. Effective price is therefore computed as `sell_in_amount / sell_in_quantity`. (F-004, H-002) |
| Q3 | Is the forecast horizon expected from the last date in the data, or from a fixed "today"? | open | Forecast 12 weeks from the last observed week (2026-05-30), holding out the final weeks for validation. |
| Q4 | Are zero-quantity / zero-amount rows returns, cancellations, or artifacts? 515 rows have zero quantity; 1,108 have zero amount while carrying 4,291 units (free goods?). | open | Flag and exclude from demand modelling; report their volume share. |

## Backlog / nice-to-have (only if time remains)

- Cross-SKU cannibalization check during promo periods
- Warehouse-level forecast reconciliation (bottom-up vs top-down)
- Prediction intervals rather than point forecasts for challenge A
