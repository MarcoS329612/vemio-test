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

> **Whose session this was.** Sessions 1 and 2 below are reproduced verbatim from the prior,
> independently authored solution this repository's baseline was imported from (authored by
> Luis Angel Almazán López; imported in commit `7476237`). They are written in that author's
> first person and describe work done outside this repository. Session 3 onward is this
> repository's own work. The full provenance statement is in the 2026-08-04 entry.

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
      Read literally the client loses 22–30% of gross revenue on every transaction — each
      SKU's own margin rate with the sign flipped. Raised as **Q5**;
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

> **Whose session this was.** As with session 1: imported baseline work, written in the
> original author's first person, done outside this repository.

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
   a break-even price (**F-011**) — the most actionable number in the challenge. *(This
   session published it as "near 47", read off the coarse ten-point display table. Session 3
   recomputed it from the simulation grid itself and superseded that figure with **46.41**.)*
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

---

## 2026-08-04 — Session 3: Porting a second solution's capabilities, and closing the registries

**Provenance, stated plainly, because it is the fact this entry exists to record.** This
repository's baseline (Sessions 1–2 above) was imported from a prior, independent solution
to the same VEMIO case, authored by Luis Angel Almazán López — credited in the initial
commit `7476237`. The capabilities landed in this session were **ported from a second,
separately authored analysis of the same dataset**, brought in deliberately rather than
rediscovered (see the provenance note at the top of
`docs/specs/2026-08-03-commercial-analysis-port.md`). Neither solution's originality is
overclaimed here: this repository's own contribution this session is the integration,
verification and, in two places (H-007's controlled re-estimate, DR-0007's degenerate-
objective fix), the correction of what the port proposed — not the underlying methods
themselves.

**Goal**: integrate five ported capabilities under full verification — not drop-in, each
number re-derived on this repository's own cleaned data — and bring both written
deliverables and all registries into line with what changed.

**Actions**

1. **Margin convention, verified rather than only argued (DR-0006).** The
   `unit_cost = bruto/(1 + margin)` reading has been in force since the first modelling
   stage but had no decision record. Added `quality.check_margin_convention`: on 414
   free-goods lines, the adopted reading gives −420,300 aggregate margin (correct sign)
   against +648,300 under the rejected reading (wrong sign — giveaways would be the most
   profitable transactions in the dataset). Stage 01 now aborts if that inverts. Q5 stays
   open — this is a defended inference, not a VEMIO-confirmed fact.
2. **Break-even discount per SKU (Task 2).** Three SKUs already sell under cost on the
   *typical* promoted line, not just in isolated deep-discount episodes: 9304 (mean promo
   discount 0.2129 against break-even 0.1803, cushion −0.0326), 1858 (0.2240/0.2063/−0.0177),
   1857 (0.2235/0.2126/−0.0109). 1875 is a marginal +0.0068 — close enough to flag as a
   near-miss rather than a comfortable no. This is the strongest new business
   recommendation this session produced, because it is a standing structural loss, not a
   one-off episode.
