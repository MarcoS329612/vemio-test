# Standard 06 — Communication

Goal: the same analysis serves two audiences without diluting either.

## 1. Two registers, always

| | Technical deliverable | Business deliverable |
|---|---|---|
| Audience | Reviewers, future analysts, AI assistants | Commercial team of the client |
| Form | Scripts + generated stage reports + methodology doc | 3–5 recommendations, 1–2 pages |
| Language | Precise, reproducible, with uncertainty quantified | Plain language, zero jargon, action-oriented |
| Test | Someone else reruns it and gets the same numbers | A commercial manager knows what to do next Monday |

## 2. Rules for the business register

- Lead with the recommendation, then the evidence, then the caveat — in that order.
- Numbers rounded to decision-relevant precision ("~12% more units", not "12.37%").
- Every recommendation names an action, an owner-shaped verb, and a magnitude
  ("Repeat combo X in warehouses A–C next quarter; expect on the order of +N units/week").
- Uncertainty stated as consequence, not statistics ("if the price response is weaker
  than estimated, revenue gain shrinks but margin still improves").
- No method names unless asked; the method lives in the technical doc.

## 3. Rules for the technical register

- Structure: assumptions → data decisions → method per challenge → results → trade-offs
  ("what I would do with more time/data" is an explicit section).
- Honesty about limitations is scored, not penalized — list them proactively.
- Every figure has a takeaway sentence in its caption; no orphan plots.

## 4. Definition of done

- Technical: reproduces end-to-end from `data/raw/` on a clean environment
  (`python scripts/run_all.py`), and every headline number traces to the script that made it.
- Business: read aloud in <5 minutes, survives the question "so what should we do?".
