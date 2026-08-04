# Stage scripts

One runnable entry point per lifecycle phase. Scripts are thin: they orchestrate,
the logic lives in [`src/analysis/`](../src/analysis/) ([DR-0003](../docs/decisions/DR-0003-scripts-over-notebooks.md)).

**Every stage writes a markdown artifact into `reports/`.** A stage that only prints to
stdout is incomplete — the artifact is what makes results reviewable without re-running
the pipeline, and what lands in git as a readable diff.

| Stage | Script | Artifact | Phase |
|---|---|---|---|
| Data intake & quality audit | `01_data_audit.py` | `reports/01_data_quality.md` | 1 |
| Exploratory data analysis | `02_eda.py` *(pending)* | `reports/02_eda.md` | 2 |
| Demand forecasting (Challenge A) | `03_forecast.py` *(pending)* | `reports/03_forecast.md` | 4 |
| Price elasticity (Challenge B) | `04_elasticity.py` *(pending)* | `reports/04_elasticity.md` | 4 |
| Promotional uplift (Challenge C) | `05_uplift.py` *(pending)* | `reports/05_uplift.md` | 4 |

## Running

```powershell
uv sync                                        # once, from the lockfile

uv run scripts\01_data_audit.py                # a single stage
uv run scripts\01_data_audit.py --nrows 50000  # smoke-test on a slice
uv run scripts\run_all.py                      # everything, in order
```

`run_all.py` discovers stages by filename and runs them in numeric order, so a new
stage needs no registration. A failing stage stops the run.

## Conventions

- Import the library directly (`from analysis import config, io, quality`) — the package
  is installed editable by `uv sync` ([DR-0004](../docs/decisions/DR-0004-uv-and-pyproject.md)),
  so no path manipulation is needed.
- Take parameters via `argparse` with sane defaults; record them in the report header so
  a reader knows what the run used.
- Detect and report; **do not clean silently**. Filters are logged with before/after row
  counts (standard 01).
- Reference registry IDs (`F-001`, `H-002`, `DR-0003`) in output and comments so any
  number traces back to its reasoning.
