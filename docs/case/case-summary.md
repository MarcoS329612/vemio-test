# Case summary (working translation)

English working summary of the original Spanish case statement
([case_statement_original.docx](case_statement_original.docx)). The original prevails
in case of discrepancy.

## Context

VEMIO is an AI-driven commercial intelligence platform for CPG companies in LATAM,
working with sales and trade-marketing teams to forecast demand, optimize pricing, and
measure real promotional impact. The case uses real, anonymized data from an active
CPG client.

## Dataset

Sell-in transactions, Jan 2025 – May 2026 (17 months) · 6 SKUs · 12 warehouses ·
~52,500 clients · ~359,000 transactions · 79 distinct promotional combos.

Grain: day × client × product × ticket × promotion.

> The statement explicitly warns the dataset contains real inconsistencies (nulls in
> discount/cost, a record with incomplete metadata, transactions with zero quantity or
> amount) and instructs us to treat them as we would in a real project.

## The three challenges

### A — Demand forecasting
Forecast **weekly demand in units** for **2–3 SKUs** of our choice, horizon **8–12 weeks**
beyond the end of history.
- Justify the model choice (baseline vs. something more sophisticated).
- Validate performance **with respect to time, without future information leakage**.
- Report forecast error with the metric most adequate for this business, and explain why.

### B — Price elasticity
For **1 SKU with enough price/discount variation**, estimate demand sensitivity to price.
- Build a **simulator**: for any price within the historically observed range for that SKU,
  estimate (a) expected demand, (b) revenue, (c) margin in currency and %, using
  `product_cost` and `product_margin`.
- Identify the price or price zone that best balances revenue and margin; justify it.
- **Do not extrapolate outside the observed price range** — there is no evidence for it.
- State the risks and assumptions that limit the estimate's reliability.

### C — Promotional uplift
Identify **at least two** past promotions or discount periods and estimate the
**incremental sales** generated during each. The identification methodology is our choice.
- Conclude with **at least one promotion to repeat and one not to repeat**, with reasons.

## Deliverables

1. Reproducible notebook or script (Python preferred) covering all three challenges.
2. A 1–2 page document: assumptions taken, methodology per challenge, and relevant
   trade-offs (what would be done differently with more time or data).
3. 3–5 business recommendations for the client's commercial team, in non-technical language.

## Evaluation criteria

| Criterion | What is evaluated | Weight |
|---|---|---|
| Technical rigor | Justified model choice, correct temporal validation (no leakage), explicit assumptions | 30% |
| Data handling | Nulls, duplicates, outliers and inconsistent records handled without losing traceability or over-cleaning | 20% |
| Business insight | Translating technical results into actionable recommendations for the commercial team | 25% |
| Communication | Clarity, structure, honesty about limitations, detail level fit to audience | 15% |
| Pragmatism | Balance between quality and time invested; avoids over-engineering for the scope | 10% |

## Logistics

- Take-home, asynchronous. Deadline: 2–4 calendar days from receipt. Estimated effort: 4–6 effective hours.
- Stack free; Python preferred. **LLM/AI use is permitted and welcome — document how it was used.**
- Delivery via GitHub/GitLab repository — **commit history is part of what is reviewed**;
  loose notebooks or zipped folders are not accepted.
- Questions about the case or dataset are encouraged: *"we prefer you ask rather than assume."*