3. **Pricing recommendation, corrected mid-port (DR-0007).** The port's original
   revenue/margin-balanced rule silently voted for the cheapest price in the grid whenever
   demand is elastic enough that revenue has no interior optimum — exactly SKU 1665's case
   (elasticity −4.734). Dropped the degenerate revenue term; the recommended price moves
   from 54.34 to **58.71** (706.6 units/week, $41,485 revenue, $8,771 margin, 21.1% —
   fewer units and more money than the number it replaces). The break-even price was
   re-verified to sit inside the p5–p95 band and recomputed from the simulation grid itself
   at **46.41**, which **supersedes** the "~47" session 2 published — that figure was read
   off the coarse ten-point display table, whose first non-negative row lands at 46.96 (see
   F-011's correction note). Every restatement of the floor now uses 46.41 and rounds **up**
   if it rounds at all: unit cost is 46.30 and the last grid point still losing money is
   46.14, so "46" is inside the loss region.
4. **Combo-level uplift, controlled for concurrency (H-007, DR-0005) — verdict:
   supported.** The port's headline claim — combo 11115 on SKU 1857 reads +50% uplift
   where the episode layer sees only +1% (not significant) — was re-estimated on this
   repository's own pipeline with concurrent combos and a linear trend as controls. Result:
   +989.0 units/week (+48.4%, p = 0.0352), against +1,064.8 (+51.4%, p = 0.0046)
   uncontrolled — 92.9% of the uncontrolled estimate retained, and the rejection condition
   (loses significance at p < 0.05, or falls below half the uncontrolled point estimate)
   was applied exactly as registered and neither clause fired. **This significance is not
   comfortable**: refitting the identical model under different covariance estimators moves
   the p-value from 0.012 (HAC-8) to 0.087 (classical OLS) — the point estimate is stable,
   the significance call is not, and that sensitivity is disclosed in full in
   `reports/05_uplift.md` §4.7 rather than only in the registry. SKU 1283's combo-level
   design is near-collinear (53 of 57 promoted weeks concurrent) and its coefficients are
   not usable as point estimates — reported to illustrate the identification problem, not
   as a finding.
5. **Warehouse allocation (Tasks 7–8).** Stage 06 splits the stage-03 SKU forecast top-down
   by historical warehouse share, guarded against allocating stock to a warehouse that has
   stopped selling. Bodega n. 11 is excluded everywhere: F-013 documents its shutdown as an
   8-month wind-down sitting inside the training window, not a data cut. 51,168 / 33,272 /
   14,185 units for SKUs 1857 / 1283 / 1665, reconciling with stage 03 to under two units by
   construction.
6. **Commercial-context EDA (Task 9, F-012…F-016).** Warehouse network heterogeneity, the
   thin per-customer signal that justifies reading uplift at the network level, and discount
   depth's discrete, largely centrally-set structure — all extending stage 02.
7. **Two defects found while closing this task, both fixed at the source rather than by
   hand-editing a generated artifact:**
   - `reports/03_forecast.md` never received the warehouse-11 caveat despite F-013
     documenting a structural break inside its training window. Added to
     `scripts/03_forecast.py` §4 and regenerated.
   - `reports/04_elasticity.md`'s SKU 1875 callout said its cushion "moved by roughly a
     point across review rounds"; the actual movement was 0.1721 → 0.1732 → 0.1735, about
     0.14 percentage points — an order of magnitude smaller than what the text claimed.
     Fixed in `scripts/04_elasticity.py` and regenerated.
8. **Consolidated finding F-017.** Three separate discount-adjacent defects had surfaced
   across sessions in scattered places: `product_cost` carrying the margin backwards
   (F-003), `bruto` not reflecting combo discounts so the panel's `discount_depth` proxy is
   blind to them (F-004/F-015), and negative `discount` values (F-004). Re-checked the third
   one directly against the raw CSV for this consolidation and found something not
   previously reported: 9,928 of the 10,084 negative-discount rows (98.5%) sit on a single
   SKU, 1283 — 8.33% of that SKU's own rows. Judged that a reader tracing "what is wrong
   with discount" is better served by one index entry than three scattered ones; F-017 does
   not replace F-003/F-004/F-015, it cross-references them.
9. **Registries closed.** Roadmap's outstanding "unit tests for leakage-sensitive helpers"
   item is done — Task 7 delivered `tests/test_allocation.py`, including
   `test_history_after_the_origin_is_never_used`, the leakage guard itself. Q5 stays open by
   design. Both business deliverables rewritten for recommendations 1, 3 (break-even
   discount as a new standing-loss recommendation), 4 (warehouse ordering from the
   allocation table), and 5 (pricing figures), plus the promotional recommendations updated
   to state the H-007 verdict rather than the port's uncontrolled number.

**Judgement calls a reviewer should be able to challenge**

- **F-017 is a judgement call, not a mechanical merge.** The three defects it consolidates
  have different discoverers, different phases, and different downstream consequences; a
  reviewer could reasonably prefer they stay as three independent findings rather than
  gaining a fourth cross-reference entry. The call made here is that a reader asking "can I
  trust the discount field" is better served by one starting point.
- **H-007's verdict rests on one pre-registered covariance estimator (HAC lag 4).** The
  point estimate is stable across every estimator tried; the significance call is not
  (0.012 to 0.087 depending on the estimator). The rejection condition was applied to the
  pre-registered estimator specifically, as written before the test ran — but a reviewer
  who prefers judging significance against a consensus across estimators would reach a
  different, more cautious verdict on the same numbers.
- **The margin-convention check (DR-0006) is now enforced by code, but it still only tests
  sign, not magnitude.** It would catch a reversion to the rejected reading; it would not
  catch a *different* wrong reading that happens to keep free goods negative.
- **Combining stage 06's allocation into a business recommendation assumes warehouse mix is
  stable over the forecast horizon.** The wind-down inside the training window (F-013) is
  direct evidence that mix is not always stable; the allocation table is a snapshot of
  recent history, not a guaranteed future split.

**Changed as a result**

- DR-0006 added; DR-0005 and DR-0007 already existed and are unchanged by this session.
  H-007 carries a verdict (supported, with disclosed significance fragility).
- `reports/03_forecast.md` and `reports/04_elasticity.md` regenerated with the two fixes
  above via `uv run scripts/run_all.py`; every figure in both business deliverables traces
  to a regenerated stage report.
- `docs/ROADMAP.md`'s unit-test item closed; Q5 stays open with the DR-0006 cross-reference
  added.

---

## 2026-08-04 — Session 4: Whole-branch review, and the fixes it forced

**Goal**: review the whole `port/commercial-analysis` branch as a reader would — every
deliverable, every generated report, every registry — and fix what the review found at the
source rather than in the artifact. Thirty-two findings were raised and closed across two
commits, `e69f8c6` and `6e7ae46`. Session 3's "Changed as a result" list predates both and
should not be read as the branch's final state; this entry is.

**Actions**

1. **Formatting and interpretability defects fixed at source (`e69f8c6`).**
   `reporting._fmt` was rendering floats as `:,.4g`, which put scientific notation into
   planner-facing tables ("5.117e+04") across stages 03–06 and printed booleans as 0/1 —
   including `already_below_cost`, the flag business recommendation 1 rests on. Separately,
   `uplift.estimate_combo_effects` was publishing `uplift_pct_vs_intercept` for SKUs whose
   fitted intercept is *negative* (1283, 1665, 1875), which inverts the sign: combo 11032 on
   1665 read −9,358% off a **positive** +6,944 coefficient. A percentage against a negative
   baseline is not interpretable, so the column is now withheld for those SKUs with the
   reason printed. H-007's numbers (1857/1858, positive intercepts) are untouched. Two
   labels were also wrong: 110 combo × SKU pairs were called "distinct combos" (79 exist),
   and 64 (SKU, warehouse) pairs were called "warehouses" in a 12-warehouse network. Every
   stage report was regenerated from the corrected sources.
2. **The margin denominator, ruled on (`6e7ae46`).** The headline data finding said two
   different things depending on where a reader looked: `docs/FINDINGS.md` gave the literal
   loss as −19.4% to −23.1% (over cost), `reports/01_data_quality.md` printed −22% to −30%
   (over revenue), and the prose deliverables quoted 18–23%, a figure no generated artifact
   supported. **Margin over revenue was adopted for money outcomes** — it is what
   `economics.margin_at_price` implements and what the stage reports print — and the
   over-cost reading of the *loss* figure was retired: every document now states the literal
   loss as −22% to −30% and names the denominator where it appears.
3. **Business numbers corrected (`6e7ae46`).** The business document had set **46** as a
   hard promotional price floor — inside the loss region, since unit cost is 46.30 and
   break-even 46.41 — and had rounded that figure down in two further places; every
   statement of the floor now uses 46.41 and rounds up. It also called 21% "the best margin
   available anywhere in the range we tested" (false: the rate peaks at 24.65% at 61.45 —
   the recommendation maximises total profit, not the profit rate, and now says so), quoted
   the unusable 42.87–64.20 raw range as the modelled domain, and shipped per-warehouse
   quantities claiming the allocation "inherits the forecast's own error rather than adding
   a new one" — true of the SKU total, false of a warehouse line whose share is itself
   estimated.
