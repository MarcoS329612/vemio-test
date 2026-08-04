"""Price elasticity and the price simulator (Challenge B).

Identification first, regression second (standard 04). The price variation in
this dataset comes almost entirely from promotional discount depth, so what is
estimated is the response to *realised* price — which is what a pricing decision
needs, but it is not the same thing as a pure list-price experiment, and the
report says so.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from . import economics, panels


def weekly_price_panel(frame: pd.DataFrame, product_code: str) -> pd.DataFrame:
    """Weekly units and realised price for one SKU, from price-usable rows only.

    Rebuilt rather than reused from the demand panel: rows with a zero realised
    price or a negative discount are legitimate demand but would corrupt the
    price variable (F-004).
    """
    rows = frame[
        frame["product_code"].eq(product_code) & frame["usable_for_price"]
    ].copy()
    rows["week"] = rows["date"].dt.to_period(panels.WEEK_FREQ)

    grouped = rows.groupby("week", observed=True)
    out = grouped.agg(
        units=("sell_in_quantity", "sum"),
        net_amount=("sell_in_amount", "sum"),
        gross_amount=("bruto", "sum"),
        promo_units=("sell_in_quantity", lambda s: float(
            s.where(rows.loc[s.index, "is_promo"], 0).sum()
        )),
        clients=("client_code", "nunique"),
    ).reset_index()

    out["week_start"] = pd.PeriodIndex(out["week"], freq=panels.WEEK_FREQ).start_time
    out["price"] = out["net_amount"] / out["units"]
    out["list_price"] = out["gross_amount"] / out["units"]
    out["promo_share"] = out["promo_units"] / out["units"]
    out["week_of_year"] = out["week_start"].dt.isocalendar().week.astype(int)
    out["t"] = np.arange(len(out))

    first, last = rows["date"].min(), rows["date"].max()
    starts = pd.PeriodIndex(out["week"], freq=panels.WEEK_FREQ).start_time
    ends = pd.PeriodIndex(out["week"], freq=panels.WEEK_FREQ).end_time
    out = out[(starts >= first) & (ends <= last)]

    return out.sort_values("week_start").reset_index(drop=True)


def _design_matrix(data: pd.DataFrame, fourier_order: int = 2) -> pd.DataFrame:
    """log price, a linear trend and annual Fourier terms.

    Seasonality and trend are controlled explicitly so the price coefficient is
    not quietly absorbing "demand was higher in March anyway".
    """
    angle = 2 * np.pi * data["week_of_year"] / 52.0
    design = pd.DataFrame({"log_price": np.log(data["price"]), "t": data["t"] / 52.0})
    for k in range(1, fourier_order + 1):
        design[f"sin{k}"] = np.sin(k * angle)
        design[f"cos{k}"] = np.cos(k * angle)
    return design


def estimate_elasticity(
    data: pd.DataFrame, fourier_order: int = 2, hac_lags: int = 4
) -> dict[str, object]:
    """Log-log demand regression with HAC standard errors.

    Newey-West rather than plain OLS errors: weekly demand is autocorrelated, and
    ignoring that produces confidence intervals narrower than the evidence
    supports — which is how an elasticity gets over-sold.
    """
    design = _design_matrix(data, fourier_order)
    y = np.log(data["units"])
    x = sm.add_constant(design)
    model = sm.OLS(y, x).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})

    conf = model.conf_int().loc["log_price"]
    return {
        "model": model,
        "elasticity": float(model.params["log_price"]),
        "std_error": float(model.bse["log_price"]),
        "p_value": float(model.pvalues["log_price"]),
        "ci_low": float(conf[0]),
        "ci_high": float(conf[1]),
        "r_squared": float(model.rsquared),
        "n_weeks": int(len(data)),
    }


def predict_units(
    fit: dict[str, object], data: pd.DataFrame, price: float, fourier_order: int = 2
) -> float:
    """Expected weekly units at ``price``, holding season and trend at their means.

    "At the average week" is the right frame for a quarterly pricing decision:
    the recommendation is a policy, not a forecast for one specific week.
    """
    model = fit["model"]
    design = _design_matrix(data, fourier_order)
    reference = design.mean()
    reference["log_price"] = np.log(price)
    x = sm.add_constant(pd.DataFrame([reference]), has_constant="add")
    return float(np.exp(model.predict(x).iloc[0]))


def simulate(
    fit: dict[str, object],
    data: pd.DataFrame,
    margin_rate: float,
    n_points: int = 60,
    fourier_order: int = 2,
) -> pd.DataFrame:
    """Price → demand, revenue and margin across the observed price range only.

    The grid is clipped to observed prices by construction. Extrapolating a
    constant-elasticity curve past the data is arithmetic, not evidence — the
    case says so explicitly, and a simulator that silently allows it invites the
    exact mistake it warns about.
    """
    low, high = float(data["price"].min()), float(data["price"].max())
    prices = np.linspace(low, high, n_points)

    # Cost is anchored to the SKU's list price, which is a property of the
    # product rather than of the week's discount.
    list_price = float(data["list_price"].median())
    cost = economics.unit_cost_from_list(list_price, margin_rate)

    rows = []
    for price in prices:
        units = predict_units(fit, data, price, fourier_order)
        revenue, margin_value, margin_pct = economics.margin_at_price(
            price, units, cost
        )
        rows.append(
            {
                "price": round(price, 2),
                "units": round(units, 1),
                "revenue": round(revenue, 0),
                "margin_value": round(margin_value, 0),
                "margin_pct": round(margin_pct, 4),
                "unit_cost": round(cost, 2),
            }
        )
    return pd.DataFrame(rows)


def recommend_price(grid: pd.DataFrame) -> dict[str, object]:
    """Pick the price that balances revenue and margin.

    Revenue-maximising and margin-maximising prices usually differ. The balanced
    choice maximises the average of the two normalised to their own maxima —
    a transparent rule, stated rather than hidden, so the commercial team can
    disagree with the weighting rather than with a black box.
    """
    normalised_revenue = grid["revenue"] / grid["revenue"].max()
    normalised_margin = grid["margin_value"] / grid["margin_value"].max()
    balanced = (normalised_revenue + normalised_margin) / 2

    return {
        "revenue_max_price": float(grid.loc[grid["revenue"].idxmax(), "price"]),
        "margin_max_price": float(grid.loc[grid["margin_value"].idxmax(), "price"]),
        "balanced_price": float(grid.loc[balanced.idxmax(), "price"]),
        "balanced_units": float(grid.loc[balanced.idxmax(), "units"]),
        "balanced_revenue": float(grid.loc[balanced.idxmax(), "revenue"]),
        "balanced_margin_value": float(grid.loc[balanced.idxmax(), "margin_value"]),
        "balanced_margin_pct": float(grid.loc[balanced.idxmax(), "margin_pct"]),
        "observed_min": float(grid["price"].min()),
        "observed_max": float(grid["price"].max()),
    }
