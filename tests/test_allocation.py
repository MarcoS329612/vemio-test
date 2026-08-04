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


def test_allocate_raises_for_a_forecast_sku_with_no_live_warehouse(network):
    """A SKU absent from `shares` must not silently vanish from the output.

    An inner merge would drop it with no warning, breaking the total the
    function otherwise preserves. A planner who asked for this SKU must get
    an error, not a quietly incomplete allocation.
    """
    shares = allocation.warehouse_shares(network, origin=ORIGIN)
    forecast = pd.DataFrame(
        {
            "week_start": [pd.Timestamp("2026-06-01")],
            "product_code": ["9999"],
            "units": [500.0],
        }
    )
    with pytest.raises(ValueError, match="9999"):
        allocation.allocate(forecast, shares)


def test_dead_warehouse_check_is_per_sku_not_network_wide():
    """A warehouse dead for one SKU but live for another is excluded only for
    the dead one.

    Computing the last-sale cutoff across all products would judge W11 by its
    activity on SKU "1665" and wrongly keep it alive — with a share — for
    SKU "1857", even though the returned frame and `excluded_reason` are
    presented per SKU.
    """
    weeks = pd.date_range("2025-06-02", periods=52, freq="7D")
    rows = []
    for week in weeks:
        rows.append(("1857", "W6", week, 300.0))
        rows.append(("1857", "W3", week, 100.0))
        if week < pd.Timestamp("2025-12-01"):
            rows.append(("1857", "W11", week, 200.0))
        # W11 keeps selling SKU 1665 all the way to the origin.
        rows.append(("1665", "W6", week, 150.0))
        rows.append(("1665", "W11", week, 50.0))
    frame = pd.DataFrame(
        {
            "product_code": [r[0] for r in rows],
            "warehouse": [r[1] for r in rows],
            "date": [r[2] for r in rows],
            "sell_in_quantity": [r[3] for r in rows],
            "usable_for_demand": [True] * len(rows),
        }
    )

    shares = allocation.warehouse_shares(frame, origin=ORIGIN)

    dead_1857 = shares[(shares["product_code"] == "1857") & (shares["warehouse"] == "W11")].iloc[
        0
    ]
    live_1665 = shares[(shares["product_code"] == "1665") & (shares["warehouse"] == "W11")].iloc[
        0
    ]

    assert dead_1857["excluded_reason"] is not None
    assert dead_1857["share"] == 0.0
    assert live_1665["excluded_reason"] is None
    assert live_1665["share"] > 0.0
