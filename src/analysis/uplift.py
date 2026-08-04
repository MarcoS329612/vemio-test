"""Promotional uplift (Challenge C).

The hard part is not arithmetic, it is the counterfactual: what would have sold
without the promotion. Two estimates are produced for every episode — a pre-period
baseline and a difference-in-differences adjustment against SKUs not promoted in
the same weeks — because they rest on different assumptions and disagreeing is
informative.

Post-promotion weeks are always checked. Uplift that is repaid by a slump
afterwards is pulled-forward demand, not incremental volume, and recommending
its repetition would be an expensive mistake.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from . import panels

PROMO_THRESHOLD = 0.5   # share of weekly units sold under a combo
QUIET_THRESHOLD = 0.2   # a week this lightly promoted counts as a clean baseline


def detect_episodes(
    panel: pd.DataFrame, product_code: str, min_weeks: int = 3
) -> pd.DataFrame:
    """Find contiguous runs of promoted weeks for one SKU.

    Episodes are derived from observed promotional intensity rather than from
    combo identifiers, because several combos can overlap on the same SKU and
    what the business actually ran is the combined pressure.
    """
    series = panel[
        panel["product_code"].eq(product_code) & panel["is_complete_week"]
    ].sort_values("week_start").reset_index(drop=True)

    promoted = series["promo_share"].gt(PROMO_THRESHOLD).to_numpy()
    episodes, start = [], None
    for i, flag in enumerate(promoted):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            episodes.append((start, i - 1))
            start = None
    if start is not None:
        episodes.append((start, len(promoted) - 1))

    rows = []
    for first, last in episodes:
        window = series.iloc[first : last + 1]
        if len(window) < min_weeks:
            continue
        rows.append(
            {
                "product_code": product_code,
                "start_index": first,
                "end_index": last,
                "start_week": window["week_start"].iloc[0],
                "end_week": window["week_start"].iloc[-1],
                "n_weeks": len(window),
                "units": float(window["units"].sum()),
                "mean_promo_share": round(float(window["promo_share"].mean()), 3),
                "mean_discount_depth": round(
                    float(window["discount_depth"].mean()), 4
                ),
                "weeks_before_available": first,
                "weeks_after_available": len(series) - 1 - last,
            }
        )
    return pd.DataFrame(rows)


def _control_factor(
    panel: pd.DataFrame,
    product_code: str,
    pre_weeks: pd.Series,
    episode_weeks: pd.Series,
) -> tuple[float, list[str]]:
    """How much control SKUs moved between the two windows.

    Controls must be quiet in *both* windows — a SKU running its own promotion
    is not a control, it is a second treatment. Returns 1.0 when no clean
    control exists, which collapses the estimate back to the pre-period baseline
    and is reported as such rather than hidden.
    """
    others = panel[
        panel["product_code"].ne(product_code) & panel["is_complete_week"]
    ]
    pre = others[others["week_start"].isin(pre_weeks)]
    during = others[others["week_start"].isin(episode_weeks)]

    quiet_pre = set(
        pre.groupby("product_code")["promo_share"].max().pipe(
            lambda s: s[s < QUIET_THRESHOLD].index
        )
    )
    quiet_during = set(
        during.groupby("product_code")["promo_share"].max().pipe(
            lambda s: s[s < QUIET_THRESHOLD].index
        )
    )
    controls = sorted(quiet_pre & quiet_during)
    if not controls:
        return 1.0, []

    def weekly_rate(frame: pd.DataFrame) -> float:
        subset = frame[frame["product_code"].isin(controls)]
        return subset.groupby("week_start")["units"].sum().mean()

    pre_rate, during_rate = weekly_rate(pre), weekly_rate(during)
    if not pre_rate or np.isnan(pre_rate) or np.isnan(during_rate):
        return 1.0, controls
    return float(during_rate / pre_rate), controls


def estimate_uplift(
    panel: pd.DataFrame,
    product_code: str,
    episode: pd.Series,
    pre_weeks: int = 6,
    post_weeks: int = 6,
) -> dict[str, object]:
    """Incremental units for one promotional episode, plus its aftermath."""
    series = panel[
        panel["product_code"].eq(product_code) & panel["is_complete_week"]
    ].sort_values("week_start").reset_index(drop=True)

    first, last = int(episode["start_index"]), int(episode["end_index"])
    pre = series.iloc[max(0, first - pre_weeks) : first]
    during = series.iloc[first : last + 1]
    post = series.iloc[last + 1 : last + 1 + post_weeks]

    clean_pre = pre[pre["promo_share"].lt(QUIET_THRESHOLD)]
    baseline_source = clean_pre if len(clean_pre) >= 3 else pre
    baseline = float(baseline_source["units"].median()) if len(baseline_source) else np.nan

    n_weeks = len(during)
    actual = float(during["units"].sum())
    expected_naive = baseline * n_weeks

    factor, controls = _control_factor(
        panel, product_code, pre["week_start"], during["week_start"]
    )
    expected_did = baseline * factor * n_weeks

    post_actual = float(post["units"].sum())
    post_expected = baseline * factor * len(post)
    post_delta = post_actual - post_expected if len(post) else np.nan

    uplift_did = actual - expected_did
    net_uplift = uplift_did + (post_delta if len(post) else 0.0)

    price = float(during["avg_net_price"].mean())
    list_price = float(during["avg_list_price"].mean())
    discount_given = (list_price - price) * actual

    return {
        "product_code": product_code,
        "start_week": episode["start_week"],
        "end_week": episode["end_week"],
        "n_weeks": n_weeks,
        "mean_discount_depth": episode["mean_discount_depth"],
        "baseline_units_per_week": round(baseline, 1),
        "baseline_weeks_used": len(baseline_source),
        "baseline_is_clean": len(clean_pre) >= 3,
        "control_skus": ", ".join(controls) if controls else "none available",
        "control_factor": round(factor, 3),
        "actual_units": round(actual, 1),
        "expected_units_naive": round(expected_naive, 1),
        "expected_units_did": round(expected_did, 1),
        "uplift_naive": round(actual - expected_naive, 1),
        "uplift_naive_%": round((actual - expected_naive) / expected_naive * 100, 1)
        if expected_naive else np.nan,
        "uplift_did": round(uplift_did, 1),
        "uplift_did_%": round(uplift_did / expected_did * 100, 1) if expected_did else np.nan,
        "post_weeks": len(post),
        "post_delta_units": round(post_delta, 1) if len(post) else np.nan,
        "net_uplift_units": round(net_uplift, 1),
        "pulled_forward": bool(len(post) and post_delta < 0),
        "avg_net_price": round(price, 2),
        "avg_list_price": round(list_price, 2),
        "discount_given": round(discount_given, 0),
    }


def promotion_economics(
    result: dict[str, object], margin_rate: float
) -> dict[str, object]:
    """Was the incremental volume worth the discount that bought it?

    Incremental margin counts only the units the promotion actually created,
    while the discount is paid on *every* unit sold in the window, including the
    ones that would have sold anyway. That asymmetry is what makes deep
    discounts on already-selling products destroy value.
    """
    price = float(result["avg_net_price"])
    list_price = float(result["avg_list_price"])
    cost = list_price / (1.0 + margin_rate)

    incremental_units = float(result["net_uplift_units"])
    incremental_margin = (price - cost) * incremental_units

    baseline_units = float(result["expected_units_did"])
    subsidy_on_baseline = (list_price - price) * baseline_units

    return {
        "unit_cost_assumed": round(cost, 2),
        "margin_per_unit_at_promo_price": round(price - cost, 2),
        "incremental_units": round(incremental_units, 1),
        "incremental_margin": round(incremental_margin, 0),
        "discount_subsidy_on_baseline_units": round(subsidy_on_baseline, 0),
        "net_margin_effect": round(incremental_margin - subsidy_on_baseline, 0),
        "verdict": "repeat" if incremental_margin > subsidy_on_baseline else "do not repeat",
    }


def combo_week_matrix(frame: pd.DataFrame, product_code: str) -> pd.DataFrame:
    """Weekly activity of every combo on one SKU.

    Each column holds the combo's share of that week's units rather than a 0/1
    flag: a combo touching 5% of a week is not the same treatment as one
    touching 90%, and a binary indicator would force the regression to pretend
    it is.
    """
    rows = frame[
        frame["product_code"].eq(product_code) & frame["usable_for_demand"]
    ].copy()
    rows["week_start"] = (
        rows["date"].dt.to_period(panels.WEEK_FREQ).dt.start_time
    )

    weekly_units = rows.groupby("week_start")["sell_in_quantity"].sum()

    promo = rows[rows["is_promo"] & rows["id_combo"].notna()].copy()
    # `id_combo` arrives as a float in the raw file. Cast once, so column names
    # and the regression's parameter index agree with the report labels.
    promo["id_combo"] = promo["id_combo"].astype(str)
    by_combo = promo.pivot_table(
        index="week_start",
        columns="id_combo",
        values="sell_in_quantity",
        aggfunc="sum",
        fill_value=0.0,
    )

    matrix = by_combo.reindex(weekly_units.index, fill_value=0.0)
    matrix = matrix.div(weekly_units, axis=0).fillna(0.0)
    matrix["units"] = weekly_units
    return matrix.sort_index()


def estimate_combo_effects(
    frame: pd.DataFrame, product_code: str, min_weeks: int = 3
) -> pd.DataFrame:
    """Per-combo uplift, net of trend and of every concurrent combo.

    Aggregating to the SKU destroys mechanic-level signal — a SKU averaging
    +1% can contain one combo at +50% and several at zero. Estimating per combo
    without controls has the opposite failure: overlapping combos each take
    credit for the same units. Entering every combo simultaneously with a trend
    term is what separates them, and `weeks_concurrent` says how much of each
    estimate rests on weeks it had to share.
    """
    matrix = combo_week_matrix(frame, product_code)
    combos = [c for c in matrix.columns if c != "units"]

    active = matrix[combos].gt(0)
    eligible = [c for c in combos if int(active[c].sum()) >= min_weeks]
    if not eligible:
        return pd.DataFrame(
            columns=[
                "id_combo", "coefficient", "std_error", "p_value",
                "weeks_active", "weeks_concurrent", "uplift_pct_vs_intercept",
            ]
        )

    design = matrix[eligible].copy()
    design["t"] = np.arange(len(matrix)) / 52.0
    x = sm.add_constant(design)
    model = sm.OLS(matrix["units"], x).fit(
        cov_type="HAC", cov_kwds={"maxlags": 4}
    )

    intercept = float(model.params["const"])
    others = active[eligible]
    rows = []
    for combo in eligible:
        weeks_active = int(others[combo].sum())
        concurrent = int((others[combo] & others.drop(columns=combo).any(axis=1)).sum())
        coefficient = float(model.params[combo])
        rows.append(
            {
                "id_combo": combo,
                "coefficient": round(coefficient, 1),
                "std_error": round(float(model.bse[combo]), 1),
                "p_value": round(float(model.pvalues[combo]), 4),
                "weeks_active": weeks_active,
                "weeks_concurrent": concurrent,
                "uplift_pct_vs_intercept": round(coefficient / intercept * 100, 1)
                if intercept else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values("coefficient", ascending=False).reset_index(
        drop=True
    )
