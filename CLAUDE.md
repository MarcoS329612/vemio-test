# CLAUDE.md — AI assistant context

Context for AI assistants (Claude Code or others) working on this repository.
Read this before touching anything.

## What this project is

Take-home case for an AI Product Engineer role (VEMIO, CPG commercial intelligence).
Three connected challenges on ~359k sell-in transactions (Jan 2025 – May 2026, 6 SKUs, 12 warehouses, ~52,500 clients):

- **A — Demand forecasting**: weekly units for 2–3 SKUs, 8–12 week horizon, temporally validated.
- **B — Price elasticity**: 1 SKU, demand sensitivity to price + a price → demand/revenue/margin simulator. Never extrapolate outside the observed price range.
- **C — Promotional uplift**: incremental sales of ≥2 past promotions; recommend one to repeat, one to drop.

Evaluation weights: technical rigor 30%, data handling 20%, business insight 25%, communication 15%, pragmatism 10%.
Source material is preserved verbatim in `docs/case/` — see `docs/case/README.md` for the provenance manifest.

## Data

- Raw file: `data/raw/20260701_Prueba_tecnica_AI Engineer.csv` (77 MB, git-ignored, original filename preserved).
  **Resolve it through `src/analysis/config.py` — never hardcode the path.**
- Data dictionary: `docs/case/original/README.md` (Spanish, as delivered by VEMIO).
- Grain: one row = day × client × product × ticket × promo (verify, don't assume).
- Known issues per the case statement — **do not assume clean data**: nulls in
  `discount`/`product_cost`, at least one record with incomplete metadata, transactions with
  zero quantity or amount, combo-level discounts that don't reconcile line by line.
- **`product_margin` is missing from the delivered CSV** despite being required by
  Challenge B — see finding F-001 and open question Q1 before using it.
- `data/raw/` and `docs/case/original/` are **immutable**: never edit, rename, or reformat them.
  All transformations produce artifacts in `data/processed/` via committed code.

## Non-negotiable working rules

1. **Baseline first.** Never fit a sophisticated model before a naive baseline (seasonal naive, moving average) establishes the bar. Report the baseline's score in every comparison.
2. **No future leakage.** Splits are strictly chronological; rolling-origin validation for forecasts. Features must be computable at prediction time — no full-series statistics fit over the test period.
3. **Traceable cleaning.** Every filter/imputation logs rule, rows affected, before/after counts. Prefer flag columns over deletion.
4. **Register claims before testing them.** Any claim that could change a decision goes into `docs/HYPOTHESES.md` **with its rejection condition written first**. Verified conclusions get promoted to `docs/FINDINGS.md`.
5. **Record decisions.** Non-obvious methodological choices get a `docs/decisions/DR-XXXX-*.md` naming the alternatives that lost and why.
6. **Log findings and actions.** New discoveries → `docs/FINDINGS.md`. End of session → `docs/WORKLOG.md`. Substantive AI contributions → `docs/AI_USAGE_LOG.md` (this last one is a case requirement).
7. **Scripts, not notebooks** (DR-0003). No `.ipynb` committed. Logic lives in `src/analysis/`; `scripts/NN_*.py` are thin stage entry points, and **every stage writes a markdown artifact + figures into `reports/`**.
8. **English everywhere** — code, docs, commits. Business deliverables may additionally be produced in Spanish.
9. **Pragmatism.** Target effort is a 4–6 hour case. Simple and well-justified beats complex. Over-engineering is explicitly penalized by the rubric.
10. **Ask rather than assume.** The case invites questions. Unknowns go to the open-questions table in `docs/ROADMAP.md` with a documented fallback so work is never blocked.

## Conventions

- Python ≥3.11 with **`uv`** (DR-0004): dependencies and tool config in `pyproject.toml`, exact versions in the committed `uv.lock`. Use `uv sync` and `uv run <script>` — **never `pip`**; this venv has no pip.
- Stage scripts are numbered by phase (`01_data_audit.py`, `02_eda.py`, …) and are runnable standalone. The `analysis` package is installed editable, so import it directly — no path shims.
- Anything reused or worth testing lives in `src/analysis/` — never copy-pasted between stages.
- Figures go to `reports/figures/` with descriptive names; generated reports to `reports/`.
- Commits: small, imperative mood, one logical change; reference registry IDs where relevant (`Add zero-quantity flag per F-004`). **The commit history is graded.**

## Where things are

| What | Where |
|---|---|
| Methodology (lifecycle + 7 standards) | `docs/methodology/` |
| Current phase, TODOs, open questions | `docs/ROADMAP.md` |
| Verified findings | `docs/FINDINGS.md` |
| Hypotheses under test | `docs/HYPOTHESES.md` |
| Decision records | `docs/decisions/` |
| Session-by-session work log | `docs/WORKLOG.md` |
| AI usage log | `docs/AI_USAGE_LOG.md` |
| Source material (verbatim) | `docs/case/` |
| Final deliverables | `reports/` |

## Definition of done (per phase)

A phase is done when its exit criteria in `docs/methodology/README.md` are met, its
artifacts exist in `reports/`, the registries are updated, and `docs/ROADMAP.md` reflects
the new state. Do not start modeling before the data-quality artifact and EDA findings exist.
