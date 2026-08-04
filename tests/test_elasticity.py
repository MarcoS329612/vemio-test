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


def _toy_grid() -> pd.DataFrame:
    """A small grid with an interior margin peak, isolated from any real regression.

    Used to exercise `recommend_price`'s degeneracy check directly: revenue = price *
    units scales as price^(1 + elasticity) under the constant-elasticity form, so
    whether an interior revenue optimum can exist depends only on the elasticity
    argument, not on this grid's shape.
    """
    return pd.DataFrame(
        {
            "price": [10.0, 20.0, 30.0, 40.0],
            "units": [100.0, 50.0, 30.0, 20.0],
            "revenue": [1000.0, 1000.0, 900.0, 800.0],
            "margin_value": [200.0, 400.0, 450.0, 380.0],
            "margin_pct": [0.2, 0.4, 0.5, 0.475],
            "unit_cost": [8.0, 8.0, 8.0, 8.0],
        }
    )


def test_recommend_price_flags_the_degenerate_revenue_objective():
    """elasticity < -1 means 1 + elasticity < 0: revenue has no interior optimum at all.

    Must fail against a version that silently reports the grid's revenue argmax as if
    it were a genuine optimum.
    """
    grid = _toy_grid()
    result = elasticity.recommend_price(grid, elasticity=-4.734)

    assert result["revenue_has_interior_optimum"] is False
    # The boundary figure is still surfaced, just marked rather than hidden.
    assert result["revenue_max_price"] == grid.loc[grid["revenue"].idxmax(), "price"]


def test_recommend_price_reports_an_interior_optimum_when_demand_is_inelastic():
    """elasticity > -1 means 1 + elasticity > 0: an interior revenue optimum can exist."""
    grid = _toy_grid()
    result = elasticity.recommend_price(grid, elasticity=-0.5)

    assert result["revenue_has_interior_optimum"] is True


def _toy_grid_with_distinct_optima() -> pd.DataFrame:
    """A grid whose revenue/margin balanced price differs from its margin-only optimum.

    Needed to prove DR-0007's rule actually switches which row gets recommended, not
    merely that a flag changes: the balanced price (price 20, driven partly by revenue)
    and the margin-only price (price 30, the true margin peak) must disagree here.
    """
    return pd.DataFrame(
        {
            "price": [10.0, 20.0, 30.0],
            "units": [10.0, 4.5, 1.67],
            "revenue": [100.0, 90.0, 50.0],
            "margin_value": [10.0, 40.0, 42.0],
            "margin_pct": [0.1, 0.44, 0.84],
            "unit_cost": [9.0, 9.0, 9.0],
        }
    )


def test_recommend_price_drops_the_revenue_term_when_degenerate():
    """DR-0007: once revenue has no interior optimum, the recommendation is the
    margin-maximising price outright, not the revenue-weighted balance — even though the
    two pick different rows here. The contaminated average is still disclosed under
    `balanced_price`, just no longer promoted to `recommended_price`.
    """
    grid = _toy_grid_with_distinct_optima()
    result = elasticity.recommend_price(grid, elasticity=-4.734)

    assert result["recommendation_rule"] == "margin_only"
    assert result["recommended_price"] == result["margin_max_price"] == 30.0
    assert result["balanced_price"] == 20.0
    assert result["recommended_price"] != result["balanced_price"]


def test_recommend_price_uses_the_balanced_rule_when_revenue_is_well_posed():
    """When an interior revenue optimum exists, the classic balanced rule still applies."""
    grid = _toy_grid_with_distinct_optima()
    result = elasticity.recommend_price(grid, elasticity=-0.5)

    assert result["recommendation_rule"] == "revenue_margin_balance"
    assert result["recommended_price"] == result["balanced_price"] == 20.0
