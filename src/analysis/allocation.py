"""Top-down allocation of a SKU forecast to warehouses.

The forecast is national because that is where the data supports a stable
model (stage 03); the order is per warehouse because that is where stock
physically ships. Splitting by historical share is the standard CPG move:
simple, auditable, and wrong in a way a planner can see and override.

Two guards matter more than the arithmetic. Shares are fitted strictly before
the forecast origin, because a share computed over the forecast window is the
same leakage the modelling standard forbids everywhere else — and it would be
invisible in the output, not a crash. And a warehouse that has stopped selling
is excluded rather than allocated its historical share: one warehouse in this
dataset winds down gradually over months during the training window, which
looks like a live warehouse in aggregate history right up until it stops.
Sending it stock on that history is exactly the failure this stage exists to
prevent, so the exclusion is recorded in `excluded_reason` rather than left
for a planner to discover after the fact.
"""

from __future__ import annotations

import pandas as pd


def warehouse_shares(
    frame: pd.DataFrame,
    origin: pd.Timestamp,
    lookback_weeks: int = 52,
    dead_warehouse_weeks: int = 8,
) -> pd.DataFrame:
    """Share of each SKU's units by warehouse, from pre-origin history only.

    ``lookback_weeks`` bounds the history window so a share reflects the
    network's current shape rather than warehouses that mattered years ago.
    ``dead_warehouse_weeks`` is the silence period after which a warehouse
    with no sales inside the window is treated as gone rather than merely
    quiet: it keeps its row here (`share = 0.0`, `excluded_reason` stated) so
    the exclusion is visible to `allocate` and to anyone reading this table,
    rather than the warehouse just disappearing.
    """
    window_start = origin - pd.Timedelta(weeks=lookback_weeks)
    history = frame[
        frame["usable_for_demand"] & frame["date"].lt(origin) & frame["date"].ge(window_start)
    ]

    totals = (
        history.groupby(["product_code", "warehouse"])["sell_in_quantity"]
        .sum()
        .reset_index(name="units")
    )

    cutoff = origin - pd.Timedelta(weeks=dead_warehouse_weeks)
    last_sale = history.groupby("warehouse")["date"].max()
    dead = set(last_sale[last_sale.lt(cutoff)].index)

    totals["excluded_reason"] = totals["warehouse"].map(
        lambda w: f"no sales in the {dead_warehouse_weeks} weeks before the origin"
        if w in dead
        else None
    )

    live = totals["excluded_reason"].isna()
    live_totals = totals[live].groupby("product_code")["units"].transform("sum")
    totals["share"] = 0.0
    totals.loc[live, "share"] = (totals.loc[live, "units"] / live_totals).round(6)

    return totals.sort_values(["product_code", "share"], ascending=[True, False]).reset_index(
        drop=True
    )


def allocate(forecast: pd.DataFrame, shares: pd.DataFrame) -> pd.DataFrame:
    """Split a long-format SKU forecast across live warehouses by their share.

    ``forecast`` must carry ``week_start``, ``product_code`` and ``units``.
    Excluded warehouses (`excluded_reason` set) are dropped here — they carry
    `share = 0.0` in ``shares`` precisely so this join never sends them stock.
    """
    live = shares.loc[shares["excluded_reason"].isna(), ["product_code", "warehouse", "share"]]
    merged = forecast.merge(live, on="product_code", how="inner")
    merged["units"] = (merged["units"] * merged["share"]).round(1)
    return (
        merged[["week_start", "product_code", "warehouse", "units"]]
        .sort_values(["product_code", "week_start", "warehouse"])
        .reset_index(drop=True)
    )
