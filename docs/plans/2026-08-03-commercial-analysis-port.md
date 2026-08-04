# Commercial-Analysis Port — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port five capabilities from an independent solution to the same VEMIO case into this repository, under full integration — where the ported method is better it replaces what is here and the affected figures are recomputed.

**Architecture:** Every capability lands in the existing `src/analysis/` library and is surfaced by an existing stage script, except warehouse allocation, which is a new stage 06 because it consumes the published forecast rather than producing it. `run_all.py` discovers `NN_*.py` by name, so stage 06 needs no registration. This is the first work in the repository to carry unit tests; `tests/` is created in Task 1.

**Tech Stack:** Python ≥3.11, uv, pandas, numpy, statsmodels, matplotlib, pytest. No new runtime dependencies.

**Spec:** `docs/specs/2026-08-03-commercial-analysis-port.md`

## Global Constraints

- **No new runtime dependencies.** StatsForecast/Nixtla is explicitly out of scope. `pyproject.toml` `dependencies` must not grow.
- **Run everything with `uv run`.** Never `pip` — this venv has no pip.
- **English everywhere** — code, docstrings, docs, commit messages (CLAUDE.md rule 8).
- **ruff**: `line-length = 100`, lint rules `E, F, I, UP, B, SIM, PD`.
- **No future leakage.** Any statistic used at prediction time is computed on history strictly prior to the forecast origin (working rule 2).
- **Flags, not deletions.** Cleaning decisions add boolean columns; rows are never dropped (working rule 3).
- **Registries before code where the rule demands it.** H-007 is registered with its rejection condition *before* the combo model is ever run (working rule 4). This is why Task 4 precedes Task 6.
- **Provenance is declared.** These methods come from a separate solution to the same case, authored outside this repository. The worklog entry names that origin.
- Margin convention is fixed and already implemented: `unit_cost = bruto / (1 + margin)`, `margin = product_cost/bruto - 1`. Everything needing margin goes through `economics.py`.
- Work on a branch. The commit history of this repository is graded; do not commit directly to `master`.

## File Structure

**Created:**
- `tests/conftest.py` — shared synthetic fixtures (weekly panel, transaction frame)
- `tests/test_economics.py` — margin convention, break-even discount
- `tests/test_elasticity.py` — observed-range guard
- `tests/test_uplift.py` — combo matrix, combo-effect identification
- `tests/test_allocation.py` — share construction, leakage, dead-warehouse exclusion
- `src/analysis/allocation.py` — top-down warehouse allocation
- `scripts/06_allocation.py` — stage 06 entry point
- `reports/06_allocation.md` — stage 06 artifact
- `docs/decisions/DR-0005-uplift-unit-of-analysis.md`
- `docs/decisions/DR-0006-margin-convention.md`

**Modified:**
- `src/analysis/quality.py` — add `check_margin_convention`
- `src/analysis/economics.py` — add `break_even_discount`
- `src/analysis/elasticity.py` — add `observed_price_band`, `predict_units` guard, `simulate` band clipping (currently `elasticity.py:128`)
- `src/analysis/uplift.py` — add `combo_week_matrix`, `estimate_combo_effects`
- `scripts/01_data_audit.py` — surface the convention check
- `scripts/02_eda.py` — commercial context sections
- `scripts/04_elasticity.py` — price band table, break-even discount table
- `scripts/05_uplift.py` — combo-effect layer
- `docs/HYPOTHESES.md`, `docs/FINDINGS.md`, `docs/WORKLOG.md`, `docs/AI_USAGE_LOG.md`, `docs/ROADMAP.md`
- `reports/business-recommendations.md`, `reports/methodology-and-tradeoffs.md`

---

### Task 1: Test scaffolding and the margin-convention check

The convention is currently argued in a docstring and defended by F-003, but nothing fails if it is wrong. Free-goods lines are the discriminating case: units shipped at a realised price of zero inside a combo. Under the adopted reading they carry a negative margin equal to their cost. Under the rejected reading (`product_cost` as a distributor list price) they carry the full reference price as positive margin, making giveaways the most profitable transactions in the dataset.

**Files:**
- Create: `tests/conftest.py`, `tests/test_economics.py`
- Modify: `src/analysis/quality.py`, `scripts/01_data_audit.py`

**Interfaces:**
- Consumes: `economics.sku_margin_rates(frame) -> DataFrame[product_code, product_name, margin_rate, rows, in_documented_band]`
- Produces: `quality.check_margin_convention(frame, rates) -> dict` with keys `free_goods_rows`, `free_goods_units`, `adopted_margin`, `rejected_margin`, `passes`

- [ ] **Step 1: Create the branch**

```bash
git checkout -b port/commercial-analysis
```

- [ ] **Step 2: Write the shared fixtures**

Create `tests/conftest.py`:

```python
"""Synthetic fixtures.

Small hand-built frames, not samples of the real data: a test that depends on
the 77 MB input is a test nobody runs.
"""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def transactions() -> pd.DataFrame:
    """Four lines for one SKU with a 25% markup, one of them free goods.

    `product_cost` is built as `bruto * (1 + margin)`, which is what the
    delivered file actually contains (F-003).
    """
    margin = 0.25
    gross = [1000.0, 800.0, 600.0, 500.0]
    net = [1000.0, 680.0, 480.0, 0.0]  # last line is bonus product
    return pd.DataFrame(
        {
            "product_code": ["1665"] * 4,
            "product_name": ["Antitranspirante 150 ml C"] * 4,
            "date": pd.to_datetime(
                ["2025-01-06", "2025-01-13", "2025-01-20", "2025-01-27"]
            ),
            "sell_in_quantity": [20.0, 16.0, 12.0, 10.0],
            "sell_in_amount": net,
            "bruto": gross,
            "product_cost": [g * (1 + margin) for g in gross],
            "is_promo": [False, True, True, True],
            "usable_for_demand": [True] * 4,
            "usable_for_price": [True, True, True, False],
        }
    )
```

- [ ] **Step 3: Write the failing test**

Create `tests/test_economics.py`:

