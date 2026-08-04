"""Data quality checks (methodology standard 01).

Each function *quantifies* an issue and returns it; none of them mutate or drop
anything. Cleaning is a separate, logged decision — mixing detection with
correction is how row counts stop reconciling.
"""

from __future__ import annotations

import pandas as pd

from . import config


def schema_check(frame: pd.DataFrame) -> pd.DataFrame:
    """Compare delivered columns against the documented dictionary."""
    delivered = list(frame.columns)
    rows = [
        {
            "column": col,
            "delivered": col in delivered,
            "dtype": str(frame[col].dtype) if col in delivered else "—",
            "note": "",
        }
        for col in config.EXPECTED_COLUMNS
    ]
    rows += [
        {
            "column": col,
            "delivered": col in delivered,
            "dtype": "—",
            "note": "documented in the dictionary but NOT delivered (F-001)",
        }
        for col in config.DOCUMENTED_BUT_MISSING_COLUMNS
    ]
    unexpected = set(delivered) - set(config.EXPECTED_COLUMNS)
    rows += [
        {"column": col, "delivered": True, "dtype": str(frame[col].dtype),
         "note": "present but not documented"}
        for col in sorted(unexpected)
    ]
    return pd.DataFrame(rows)


def completeness(frame: pd.DataFrame) -> pd.DataFrame:
    """Null counts and rates per column, ordered by severity."""
    nulls = frame.isna().sum()
    out = pd.DataFrame(
        {
            "column": nulls.index,
            "nulls": nulls.to_numpy(),
            "null_rate_%": (nulls.to_numpy() / len(frame) * 100).round(3),
        }
    )
    return out.sort_values("nulls", ascending=False).reset_index(drop=True)


