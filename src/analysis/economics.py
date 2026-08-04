"""Unit economics: reconstructing cost and margin.

`product_margin` is not in the delivered file and `product_cost` is inconsistent
with a profitable business (findings F-001 and F-003). Everything that needs a
margin goes through here, so the assumption is stated once and can be switched
in one place if VEMIO answers open question Q5.
"""

from __future__ import annotations

import pandas as pd

# Reading adopted for the deliverable, pending Q5. The dictionary describes
# `product_margin` as a markup over cost, so list price = cost x (1 + margin)
# and therefore cost = list price / (1 + margin). The delivered `product_cost`
# equals list price x (1 + margin) — the same factor, applied the wrong way.
ASSUMED_READING = "cost = bruto / (1 + margin), with margin = product_cost/bruto - 1"


def sku_margin_rates(frame: pd.DataFrame) -> pd.DataFrame:
    """Recover the per-SKU markup implied by `product_cost` and `bruto`.

    F-003 established this ratio is exactly constant within each SKU and lands
    inside the 0.20–0.30 band the dictionary documents, which is what makes the
    reconstruction defensible rather than convenient.
    """
    usable = frame[frame["bruto"].gt(0) & frame["product_cost"].gt(0)]
    grouped = usable.groupby(["product_code", "product_name"])
    rates = pd.DataFrame(
        {
            "margin_rate": (grouped["product_cost"].sum() / grouped["bruto"].sum()) - 1,
            "rows": grouped.size(),
        }
    ).reset_index()
    rates["margin_rate"] = rates["margin_rate"].round(4)
    rates["in_documented_band"] = rates["margin_rate"].between(0.20, 0.30)
    return rates


def margin_rate_for(rates: pd.DataFrame, product_code: str) -> float:
    row = rates.loc[rates["product_code"].eq(product_code), "margin_rate"]
    if row.empty:
        raise KeyError(f"No margin rate recovered for SKU {product_code}")
    return float(row.iloc[0])


def unit_cost_from_list(list_price: float, margin_rate: float) -> float:
    """Acquisition cost per unit under the adopted reading."""
    return list_price / (1.0 + margin_rate)


def margin_at_price(
    price: float, units: float, unit_cost: float
) -> tuple[float, float, float]:
    """Return (revenue, margin in currency, margin as a share of revenue)."""
    revenue = price * units
    margin_value = (price - unit_cost) * units
    margin_pct = margin_value / revenue if revenue else float("nan")
    return revenue, margin_value, margin_pct


def literal_reading_margin(price: float, delivered_unit_cost: float) -> float:
    """Margin share if `product_cost` were taken at face value.

    Kept so the report can show the consequence of *not* making the assumption
    rather than only asserting that the assumption is needed.
    """
    return (price - delivered_unit_cost) / price if price else float("nan")
