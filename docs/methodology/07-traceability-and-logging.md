# Standard 07 — Traceability & logging

Goal: any reader — a reviewer, a colleague six months later, or a fresh AI session —
can reconstruct **what is true, what we chose, and why**, without access to the
conversation that produced it.

This is the standard that makes the other six auditable. It is also the one most often
skipped, because its payoff is deferred.

## 1. The four registries

Each answers a different question. Writing a note in the wrong one is how registries rot.

| Registry | Question | Entry is created when |
|---|---|---|
| [`FINDINGS.md`](../FINDINGS.md) | *What is true?* | Something is **verified** about the data, case, or domain that affects how results should be read |
| [`HYPOTHESES.md`](../HYPOTHESES.md) | *What might be true?* | A claim is **proposed** that could change a decision — before it is tested |
| [`decisions/`](../decisions/) | *What did we choose?* | A non-obvious choice is made **with a credible alternative** |
| [`WORKLOG.md`](../WORKLOG.md) | *What did we do, and why?* | End of each work session |

Plus [`AI_USAGE_LOG.md`](../AI_USAGE_LOG.md), which records how AI assistants contributed
and how their output was verified (see standard 05).

Promotion path: a hypothesis that reaches `supported` has its conclusion **promoted into
`FINDINGS.md`**; the hypothesis entry keeps the evidence trail.

## 2. What deserves an entry

Write it down when the answer to any of these is yes:

- Would a reviewer be surprised by this, or ask "why?"
- Did this change what we will do next?
- Did we reject a credible alternative?
- Would we forget the reasoning in a month?
- Does a downstream number depend on this being true?

Do **not** log routine work — renaming a variable, fixing a typo, reformatting a plot.
Volume is the enemy of a registry; if everything is logged, nothing is read.

## 3. Rules that keep the trail honest

- **Write before, not after.** Rejection conditions before running tests; decision
  rationale at the moment of deciding. Reasoning reconstructed after seeing the result is
  rationalization, and it reads that way.
- **Evidence, not assertion.** Every finding cites a number, a figure, or a code location.
  "The data is clean" is not a finding; "0.4% of rows have zero quantity, concentrated in
  warehouse 7" is.
- **Name the impact.** A finding without a stated consequence is trivia. Say what it
  changes: an assumption, a filter, a caveat in the report.
- **Record negative and inconvenient results.** Rejected hypotheses, methods that failed,
  and limitations you could not resolve are part of the trail. The evaluation criteria
  reward honesty about limitations explicitly.
- **Cross-link by ID.** `F-001`, `H-003`, `DR-0002`, `Q1` are stable identifiers; use them
  in code comments, commit messages, and reports so any number can be traced to its
  reasoning.
- **Update, don't duplicate.** When a finding's status changes, edit its entry and note the
  change — do not append a second entry about the same thing.

## 4. Traceability inside the code and the deliverables

- **Commits**: small, imperative, one logical change; reference registry IDs where relevant
  (`Add zero-quantity flag per F-004`). The commit history is itself a deliverable here.
- **Scripts**: each analysis stage writes a markdown artifact to `reports/` recording the
  parameters it ran with, the row counts before/after each filter, and the numbers it
  produced — so results are readable and auditable without re-running the pipeline.
- **Data**: raw is immutable; every processed artifact is reproducible from raw by
  committed code. A number that cannot be regenerated is a bug, not a result.
- **Reports**: figures and headline numbers point back to the script that produced them.

## 5. Definition of done for traceability

At the end of the project, a reader who has never seen the conversation can answer,
using only the repository: *Why this model? Why this metric? What was wrong with the data
and what was done about it? What is the analysis not able to tell us?*
