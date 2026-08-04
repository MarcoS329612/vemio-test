# DR-0002 — Repository layout, raw-data immutability, and what gets committed

- **Date**: 2026-08-02
- **Status**: accepted
- **Phase**: 1
- **Decided by**: Luis Angel Almazán López (AI-assisted: yes — Claude Code)
- **Partially superseded by**: [DR-0003](DR-0003-scripts-over-notebooks.md) — the working
  medium is scripts, not notebooks. The data-handling rules below still stand.

## Context

The delivered dataset is a single 77 MB CSV. Delivery is via a git repository whose
**commit history is explicitly part of the evaluation**. We need a layout that keeps the
analysis reproducible, keeps the repository reviewable, and makes it impossible to
accidentally corrupt the source data.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| Commit the raw CSV | Anyone cloning gets a working repo immediately | 77 MB in history forever; bloats clones; risks committing client data to a public repo |
| Git LFS | Large file handled properly; repo stays clean | Requires reviewers to have LFS configured; extra setup friction for a take-home |
| **Git-ignore `data/`, document the expected path** | Repo stays small and reviewable; no client data published; reproducibility preserved via documented placement + code | Reviewer must place the file manually (one line in the README) |
| Commit a sampled subset | Repo runs out of the box | Results in the repo would not match results from the real file; misleading |

## Decision

- `data/raw/` is **immutable** and **git-ignored**. The provided CSV is placed at
  `data/raw/sell_in_transactions.csv`; the original filename is recorded in the README.
- `data/processed/` is git-ignored and **fully reproducible** from raw via committed code.
- Analysis stages are numbered by phase and runnable standalone; reusable logic is
  extracted to `src/analysis/` rather than copy-pasted between stages.
  *(Originally written assuming notebooks — see DR-0003 for the medium change.)*
- Reports and figures live in `reports/`; source material from VEMIO lives untouched in
  `docs/case/`.

## Rationale

Not committing the data is primarily a client-confidentiality call: the dataset is real
(anonymized) data from an active VEMIO client, and the repository may be public. The
size argument reinforces it but is secondary. The cost — one manual file placement — is
bounded and documented in the README.

Raw immutability is the foundation for the traceable-cleaning standard: if raw can be
edited, no cleaning log can be trusted, and the 20% data-handling criterion is
unverifiable. Every transformation must therefore be expressed as code producing a
`data/processed/` artifact.

## Consequences

- A reviewer cloning the repo cannot run it until they place the CSV; the README states
  this in the "Getting started" section.
- Any result that cannot be regenerated from `data/raw/` + committed code is a bug, not a
  result. This is the reproducibility test in the definition of done.
- Because processed data is not committed, the generated stage reports in `reports/` must
  be committed so a reviewer can read results without running anything.
- Revisit trigger: if VEMIO confirms the repository will remain private and they prefer a
  self-contained clone, committing the raw file via Git LFS becomes reasonable.