```python
from analysis import economics, quality


def test_recovered_margin_rate_matches_the_constructed_markup(transactions):
    rates = economics.sku_margin_rates(transactions)
    assert rates.loc[0, "margin_rate"] == 0.25
    assert bool(rates.loc[0, "in_documented_band"])


def test_free_goods_carry_a_negative_margin_under_the_adopted_reading(transactions):
    rates = economics.sku_margin_rates(transactions)
    result = quality.check_margin_convention(transactions, rates)

    assert result["free_goods_rows"] == 1
    assert result["free_goods_units"] == 10.0
    # Giving product away costs money.
    assert result["adopted_margin"] < 0
    # The rejected reading would make giveaways the most profitable lines.
    assert result["rejected_margin"] > 0
    assert result["passes"] is True
```

- [ ] **Step 4: Run it and confirm it fails**

Run: `uv run pytest tests/test_economics.py -v`
Expected: FAIL — `AttributeError: module 'analysis.quality' has no attribute 'check_margin_convention'`

- [ ] **Step 5: Implement the check**

Append to `src/analysis/quality.py`:

```python
def check_margin_convention(
    frame: pd.DataFrame, rates: pd.DataFrame
) -> dict[str, object]:
    """Verify the adopted cost reading against free-goods lines.

    The reading in `economics.py` is an inference (F-003, open question Q5), so
    it is checked rather than only asserted. Lines shipped at a realised price
    of zero inside a combo are the discriminating case: under the adopted
    reading they lose money, which is what giving product away does. Under the
    rejected reading — `product_cost` as a distributor list price, margin as
    list minus sell-in — they book the full reference price as profit, which
    would make giveaways the most profitable transactions in the file.
    """
    free = frame[
        frame["sell_in_quantity"].gt(0)
        & frame["sell_in_amount"].le(0)
        & frame["bruto"].gt(0)
    ]
    if free.empty:
        return {
            "free_goods_rows": 0,
            "free_goods_units": 0.0,
            "adopted_margin": float("nan"),
            "rejected_margin": float("nan"),
            "passes": False,
        }

    lookup = rates.set_index("product_code")["margin_rate"]
    markup = free["product_code"].map(lookup)

    adopted_cost = free["bruto"] / (1.0 + markup)
    adopted = float((free["sell_in_amount"] - adopted_cost).sum())
    rejected = float((free["product_cost"] - free["sell_in_amount"]).sum())

    return {
        "free_goods_rows": int(len(free)),
        "free_goods_units": float(free["sell_in_quantity"].sum()),
        "adopted_margin": round(adopted, 2),
        "rejected_margin": round(rejected, 2),
        "passes": bool(adopted < 0 < rejected),
    }
```

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_economics.py -v`
Expected: PASS, 2 tests

- [ ] **Step 7: Surface it in stage 01**

In `scripts/01_data_audit.py`, after the existing cost/margin section, add a
subsection that calls `quality.check_margin_convention(flagged, rates)` and
writes the four numbers into the report with a one-line verdict. If `passes`
is `False`, raise `SystemExit` with the message
`"Margin convention check failed: free goods do not lose money under the adopted reading"` —
a silent pass here would let every currency figure downstream be wrong.

- [ ] **Step 8: Regenerate the stage-01 artifact**

Run: `uv run scripts/01_data_audit.py`
Expected: completes, `reports/01_data_quality.md` gains the convention-check section, `passes` is true on the real data.

- [ ] **Step 9: Commit**

```bash
git add tests/ src/analysis/quality.py scripts/01_data_audit.py reports/01_data_quality.md
git commit -m "Verify the margin convention against free-goods lines"
```

---

### Task 2: Break-even discount for all six SKUs

`reports/04_elasticity.md` reports a break-even *price* for one SKU. The same unit economics give the maximum discount depth each SKU absorbs before its realised price falls under cost — expressed in the lever the commercial team actually moves.

**Files:**
- Modify: `src/analysis/economics.py`, `scripts/04_elasticity.py`
- Test: `tests/test_economics.py`

**Interfaces:**
- Consumes: `economics.sku_margin_rates`, `economics.unit_cost_from_list(list_price, margin_rate) -> float`
- Produces: `economics.break_even_discount(rates) -> DataFrame[product_code, product_name, margin_rate, break_even_discount]`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_economics.py`:

```python
def test_break_even_discount_is_the_markup_identity(transactions):
    rates = economics.sku_margin_rates(transactions)
    table = economics.break_even_discount(rates)

    # margin / (1 + margin) — 0.25 / 1.25
    assert table.loc[0, "break_even_discount"] == 0.2


def test_at_the_break_even_discount_price_equals_cost(transactions):
    rates = economics.sku_margin_rates(transactions)
    depth = float(economics.break_even_discount(rates).loc[0, "break_even_discount"])

    list_price = 50.0
    cost = economics.unit_cost_from_list(list_price, 0.25)
    assert list_price * (1 - depth) == pytest.approx(cost)
```

Add `import pytest` at the top of the file.

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_economics.py -v`
Expected: FAIL — `AttributeError: module 'analysis.economics' has no attribute 'break_even_discount'`

- [ ] **Step 3: Implement it**

Append to `src/analysis/economics.py`:

```python
def break_even_discount(rates: pd.DataFrame) -> pd.DataFrame:
    """Deepest discount each SKU absorbs before selling under cost.

    With cost = list / (1 + m), the realised price equals cost when the depth
    reaches m / (1 + m). Stated as depth rather than as a price because depth is
    the lever the commercial team actually sets, and it is comparable across
    SKUs whose absolute prices differ by an order of magnitude.
    """
    table = rates[["product_code", "product_name", "margin_rate"]].copy()
    table["break_even_discount"] = (
        table["margin_rate"] / (1.0 + table["margin_rate"])
    ).round(4)
    return table.sort_values("break_even_discount").reset_index(drop=True)
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_economics.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Add the comparison to stage 04**

In `scripts/04_elasticity.py`, build a table joining `economics.break_even_discount(rates)` to each SKU's mean observed `discount_depth` from the weekly panel, with a column `already_below_cost = mean_discount_depth > break_even_discount`. Write it into `reports/04_elasticity.md` under a heading "Break-even discount by SKU". Any SKU flagged `True` is a standing loss, not an occasional one — call that out in the surrounding prose.