def cardinality(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Distinct value counts — cheap sanity check against the stated dataset shape."""
    return pd.DataFrame(
        [{"column": c, "distinct": int(frame[c].nunique(dropna=True))} for c in columns]
    )


def grain_check(frame: pd.DataFrame, keys: tuple[str, ...]) -> dict[str, object]:
    """Test whether the claimed grain actually identifies a row.

    The dictionary *claims* a grain; standard 01 requires verifying it. Nulls in
    key columns are reported alongside, because `id_combo` is null for every
    organic sale: pandas treats those nulls as equal when detecting duplicates,
    so a large null count with zero duplicates means organic rows are still
    separated by the other four keys — worth seeing rather than inferring.
    """
    subset = frame[list(keys)]
    key_nulls = int(subset.isna().any(axis=1).sum())
    duplicated = int(subset.duplicated(keep=False).sum())
    return {
        "keys": " × ".join(keys),
        "rows": len(frame),
        "rows_with_null_in_key": key_nulls,
        "rows_in_duplicate_groups": duplicated,
        "grain_is_unique": duplicated == 0,
    }


def validity(frame: pd.DataFrame) -> pd.DataFrame:
    """Count records that are structurally valid but business-implausible.

    These are candidates for exclusion, not automatic deletions: standard 01
    requires flagging with a logged rationale, since some (returns, giveaways)
    may be real business events rather than defects.
    """
    checks = {
        "sell_in_quantity == 0": frame["sell_in_quantity"].eq(0),
        "sell_in_quantity < 0": frame["sell_in_quantity"].lt(0),
        "sell_in_amount == 0": frame["sell_in_amount"].eq(0),
        "sell_in_amount < 0": frame["sell_in_amount"].lt(0),
        "product_cost is null": frame["product_cost"].isna(),
        "product_cost <= 0": frame["product_cost"].le(0),
        "discount is null": frame["discount"].isna(),
        "discount < 0": frame["discount"].lt(0),
        "date failed to parse": frame["date"].isna(),
        "sold in a combo": frame["id_combo"].notna(),
    }
    rows = []
    for label, mask in checks.items():
        count = int(mask.sum())
        rows.append(
            {
                "check": label,
                "rows": count,
                "rows_%": round(count / len(frame) * 100, 3),
                "units_affected": float(
                    frame.loc[mask, "sell_in_quantity"].sum(skipna=True)
                ),
                "amount_affected": float(
                    frame.loc[mask, "sell_in_amount"].sum(skipna=True)
                ),
            }
        )
    return pd.DataFrame(rows)


def duplicate_rows(frame: pd.DataFrame) -> dict[str, int]:
    """Fully identical rows — always suspicious, never silently acceptable."""
    exact = int(frame.duplicated(keep=False).sum())
    return {"rows_in_exact_duplicate_groups": exact}


def date_format_evidence(frame: pd.DataFrame) -> dict[str, object]:
    """Prove the dd/mm/yyyy reading is right, don't assume it.

    The `year` and `month` columns are an independent witness: if the parse is
    correct they agree with the parsed date on every row. Under a mm/dd reading
    they would disagree wherever the true day exceeds 12.
    """
    parsed = frame["date"]
    agrees = (parsed.dt.year == frame["year"]) & (parsed.dt.month == frame["month"])
    valid = parsed.notna()
    return {
        "rows_parsed": int(valid.sum()),
        "rows_failed_to_parse": int((~valid).sum()),
        "rows_agreeing_with_year_month": int((agrees & valid).sum()),
        "rows_disagreeing_with_year_month": int((~agrees & valid).sum()),
        "days_above_12_present": bool((parsed.dt.day > 12).any()),
    }


def coverage(frame: pd.DataFrame) -> dict[str, object]:
    """Temporal span and continuity at weekly grain."""
    dates = frame["date"].dropna()
    weeks = dates.dt.to_period("W")
    span = pd.period_range(weeks.min(), weeks.max(), freq="W")
    observed = set(weeks.unique())
    return {
        "first_date": str(dates.min().date()),
        "last_date": str(dates.max().date()),
        "distinct_days": int(dates.dt.date.nunique()),
        "weeks_spanned": len(span),
        "weeks_observed": len(observed),
        "weeks_missing": len(set(span) - observed),
    }


def reconciliation(
    frame: pd.DataFrame, tolerance: float = 0.01, frac_tolerance: float = 0.001
) -> pd.DataFrame:
    """Test how `bruto`, `sell_in_amount` and `discount` relate (H-002).

    Segmented deliberately. On organic rows the gross and net amounts are equal
    and `discount` is zero, so *every* reading of `discount` matches trivially;
    pooling them inflates each test by the same ~64% and makes the readings look
    indistinguishable. The rightmost segment — promo rows that actually show a
    gross/net gap — is the one that discriminates.
    """
    gap = frame["bruto"] - frame["sell_in_amount"]
    gap_fraction = gap / frame["bruto"]
    discount = frame["discount"]
    promo = frame["id_combo"].notna()
    has_gap = gap.abs().gt(tolerance)

    segments = {
        "all rows": pd.Series(True, index=frame.index),
        "organic (no combo)": ~promo,
        "promo (in combo)": promo,
        "promo AND bruto≠net": promo & has_gap,
    }
    tests = {
        "bruto == sell_in_amount (no discount applied)": gap.abs().le(tolerance),
        "discount == bruto − net  (currency reading)": (
            (discount - gap).abs().le(tolerance)
        ),
        "discount == (bruto − net)/bruto  (fraction reading)": (
            (discount - gap_fraction).abs().le(frac_tolerance)
        ),
        "discount == 100·(bruto − net)/bruto  (percent-points)": (
            (discount - 100 * gap_fraction).abs().le(frac_tolerance)
        ),
    }

    rows = []
    for label, mask in tests.items():
        row: dict[str, object] = {"reconciliation test": label}
        clean = mask.fillna(False)
        for seg_label, seg in segments.items():
            denominator = int(seg.sum())
            matched = int((clean & seg).sum())
            row[f"{seg_label} (%)"] = (
                round(matched / denominator * 100, 2) if denominator else float("nan")
            )
        rows.append(row)
    return pd.DataFrame(rows)


def discount_profile(frame: pd.DataFrame) -> pd.DataFrame:
    """Value distribution of `discount` — which settles its unit of measure.

    A column documented as a percentage that never exceeds 1.0 is a fraction,
    not percent-points. Negative values are not a rounding artefact and need an
    explanation before the column is used as a price driver.
    """
    d = frame["discount"]
    non_zero = d[d.ne(0) & d.notna()]
    return pd.DataFrame(
        [
            {"statistic": "null", "value": int(d.isna().sum())},
            {"statistic": "exactly zero", "value": int(d.eq(0).sum())},
            {"statistic": "negative", "value": int(d.lt(0).sum())},
            {"statistic": "positive", "value": int(d.gt(0).sum())},
            {"statistic": "min", "value": float(d.min())},
            {"statistic": "max", "value": float(d.max())},
            {"statistic": "median (non-zero)", "value": float(non_zero.median())},
            {"statistic": "p95 (non-zero)", "value": float(non_zero.quantile(0.95))},
            {"statistic": "values above 1.0", "value": int(d.gt(1).sum())},
        ]
    )


def cost_margin_structure(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-SKU relationship between `product_cost` and `bruto` (F-001 / H-001).

    Two things are being read off this table at once:

    1. Whether the per-SKU ratio is constant, which decides whether the missing
       `product_margin` column can be reconstructed at all.
    2. Its *direction*. The dictionary describes margin as a markup over cost,
       so gross revenue should exceed cost. A ratio above 1 means the delivered
       cost sits above the price it is compared against, and every transaction
       reads as loss-making — which is the kind of thing to raise, not silently
       correct.
    """
    usable = frame[frame["bruto"].gt(0) & frame["product_cost"].gt(0)].copy()
    usable["cost_over_bruto"] = usable["product_cost"] / usable["bruto"]
    grouped = usable.groupby(["product_code", "product_name"])["cost_over_bruto"]

    out = pd.DataFrame(
        {
            "rows": grouped.size(),
            "cost/bruto mean": grouped.mean().round(6),
            "cost/bruto std": grouped.std().round(9),
            "distinct values": grouped.nunique(),
        }
    ).reset_index()
    out["implied margin (cost/bruto − 1)"] = (out["cost/bruto mean"] - 1).round(4)
    out["margin as literally delivered ((bruto−cost)/bruto)"] = (
        (1 - out["cost/bruto mean"]).round(4)
    )
    return out


def price_variation(frame: pd.DataFrame) -> pd.DataFrame:
    """Realised unit-price spread per SKU — the input to Challenge B's SKU choice.

    Elasticity needs a SKU whose price actually moved. Counting *distinct*
    realised prices separates SKUs with genuine variation from those sold at a
    near-constant price, and doing it before modelling makes the selection a
    documented criterion rather than a convenient one (H-004).
    """
    usable = frame[frame["sell_in_quantity"].gt(0) & frame["bruto"].gt(0)].copy()
    usable["unit_list"] = usable["bruto"] / usable["sell_in_quantity"]
    usable["unit_net"] = usable["sell_in_amount"] / usable["sell_in_quantity"]

    grouped = usable.groupby(["product_code", "product_name"])
    out = pd.DataFrame(
        {
            "rows": grouped.size(),
            "distinct list prices": grouped["unit_list"].nunique(),
            "distinct net prices": grouped["unit_net"].nunique(),
            "net price min": grouped["unit_net"].min().round(3),
            "net price median": grouped["unit_net"].median().round(3),
            "net price max": grouped["unit_net"].max().round(3),
            "weeks observed": grouped["date"].apply(
                lambda s: s.dt.to_period("W").nunique()
            ),
        }
    ).reset_index()
    out["max/median"] = (out["net price max"] / out["net price median"]).round(2)
    return out


def check_margin_convention(
    frame: pd.DataFrame, rates: pd.DataFrame
) -> dict[str, object]:
    """Verify the adopted cost reading against free-goods lines.

    The reading in `economics.py` is an inference (F-003, open question Q5), so
    it is checked rather than only asserted. Lines shipped at a realised price
    of zero inside a combo are the discriminating case: under the adopted
    reading they lose money, which is what giving product away does. Under the
    rejected reading — `product_cost` as a distributor list price, margin as
    list minus sell-in — they book the full reference price as profit, which
    would make giveaways the most profitable transactions in the file.
    """
    free = frame[
        frame["sell_in_quantity"].gt(0)
        & frame["sell_in_amount"].le(0)
        & frame["bruto"].gt(0)
    ]
    if free.empty:
        return {
            "free_goods_rows": 0,
            "free_goods_units": 0.0,
            "adopted_margin": float("nan"),
            "rejected_margin": float("nan"),
            "passes": False,
        }

    lookup = rates.set_index("product_code")["margin_rate"]
    markup = free["product_code"].map(lookup)

    adopted_cost = free["bruto"] / (1.0 + markup)
    adopted = float((free["sell_in_amount"] - adopted_cost).sum())
    rejected = float((free["product_cost"] - free["sell_in_amount"]).sum())

    return {
        "free_goods_rows": int(len(free)),
        "free_goods_units": float(free["sell_in_quantity"].sum()),
        "adopted_margin": round(adopted, 2),
        "rejected_margin": round(rejected, 2),
        "passes": bool(adopted < 0 < rejected),
    }


def incomplete_metadata(frame: pd.DataFrame) -> pd.DataFrame:
    """Isolate rows missing descriptive metadata.

    The case statement warns of "a record with incomplete metadata". Locating it
    exactly — rather than filtering the symptom away — is what standard 01 means
    by not over-cleaning.
    """
    descriptive = ["category", "subcategory", "brand", "basket", "product_name"]
    mask = frame[descriptive].isna().any(axis=1)
    columns = [
        "date", "warehouse", "client_code", "product_code", "ticket_code",
        "id_combo", "sell_in_quantity", "sell_in_amount", "bruto",
        "product_cost", "discount", *descriptive,
    ]
    return frame.loc[mask, columns].reset_index(drop=True)
