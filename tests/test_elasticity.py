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
