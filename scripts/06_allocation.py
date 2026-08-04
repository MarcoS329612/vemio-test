"""Stage 06 — Warehouse allocation of the SKU forecast.

    uv run scripts/06_allocation.py

Output: reports/06_allocation.md

Runs after stage 03 because it consumes the published forecast rather than
producing one. Allocation is a layer on top of the model, not part of it.
"""

from __future__ import annotations

import argparse

import pandas as pd

from analysis import allocation, cleaning, config, io
from analysis.reporting import MarkdownReport

LOOKBACK_WEEKS = 52
DEAD_WAREHOUSE_WEEKS = 8
FORECAST_CSV = "03_forecast_next_12_weeks.csv"


def load_forecast() -> pd.DataFrame:
    """Read stage 03's artifact, already long-format, into what `allocate` expects.

    Columns as delivered: `product_code, product_name, week_start,
    forecast_units, model`. No melt is needed — only a rename and the usual
    dtype normalisation applied to every other stage's inputs.
    """
    forecast = pd.read_csv(config.REPORTS_DIR / FORECAST_CSV)
    forecast["week_start"] = pd.to_datetime(forecast["week_start"])
    forecast["product_code"] = forecast["product_code"].astype(str)
    return forecast.rename(columns={"forecast_units": "units"})


def main(
    lookback_weeks: int = LOOKBACK_WEEKS,
    dead_warehouse_weeks: int = DEAD_WAREHOUSE_WEEKS,
) -> None:
    raw = io.load_raw_transactions()
    flagged, _ = cleaning.flag_records(raw)

    forecast = load_forecast()
    origin = forecast["week_start"].min()

    shares = allocation.warehouse_shares(
        flagged,
        origin=origin,
        lookback_weeks=lookback_weeks,
        dead_warehouse_weeks=dead_warehouse_weeks,
    )
    allocated = allocation.allocate(forecast, shares)

    csv_path = config.REPORTS_DIR / "06_allocation_by_warehouse.csv"
    allocated.to_csv(csv_path, index=False)

    excluded = shares[shares["excluded_reason"].notna()]

    report = MarkdownReport(
        title="Stage 06 — Warehouse allocation",
        stage="scripts/06_allocation.py",
        subtitle=(
            "The stage-03 forecast is national because that is the grain the data "
            "supports. Stock ships per warehouse, so it is split by historical "
            "share — simple, auditable, and wrong in a way a planner can see."
        ),
    )

    report.heading("1. Share basis")
    report.key_values(
        {
            "Forecast origin": origin.date().isoformat(),
            "Lookback window": f"{lookback_weeks} weeks before the origin",
            "Dead-warehouse silence period": f"{dead_warehouse_weeks} weeks",
            "Warehouses in the share base": int((shares["share"] > 0).sum()),
            "Warehouses excluded": int(len(excluded)),
        }
    )
    report.note(
        "Shares are fitted strictly before the forecast origin. A share computed "
        "over the forecast window is the same future leakage the modelling "
        "standard forbids, and it would be invisible in the output."
    )

    report.heading("2. Shares by SKU and warehouse")
    report.table(shares)

    if not excluded.empty:
        report.heading("3. Excluded warehouses")
        report.table(excluded[["product_code", "warehouse", "units", "excluded_reason"]])
        report.note(
            "A warehouse that stopped selling still carries historical volume. "
            "Allocating it stock on that history is exactly the failure this "
            "stage exists to prevent. The check runs per (product_code, warehouse), "
            "not network-wide, because a warehouse can go dark for one SKU while "
            "staying active for another."
        )

    report.heading("4. Weekly allocation")
    report.text(
        "The planner-facing output: units to send, per SKU, per warehouse, per "
        f"week. Full table in `{csv_path.name}`."
    )
    preview = allocated.head(40).copy()
    preview["week_start"] = preview["week_start"].dt.date
    report.table(preview)

    report.heading("5. Reconciliation")
    totals = allocated.groupby("product_code")["units"].sum().round(1).rename("allocated_total")
    forecast_totals = forecast.groupby("product_code")["units"].sum().round(1).rename(
        "forecast_total"
    )
    recon = totals.reset_index().merge(
        forecast_totals.reset_index(), on="product_code", how="outer"
    )
    recon["difference"] = (recon["allocated_total"] - recon["forecast_total"]).round(1)
    report.table(recon)
    report.note(
        "Allocated totals reconcile to the SKU forecast by construction — shares "
        "for the live warehouses sum to 1.0, so splitting and re-summing returns "
        "the forecast total up to rounding to one decimal place."
    )

    report.heading("6. What this assumes")
    report.bullets(
        [
            "Warehouse mix is stable over the horizon — the wind-down inside the "
            "training window shows that is not guaranteed.",
            "Top-down cannot discover warehouse-level demand shifts the national "
            "forecast does not contain.",
            "Allocated totals reconcile to the SKU forecast by construction, so "
            "they inherit its error, roughly a quarter of volume per week.",
        ]
    )

    path = report.write(
        "06_allocation.md",
        params={
            "lookback_weeks": lookback_weeks,
            "dead_warehouse_weeks": dead_warehouse_weeks,
        },
    )
    print(f"Wrote {path}")
    print(f"Wrote {csv_path}")
    print(recon.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lookback-weeks", dest="lookback_weeks", type=int, default=LOOKBACK_WEEKS)
    parser.add_argument(
        "--dead-warehouse-weeks",
        dest="dead_warehouse_weeks",
        type=int,
        default=DEAD_WAREHOUSE_WEEKS,
    )
    main(**vars(parser.parse_args()))