4. **Stale registry and index entries closed (`6e7ae46`).** DR-0006 indexed, stage 06 added
   to `scripts/README.md`, the port spec marked implemented, Phase 1 closed in the roadmap,
   "74 complete weeks" corrected to 72, and the Welch t-test promised in the spec but never
   built formally withdrawn with its reasoning recorded — it cannot condition on concurrent
   combos, and `combo_p_value_sensitivity` already provides the model-dependence check it
   was meant to give. Provenance was added rather than softened: `README.md` states both
   imports on its front page, and Sessions 1–2 here are marked as the baseline author's
   first-person record of work done outside this repository.

**This entry's own correction: the denominator ruling was overstated when it was written.**
Fixing the loss figure was right; the wording that shipped with it was not. Both prose
deliverables came out asserting that *every* margin percentage in the repository is margin
over revenue. That is false, and the repository is not wrong for making it false — it
genuinely reports two quantities that need two denominators. `economics.sku_margin_rates`
returns `product_cost/bruto − 1`, a **markup over cost**, printed as `margin_rate` in
`reports/04_elasticity.md` §3 and §6 and quoted as "22% to 30%" in prose; over revenue those
same margins are 18.0%–23.1% (SKU 1665 at a 60.19 list price against a 46.30 unit cost keeps
23.1%, not 30%). Only the **money outcomes** — margin in currency and margin percentage at a
price, in the simulator and the promotion economics — are over revenue. The blanket claim
also broke its own paragraph: the sentence explaining that applying the margin backwards
turns each product's margin into a loss of the same size is true only when that margin is
read over cost, the opposite of the rule declared two sentences earlier. Both claims are now
replaced by the accurate two-denominator statement, the over-revenue equivalent is given
once where the 22–30% figures first appear in each document, and the coincidence sentence
was **kept and made explicit** rather than cut — it is the observation that made the anomaly
recognisable in the first place, so it now names the denominator on each side ("the markup
over cost with the sign flipped, measured over revenue").

**Judgement calls a reviewer should be able to challenge**

- **Keeping the coincidence sentence is a choice, not a necessity.** Cutting it would have
  removed a reader trap at no cost to the argument. It was kept because the numerical
  coincidence — loss over revenue equals markup over cost — is *how* the inverted export was
  spotted, and a finding that hides its own detection route is harder to audit.
- **The two-denominator convention is honest but not the simplest option.** Converting the
  recovered rates to over-revenue everywhere would leave one convention in the repository.
  That was rejected because the 0.22–0.30 figures have to stay comparable to the data
  dictionary's own "0.20–0.30" band, which is where their credibility comes from.

**Changed as a result**

- `reports/methodology-and-tradeoffs.md` and `reports/technical-walkthrough.md` no longer
  claim a single repository-wide margin denominator; `reports/business-recommendations.md`,
  `docs/FINDINGS.md` (F-003, F-008) and `docs/ROADMAP.md` (Q5) name which denominator each
  figure uses.
- `scripts/04_elasticity.py` labelled its grid excerpt "Every tenth grid point" while
  emitting `grid.iloc[::6]`; corrected to "every sixth" and `reports/04_elasticity.md`
  regenerated. §3 now states in the report itself that `margin_rate` is a markup over cost
  and that the money columns are over revenue. The headline pricing figures are unchanged:
  58.71, 706.6 units, $41,485, 21.1%, break-even 46.41.
- The walkthrough's own grid excerpt is described accurately — every twelfth point plus
  index 54, which is a +6 step, not a twelfth.

---

## 2026-08-04 — Session 5: Bringing both deliverables inside the case statement's stated limits

**Why this mattered.** Section 4 of the case statement sets two explicit limits, and both
written deliverables were outside them. Deliverable 3 asks for **"3 a 5 recomendaciones"**;
`reports/business-recommendations.md` carried seven. Deliverable 2 asks for a **"documento de
1-2 páginas"**; `reports/methodology-and-tradeoffs.md` was 3,411 words, three to six times
that. The evaluation weights make this expensive twice over: *comunicación* (15%) explicitly
rewards "nivel de detalle adecuado a la audiencia", and *pragmatismo* (10%) explicitly
penalises over-engineering for the scope. Missing a stated numeric limit is also the cheapest
possible signal that the brief was not read closely — and no amount of rigor elsewhere buys
that back.

**Seven recommendations to five, by merging what were duplicate findings.** Old 1 (three SKUs
promote below break-even) and old 2 (stop discounting Desodorante 150 ml A) are one finding:
1875's cushion of 0.68% makes it the *marginal case* of old 1's rule, and the 60-week
1875-vs-1665 contrast is that rule seen in a single promotion rather than a portfolio average.
They are now one recommendation about **discount policy**. Old 3 (the best promotion carried
no discount) and old 4 (the March shampoo campaign failed on average but one bundle inside it
worked) are one finding about **promotional mechanics**: non-price mechanics outperformed
discounts, and the March case is the evidence for why evaluation has to happen per combo
rather than per SKU. The remaining three — forecast volumes, warehouse allocation, price
level — were already distinct and are unchanged apart from renumbering.

Nothing that earns marks was dropped in the merge. Every currency and volume figure survives;
so do the SKU 1283 imputation caveat (29.07% null `discount` counted as zero, plus 98.5% of
the dataset's negative-discount rows), the two-sources-of-error statement on the warehouse
lines, the H-007 significance-fragility caution, and the instruction never to round the 46.41
floor down. The closing Q5 caveat block enumerates which recommendations depend on the cost
correction; under the old scheme it read "1, 2, 3, 4 and 7", and it is now **"1, 2 and 5"** —
the merges moved old 3 and 4 into new 2, and old 7 into new 5, while new 3 and 4 carry volume
figures only. That enumeration was the one thing in the document that could silently go wrong
under renumbering, so it was rederived from which recommendations actually quote currency
rather than mapped mechanically.

**Methodology document: 3,411 words to ~1,100.** Cut depth, not honesty. What survives is what
the brief names — the provenance statement (plain, unchanged in substance), assumptions per
challenge, method per challenge in a sentence or two, trade-offs, and what I would do
differently — plus an explicit *Honest limitations* section carrying the five things it would
be convenient to omit: baselines beating the sophisticated models on two of three SKUs, the
sell-in versus sell-out reframe, parallel trends being untestable here, H-007's significance
fragility, and the cost convention being an inference. A pointer to the walkthrough for the
full reasoning now sits in the opening paragraph.

**Cut material was moved, not deleted.** `reports/technical-walkthrough.md` has no length
limit and exists for exactly this, so each removed passage was placed where it belongs in that
document's existing structure and voice: the three-SKU selection rationale and the
point-forecasts-not-intervals limitation into Challenge A; the pre-registered SKU selection
criterion (F-006), the four estimate-limiting risks, and Desodorante's 0.68% cushion as the
marginal case of the break-even rule into Challenge B; the absence of a client-level control
group and the cannibalisation / realised-vs-offered-depth limits into Challenge C; the 74-week
coverage with 72 complete weeks and the exact location of the incomplete-metadata record
(2026-02-18, `bodega n. 6`, client 981302, product 1857) into Phase 1. Passages the
walkthrough already covered — the cost inversion, the discount decoding, WAPE versus MAPE, the
uplift layers, the whole allocation section — were dropped rather than duplicated.

**Judgement calls a reviewer should be able to challenge**

- **Five, not three.** The brief permits either. Five was chosen because each survivor maps to
  a different lever the commercial team actually pulls — discount policy, promotional
  mechanics, forecast volumes, warehouse allocation, price level — and collapsing further
  would have forced unrelated decisions into one heading.
- **The word target was treated as ~1,100, not 900.** Going lower meant cutting either the
  provenance statement or the limitations list, and both are load-bearing for honesty.
- **The allocation section was kept in the short document** even though it is not one of the
  three challenges, because recommendation 4 rests on it and a reviewer reading only the
  1–2 page document would otherwise meet an unexplained deliverable.

**Verification.** `uv run pytest` — 29 passed. `uv run ruff check --no-cache src scripts
tests` — clean. Both unaffected, as expected: no code changed. Every figure retained in the
merge was re-checked against its generated artifact (`reports/04_elasticity.md` §6 for the
cushions and the null-discount share, `reports/05_uplift.md` for the episode economics,
`reports/06_allocation.md` for the warehouse shares) rather than paraphrased from the previous
draft.

---

## 2026-08-04 — Session 6: Translating the two written deliverables into Spanish

**Why this mattered.** The case statement is written in Spanish, and its deliverable 3 names
the audience explicitly: **"3 a 5 recomendaciones de negocio dirigidas al equipo comercial del
cliente, en lenguaje no técnico"**. That team is Spanish-speaking; VEMIO's client base is
LATAM CPG. Both written deliverables were in English, which put a language barrier between the
recommendations and the people meant to act on them — a direct hit on *comunicación* (15%),
whose criterion is "nivel de detalle adecuado a la audiencia", and on *insight de negocio*
(25%), which is graded on whether the results are actionable *for the commercial team*. Rule 8
in `CLAUDE.md` already anticipated this: code, docs and commits in English, business
deliverables may additionally be produced in Spanish.

**What changed.** `reports/business-recommendations.md` and
`reports/methodology-and-tradeoffs.md` are now in Spanish, replacing the English versions
rather than sitting alongside them — two copies of a graded deliverable would immediately
raise which one is authoritative and which one drifts first. Everything else stays in English:
code, docstrings, commits, `reports/technical-walkthrough.md`, the generated `NN_*.md` stage
reports, and everything under `docs/`.

**Written, not rendered.** Both were rewritten in Mexican/LATAM business register rather than
transposed sentence by sentence, and the case statement's own vocabulary is the reference for
terms it names: sell-in, elasticidad de precio, uplift promocional, reabasto, punto de venta,
trade marketing, fuga de información, markup sobre costo. Product names, `bodega n. N`, SKU
codes, column names and artifact filenames are left exactly as the data carries them.

**Numbers were copied, never reformatted.** Mexico uses the period as decimal separator and
the comma for thousands — identical to the convention already in the files — so reformatting
would have bought nothing and risked breaking traceability against the generated artifacts.
Verified mechanically: every numeric token in both files was extracted and diffed against the
English versions at `HEAD`, and both diffs are empty. That covers 58.71, 46.41, 45.32–61.45,
42.87–64.20, the WAPE figures, the p-value range, and every cushion and discount depth.

**What was protected from being smoothed away in translation.** Several passages exist because
a reviewer forced them, and translation is exactly where that kind of thing quietly softens:
the provenance statement naming the two other authors (translated plainly, not made vague);
the Q5 caveat block and its enumeration of which recommendations depend on the cost
correction; the instruction never to round the 46.41 floor down; the margin **value** versus
margin **rate** distinction in the pricing recommendation; the SKU 1283 imputation caveat and
the allocation's two-sources-of-error statement; and all six honest limitations in the
methodology document.

**The Q5 enumeration was re-derived, not carried over.** It reads **"1, 2 y 5"**. Recommendation
order is unchanged by the translation, and the check is which recommendations actually quote a
currency figure: 1 (the 42,000 / 76,000 contrast and the 2.37-vs-5.41 per-unit margins), 2 (the
235,000, 48,000, 67,000, 35,000 and 33,000 episode results) and 5 (41,500 revenue, 8,800 gross
profit, the 46.41 floor). Recommendations 3 and 4 carry volume figures only. Unchanged, and
correct for the same reason as before.

**Length.** The methodology document is **1,337 words**, against 1,124 in English — a 19%
expansion, within the normal Spanish-to-English ratio and still inside the case's "1-2
páginas". Nothing from the must-survive list was cut to get there; the prose was tightened
instead.

**Cross-references updated** so nothing mislabels the language: `README.md`,
`docs/README.md`, `reports/README.md`, `docs/ROADMAP.md` and `reports/technical-walkthrough.md`
now say which documents are in Spanish and why. `reports/README.md` gained a Language column.
Filenames are unchanged, so no link moved.

**Verification.** `uv run pytest` — 29 passed. `uv run ruff check --no-cache src scripts tests`
— clean. Both expected to be unaffected: no code changed, and no script reads either
deliverable.
