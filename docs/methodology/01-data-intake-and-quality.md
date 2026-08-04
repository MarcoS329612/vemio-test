# Standard 01 — Data intake & quality audit

Goal: know exactly what the data is, how much to trust it, and leave a paper trail
for every cleaning decision. Bad data handled silently is the fastest way to a
confident wrong answer.

## 1. Intake checklist

Before any analysis:

- [ ] **Provenance**: where did the file come from, when, and is it immutable in `data/raw/`?
- [ ] **Grain check**: confirm what one row represents by *testing* it (e.g., is
  `ticket_code × product_code` unique? if not, why?). Never trust the stated grain — verify it.
- [ ] **Dictionary vs reality**: for every column, compare the documented meaning with
  observed dtype, range, cardinality, and null rate. Flag mismatches.
- [ ] **Coverage**: date range continuity (missing days/weeks?), entity coverage
  (all warehouses/SKUs present over the whole period, or do some appear/disappear?).
- [ ] **Reconciliation**: do derived columns reconcile (e.g., does `amount ≈ bruto − discount`?
  does `margin` behave as documented)? Quantify the % of rows where they don't.

## 2. Quality audit dimensions

Quantify each issue — counts and % of rows/value affected — before deciding anything:

| Dimension | Typical checks |
|---|---|
| Completeness | Nulls per column; rows with incomplete metadata |
| Validity | Zero/negative quantities or amounts; impossible dates; out-of-range values |
| Uniqueness | Duplicate rows; duplicate keys at the stated grain |
| Consistency | Cross-column reconciliation; same entity spelled differently |
| Distribution | Outliers (define the rule: e.g., robust z-score / IQR at the modeling grain) |

## 3. Cleaning decision rules

Every cleaning action follows this protocol:

1. **State the rule** — e.g., "exclude rows with `sell_in_quantity == 0` from demand models".
2. **Quantify the impact** — rows affected, % of volume/revenue affected, per SKU if relevant.
3. **Choose an action** with rationale — exclude, impute, cap, or keep-and-flag. Prefer
   **keep-and-flag** (boolean columns like `is_zero_qty`) over deletion, so downstream
   steps choose their own filters.
4. **Log it** in the cleaning decision log (table below) inside the data-quality report.
5. If the choice materially affects results, test sensitivity to it in Phase 5.

Cleaning decision log format:

| # | Rule | Rows affected (% ) | Action | Rationale | Downstream impact |
|---|---|---|---|---|---|

### Anti-patterns (explicitly banned)

- `dropna()` without a logged reason and count.
- Overwriting raw files or mutating `data/raw/`.
- "Over-cleaning": removing outliers that are real business events (e.g., promo spikes are
  signal, not noise, in a promo-uplift analysis).
- Imputation that leaks the future (e.g., filling a gap with the series mean computed over
  the full period, then forecasting on it).

## 4. Artifacts

- **Data-quality report**: `scripts/01_data_audit.py` → `reports/01_data_quality.md`,
  containing the issues found with counts, the cleaning decision log table, and the
  parameters the run used.
- **Processed dataset(s)** in `data/processed/` with a reproducible build path
  (raw → committed code → processed), including flag columns.
- **Registry updates**: verified issues → `FINDINGS.md`; suspected ones → `HYPOTHESES.md`;
  cleaning rules that materially change volumes → a decision record.
