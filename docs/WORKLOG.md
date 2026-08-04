# Work log

Chronological record of **relevant actions**: what was done, why, and what changed as a
result. One entry per work session. Routine edits are not logged; anything that changes
the data, the method, or the project's direction is.

Purpose: a reviewer (or a future AI session) can reconstruct how the project arrived at
its current state without reading the git diff line by line. Git says *what changed*;
this says *why it changed*.

Standard: [methodology/07-traceability-and-logging.md](methodology/07-traceability-and-logging.md).

---

## 2026-08-02 — Session 1: Methodology foundation

**Goal**: establish a professional, reusable methodology for AI-assisted analytics before
touching the analysis, and complete Phase 0 (business framing) + start Phase 1 (intake).

**Actions**

1. **Read the source material directly, not from summary.** Extracted the case statement
   text from the `.docx` and read the CSV header from the file itself. This surfaced
   finding **F-001** immediately (missing `product_margin`) — it would have been missed by
   trusting the data dictionary alone.
2. **Established the repository structure** (`data/`, `docs/`, `src/`, `scripts/`,
   `reports/`) and the raw-data immutability rule. Recorded as **DR-0002**.
3. **Preserved the originals verbatim** in `docs/case/original/` with SHA-256 checksums
   (**F-002**), after the user flagged that the reference files must be kept intact. The
   dataset keeps its original filename in `data/raw/`; code resolves it via
   `src/analysis/config.py` rather than hardcoding paths.
4. **Wrote the methodology** (`docs/methodology/`): six-phase lifecycle with entry/exit
   criteria, plus standards for data quality, EDA, hypotheses, modeling, AI collaboration,
   communication, and traceability. Full CRISP-DM was considered and rejected as
   over-engineered for a 4–6 hour case — recorded as **DR-0001**.
5. **Completed Phase 0 (business framing)** in `ROADMAP.md`: the three challenges restated
   as decisions to support, with "good enough" criteria and an explicit out-of-scope list.
6. **Seeded the registries**: six hypotheses (H-001…H-006) with rejection conditions
   written *before* any test; two findings; four open questions to VEMIO, each with a
   documented fallback so no question blocks progress.
7. **Chose scripts over notebooks** for all analysis code, after the user's preference and
   on independent merits (reviewable diffs, testability, lower token cost for AI
   collaboration). Recorded as **DR-0003**; the methodology and roadmap were rewritten to
   match.
8. **Built the analysis skeleton and ran it against the real data**: `src/analysis/`
   (`config`, `io`, `quality`, `reporting`) plus `scripts/01_data_audit.py`, which emits
   `reports/01_data_quality.md`. Building it revealed a detail worth pinning: the CSV
   writes dates as `dd/mm/yyyy`, which parsed wrong would silently reorder 17 months of
   history — so the format is pinned in `config.py` and re-verified against the `year`/
   `month` columns on every run rather than inferred.
9. **Corrected the environment tooling.** The first pass used `requirements.txt` and a
   `sys.path` shim; the user pointed out the project already uses `uv`. Replaced with
   `pyproject.toml` + committed `uv.lock` and an editable install (**DR-0004**), which also
   made the shim unnecessary. Loose version ranges would have undercut the reproducibility
   claim the stage reports make.

10. **Ran the audit against all 358,775 rows and it paid for itself immediately.** Three
    material findings, none of which the data dictionary would have revealed:
    - **F-003 (critical)**: `product_cost` exceeds `bruto` on *every* row, by a factor that
      is exactly constant per SKU (std = 0.0) and equal to 1 + the documented margin.
      Read literally the client loses 18–23% on every transaction. Raised as **Q5**;
      the same evidence makes the missing `product_margin` exactly recoverable, which
      resolves F-001 in practice.
    - **F-004**: `discount` is a fraction, not percent-points, and reconciles only at
      bundle level — the currency reading matches **0** of 128,977 promo rows with a
      gross/net gap. So effective price must come from `sell_in_amount / sell_in_quantity`.
      It is also negative on 2.81% of rows, which is unexplained (**Q6**).
    - **F-006**: only two of six SKUs carry enough realised price variation to support an
      elasticity estimate, which turns Challenge B's SKU choice into a documented criterion.
