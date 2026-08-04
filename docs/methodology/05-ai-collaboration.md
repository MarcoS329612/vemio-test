# Standard 05 — AI collaboration

Goal: use AI assistants aggressively for leverage, without ever outsourcing judgment
or accountability. AI-assisted is fine; AI-unverified is not.

## 1. Roles

| Role | AI does | Human does |
|---|---|---|
| Methodology & design | Propose approaches with pros/cons | Choose, record the DR |
| Code | Draft transformations, models, plots | Review, run, spot-check outputs |
| EDA | Suggest cuts, compute summaries, surface anomalies | Judge relevance, confirm surprising results against raw data |
| Hypotheses | Propose candidates, design tests | Approve rejection conditions, sign verdicts |
| Writing | Draft docs in both registers (technical/business) | Own every claim published |

## 2. Context engineering

- `CLAUDE.md` at repo root is the assistant's entry point: project state, rules,
  and pointers. Keep it current — a stale context file is worse than none.
- Registries (`ROADMAP.md`, `HYPOTHESES.md`, `decisions/`) double as AI context: they
  let a fresh session reconstruct the project without re-explaining.
- When a session produces a durable decision, it must land in a file — chat history
  is not project memory.

## 3. Verification rules

- **Numbers**: any AI-computed number that reaches a report is re-derived or
  spot-checked from the data (different query path when feasible).
- **Code**: AI-drafted code is read before it is run on real data; data-mutating steps
  are reviewed line by line.
- **Claims**: AI-proposed interpretations enter the hypothesis registry like any other —
  they earn `supported` through evidence, not eloquence.
- **Known failure modes to watch**: plausible-but-wrong statistics, silent assumption
  changes mid-analysis, over-confident causal language, leakage introduced via
  convenient features.

## 4. Usage log

`docs/AI_USAGE_LOG.md` records substantive AI contributions: date, task, tool/model,
what the AI produced, and how it was verified. Granularity: one entry per work session
or major artifact — not per prompt. This satisfies transparency requirements
(the case explicitly welcomes AI use *if documented*) and makes the workflow reusable.
