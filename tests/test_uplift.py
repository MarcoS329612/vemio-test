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