- [ ] **Step 6: Regenerate and read the artifact**

Run: `uv run scripts/04_elasticity.py`
Expected: completes; the new table appears. Record which SKUs come back `True` — Task 10 needs them for the business recommendations.

- [ ] **Step 7: Commit**

```bash
git add src/analysis/economics.py scripts/04_elasticity.py tests/test_economics.py reports/
git commit -m "Add break-even discount per SKU"
```

---

### Task 3: Observed-price-band guard (p5–p95)

The brief forbids extrapolating outside the observed price range, and `simulate` currently bounds the grid with the raw min and max (`elasticity.py:128`). Those extremes are not prices: the floor is free bonus product inside combos and the ceiling is a handful of records where net exceeds gross and the implied discount is negative. The band must be p5–p95 of weekly price, and `predict_units` must refuse anything outside it.

**Files:**
- Modify: `src/analysis/elasticity.py`, `scripts/04_elasticity.py`
- Test: `tests/test_elasticity.py`

**Interfaces:**
- Consumes: `elasticity.weekly_price_panel`, `elasticity.estimate_elasticity`
- Produces: `elasticity.observed_price_band(data, low_q=0.05, high_q=0.95) -> tuple[float, float]`; `predict_units` gains keyword `band: tuple[float, float] | None = None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_elasticity.py`:

```python
import numpy as np
import pandas as pd
import pytest

from analysis import elasticity


@pytest.fixture
def price_weeks() -> pd.DataFrame:
    """40 weeks of clean prices around 50, plus one broken week at 400."""
    rng = np.random.default_rng(0)
    prices = np.concatenate([np.linspace(45.0, 55.0, 39), [400.0]])
    units = 10_000 / prices * rng.uniform(0.95, 1.05, len(prices))
    weeks = pd.date_range("2025-01-06", periods=len(prices), freq="7D")
    return pd.DataFrame(
        {
            "week_start": weeks,
            "price": prices,
            "list_price": prices * 1.1,
            "units": units,
            "week_of_year": weeks.isocalendar().week.astype(int),
            "t": np.arange(len(prices)),
        }
    )


def test_band_excludes_the_broken_extreme(price_weeks):
    low, high = elasticity.observed_price_band(price_weeks)
    assert high < 100.0
    assert low >= price_weeks["price"].min()


def test_predict_units_refuses_a_price_outside_the_band(price_weeks):
    fit = elasticity.estimate_elasticity(price_weeks)
    band = elasticity.observed_price_band(price_weeks)

    with pytest.raises(ValueError, match="outside the observed price band"):
        elasticity.predict_units(fit, price_weeks, 400.0, band=band)


def test_simulate_grid_stays_inside_the_band(price_weeks):
    fit = elasticity.estimate_elasticity(price_weeks)
    low, high = elasticity.observed_price_band(price_weeks)
    grid = elasticity.simulate(fit, price_weeks, margin_rate=0.25)

    assert grid["price"].min() >= round(low, 2) - 0.01
    assert grid["price"].max() <= round(high, 2) + 0.01
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_elasticity.py -v`
Expected: FAIL — `AttributeError: module 'analysis.elasticity' has no attribute 'observed_price_band'`

- [ ] **Step 3: Implement the band**

Add to `src/analysis/elasticity.py`, above `predict_units`:

```python
def observed_price_band(
    data: pd.DataFrame, low_q: float = 0.05, high_q: float = 0.95
) -> tuple[float, float]:
    """The price range the simulator is allowed to answer within.

    Not the raw min and max: the floor of the realised-price distribution is
    bonus product shipped inside a combo and the ceiling is records where net
    exceeds gross, so both tails are artefacts rather than prices anyone set.
    Quantiles keep the band inside the evidence.
    """
    return (
        float(data["price"].quantile(low_q)),
        float(data["price"].quantile(high_q)),
    )
```

- [ ] **Step 4: Add the guard to `predict_units`**

Change the signature to
`def predict_units(fit, data, price, fourier_order=2, band=None) -> float:`
and insert immediately after the docstring:

```python
    if band is not None and not (band[0] <= price <= band[1]):
        raise ValueError(
            f"Price {price:.2f} is outside the observed price band "
            f"[{band[0]:.2f}, {band[1]:.2f}]. The case forbids extrapolating "
            "beyond observed prices, and a constant-elasticity curve past the "
            "data is arithmetic, not evidence."
        )
```

- [ ] **Step 5: Clip the simulator grid to the band**

