# AI usage log

The case explicitly permits and welcomes LLM/AI use **provided it is documented**.
This log records substantive AI contributions: what was delegated, what came back, and
**how it was verified**. Granularity is one entry per work session or major artifact —
not per prompt.

Governing standard: [methodology/05-ai-collaboration.md](methodology/05-ai-collaboration.md).

## Standing rules applied throughout

- AI-computed numbers that reach a report are re-derived or spot-checked against the data
  through a different query path before publication.
- AI-drafted code is read before being run on real data; any data-mutating step is
  reviewed line by line.
- AI-proposed interpretations enter `HYPOTHESES.md` like any other claim — they earn
  `supported` through evidence, not through fluency.
- Accountability for every published claim rests with the author, not the tool.

## Entries

### 2026-08-02 — Session 1: Methodology foundation and project scaffolding

- **Tool**: Claude Code (Claude Fable 5 / Opus 5)
- **Task delegated**: Read the case statement and dataset header; propose and draft a
  reusable AI-assisted analytics methodology; scaffold the repository, documentation
  index, hypothesis registry, decision records, and roadmap.
- **AI produced**:
  - Repository structure (`data/`, `docs/`, `src/analysis/`, `scripts/`, `reports/`) and
    placement of the provided files into `data/raw/` and `docs/case/`.
  - The six-phase methodology in `docs/methodology/` with entry/exit criteria and
    per-phase standards.
  - `CLAUDE.md` (AI context file), `README.md`, documentation index.
  - Initial hypothesis registry (H-001…H-006) with rejection conditions written before
    any test was run.
  - Decision records DR-0001 (methodology), DR-0002 (repo & data handling) and DR-0003
    (scripts over notebooks), each naming the alternatives that were rejected.
  - The traceability standard and the `FINDINGS.md` / `WORKLOG.md` registries, after the
    user asked that findings, decisions and relevant actions be documented explicitly.
  - The `src/analysis/` library skeleton (`config`, `io`, `quality`, `reporting`) and the
    `scripts/` stage entry points, including a runnable Phase 1 data-quality audit.
  - English working summary of the Spanish case statement (`docs/case/case-summary.md`).
- **Human verification**:
  - Case requirements, evaluation weights, and logistics cross-checked against the
    original `.docx` text extracted from the file (not from memory or summary).
  - Dataset header read directly from the CSV: **21 columns confirmed**, and
    `product_margin` confirmed **absent** despite being required by Challenge B and
    described in the data dictionary. Raised as open question Q1 in `ROADMAP.md` with a
    documented fallback rather than a silent assumption.
  - Row count confirmed directly from the file (~358,776 data rows, consistent with the
    stated ~359,000 transactions).
  - Methodology content reviewed for right-sizing against the 10% pragmatism criterion;
    full CRISP-DM was explicitly rejected as over-engineered for the scope.
  - The audit script was executed against all 358,775 real rows rather than assumed to
    work; its outputs are the evidence behind the Phase 1 findings.
  - The critical finding (F-003, inverted cost/margin direction) was **re-derived through
    an independent ad-hoc query** before being written up, not taken from the audit
    script's own output — the two paths agree, and the per-SKU ratios land exactly on the
    0.20–0.30 band the dictionary documents.
  - Entity counts (6 SKUs, 12 warehouses, 52,555 clients, 79 combos, 74 weeks) were checked
    against the figures stated in the case statement.
- **Corrections made to AI output**:
  - The AI initially renamed the delivered files (`sell_in_transactions.csv`) and moved
    them out of their original folder. Corrected on the user's instruction: originals are
    now preserved verbatim in `docs/case/original/` with checksums, and the dataset keeps
    its delivered filename. Provenance beats tidiness.
  - Notebooks were replaced by scripts as the working medium (DR-0003) on the user's
    preference; the rationale was then argued on its own merits, not accepted by fiat.
  - The AI defaulted to `requirements.txt` and a `sys.path` shim despite the project
    already using `uv`. Corrected to `pyproject.toml` + committed `uv.lock` with an
    editable install (DR-0004), which also removed the need for the shim.
  - The AI's first reconciliation test pooled organic rows, where every candidate reading
    matches trivially — the output looked conclusive at ~64% and was not. Segmented on
    review; the corrected test discriminates 48.21% vs 0%. A code comment asserting that
    pandas treats nulls as non-matching in duplicate detection was also wrong and was
    fixed. Both are examples of the failure mode standard 05 warns about: plausible,
    fluent, and incorrect.
- **Not delegated**: business framing decisions, scope boundaries, the choice of working
  medium, and the open questions raised to VEMIO — reviewed and owned by the author.

### 2026-08-03 — Session 2: All three challenges

- **Tool**: Claude Code (Claude Fable 5 / Opus 5)
- **Task delegated**: Implement and run Challenges A, B and C end-to-end, and draft both
  written deliverables.
- **AI produced**: the cleaning, panel, forecasting, elasticity, uplift, economics, metrics
  and plotting modules; the four stage scripts; and first drafts of the methodology document
  and the business recommendations.
- **Human verification**:
  - The full pipeline was executed against all 358,775 real rows, not sampled or mocked.
    Every figure in both deliverables comes from a generated stage report.
  - Model selection was left to out-of-sample WAPE across rolling origins rather than
    chosen. The result — that naive baselines win on two of three SKUs — was reported as-is
    rather than replaced with a model that looked more impressive.
  - The elasticity of −4.73 was interrogated rather than accepted: it is far above a
    plausible consumer elasticity, which led to identifying the sell-in forward-buying
    interpretation. That reframing changes what the number may be used for.
- **Corrections made to AI output**:
  - The first uplift implementation required a post-promotion window, which silently
    excluded the two best-identified episodes in the dataset (SKUs 1857/1858, unpromoted for
    14 months). Caught on reviewing why only 5 of 12 episodes were evaluated; relaxing the
    filter is what surfaced finding F-008.
  - The first uplift table omitted the `control_skus` column, hiding that the
    difference-in-differences correction had collapsed to the naive comparison on most
    episodes. Surfaced, and an explicit evidence grade added, because an estimate that
    silently degrades to a weaker method is worse than one that admits it.
  - The AI initially reported `MASE` without noting that a one-step-naive denominator makes
    values above 1 unremarkable at a 12-week horizon. Caveat added rather than the metric
    quietly dropped.
- **Not delegated**: the interpretation of the cost anomaly, the decision to raise questions
  to VEMIO rather than assume, the weighting behind the price recommendation, and the final
  wording of every claim in the business document.

<!-- Template for subsequent entries:

### YYYY-MM-DD — Session N: <title>
- **Tool**:
- **Task delegated**:
- **AI produced**:
- **Human verification**:
- **Corrections made to AI output**:
- **Not delegated**:
-->
