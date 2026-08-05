# AI-Driven Commercial Analytics — CPG Case (VEMIO)

Demand forecasting, price elasticity, and promotional uplift analysis for a CPG client,
built on a reusable, AI-assisted data analytics methodology.

> This repository serves two purposes:
> 1. **Solve the case**: three connected business questions (forecast, elasticity, uplift) on ~359k sell-in transactions.
> 2. **Establish a foundation**: a professional methodology for AI-assisted analytics projects, reusable across future projects.

## The case in one paragraph

A CPG client's commercial team needs input for next quarter's replenishment and promotion plan.
Using 17 months of sell-in transactions (Jan 2025 – May 2026, 6 SKUs, 12 warehouses, ~52,500 clients), we must:
(**A**) forecast weekly demand for 2–3 SKUs, 8–12 weeks ahead;
(**B**) estimate price elasticity for 1 SKU and build a price → demand/revenue/margin simulator;
(**C**) quantify the incremental sales of at least two past promotions and recommend which to repeat and which to drop.
Original statement and data dictionary, preserved verbatim: [docs/case/](docs/case/README.md).

## Repository structure

```
├── README.md                  ← you are here
├── CLAUDE.md                  ← context file for AI assistants working on this repo
├── pyproject.toml             ← dependencies + tool config; uv.lock pins exact versions
├── data/
│   ├── raw/                   ← immutable input, original filename kept (git-ignored)
│   └── processed/             ← derived datasets, reproducible from raw (git-ignored)
├── src/analysis/              ← the library: config, I/O, quality, panels, models, reporting
├── scripts/                   ← one runnable entry point per lifecycle stage
├── reports/                   ← generated artifacts + final deliverables
│   └── figures/
└── docs/
    ├── README.md              ← documentation index
    ├── ROADMAP.md             ← phases, milestones, TODOs, open questions
    ├── FINDINGS.md            ← what we verified to be true, with evidence
    ├── HYPOTHESES.md          ← what might be true: claims under test
    ├── WORKLOG.md             ← what we did, when, and why
    ├── AI_USAGE_LOG.md        ← how AI assistants were used (case requirement)
    ├── case/                  ← source material from VEMIO, verbatim + checksums
    ├── decisions/             ← decision records: choices, alternatives, trade-offs
    └── methodology/           ← the reusable methodology
```

Analysis code is **scripts, not notebooks** — the reasoning is in
[DR-0003](docs/decisions/DR-0003-scripts-over-notebooks.md). Each stage script writes a
markdown artifact and figures into `reports/`, so results are readable without running anything.

## Methodology at a glance

A phased lifecycle adapted from CRISP-DM and right-sized for AI-assisted work. Each phase
has explicit entry/exit criteria and produces auditable artifacts
(full detail in [docs/methodology/](docs/methodology/README.md)):

```mermaid
flowchart LR
    P0[0. Business framing] --> P1[1. Data intake & quality audit]
    P1 --> P2[2. EDA]
    P2 --> P3[3. Hypotheses]
    P3 --> P4[4. Modeling]
    P4 --> P5[5. Validation]
    P5 --> P6[6. Communication]
    P5 -. new questions .-> P2
```

Core principles:

- **Baseline first** — no sophisticated model before a naive one sets the bar.
- **No future leakage** — validation is strictly temporal (rolling-origin); features never look ahead.
- **Traceable data handling** — every cleaning decision logged with row counts; records are flagged, not silently dropped.
- **Hypothesis-driven** — claims enter [HYPOTHESES.md](docs/HYPOTHESES.md) with a rejection condition written *before* the test.
- **Decisions on record** — non-obvious choices get a decision record naming the alternative that lost.
- **Findings and actions logged** — [FINDINGS.md](docs/FINDINGS.md) and [WORKLOG.md](docs/WORKLOG.md) keep the trail readable without the conversation.
- **Two audiences** — every result is written twice: technical (reproducible) and business (actionable, no jargon).
- **AI as collaborator, not oracle** — AI output is verified and logged in [AI_USAGE_LOG.md](docs/AI_USAGE_LOG.md).
- **Pragmatism** — depth proportional to the decision at stake; over-engineering is a defect.

## Getting started