In `simulate`, replace
`low, high = float(data["price"].min()), float(data["price"].max())`
with
`low, high = observed_price_band(data)`
and pass `band=(low, high)` through to the `predict_units` call inside the loop.

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_elasticity.py -v`
Expected: PASS, 3 tests

- [ ] **Step 7: Publish the band and check the effect on the headline**

In `scripts/04_elasticity.py`, write a per-SKU table of `observed_price_band` into `reports/04_elasticity.md` under "Price range with evidence behind it", stating that the simulator refuses prices outside it.

Run: `uv run scripts/04_elasticity.py`

The break-even price for SKU 1665 was 47 against a raw range of 42.87–64.20. Compare the new figure. **If the break-even price now falls outside the p5–p95 band, that is a finding, not a bug** — it would mean the break-even was only reachable in the artefact tail. Record it either way for Task 10.

- [ ] **Step 8: Commit**

```bash
git add src/analysis/elasticity.py scripts/04_elasticity.py tests/test_elasticity.py reports/
git commit -m "Bound the price simulator by the p5-p95 observed band"
```

---

### Task 4: Register H-007 and DR-0005 before any combo code is written

Working rule 4: a claim that could change a decision enters `HYPOTHESES.md` with its rejection condition written *first*. Task 6 tests whether the ported combo-level result survives control for concurrency. Registering afterwards would make the rejection condition unfalsifiable in practice.

**Files:**
- Modify: `docs/HYPOTHESES.md`
- Create: `docs/decisions/DR-0005-uplift-unit-of-analysis.md`

- [ ] **Step 1: Add H-007**

Append to `docs/HYPOTHESES.md`, matching the existing entry format (H-001…H-006 are the template):

> **H-007 — Combo-level uplift survives control for concurrent combos.**
> Status: `testing`.
> The ported analysis estimates uplift per `id_combo` and finds SKU 1857 averaging +1% (not significant) while combo n.33 inside it reads +50% (p ≈ 0.011). This repository's episode approach was chosen because combos overlap on the same SKU. The claim under test is that the combo-level effect is real and not an artefact of other combos running in the same weeks.
> **Rejection condition:** rejected if the combo that reads +50% uncontrolled loses significance at p < 0.05 once concurrent combos and a linear trend enter the model, or if its point estimate falls below half of the uncontrolled estimate.
> Concurrency pressure differs by SKU: 31 combos across 57 promotional weeks on SKU 1283, but only 9 across 31 on SKU 1857, where the result lives. So the objection is real but not obviously fatal to this specific estimate.

- [ ] **Step 2: Write DR-0005**

Create `docs/decisions/DR-0005-uplift-unit-of-analysis.md` following the shape of `docs/decisions/DR-0000-template.md`. Decision: estimate at combo level with concurrent combos as controls, keeping episodes as a second layer. Alternatives that lost:
- **Episodes alone** — measures combined promotional pressure, which is a real quantity, but masks mechanic-level heterogeneity; a SKU averaging +1% can contain a combo at +50%.
- **Uncontrolled combo-level** — right unit, but contaminated when combos overlap, and on this dataset they demonstrably do.

Consequence: the two layers answer different questions and both are reported, with what each one measures stated.

- [ ] **Step 3: Commit**

```bash
git add docs/HYPOTHESES.md docs/decisions/DR-0005-uplift-unit-of-analysis.md
git commit -m "Register H-007 and DR-0005 before testing combo-level uplift"
```

---

### Task 5: Weekly combo-activity matrix

The regression in Task 6 needs one indicator column per combo per week. `panels.build_promo_calendar` gives combo windows but not weekly activity, so this is new.

**Files:**
- Modify: `src/analysis/uplift.py`
- Test: `tests/test_uplift.py`

**Interfaces:**
- Consumes: `panels.WEEK_FREQ`; a flagged transaction frame with `id_combo`, `is_promo`, `usable_for_demand`
- Produces: `uplift.combo_week_matrix(frame, product_code) -> DataFrame` indexed by `week_start`, one column per `id_combo` holding that combo's share of the week's units, plus a `units` column

- [ ] **Step 1: Write the failing test**

Create `tests/test_uplift.py`:

```python
import numpy as np
import pandas as pd
import pytest

from analysis import uplift


@pytest.fixture
def combo_frame() -> pd.DataFrame:
    """Three weeks: combo A alone, then A and B together, then nothing."""
    rows = [
        ("2025-01-06", "A", 100.0, True),
        ("2025-01-13", "A", 60.0, True),
        ("2025-01-13", "B", 40.0, True),
        ("2025-01-20", None, 80.0, False),
    ]
    return pd.DataFrame(
        {
            "product_code": ["1857"] * len(rows),
            "date": pd.to_datetime([r[0] for r in rows]),
            "id_combo": [r[1] for r in rows],
            "sell_in_quantity": [r[2] for r in rows],
            "is_promo": [r[3] for r in rows],
            "usable_for_demand": [True] * len(rows),
        }
    )


def test_matrix_records_both_concurrent_combos(combo_frame):
    matrix = uplift.combo_week_matrix(combo_frame, "1857")

    week = pd.Timestamp("2025-01-13")
    assert matrix.loc[week, "A"] == pytest.approx(0.6)
    assert matrix.loc[week, "B"] == pytest.approx(0.4)
    assert matrix.loc[week, "units"] == 100.0


