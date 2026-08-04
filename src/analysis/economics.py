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


def mean_promo_discount(frame: pd.DataFrame) -> pd.DataFrame:
    """Unit-weighted mean promotional discount, read straight from `discount`.

    `panels.build_weekly_sku_panel`'s `discount_depth` is a bruto-vs-net proxy
    (1 − avg_net_price / avg_list_price). It is blind to combo-level discounts
    that never reach `bruto` line by line — the reconciliation defect F-004
    documents (see `quality.reconciliation`): a combo can carry a real,
    constant `discount` while `bruto == sell_in_amount` on nearly every one of
    its lines, which the panel proxy reads as no discount at all.

    `discount` is the field the data dictionary defines as the promotional
    depth, so this measure uses it directly — weighted by units, restricted to
    promoted lines (`is_promo`), since non-promo lines carry `discount == 0`
    by construction and would only dilute the answer toward zero.

    A null `discount` on a promoted line is treated as zero for the weighted
    sum rather than dropped: the row's units are real promotional volume and
    stay in the denominator, but with no evidence of what depth they actually
    carried, they cannot be assumed to match the SKU's typical discount either.
    """
    promo = frame[frame["is_promo"]].copy()
    promo["discount"] = promo["discount"].fillna(0)
    promo["weighted_discount"] = promo["discount"] * promo["sell_in_quantity"]

    grouped = promo.groupby(["product_code", "product_name"])
    result = pd.DataFrame(
        {
            "mean_promo_discount": (
                grouped["weighted_discount"].sum() / grouped["sell_in_quantity"].sum()
            ),
        }
    ).reset_index()
    result["mean_promo_discount"] = result["mean_promo_discount"].round(4)
    return result
