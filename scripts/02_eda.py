"""Stage 02 — Cleaning decisions, weekly panel and exploratory analysis.

Implements standard 02: exploration organised around the three business
questions, ending in findings rather than plots. Also applies the cleaning rules
deferred from stage 01 — as flags with a logged rationale, never as deletions.

    uv run scripts/02_eda.py

Outputs: reports/02_eda.md, figures, and the weekly panel in data/processed/.
"""

from __future__ import annotations

import argparse

from analysis import cleaning, io, panels, plotting
from analysis.reporting import MarkdownReport, section_findings


def main(nrows: int | None = None) -> None:
    print("Loading raw transactions …")
    raw = io.load_raw_transactions(nrows=nrows)
    flagged, cleaning_log = cleaning.flag_records(raw)
    print(f"Flagged {len(flagged):,} rows")

    panel = panels.build_weekly_sku_panel(flagged)
    calendar = panels.build_promo_calendar(flagged)
    io.save_processed(panel.assign(week=panel["week"].astype(str)), "weekly_sku_panel")
    io.save_processed(calendar, "promo_calendar")
    print(f"Panel: {len(panel):,} SKU-weeks · promo calendar: {len(calendar):,} combos")

    report = MarkdownReport(
        title="Stage 02 — Cleaning, weekly panel and EDA",
        stage="scripts/02_eda.py",
        subtitle=(
            "Cleaning decisions applied as flags, the weekly SKU panel the three "
            "challenges share, and the exploration that selects SKUs and promotions."
        ),
    )

    # ------------------------------------------------------------- cleaning
    report.heading("1. Cleaning decision log")
    report.text(
        "Each rule adds a boolean column; nothing is deleted. Downstream stages pick a "
        "selector, so every exclusion stays visible and reversible (standard 01)."
    )
    report.table(cleaning_log)
    report.note(
        "Zero-amount rows keep their units: shipping stock at no charge is still demand, "
        "and dropping it would bias a units forecast downwards. They are excluded from "
        "price work instead, because a realised price of zero is not a point on a "
        "demand curve."
    )

    # ---------------------------------------------------------------- panel
    complete = panel[panel["is_complete_week"]]
    partial = panel[~panel["is_complete_week"]]
    report.heading("2. The weekly SKU panel")
    report.key_values(
        {
            "SKU-weeks (all)": len(panel),
            "SKU-weeks (complete weeks only)": len(complete),
            "Partial weeks excluded from modelling": int(
                partial["week"].nunique()
            ),
            "First complete week": str(complete["week_start"].min().date()),
            "Last complete week": str(complete["week_start"].max().date()),
            "Complete weeks per SKU": int(
                complete.groupby("product_code").size().median()
            ),
        }
    )
    report.note(
        "The first and last calendar weeks are truncated by the extract boundaries. They "
        "are flagged rather than dropped, because a truncated week looks like a demand "
        "collapse to any model that sees it — and like a real data point to any reader "
        "who does not know it was cut."
    )

    report.heading("3. Volume and price structure per SKU")
    summary = (
        complete.groupby(["product_code", "product_name"])
        .agg(
            weeks=("week", "nunique"),
            total_units=("units", "sum"),
            median_weekly_units=("units", "median"),
            cv_weekly_units=("units", lambda s: round(s.std() / s.mean(), 3)),
            median_price=("avg_net_price", "median"),
            price_p10=("avg_net_price", lambda s: round(s.quantile(0.10), 2)),
            price_p90=("avg_net_price", lambda s: round(s.quantile(0.90), 2)),
            median_promo_share=("promo_share", "median"),
        )
        .reset_index()
    )
    summary["price_spread_p90/p10"] = (
        summary["price_p90"] / summary["price_p10"]
    ).round(2)
    report.table(summary)
    report.note(
        "`cv_weekly_units` (coefficient of variation) is the forecastability signal: a "
        "low value means a naive baseline will already be hard to beat. "
        "`price_spread_p90/p10` is the elasticity signal — a SKU whose weekly price "
        "barely moves cannot identify a price response (**H-004**)."
    )

    figure = plotting.weekly_series_grid(
        panel, sorted(panel["product_code"].unique()), "02_weekly_units_by_sku"
    )
    report.figure(
        figure,
        "Weekly units per SKU across the 74-week history. Promo-dominated weeks are "
        "marked; the level shifts they produce are what Challenge C must separate from "
        "underlying demand.",
    )

    # ----------------------------------------------------------- promotions
    report.heading("4. Promotion calendar")
    material = calendar[calendar["is_material"]]
    report.key_values(
        {
            "Distinct combos": len(calendar),
            "Combos above the materiality floor (500 units)": len(material),
            "Units sold under a combo": float(calendar["units"].sum()),
            "Median combo duration (days)": float(calendar["duration_days"].median()),
        }
    )
    report.text("The largest promotions by volume — Challenge C's candidate pool:")
    report.table(
        material.head(12)[
            ["id_combo", "combo", "product_code", "first_date", "last_date",
             "duration_days", "weeks", "units", "discount_depth", "warehouses"]
        ]
    )
    report.note(
        "A combo's `discount_depth` here is realised (1 − net/gross), not the nominal "
        "offer. Candidates for uplift estimation need enough duration to see a before "
        "and an after, and enough volume for the effect to clear week-to-week noise."
    )

    # ------------------------------------------------------------- seasonality
    report.heading("5. Seasonality and trend")
    monthly = (
        complete.groupby(["product_code", "month"])["units"].median().unstack("month")
    )
    report.text("Median weekly units by calendar month, per SKU:")
    report.table(monthly.round(0).reset_index())
    report.note(
        "Read for shape, not level. A flat row means a seasonal-naive baseline has "
        "nothing to exploit and a moving average will be the one to beat (**H-003**)."
    )

    # ---------------------------------------------------------------- price
    report.heading("6. Price–quantity relationship (Challenge B precondition)")
    candidates = summary.nlargest(2, "price_spread_p90/p10")["product_code"].tolist()
    for code in candidates:
        series = complete[complete["product_code"].eq(code)]
        name = series["product_name"].iloc[0]
        fig = plotting.price_quantity_scatter(
            series, f"{code} — {name}: weekly price vs units", f"02_price_qty_{code}"
        )
        corr = series["avg_net_price"].corr(series["units"])
        report.figure(
            fig,
            f"{code} ({name}): weekly realised price against units, both on log scales. "
            f"Correlation {corr:.2f} — a downward slope is the precondition for an "
            "elasticity estimate, not proof of one.",
        )

    # ------------------------------------------------------------- hand-off
    report.heading("7. Candidate findings for the registry")
    report.text(
        section_findings(
            [
                ("H-003", "Seasonality strength per SKU — §5."),
                ("H-004", "Price variation and its direction — §3, §6."),
                ("H-005", "Promotion windows available for uplift — §4."),
            ]
        )
    )

    path = report.write("02_eda.md", params={"nrows": nrows or "all"})
    print(f"Wrote {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nrows", type=int, default=None)
    main(**vars(parser.parse_args()))