def test_unpromoted_week_is_all_zeros(combo_frame):
    matrix = uplift.combo_week_matrix(combo_frame, "1857")

    week = pd.Timestamp("2025-01-20")
    assert matrix.loc[week, "A"] == 0.0
    assert matrix.loc[week, "B"] == 0.0
    assert matrix.loc[week, "units"] == 80.0
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_uplift.py -v`
Expected: FAIL — `AttributeError: module 'analysis.uplift' has no attribute 'combo_week_matrix'`

- [ ] **Step 3: Implement it**

Append to `src/analysis/uplift.py` (add `from . import panels` to the imports):

```python
def combo_week_matrix(frame: pd.DataFrame, product_code: str) -> pd.DataFrame:
    """Weekly activity of every combo on one SKU.

    Each column holds the combo's share of that week's units rather than a 0/1
    flag: a combo touching 5% of a week is not the same treatment as one
    touching 90%, and a binary indicator would force the regression to pretend
    it is.
    """
    rows = frame[
        frame["product_code"].eq(product_code) & frame["usable_for_demand"]
    ].copy()
    rows["week_start"] = (
        rows["date"].dt.to_period(panels.WEEK_FREQ).dt.start_time
    )

    weekly_units = rows.groupby("week_start")["sell_in_quantity"].sum()

    promo = rows[rows["is_promo"] & rows["id_combo"].notna()].copy()
    # `id_combo` arrives as a float in the raw file. Cast once, so column names
    # and the regression's parameter index agree with the report labels.
    promo["id_combo"] = promo["id_combo"].astype(str)
    by_combo = (
        promo.groupby(["week_start", "id_combo"])["sell_in_quantity"]
        .sum()
        .unstack(fill_value=0.0)
    )

    matrix = by_combo.reindex(weekly_units.index, fill_value=0.0)
    matrix = matrix.div(weekly_units, axis=0).fillna(0.0)
    matrix["units"] = weekly_units
    return matrix.sort_index()
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_uplift.py -v`
Expected: PASS, 2 tests

- [ ] **Step 5: Commit**

```bash
git add src/analysis/uplift.py tests/test_uplift.py
git commit -m "Add weekly combo-activity matrix"
```

---

### Task 6: Combo-effect regression and the H-007 verdict

Fit, per SKU:

```
units_t = g0 + g1 * t + sum_k gk * combo_share_k,t + e
```

Each `gk` is net of secular trend and net of every other combo active in the same weeks. The Welch t-test is kept alongside for combos with a clean unpromoted control window, as a non-parametric contrast that does not depend on the linear form.

**Files:**
- Modify: `src/analysis/uplift.py`, `scripts/05_uplift.py`
- Test: `tests/test_uplift.py`

**Interfaces:**
- Consumes: `uplift.combo_week_matrix`
- Produces: `uplift.estimate_combo_effects(frame, product_code, min_weeks=3) -> DataFrame[id_combo, coefficient, std_error, p_value, weeks_active, weeks_concurrent, uplift_pct_vs_intercept]`

- [ ] **Step 1: Write the failing identification test**

Append to `tests/test_uplift.py`:

```python
@pytest.fixture
def overlapping_effects() -> pd.DataFrame:
    """Combo A adds 100 units/week, combo B adds 50, and they overlap.

    Baseline is a flat 500 plus small noise. A always takes exactly 50% of the
    week's units and B exactly 30%, so the share regressors are `0.5 * 1[A]` and
    `0.3 * 1[B]` and the true coefficients are 100/0.5 = 200 and 50/0.3 = 166.7.
    Recovering both means the estimator separated overlapping combos, which is
    the whole point of the design. Noise keeps the fit from being singular.
    """
    rng = np.random.default_rng(0)
    weeks = pd.date_range("2025-01-06", periods=30, freq="7D")
    noise = rng.normal(0.0, 5.0, len(weeks))

    rows = []
    for i, week in enumerate(weeks):
        a, b = 5 <= i < 20, 12 <= i < 25
        units = 500.0 + 100.0 * a + 50.0 * b + noise[i]
        if a:
            rows.append((week, "A", units * 0.5, True))
        if b:
            rows.append((week, "B", units * 0.3, True))
        rows.append((week, None, units * (1.0 - 0.5 * a - 0.3 * b), False))

    return pd.DataFrame(
        {
            "product_code": ["1857"] * len(rows),
            "date": [r[0] for r in rows],
            "id_combo": [r[1] for r in rows],
            "sell_in_quantity": [r[2] for r in rows],
            "is_promo": [r[3] for r in rows],
            "usable_for_demand": [True] * len(rows),
        }
    )


def test_each_combo_recovers_its_own_effect(overlapping_effects):
    effects = uplift.estimate_combo_effects(overlapping_effects, "1857").set_index(
        "id_combo"
    )

    assert set(effects.index) == {"A", "B"}
    assert effects.loc["A", "coefficient"] == pytest.approx(200.0, abs=10.0)
    assert effects.loc["B", "coefficient"] == pytest.approx(166.7, abs=10.0)


