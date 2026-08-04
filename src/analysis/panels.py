"""Aggregation to the decision grain.

The three challenges all consume the same weekly SKU panel, built once here
(standard 02). Building it twice is how a forecast and an elasticity estimate
end up quietly disagreeing about what a week is.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Weeks run Monday–Sunday. The data has no Sunday sales, so a "complete" week is
# defined by calendar span rather than by observed selling days.
WEEK_FREQ = "W-SUN"


def _week_bounds(period: pd.PeriodIndex) -> tuple[pd.Series, pd.Series]:
    return period.start_time, period.end_time


def build_weekly_sku_panel(frame: pd.DataFrame) -> pd.DataFrame:
    """Weekly units, revenue and promo intensity per SKU.

    Only rows flagged ``usable_for_demand`` contribute: zero-quantity rows carry
    no demand signal, and including them would depress nothing while adding
    noise to the price columns.

    Partial weeks at the start and end of the history are marked, not dropped —
    a truncated first week looks like a demand collapse to any model that sees it.
    """
    usable = frame[frame["usable_for_demand"]].copy()
    usable["week"] = usable["date"].dt.to_period(WEEK_FREQ)

    grouped = usable.groupby(["product_code", "product_name", "week"], observed=True)
    panel = grouped.agg(
        units=("sell_in_quantity", "sum"),
        net_amount=("sell_in_amount", "sum"),
        gross_amount=("bruto", "sum"),
        cost=("product_cost", "sum"),
        tickets=("ticket_code", "nunique"),
        clients=("client_code", "nunique"),
        warehouses=("warehouse", "nunique"),
        promo_units=("sell_in_quantity", lambda s: float(
            s.where(usable.loc[s.index, "is_promo"], 0).sum()
        )),
    ).reset_index()

    panel["week_start"], panel["week_end"] = _week_bounds(
        pd.PeriodIndex(panel["week"], freq=WEEK_FREQ)
    )

    first_date, last_date = usable["date"].min(), usable["date"].max()
    panel["is_complete_week"] = (
        panel["week_start"].ge(first_date) & panel["week_end"].le(last_date)
    )

    # Realised price, not list price: F-004 showed `discount` does not reconcile
    # row by row, so the only trustworthy price is revenue over units.
    panel["avg_net_price"] = panel["net_amount"] / panel["units"]
    panel["avg_list_price"] = panel["gross_amount"] / panel["units"]
    panel["discount_depth"] = 1 - panel["avg_net_price"] / panel["avg_list_price"]
    panel["promo_share"] = panel["promo_units"] / panel["units"]

    panel["week_index"] = (
        panel["week_start"] - panel["week_start"].min()
    ).dt.days // 7
    panel["month"] = panel["week_start"].dt.month
    panel["week_of_year"] = panel["week_start"].dt.isocalendar().week.astype(int)

    return panel.sort_values(["product_code", "week_start"]).reset_index(drop=True)


def build_promo_calendar(frame: pd.DataFrame, min_units: float = 500.0) -> pd.DataFrame:
    """Reconstruct when each combo ran, on which SKU, and how deep the discount was.

    Challenge C needs promo *windows*, which the transaction table only implies.
    Combos below ``min_units`` are kept in the table but will not survive the
    uplift selection — too small for an effect to be separable from noise.
    """
    promo = frame[frame["is_promo"] & frame["usable_for_demand"]].copy()
    promo["week"] = promo["date"].dt.to_period(WEEK_FREQ)

    grouped = promo.groupby(["id_combo", "combo", "product_code", "product_name"])
    calendar = grouped.agg(
        first_date=("date", "min"),
        last_date=("date", "max"),
        weeks=("week", "nunique"),
        units=("sell_in_quantity", "sum"),
        net_amount=("sell_in_amount", "sum"),
        gross_amount=("bruto", "sum"),
        clients=("client_code", "nunique"),
        warehouses=("warehouse", "nunique"),
    ).reset_index()

    calendar["duration_days"] = (
        calendar["last_date"] - calendar["first_date"]
    ).dt.days + 1
    calendar["discount_depth"] = 1 - calendar["net_amount"] / calendar["gross_amount"]
    calendar["units_per_week"] = calendar["units"] / calendar["weeks"].clip(lower=1)
    calendar["is_material"] = calendar["units"].ge(min_units)

    return calendar.sort_values("units", ascending=False).reset_index(drop=True)


def weekly_series(panel: pd.DataFrame, product_code: str) -> pd.DataFrame:
    """Complete-week series for one SKU, indexed by week start."""
    series = panel[
        panel["product_code"].eq(product_code) & panel["is_complete_week"]
    ].copy()
    return series.sort_values("week_start").reset_index(drop=True)


def seasonal_naive(values: np.ndarray, horizon: int, season: int) -> np.ndarray:
    """Repeat the last full season forward — the baseline every model must beat."""
    if len(values) < season:
        return np.repeat(values[-1], horizon)
    tail = values[-season:]
    return np.array([tail[i % season] for i in range(horizon)])


def moving_average(values: np.ndarray, horizon: int, window: int = 4) -> np.ndarray:
    """Flat forecast at the mean of the last ``window`` observations."""
    level = float(np.mean(values[-window:]))
    return np.repeat(level, horizon)
