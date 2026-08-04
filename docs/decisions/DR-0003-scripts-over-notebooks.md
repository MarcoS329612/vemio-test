# DR-0003 — Script-first analysis architecture (no notebooks)

- **Date**: 2026-08-02
- **Status**: accepted
- **Phase**: 1
- **Decided by**: Luis Angel Almazán López (AI-assisted: yes — Claude Code)
- **Supersedes**: the notebook-based artifacts assumed in DR-0002

## Context

All analysis code for the three challenges must be reproducible and reviewable, and the
work is done in close collaboration with an AI assistant. The case explicitly accepts
"notebook **or** script". The commit history is part of what is evaluated.

Question: notebooks or plain Python scripts as the primary analysis medium?

## Options considered

| Option | Pros | Cons |
|---|---|---|
| Jupyter notebooks | Familiar to reviewers; inline output and plots; natural narrative flow | Diffs are JSON noise — commit history becomes unreviewable; hidden out-of-order execution state; hard to unit-test; hard to reuse across challenges; feeding a notebook to an AI assistant carries all stored outputs as context (expensive and noisy) |
| **Scripts (`src/` library + `scripts/` stages) emitting markdown/figure artifacts** | Clean, reviewable diffs; deterministic top-to-bottom execution by construction; testable functions; reuse across the three challenges; cheap and precise as AI context; artifacts make results readable without running anything | Reviewer sees results in generated reports rather than inline; slightly more upfront structure |
| Hybrid: scripts for logic, thin notebooks for narrative | Best of both in principle | Two artifacts to keep in sync; the notebooks drift; over-engineered for a 6-hour case |
| Literate scripts (jupytext / `# %%` cells) | Diff-friendly *and* cell-executable in the IDE | Extra tooling dependency; benefit is mostly interactive, and we are not working interactively |

## Decision

Scripts only. Two layers:

- **`src/analysis/`** — importable library: configuration, I/O, quality checks, panel
  construction, modeling, metrics, plotting, report emission. This is where logic lives
  and where tests point.
- **`scripts/`** — one numbered entry point per lifecycle stage (`01_data_audit.py`,
  `02_eda.py`, `03_forecast.py`, `04_elasticity.py`, `05_uplift.py`), plus `run_all.py`.
  Each stage is runnable standalone, reads from `data/`, and **writes a markdown artifact
  and figures into `reports/`**.

No `.ipynb` files are committed.

## Rationale

The deciding factor is that the commit history is graded. Notebook diffs are stored JSON
including outputs and execution counts — a reviewer cannot see what actually changed
between commits, which forfeits the signal the history is supposed to carry.

Second, reproducibility is structural rather than promised: a script cannot be run out of
order, so "restart the kernel and rerun" stops being a discipline the author must remember.

Third, this is AI-assisted work. A script is precise context — an assistant reads and
edits the exact function under discussion. A notebook drags every stored output along with
it, which costs tokens and dilutes the signal. Over a multi-session project this compounds.

The cost — losing inline output — is paid off by the artifact rule: every stage writes its
findings, row counts and figures to `reports/`, so results stay readable without running
anything, and they land in git as reviewable markdown rather than embedded JSON blobs.

## Consequences

- Each stage script must emit an artifact; a stage that only prints to stdout is incomplete.
- Logic must be extracted into `src/analysis/` rather than accumulating in the stage
  scripts, so that the three challenges share the data-loading and panel-building code.
- Reusable functions become testable; a small test suite is now cheap to add for the
  leakage-sensitive parts (temporal splits, panel construction).
- References to notebooks in DR-0002 and in the methodology standards are superseded by
  this record.
- Revisit trigger: if a reviewer explicitly asks for a notebook deliverable, generate one
  from the scripts at the end rather than making it the working medium.