11. **Fixed two defects the first audit run exposed in my own code**: the reconciliation
    test pooled organic rows, where every reading matches trivially — masking the answer
    behind a uniform ~64%; it is now segmented, and the discriminating segment shows
    48.21% vs 0%. A code comment also asserted that pandas treats nulls as non-matching in
    duplicate detection, which is false; corrected rather than left as a plausible-sounding
    wrong explanation.

**Changed as a result**

- Phase 0 closed. Phase 1 substantially complete: shape, grain, coverage, date format,
  completeness, reconciliation and price structure all verified and documented.
- Analysis architecture is script-first: `src/analysis/` (library) + `scripts/` (stages),
  each stage emitting a markdown artifact into `reports/` so results are readable without
  re-running anything. Proven end-to-end on the real dataset.
- H-001 and H-002 moved to `supported`; H-004 to `testing`.
- Q1 and Q2 are effectively resolved by evidence; **Q5 and Q6 are new and were raised
  because the data contradicted its own documentation** — exactly the case's instruction to
  ask rather than assume.

**Open at end of session**: Q3–Q6 with VEMIO. Remaining Phase 1 work (cleaning decision
log, weekly panel) moves into stage 02, where the flags belong alongside the panel build.

---

## 2026-08-03 — Session 2: All three challenges

**Goal**: answer Challenges A, B and C and produce both written deliverables.

**Actions**

1. **Stage 02 — cleaning and the shared panel.** Six boolean flags, no deletions. The
   judgement call worth recording: zero-amount rows *keep* their units, because shipping
   stock free of charge is real demand and dropping it would bias a units forecast
   downward — but they are excluded from price work, where a realised price of zero is not
   a point on a demand curve. Built the weekly SKU panel once, in one place, so the three
   challenges could not quietly disagree about what a week is.
2. **Stage 03 — forecasting.** Seven models, five rolling origins, 12-week horizon. A first
   pass showed *every* level-only model under-forecasting by 13–30%, which was a diagnostic
   rather than an annoyance: the series drift upward and flat forecasts cannot follow. Added
   damped drift and an ensemble in response. Damped drift now wins on the seasonal SKU;
   moving average still wins on the other two, and the report says so (**F-010**).
3. **Stage 04 — elasticity.** −4.73 on SKU 1665. Two qualifications discovered during the
   work matter more than the coefficient: the price variation is discount depth on an
   almost-always-promoted SKU, and this is *sell-in*, so the number absorbs distributor
   forward-buying. Both are now stated everywhere the figure appears. The simulator surfaced
   a break-even price near 47 (**F-011**) — the most actionable number in the challenge.
4. **Stage 05 — uplift.** First implementation excluded episodes still running at the end of
   the extract, which silently dropped the two *best-identified* events in the dataset —
   SKUs 1857 and 1858, unpromoted for 14 months before March 2026. Relaxed the filter and
   graded every estimate on identification strength instead. That change is what surfaced
   **F-008**: the same promotion, opposite margin verdicts on two SKUs.
5. **Wrote both deliverables** and verified the whole pipeline reproduces from raw data via
   `run_all.py`.

**Changed as a result**

- All six hypotheses now carry verdicts: H-001/H-002 supported, H-003 **rejected**, H-004
  supported but reframed, H-005/H-006 partially supported. The rejection of H-003 is the
  more useful result — seasonality is visible but not *exploitable*, because 17 months
  observes each annual cycle roughly once.
- Four new findings (F-008 to F-011) drive four of the five business recommendations.

**Judgement calls a reviewer should be able to challenge**

- The "balanced price" rule weights revenue and margin equally after normalising each to its
  own maximum. Arbitrary, so it is stated in the report rather than buried, with the
  margin-maximising alternative given alongside.
- Uplift episodes are derived from observed promotional intensity rather than combo IDs,
  because combos overlap on the same SKU. This measures combined pressure, not any single
  offer.

**Outstanding debt**: the model, metric and uplift-strategy decisions are argued inside the
stage reports but have not been extracted into decision records. Recorded in the roadmap
rather than quietly dropped.