Environment and dependencies are managed with [`uv`](https://docs.astral.sh/uv/) via
`pyproject.toml` + a committed `uv.lock` ([DR-0004](docs/decisions/DR-0004-uv-and-pyproject.md)).

```powershell
# 1. Create the environment from the lockfile (exact pinned versions)
uv sync

# 2. Place the raw dataset (not committed — 77 MB, client data)
#    data\raw\20260701_Prueba_tecnica_AI Engineer.csv

# 3. Run a stage — each writes its artifact into reports/
uv run scripts\01_data_audit.py

# …or reproduce everything from raw data
uv run scripts\run_all.py
```

The dataset keeps its **original filename** so provenance is self-evident; code resolves
it through `src/analysis/config.py`. Checksums for all delivered files are in
[docs/case/README.md](docs/case/README.md). Everything under `data/processed/` is
reproducible from raw.

## Deliverables

| Case requirement | Where it lives |
|---|---|
| Reproducible code for challenges A, B, C | [`scripts/`](scripts/) + [`src/analysis/`](src/analysis/) |
| Methodology, assumptions & trade-offs | [reports/methodology-and-tradeoffs.md](reports/methodology-and-tradeoffs.md) |
| Business recommendations, non-technical | [reports/business-recommendations.md](reports/business-recommendations.md) |
| Documentation of AI usage | [docs/AI_USAGE_LOG.md](docs/AI_USAGE_LOG.md) |

For the full reasoning behind each method — and the technical vocabulary explained as it
appears — see the [technical walkthrough](reports/technical-walkthrough.md).

Generated stage reports, each reproducing from raw data:

| Stage | Report |
|---|---|
| Data quality audit | [reports/01_data_quality.md](reports/01_data_quality.md) |
| Cleaning, weekly panel, EDA | [reports/02_eda.md](reports/02_eda.md) |
| **A** — Demand forecasting | [reports/03_forecast.md](reports/03_forecast.md) |
| **B** — Price elasticity & simulator | [reports/04_elasticity.md](reports/04_elasticity.md) |
| **C** — Promotional uplift | [reports/05_uplift.md](reports/05_uplift.md) |
| Warehouse allocation (splits the stage-03 forecast) | [reports/06_allocation.md](reports/06_allocation.md) |

## Headline results

- **A** — On two of three SKUs, no model beat a 4-week moving average (WAPE 0.257 and 0.291);
  only the seasonal SKU supported something better, damped drift at 0.272 against a 0.322
  baseline. Reporting that is the finding, not a failure to find one.
- **B** — Sell-in price elasticity of **−4.73** [−5.71, −3.76] for SKU 1665, with a
  **break-even price of 46.41** below which **10%** of the 72-week history was priced. The
  same break-even identity, generalised to all six SKUs as a discount depth, shows three
  SKUs (the shampoos) already running a mean promotional discount deeper than their own
  break-even depth — a standing structural loss, not an occasional deep-discount week.
  Because demand is this elastic, revenue has no interior optimum anywhere in the price
  domain, so the recommended price is the margin-maximising one, **58.71** (~707
  units/week, ~41,485 revenue, ~8,771 margin, 21.1%) — see **DR-0007**.
- **C** — The same 60-week promotion made **+42,311** on one SKU and lost **−76,315** on
  another, purely because of their different margin bases. The best promotion of the whole
  period involved **no discount at all**. A concurrency-controlled re-estimate of one
  specific bundle mechanic on SKU 1857 (**H-007**, supported) confirms a real +48.4% uplift
  that the SKU-level average (+1%, not significant) alone would have hidden — though the
  statistical significance of that combo-level reading is sensitive to the choice of
  standard errors, disclosed in full in `reports/05_uplift.md` §4.7.
- **Allocation** — Stage 06 splits the SKU forecast across 12 warehouses by historical
  share, reconciling to the forecast total. Bodega n. 11 is excluded everywhere: **F-013**
  shows its shutdown is an 8-month wind-down sitting inside the training window, not a data
  cut.
- **Data** — `product_cost` exceeds gross revenue on *every* row; the margin appears to have
  been applied backwards on export. Raised with VEMIO, corrected explicitly and now checked
  by code (**DR-0006**), and every affected figure is flagged. See
  [docs/FINDINGS.md](docs/FINDINGS.md).

## Status

Current phase, open TODOs and the questions raised with VEMIO: [docs/ROADMAP.md](docs/ROADMAP.md).