def test_concurrent_weeks_are_reported(overlapping_effects):
    effects = uplift.estimate_combo_effects(overlapping_effects, "1857").set_index(
        "id_combo"
    )
    # A runs weeks 5-19, B runs 12-24: eight weeks overlap.
    assert effects.loc["A", "weeks_concurrent"] == 8
    assert effects.loc["B", "weeks_concurrent"] == 8
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_uplift.py -v`
Expected: FAIL — `AttributeError: module 'analysis.uplift' has no attribute 'estimate_combo_effects'`

- [ ] **Step 3: Implement it**

Append to `src/analysis/uplift.py` (add `import statsmodels.api as sm` to the imports):

```python
def estimate_combo_effects(
    frame: pd.DataFrame, product_code: str, min_weeks: int = 3
) -> pd.DataFrame:
    """Per-combo uplift, net of trend and of every concurrent combo.

    Aggregating to the SKU destroys mechanic-level signal — a SKU averaging
    +1% can contain one combo at +50% and several at zero. Estimating per combo
    without controls has the opposite failure: overlapping combos each take
    credit for the same units. Entering every combo simultaneously with a trend
    term is what separates them, and `weeks_concurrent` says how much of each
    estimate rests on weeks it had to share.
    """
    matrix = combo_week_matrix(frame, product_code)
    combos = [c for c in matrix.columns if c != "units"]

    active = matrix[combos].gt(0)
    eligible = [c for c in combos if int(active[c].sum()) >= min_weeks]
    if not eligible:
        return pd.DataFrame(
            columns=[
                "id_combo", "coefficient", "std_error", "p_value",
                "weeks_active", "weeks_concurrent", "uplift_pct_vs_intercept",
            ]
        )

    design = matrix[eligible].copy()
    design["t"] = np.arange(len(matrix)) / 52.0
    x = sm.add_constant(design)
    model = sm.OLS(matrix["units"], x).fit(
        cov_type="HAC", cov_kwds={"maxlags": 4}
    )

    intercept = float(model.params["const"])
    others = active[eligible]
    rows = []
    for combo in eligible:
        weeks_active = int(others[combo].sum())
        concurrent = int((others[combo] & others.drop(columns=combo).any(axis=1)).sum())
        coefficient = float(model.params[combo])
        rows.append(
            {
                "id_combo": combo,
                "coefficient": round(coefficient, 1),
                "std_error": round(float(model.bse[combo]), 1),
                "p_value": round(float(model.pvalues[combo]), 4),
                "weeks_active": weeks_active,
                "weeks_concurrent": concurrent,
                "uplift_pct_vs_intercept": round(coefficient / intercept * 100, 1)
                if intercept else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values("coefficient", ascending=False).reset_index(
        drop=True
    )
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_uplift.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Add the combo layer to stage 05**

In `scripts/05_uplift.py`, after the existing episode section, add a "Combo-level effects" section per eligible SKU calling `uplift.estimate_combo_effects(flagged, code)`. Write the table into `reports/05_uplift.md` and state in prose what the two layers measure: episodes are combined promotional pressure on a SKU, combo effects are the marginal contribution of one mechanic net of the others.

- [ ] **Step 6: Run it and record the H-007 verdict**

Run: `uv run scripts/05_uplift.py`

Find combo n.33 on SKU 1857 in the output. Apply the rejection condition from H-007 exactly as written: rejected if p ≥ 0.05, or if the coefficient falls below half the uncontrolled +50%. Update `docs/HYPOTHESES.md` with the verdict and the numbers behind it.

**A rejection is a result and gets published.** It would mean the ported headline was concurrency, and saying so is worth more than deleting the section.

- [ ] **Step 7: Commit**

```bash
git add src/analysis/uplift.py scripts/05_uplift.py tests/test_uplift.py docs/HYPOTHESES.md reports/
git commit -m "Estimate combo-level uplift net of concurrent combos, resolving H-007"
```

---

### Task 7: Warehouse allocation module

A SKU-level national forecast is not an order. Top-down allocation by historical share turns it into one.

**Files:**
- Create: `src/analysis/allocation.py`
- Test: `tests/test_allocation.py`

**Interfaces:**
- Consumes: a flagged transaction frame with `product_code`, `warehouse`, `date`, `sell_in_quantity`, `usable_for_demand`
- Produces:
  - `allocation.warehouse_shares(frame, origin, lookback_weeks=52, dead_warehouse_weeks=8) -> DataFrame[product_code, warehouse, units, share, excluded_reason]`
  - `allocation.allocate(forecast, shares) -> DataFrame[week_start, product_code, warehouse, units]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_allocation.py`:

```python
import pandas as pd
import pytest

from analysis import allocation


@pytest.fixture
def network() -> pd.DataFrame:
    """Two live warehouses plus one that stops selling halfway through."""
    weeks = pd.date_range("2025-06-02", periods=52, freq="7D")
    rows = []
    for week in weeks:
        rows.append((week, "W6", 300.0))
        rows.append((week, "W3", 100.0))
        if week < pd.Timestamp("2025-12-01"):
            rows.append((week, "W11", 200.0))
    return pd.DataFrame(
        {
            "product_code": ["1857"] * len(rows),
            "warehouse": [r[1] for r in rows],
            "date": [r[0] for r in rows],
            "sell_in_quantity": [r[2] for r in rows],
            "usable_for_demand": [True] * len(rows),
        }
    )


ORIGIN = pd.Timestamp("2026-06-01")


def test_shares_sum_to_one_per_sku(network):
    shares = allocation.warehouse_shares(network, origin=ORIGIN)
    live = shares[shares["excluded_reason"].isna()]
    assert float(live["share"].sum()) == pytest.approx(1.0)


def test_dead_warehouse_is_excluded_with_a_stated_reason(network):
    shares = allocation.warehouse_shares(network, origin=ORIGIN)
    dead = shares[shares["warehouse"].eq("W11")].iloc[0]

    assert dead["share"] == 0.0
    assert "no sales" in dead["excluded_reason"]


def test_history_after_the_origin_is_never_used(network):
    """A share fitted over the forecast window is leakage."""
    future = network.copy()
    future["date"] = future["date"] + pd.Timedelta(days=730)
    future["warehouse"] = "W99"
    combined = pd.concat([network, future], ignore_index=True)

    shares = allocation.warehouse_shares(combined, origin=ORIGIN)
    assert "W99" not in set(shares["warehouse"])


def test_allocation_preserves_the_sku_total(network):
    shares = allocation.warehouse_shares(network, origin=ORIGIN)
    forecast = pd.DataFrame(
        {
            "week_start": [pd.Timestamp("2026-06-01")],
            "product_code": ["1857"],
            "units": [1000.0],
        }
    )
    allocated = allocation.allocate(forecast, shares)
    assert allocated["units"].sum() == pytest.approx(1000.0)
```

- [ ] **Step 2: Run them and confirm they fail**

Run: `uv run pytest tests/test_allocation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'analysis.allocation'`

- [ ] **Step 3: Implement the module**

Create `src/analysis/allocation.py`:

```python
"""Top-down allocation of a SKU forecast to warehouses.

The forecast is national because that is where the data supports a stable
model; the order is per warehouse because that is where stock physically goes.
Splitting by historical share is the standard CPG move: simple, auditable, and
wrong in a way a planner can see and override.

Two guards matter more than the arithmetic. Shares are fitted strictly before
the forecast origin, because a share computed over the forecast window is the
same leakage the modelling standard forbids. And a warehouse that has stopped
selling is excluded rather than allocated its historical share — warehouse 11
winds down during the training window, and sending it stock is exactly the
failure this stage exists to prevent.
"""

from __future__ import annotations

import pandas as pd


def warehouse_shares(
    frame: pd.DataFrame,
    origin: pd.Timestamp,
    lookback_weeks: int = 52,
    dead_warehouse_weeks: int = 8,
) -> pd.DataFrame:
    """Share of each SKU's units by warehouse, from pre-origin history only."""
    window_start = origin - pd.Timedelta(weeks=lookback_weeks)
    history = frame[
        frame["usable_for_demand"]
        & frame["date"].lt(origin)
        & frame["date"].ge(window_start)
    ]

    totals = (
        history.groupby(["product_code", "warehouse"])["sell_in_quantity"]
        .sum()
        .reset_index(name="units")
    )

    cutoff = origin - pd.Timedelta(weeks=dead_warehouse_weeks)
    last_sale = history.groupby("warehouse")["date"].max()
    dead = set(last_sale[last_sale < cutoff].index)

    totals["excluded_reason"] = totals["warehouse"].map(
        lambda w: f"no sales in the {dead_warehouse_weeks} weeks before the origin"
        if w in dead
        else None
    )

    live = totals["excluded_reason"].isna()
    live_totals = totals[live].groupby("product_code")["units"].transform("sum")
    totals["share"] = 0.0
    totals.loc[live, "share"] = (totals.loc[live, "units"] / live_totals).round(6)

    return totals.sort_values(
        ["product_code", "share"], ascending=[True, False]
    ).reset_index(drop=True)


def allocate(forecast: pd.DataFrame, shares: pd.DataFrame) -> pd.DataFrame:
    """Split a long-format SKU forecast across warehouses.

    ``forecast`` must carry ``week_start``, ``product_code`` and ``units``.
    """
    live = shares[shares["excluded_reason"].isna()][
        ["product_code", "warehouse", "share"]
    ]
    merged = forecast.merge(live, on="product_code", how="inner")
    merged["units"] = (merged["units"] * merged["share"]).round(1)
    return merged[["week_start", "product_code", "warehouse", "units"]].sort_values(
        ["product_code", "week_start", "warehouse"]
    ).reset_index(drop=True)
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_allocation.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Commit**

```bash
git add src/analysis/allocation.py tests/test_allocation.py
git commit -m "Add top-down warehouse allocation with leakage and dead-warehouse guards"
```

---

### Task 8: Stage 06 — the allocation artifact

**Files:**
- Create: `scripts/06_allocation.py`, `reports/06_allocation.md`
- Modify: none

**Interfaces:**
- Consumes: `allocation.warehouse_shares`, `allocation.allocate`, `reports/03_forecast_next_12_weeks.csv`, `analysis.reporting.MarkdownReport`, `analysis.plotting`

- [ ] **Step 1: Inspect the forecast artifact's shape**

Run: `uv run python -c "import pandas as pd; d=pd.read_csv('reports/03_forecast_next_12_weeks.csv'); print(d.head()); print(d.dtypes)"`

The stage-03 report renders it wide (`week_start` plus one column per SKU). Confirm before writing the reader; if it is wide, melt it to long `week_start, product_code, units` — `allocate` expects long format.

- [ ] **Step 2: Write the stage script**

Create `scripts/06_allocation.py`. `MarkdownReport` is a fluent builder — `heading`, `text`, `table`, `note`, `key_values`, `write(filename, params)` — and `write` stamps the run metadata and input checksum into the header automatically.

```python
"""Stage 06 — Warehouse allocation of the SKU forecast.

    uv run scripts/06_allocation.py

Output: reports/06_allocation.md

Runs after stage 03 because it consumes the published forecast rather than
producing one. Allocation is a layer on top of the model, not part of it.
"""

from __future__ import annotations

import pandas as pd

from analysis import allocation, cleaning, config, io
from analysis.reporting import MarkdownReport

LOOKBACK_WEEKS = 52
FORECAST_CSV = "03_forecast_next_12_weeks.csv"


def load_forecast() -> pd.DataFrame:
    """Read stage 03's artifact as long-format week_start/product_code/units."""
    wide = pd.read_csv(config.REPORTS_DIR / FORECAST_CSV)
    long = wide.melt(
        id_vars="week_start", var_name="product_code", value_name="units"
    )
    long["week_start"] = pd.to_datetime(long["week_start"])
    long["product_code"] = long["product_code"].astype(str)
    return long.dropna(subset=["units"])


def main(lookback_weeks: int = LOOKBACK_WEEKS) -> None:
    raw = io.load_raw_transactions()
    flagged, _ = cleaning.flag_records(raw)

    forecast = load_forecast()
    origin = forecast["week_start"].min()

    shares = allocation.warehouse_shares(
        flagged, origin=origin, lookback_weeks=lookback_weeks
    )
    allocated = allocation.allocate(forecast, shares)

    csv_path = config.REPORTS_DIR / "06_allocation_by_warehouse.csv"
    allocated.to_csv(csv_path, index=False)

    excluded = shares[shares["excluded_reason"].notna()]

    report = MarkdownReport(
        title="Stage 06 — Warehouse allocation",
        stage="scripts/06_allocation.py",
        subtitle=(
            "The stage-03 forecast is national because that is the grain the data "
            "supports. Stock ships per warehouse, so it is split by historical "
            "share — simple, auditable, and wrong in a way a planner can see."
        ),
    )

    report.heading("1. Share basis")
    report.key_values(
        {
            "Forecast origin": origin.date().isoformat(),
            "Lookback window": f"{lookback_weeks} weeks before the origin",
            "Warehouses in the share base": int((shares["share"] > 0).sum()),
            "Warehouses excluded": int(len(excluded)),
        }
    )
    report.note(
        "Shares are fitted strictly before the forecast origin. A share computed "
        "over the forecast window is the same future leakage the modelling "
        "standard forbids, and it would be invisible in the output."
    )

    report.heading("2. Shares by SKU and warehouse")
    report.table(shares)

    if not excluded.empty:
        report.heading("3. Excluded warehouses")
        report.table(excluded[["warehouse", "units", "excluded_reason"]])
        report.note(
            "A warehouse that stopped selling still carries historical volume. "
            "Allocating it stock on that history is exactly the failure this "
            "stage exists to prevent."
        )

    report.heading("4. Weekly allocation")
    report.text(
        "The planner-facing output: units to send, per SKU, per warehouse, per "
        f"week. Full table in `{csv_path.name}`."
    )
    report.table(allocated.head(40))

    report.heading("5. What this assumes")
    report.bullets(
        [
            "Warehouse mix is stable over the horizon — the wind-down inside the "
            "training window shows that is not guaranteed.",
            "Top-down cannot discover warehouse-level demand shifts the national "
            "forecast does not contain.",
            "Allocated totals reconcile to the SKU forecast by construction, so "
            "they inherit its error, roughly a quarter of volume per week.",
        ]
    )

    path = report.write("06_allocation.md", params={"lookback_weeks": lookback_weeks})
    print(f"Wrote {path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
```

Check `scripts/05_uplift.py`'s `argparse` block and mirror it if the other stages expose CLI parameters; keep the signature of `main` either way.

- [ ] **Step 3: Run it**

Run: `uv run scripts/06_allocation.py`
Expected: completes; `reports/06_allocation.md` and the CSV exist; excluded warehouses are listed with reasons; per-SKU allocated totals match the stage-03 totals (51,200 / 33,300 / 14,200 units respectively, to rounding).

- [ ] **Step 4: Verify the runner discovers it**

`run_all.py` finds stages by globbing `[0-9][0-9]_*.py`, so no registration is needed — but confirm the glob actually sees it rather than assuming:

Run: `uv run python -c "from pathlib import Path; print([p.name for p in sorted(Path('scripts').glob('[0-9][0-9]_*.py'))])"`
Expected: `06_allocation.py` appears last in the list, after `05_uplift.py`.

- [ ] **Step 5: Commit**

```bash
git add scripts/06_allocation.py reports/06_allocation.md reports/06_allocation_by_warehouse.csv
git commit -m "Add stage 06: warehouse allocation of the SKU forecast"
```

---

### Task 9: Commercial context in stage 02

Stage 02 covers levels, concentration, temporal and price structure per SKU. It does not cover the network, the customer base, or the structure of the discount itself.

**Files:**
- Modify: `scripts/02_eda.py`, `reports/02_eda.md`
- Create: figures under `reports/figures/` with the `02_` prefix

- [ ] **Step 1: Add the five sections**

Extend `scripts/02_eda.py` so `reports/02_eda.md` gains:

1. **Warehouse network** — per warehouse: routes, clients, revenue, revenue per client, and revenue share. Include the top product per warehouse.
2. **Warehouse 11 shutdown** — last sale date per warehouse, plus monthly ticket counts for the wind-down showing it is gradual, not a data cut. State that this is a structural break inside the training window.
3. **Customer base** — distribution of purchase frequency and basket length, and the consequence for Challenge C: a low-frequency customer makes uplift a network-level effect, not a per-customer one.
4. **Discount structure** — the frequency table of realised discount depths showing discrete levels rather than a continuum, the 100% group identified as bonus product, and the within-client dispersion of depth for clients with ≥10 discounted lines (near zero ⇒ discount is not client-specific).
5. **No control group** — weekly realised price per warehouse for a promoted SKU, showing price drops are simultaneous across all twelve rather than staggered. This is the identification diagnostic that rules out difference-in-differences for Challenge C.

- [ ] **Step 2: Run it**

Run: `uv run scripts/02_eda.py`
Expected: completes; new sections and figures appear.

- [ ] **Step 3: Record the findings**

Add to `docs/FINDINGS.md`, continuing from F-011 (so F-012 onward), one entry per section with its evidence. The two that change how existing results should be read:
- the warehouse-11 structural break, which belongs in the stage-03 forecast caveats
- the absence of a control group, which stage 05 currently assumes without evidence

Cross-reference the second one from `reports/05_uplift.md`.

- [ ] **Step 4: Commit**

```bash
git add scripts/02_eda.py reports/02_eda.md reports/figures/ docs/FINDINGS.md reports/05_uplift.md
git commit -m "Add commercial context and the identification diagnostic to stage 02"
```

---

### Task 10: Registries, decision records, and deliverable refresh

**Files:**
- Create: `docs/decisions/DR-0006-margin-convention.md`
- Modify: `docs/WORKLOG.md`, `docs/AI_USAGE_LOG.md`, `docs/ROADMAP.md`, `docs/FINDINGS.md`, `reports/business-recommendations.md`, `reports/methodology-and-tradeoffs.md`, `README.md`

- [ ] **Step 1: Write DR-0006**

Create `docs/decisions/DR-0006-margin-convention.md`. The convention has been implemented since the first modelling stage but has no decision record. Decision: `unit_cost = bruto / (1 + margin)`. Alternatives that lost:
- **Taking `product_cost` literally** — makes every transaction loss-making, contradicting the documented 20–30% margin band.
- **`product_cost` as a distributor list price, margin = list − sell-in** — fails the free-goods test from Task 1: giveaways would book the full reference price as profit, and deeper discounts would report more margin.

Cite the Task 1 check as the evidence and note that Q5 stays open — this is a defended inference, not a verified fact.

- [ ] **Step 2: Update the business recommendations**

Rewrite the affected parts of `reports/business-recommendations.md`:
- **New recommendation** from Task 2: any SKU whose mean discount depth already exceeds its own break-even discount is a standing loss. Use the SKUs recorded in Task 2 Step 6.
- **New recommendation** from Tasks 7–8: order by warehouse using the allocation table, with warehouse 11 excluded and why.
- **Recommendation 5** (`break-even price near 47`): update if Task 3 Step 7 moved it once the band excludes the artefact tail.
- **The promotional recommendations**: reflect the H-007 verdict from Task 6. If combo-level effects survived, name the specific mechanics. If they did not, say the SKU-level reading stands and why the combo-level result did not survive.

Keep the document's existing voice: no jargon, currency figures flagged as dependent on the cost correction.

- [ ] **Step 3: Update the methodology document**

In `reports/methodology-and-tradeoffs.md`, add the two-layer uplift design (episodes and combo effects, what each measures), the p5–p95 band and why the raw range is not usable, and the top-down allocation with its two guards.

- [ ] **Step 4: Update the registries**

- `docs/ROADMAP.md`: mark the ported capabilities done, keep Q5 open, and close the outstanding "unit tests for leakage-sensitive helpers" item — Task 7 delivers exactly that.
- `docs/WORKLOG.md`: one session entry. State the provenance explicitly — these methods come from a separate, independently authored solution to the same case. Record the H-007 verdict and the judgement calls a reviewer should be able to challenge.
- `docs/AI_USAGE_LOG.md`: the AI contribution to this session.
- `README.md`: add stage 06 to the stage table, and update the headline results for anything Tasks 2, 3 and 6 changed.

- [ ] **Step 5: Full reproduction from raw data**

Run: `uv run pytest -v`
Expected: PASS, 15 tests across four files.

Run: `uv run scripts/run_all.py`
Expected: all six stages complete in order; every artifact in `reports/` regenerates. This is the definition-of-done check — a number in a deliverable that does not survive this run is a number that does not reproduce.

Run: `uv run ruff check src scripts tests`
Expected: no violations.

- [ ] **Step 6: Commit**

```bash
git add docs/ reports/ README.md
git commit -m "Close the registries and refresh both deliverables after the port"
```

---

## Definition of Done

- `uv run pytest -v` passes, 15 tests.
- `uv run scripts/run_all.py` completes on a clean environment with only the raw file in place.
- `uv run ruff check src scripts tests` is clean.
- Stage 01 fails loudly if the margin convention is violated.
- H-007 carries a verdict, whichever way it went.
- DR-0005 and DR-0006 exist.
- Every currency figure in `reports/` traces to `economics.py`.
- `pyproject.toml` `dependencies` is unchanged.
