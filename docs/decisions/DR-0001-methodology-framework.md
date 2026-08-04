# DR-0001 — Adopt a phased CRISP-DM variant with explicit registries

- **Date**: 2026-08-02
- **Status**: accepted
- **Phase**: 0
- **Decided by**: Luis Angel Almazán López (AI-assisted: yes — Claude Code)

## Context

The project must (a) deliver a time-boxed take-home case (~4–6 effective hours) whose
evaluation explicitly rewards technical rigor, traceable data handling, and honesty about
limitations, and (b) serve as a reusable foundation for future AI-assisted analytics
projects. It must also be legible to AI assistants across sessions, since chat history is
not durable project memory.

Question: what working methodology do we adopt?

## Options considered

| Option | Pros | Cons |
|---|---|---|
| Ad-hoc notebook exploration | Fastest start; zero ceremony | Irreproducible; data decisions made silently; high leakage risk; nothing to reuse; fails the "data handling" and "communication" criteria |
| Full CRISP-DM or Microsoft TDSP | Battle-tested; complete artifact set; recognizable to reviewers | Documentation weight is disproportionate for a 6-hour case; risks scoring badly on the pragmatism criterion |
| Notebook + a single README at the end | Low overhead; some narrative | Decisions get reconstructed after the fact (i.e., rationalized); no defense against confirmation bias; poor AI context |
| **Phased CRISP-DM, slimmed, plus three registries (hypotheses, decisions, AI log)** | Auditable trail; each phase capped at 1–2 short artifacts; registries double as AI context; directly maps to the evaluation criteria; portable to other projects | Small per-phase documentation cost; requires discipline to keep registries current |

## Decision

Adopt the slimmed phased lifecycle documented in
[`docs/methodology/`](../methodology/README.md) — six phases with explicit entry/exit
criteria — supported by three living registries: `HYPOTHESES.md`, `docs/decisions/`, and
`AI_USAGE_LOG.md`.

## Rationale

The evaluation rubric is essentially a methodology test: 30% technical rigor (justified
choices, no leakage), 20% data handling (traceability, no over-cleaning), 15%
communication (honesty about limitations). Those are exactly the things that get lost when
work is done ad-hoc and documented afterwards. Writing the rationale *before* the result
is also the only cheap defense against post-hoc rationalization.

Full CRISP-DM lost on the pragmatism criterion (10%), which explicitly penalizes
over-engineering. The slimmed variant keeps the auditability and drops the ceremony:
no separate business-understanding deliverable, no formal deployment phase, registries
instead of per-phase reports.

The registries carry a second benefit specific to AI-assisted work: a fresh assistant
session can reconstruct the project's state and reasoning from files rather than from a
lost conversation.

## Consequences

- Every non-obvious methodological choice from here on costs ~10 minutes of writing a DR.
  Accepted: that cost is the deliverable's audit trail.
- Hypotheses must be registered with a rejection condition before testing. This will
  occasionally feel slow; it is the mechanism that keeps the analysis falsifiable.
- The methodology directory is written project-agnostic so it can be copied wholesale into
  the next project (see the reuse checklist at the end of `methodology/README.md`).
- Revisit trigger: if the registry overhead visibly cuts into analysis time, cut the
  per-phase artifacts before cutting the registries — the registries are the load-bearing part.
