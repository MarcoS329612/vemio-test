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
