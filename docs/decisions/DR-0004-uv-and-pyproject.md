# DR-0004 — `uv` + `pyproject.toml` as the environment and packaging contract

- **Date**: 2026-08-02
- **Status**: accepted
- **Phase**: 1
- **Decided by**: Luis Angel Almazán López (AI-assisted: yes — Claude Code)
- **Corrects**: an initial `requirements.txt` + `sys.path` shim, which ignored the tooling
  already in use in this environment

## Context

Reproducibility is the definition of done for the technical deliverable (standard 06): a
reviewer must be able to regenerate every number from `data/raw/` on a clean machine. That
requires pinning not just which packages, but which *versions*, and making the `analysis`
package importable from the stage scripts.

`uv` is already the environment manager in this workspace — the project's `.venv` was
created by it and has no `pip` installed.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| `requirements.txt` + `sys.path` shim in each script | No build step; familiar to everyone | Loose version ranges — not a reproducible pin; the shim is a workaround for not packaging; conflicts with the `uv`-managed venv, which has no `pip` |
| `requirements.txt` + `pip-compile` lockfile | Real pinning; widely understood | Two files to keep in sync; still needs `pip`, which this venv lacks; still needs the import shim |
| **`pyproject.toml` + `uv sync` (lockfile committed)** | Single source of truth for metadata, dependencies, and tool config; `uv.lock` pins the exact resolved graph; the package installs editable so `from analysis import …` just works — no shim; matches the tooling already here | Reviewer needs `uv` installed (a one-line install) |
| Poetry / PDM | Mature, similar guarantees | Another tool to introduce when `uv` is already present; slower |

## Decision

`pyproject.toml` is the single contract: project metadata, runtime dependencies, a `dev`
dependency group (pytest, ruff), and tool configuration (ruff lint rules, pytest paths).
`uv sync` creates the environment and installs the `analysis` package in editable mode.
**`uv.lock` is committed**; `requirements.txt` and the `scripts/_bootstrap.py` shim are removed.

Commands become `uv run scripts/01_data_audit.py` and `uv run scripts/run_all.py`.

## Rationale

The deciding factor is that a lockfile is what makes "reproducible" true rather than
aspirational. `requirements.txt` with `>=` ranges reproduces *a* working environment, not
*the* environment that produced the committed numbers — and a stage report that cites a
checksum of its input while leaving its dependency versions floating is only half-honest.

Installing the package properly also removes the `sys.path` shim. The shim worked, but it
existed only to avoid packaging; with `pyproject.toml` present, packaging is one line and
the scripts import the library the same way a test or any other consumer would.

Choosing `uv` over Poetry is simply following what is already installed. Introducing a
second environment manager would be exactly the over-engineering the pragmatism criterion
penalises.

## Consequences

- Reviewers need `uv`; the README states the one-line install and the two commands.
- `uv.lock` must be committed and updated deliberately — a dependency change is a commit,
  not a side effect.
- Tool configuration (ruff, pytest) now lives in `pyproject.toml`, so there is one place to
  look rather than scattered config files.
- Revisit trigger: if VEMIO's reviewers cannot install `uv`, export a pinned
  `requirements.txt` from the lockfile (`uv export`) as a compatibility artifact — keeping
  the lockfile as the source of truth.
