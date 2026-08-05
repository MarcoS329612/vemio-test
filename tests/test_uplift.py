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


def test_mixed_week_denominator_is_whole_week_units():
    """A week where combo A covers only part of the volume, the rest unpromoted.

    If the share denominator were computed over promoted-only volume instead of
    the whole week, A's share here would read 1.0 (40 promoted units / 40
    promoted units) instead of the correct 0.4 (40 / 100 total). The earlier
    fixtures never mixed promoted and non-promoted rows in the same week, so an
    implementation with this bug would still pass them.
    """
    rows = [
        ("2025-01-06", "A", 40.0, True),
        ("2025-01-06", None, 60.0, False),
    ]
    frame = pd.DataFrame(
        {
            "product_code": ["1857"] * len(rows),
            "date": pd.to_datetime([r[0] for r in rows]),
            "id_combo": [r[1] for r in rows],
            "sell_in_quantity": [r[2] for r in rows],
            "is_promo": [r[3] for r in rows],
            "usable_for_demand": [True] * len(rows),
        }
    )

    matrix = uplift.combo_week_matrix(frame, "1857")

    week = pd.Timestamp("2025-01-06")
    assert matrix.loc[week, "A"] == pytest.approx(0.4)
    assert matrix.loc[week, "units"] == 100.0


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


@pytest.fixture
def autocorrelated_effects() -> pd.DataFrame:
    """The same overlapping design, but with a modest effect and AR(1) noise.

    `overlapping_effects` is deliberately near-noiseless so the coefficients can be
    asserted tightly — which makes every estimator return p ≈ 0 there, and a
    sensitivity table that cannot move is no test of a sensitivity table. Serial
    correlation in the residual is exactly the condition HAC exists to handle, so
    this is the fixture where classical and HAC errors genuinely disagree.
    """
    rng = np.random.default_rng(0)
    weeks = pd.date_range("2025-01-06", periods=40, freq="7D")

    innovations = rng.normal(0.0, 80.0, len(weeks))
    noise, previous = np.zeros(len(weeks)), 0.0
    for i, innovation in enumerate(innovations):
        previous = 0.6 * previous + innovation
        noise[i] = previous

    rows = []
    for i, week in enumerate(weeks):
        a, b = 5 <= i < 20, 12 <= i < 25
        units = 500.0 + 30.0 * a + 50.0 * b + noise[i]
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


def test_sensitivity_table_spans_classical_and_hac_estimators(autocorrelated_effects):
    """Disclosure aid for H-007: does not change the specified estimate, just shows
    a reader how the p-value moves under alternative error-structure assumptions."""
    table = uplift.combo_p_value_sensitivity(autocorrelated_effects, "1857", "A")

    assert table["estimator"].iloc[0] == "classical OLS (non-robust)"
    assert "HAC maxlags=4" in table["estimator"].to_numpy()
    assert table["p_value"].between(0.0, 1.0).all()
    # The point of the table is that the p-value *moves* with the estimator. Without
    # this, an implementation that returned the same constant for every row — the
    # exact failure the disclosure exists to rule out — would still pass.
    distinct_p_values = table["p_value"].nunique()
    assert distinct_p_values > 1
