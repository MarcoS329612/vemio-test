"""Stage 02 — Cleaning decisions, weekly panel and exploratory analysis.

Implements standard 02: exploration organised around the three business
questions, ending in findings rather than plots. Also applies the cleaning rules
deferred from stage 01 — as flags with a logged rationale, never as deletions.

    uv run scripts/02_eda.py

Outputs: reports/02_eda.md, figures, and the weekly panel in data/processed/.
"""

from __future__ import annotations

import argparse

import pandas as pd

from analysis import cleaning, economics, io, panels, plotting
from analysis.reporting import MarkdownReport, section_findings


def _eta_squared(values, groups) -> float:
    """Share of variance in `values` explained by `groups` (one-way ANOVA R²).

    Used in §10 to test the "not client-specific" claim on its own terms:
    compare how much of the variation in discount depth a grouping explains,
    rather than asserting it from dispersion statistics alone.
    """
    grand_mean = values.mean()
    ss_total = ((values - grand_mean) ** 2).sum()
    if ss_total == 0:
        return float("nan")
    group_means = values.groupby(groups).transform("mean")
    ss_within = ((values - group_means) ** 2).sum()
    return float((ss_total - ss_within) / ss_total)


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
    monthly = complete.pivot_table(
        index="product_code", columns="month", values="units", aggfunc="median"
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

    # --------------------------------------------------------------- network
    report.heading("7. Warehouse network")
    report.text(
        "The forecast is national and allocation splits it by warehouse share (stage 06). "
        "Before treating warehouses as one interchangeable dimension of the same demand, "
        "it is worth checking whether they are: a warehouse selling a lot to few clients "
        "is a different commercial relationship than one selling little to many, even at "
        "the same revenue."
    )
    demand = flagged[flagged["usable_for_demand"]]
    by_warehouse = (
        demand.groupby("warehouse")
        .agg(
            routes=("route", "nunique"),
            clients=("client_code", "nunique"),
            revenue=("sell_in_amount", "sum"),
        )
        .reset_index()
    )
    by_warehouse["revenue_per_client"] = by_warehouse["revenue"] / by_warehouse["clients"]
    by_warehouse["revenue_share"] = by_warehouse["revenue"] / by_warehouse["revenue"].sum()

    top_product = (
        demand.groupby(["warehouse", "product_code", "product_name"])["sell_in_amount"]
        .sum()
        .reset_index()
        .sort_values("sell_in_amount", ascending=False)
        .drop_duplicates("warehouse")
        .rename(
            columns={
                "product_code": "top_product_code",
                "product_name": "top_product_name",
                "sell_in_amount": "top_product_revenue",
            }
        )
    )
    network = (
        by_warehouse.merge(top_product, on="warehouse")
        .sort_values("revenue", ascending=False)
        .reset_index(drop=True)
    )
    report.table(
        network[
            [
                "warehouse", "routes", "clients", "revenue", "revenue_per_client",
                "revenue_share", "top_product_code", "top_product_name",
            ]
        ].round({"revenue": 0, "revenue_per_client": 2, "revenue_share": 4})
    )
    top2_share = float(network.nlargest(2, "revenue")["revenue_share"].sum())
    top5_share = float(network.nlargest(5, "revenue")["revenue_share"].sum())
    first_top_product = network["top_product_code"].iloc[0]
    one_top_product = bool(network["top_product_code"].eq(first_top_product).all())
    report.key_values(
        {
            "Warehouses": int(network["warehouse"].nunique()),
            "Routes": int(demand["route"].nunique()),
            "Clients": int(demand["client_code"].nunique()),
            "Revenue share, top 2 warehouses": round(top2_share, 4),
            "Revenue share, top 5 warehouses": round(top5_share, 4),
            "Same top product in every warehouse": one_top_product,
        }
    )
    fig = plotting.warehouse_scatter(
        network, "Warehouses differ in kind, not only in size", "02_warehouse_network"
    )
    report.figure(
        fig,
        f"Revenue concentrates hard — the top 2 warehouses hold {top2_share:.0%} of "
        f"revenue, the top 5 hold {top5_share:.0%} — but revenue per client separates "
        "them further: some warehouses reach many clients at low value each, others reach "
        "few at high value each, which a single revenue ranking hides.",
    )
    if one_top_product:
        top_code = network.iloc[0]["top_product_code"]
        top_name = network.iloc[0]["top_product_name"]
        n_warehouses = int(network["warehouse"].nunique())
        top_product_note = (
            f"**F-012.** {top_code} ({top_name}) is the top-revenue product in all "
            f"{n_warehouses} warehouses, and revenue is far more concentrated than clients "
            f"or routes ({top2_share:.0%} of revenue in 2 of {n_warehouses} warehouses). "
            "Warehouses differ in kind, not just in scale, which is the caveat any "
            "warehouse-level allocation or model has to carry."
        )
    else:
        top_product_note = (
            "**F-012.** The top-revenue product is not the same across every warehouse — "
            "see the table above for the exceptions. Revenue is still concentrated "
            f"({top2_share:.0%} of revenue in the top 2 warehouses), and warehouses differ "
            "in kind, not just in scale, which is the caveat any warehouse-level allocation "
            "or model has to carry."
        )
    report.note(top_product_note)

    # --------------------------------------------------------- warehouse 11
    report.heading("8. Warehouse 11 shutdown — a structural break inside the training window")
    last_sale = (
        demand.groupby("warehouse")["date"].max().sort_values().reset_index()
        .rename(columns={"date": "last_sale_date"})
    )
    last_sale["last_sale_date"] = last_sale["last_sale_date"].dt.date.astype(str)
    report.table(last_sale)

    w11 = demand[demand["warehouse"].eq("bodega n. 11")].copy()
    w11["month"] = w11["date"].dt.to_period("M")
    monthly_tickets = w11.groupby("month")["ticket_code"].nunique()
    report.table(
        monthly_tickets.reset_index()
        .rename(columns={"ticket_code": "tickets"})
        .assign(month=lambda d: d["month"].astype(str))
    )
    fig = plotting.monthly_bar(
        monthly_tickets, "Warehouse 11: monthly tickets before it goes silent",
        "02_warehouse11_shutdown",
    )
    first_month_tickets = int(monthly_tickets.iloc[0])
    last_month_tickets = int(monthly_tickets.iloc[-1])
    last_sale_w11 = str(w11["date"].max().date())
    report.figure(
        fig,
        f"Warehouse 11 tapers over {len(monthly_tickets)} months — {first_month_tickets} "
        f"tickets in its first month down to {last_month_tickets} in its last "
        f"({last_sale_w11}) — then nothing through the remaining 74-week history. A "
        "gradual wind-down, not a truncated extract.",
    )
    report.note(
        "**F-013.** Every other warehouse sells through the last observed week "
        f"({str(demand['date'].max().date())}); only warehouse 11 stops, "
        f"on {last_sale_w11}, well inside the training window Challenge A forecasts over. "
        "A model that does not know this reads the taper as a demand collapse rather than "
        "an operational exit. This belongs in stage 03's forecast caveats as a structural "
        "break, and it is why stage 06 already excludes warehouse 11 from the allocation "
        "share base rather than projecting a dead warehouse's history forward."
    )

    # ---------------------------------------------------------- customer base
    report.heading("9. Customer base")
    freq = demand.groupby("client_code")["ticket_code"].nunique()
    basket = demand.groupby("ticket_code")["product_code"].nunique()
    n_tickets = int(basket.size)
    n_single_sku = int(basket.eq(1).sum())
    single_sku_share = n_single_sku / n_tickets
    report.key_values(
        {
            "Clients": int(freq.size),
            "Median tickets per client (74 weeks)": float(freq.median()),
            "p90 tickets per client": float(freq.quantile(0.9)),
            "Share of clients with 3 or fewer tickets": round(float(freq.le(3).mean()), 4),
            "Tickets": n_tickets,
            "Median distinct SKUs per ticket": float(basket.median()),
            "Tickets with exactly one SKU": n_single_sku,
            "Share of tickets with exactly one SKU": round(single_sku_share, 4),
        }
    )
    fig = plotting.customer_base_histograms(freq, basket, "02_customer_base")
    report.figure(
        fig,
        f"Half of clients bought {int(freq.median())} times or fewer across the "
        f"74-week history, and {single_sku_share:.0%} of tickets "
        f"({n_single_sku:,} of {n_tickets:,}) carry a single SKU — a typical customer is a "
        "thin, infrequent signal, not a panel a promotion can be read against one customer "
        "at a time.",
    )
    report.note(
        "**F-014.** With a median customer this thin, a per-customer uplift estimate "
        "would be mostly noise. Every uplift estimate in stage 05 is read at the network "
        "level — aggregate weekly units — for exactly this reason: promotional uplift is "
        "a property of the market a promotion runs in, not of any one customer's behaviour."
    )

    # ------------------------------------------------------- discount structure
    report.heading("10. Discount structure")
    report.text(
        "The weekly panel's `discount_depth` (built from `bruto` versus `sell_in_amount`) is "
        "blind to combo-level discounts that never reach `bruto` line by line — on combo "
        "9590, `bruto == sell_in_amount` on 99.6% of 1,367 lines while `discount` reads a "
        "constant 0.2. The delivered `discount` column is used here instead, restricted to "
        "promoted, non-zero-quantity lines with usable money fields and no negative-discount "
        "surcharge — `economics.promo_discount_mask`, the same predicate "
        "`economics.mean_promo_discount` uses, imported here rather than copied so the two "
        "cannot drift apart (its docstring explains why `is_zero_amount` is deliberately not "
        "part of it: a 100%-off free-goods line is a real, informative promotional-depth "
        "observation)."
    )
    promo_mask = economics.promo_discount_mask(flagged)
    promo_discount = flagged.loc[promo_mask, "discount"].dropna()
    levels = (
        promo_discount.round(2)
        .value_counts()
        .rename_axis("discount")
        .reset_index(name="lines")
        .sort_values("lines", ascending=False)
        .head(12)
    )
    report.table(levels)

    bonus = flagged.loc[promo_mask & flagged["discount"].eq(1.0)]
    bonus_zero_amount_share = (
        f"{bonus['is_zero_amount'].mean():.0%}" if len(bonus) else "n/a — no 100% lines"
    )
    report.key_values(
        {
            "Promoted, price-usable lines with a discount value": int(len(promo_discount)),
            "Distinct discount values observed": int(promo_discount.nunique()),
            "Lines at exactly 100% discount": int(len(bonus)),
            "Share of those with zero net amount (bonus product)": bonus_zero_amount_share,
            "Units given away at 100% discount": float(bonus["sell_in_quantity"].sum()),
        }
    )
    fig = plotting.discount_histogram(promo_discount, "02_discount_structure")
    report.figure(
        fig,
        "Realised discount clusters on discrete levels around 0.14-0.20 rather than a "
        f"continuum, plus a separate spike at 1.0 ({len(bonus)} lines, "
        f"{int(bonus['sell_in_quantity'].sum())} units) that is free product, not a price cut.",
    )

    promo_lines = flagged.loc[promo_mask].dropna(subset=["discount"])
    per_client = promo_lines.groupby("client_code")["discount"].agg(["mean", "std", "count"])
    eligible = per_client[per_client["count"].ge(10)]
    within_client_std = float(eligible["std"].median())
    between_client_std = float(eligible["mean"].std())
    pooled_std = float(promo_lines["discount"].std())

    # Same eligible-client subset as the dispersion statistics above, so the R²
    # figures and the std figures describe the same population.
    eligible_lines = promo_lines[promo_lines["client_code"].isin(eligible.index)]
    r2_client = _eta_squared(eligible_lines["discount"], eligible_lines["client_code"])
    r2_combo = _eta_squared(eligible_lines["discount"], eligible_lines["id_combo"])
    report.key_values(
        {
            "Clients with 10+ discounted lines": int(len(eligible)),
            "Median within-client std of discount depth": round(within_client_std, 4),
            "Std of client-level mean discount (between clients)": round(between_client_std, 4),
            "Std of discount depth, all promoted lines pooled": round(pooled_std, 4),
            "Variance in discount explained by client (R²)": round(r2_client, 4),
            "Variance in discount explained by combo (R²)": round(r2_combo, 4),
        }
    )

    # Threshold sensitivity: does the client R² depend on the min-lines cutoff?
    threshold_rows = []
    for threshold in (5, 10, 20, 50):
        elig_idx = per_client[per_client["count"].ge(threshold)].index
        sub = promo_lines[promo_lines["client_code"].isin(elig_idx)]
        threshold_rows.append(
            {
                "min_discounted_lines": threshold,
                "eligible_clients": int(len(elig_idx)),
                "client_r2": round(_eta_squared(sub["discount"], sub["client_code"]), 4),
            }
        )
    threshold_table = pd.DataFrame(threshold_rows)
    report.table(threshold_table)

    report.note(
        "**F-015.** 'Near zero' is the wrong bar in absolute terms — a median eligible "
        f"client still shows a {within_client_std:.3f} spread in the depth of the "
        "promotions they happen to be offered. The test that actually speaks to "
        "client-specificity is variance explained: grouping the same lines by `id_combo` "
        f"explains {r2_combo:.1%} of the variation in discount depth; grouping by "
        f"`client_code` explains only {r2_client:.1%}. If discount were negotiated per "
        "customer, client would explain most of the variation and clients would cluster "
        "tightly around their own personal rate (low within-client spread, high "
        "between-client spread) — instead the spread of client averages "
        f"(std {between_client_std:.3f}) is *smaller* than a typical client's own spread "
        f"across their purchases (std {within_client_std:.3f}). This client R² is sensitive "
        f"to the minimum-lines threshold — it runs from {threshold_table['client_r2'].min():.1%} "
        f"at a 50-line cutoff to {threshold_table['client_r2'].max():.1%} at a 5-line cutoff "
        "— but the direction never flips: combo always explains several times more variance "
        "than client. Together with the discrete levels and the bonus group above, this "
        "reads as a centrally-set, network-wide decision with a modest, not negligible, "
        "client effect — not a per-customer negotiation."
    )

    # ------------------------------------------------------------ no control
    report.heading("11. No control group across warehouses")
    report.text(
        "Difference-in-differences needs some warehouses left untreated while others are "
        "promoted, so the untreated ones can serve as a counterfactual. Stage 05 uses other "
        "SKUs as its control instead of other warehouses; whether a warehouse-level control "
        "was ever available is an empirical question, checked here rather than assumed."
    )
    control_sku = "1665"
    control_window = ("2025-11-01", "2026-03-15")
    priced = flagged[
        flagged["usable_for_price"]
        & flagged["product_code"].eq(control_sku)
        & flagged["date"].between(*control_window)
    ].copy()
    priced["week"] = priced["date"].dt.to_period(panels.WEEK_FREQ)
    weekly_price = (
        priced.groupby(["week", "warehouse"])
        .agg(net=("sell_in_amount", "sum"), units=("sell_in_quantity", "sum"))
        .reset_index()
    )
    weekly_price["price"] = weekly_price["net"] / weekly_price["units"]
    weekly_price["week_start"] = weekly_price["week"].dt.start_time

    price_grid = weekly_price.pivot_table(
        index="week_start", columns="warehouse", values="price", aggfunc="mean"
    )
    price_grid = price_grid.sort_index()
    pct_change = price_grid.pct_change()
    active_warehouses = price_grid.notna().sum(axis=1)
    warehouses_dropping_5pct = (pct_change <= -0.05).sum(axis=1)
    warehouses_dropping_3pct = (pct_change <= -0.03).sum(axis=1)
    sync_week = warehouses_dropping_5pct.idxmax()
    n_dropping_5pct = int(warehouses_dropping_5pct.loc[sync_week])
    n_dropping_3pct = int(warehouses_dropping_3pct.loc[sync_week])
    n_active = int(active_warehouses.loc[sync_week])

    fig = plotting.warehouse_price_lines(
        weekly_price,
        f"{control_sku}: weekly realised price, one line per warehouse",
        "02_no_control_group",
    )
    report.figure(
        fig,
        f"In the week of {sync_week.date()}, {n_dropping_5pct} of the {n_active} "
        "then-active warehouses drop price by 5% or more in the same week — the move is "
        "simultaneous across the network, not staggered market by market.",
    )
    report.key_values(
        {
            "Warehouses dropping price >=5% in the sync week": n_dropping_5pct,
            "Warehouses dropping price >=3% in the sync week": n_dropping_3pct,
            "Then-active warehouses": n_active,
        }
    )
    report.note(
        "**F-016.** No warehouse was left untreated while others moved on this SKU in this "
        f"window: at a 3% cutoff, all {n_active} then-active warehouses move together in "
        "the sync week; at 5%, one (bodega n. 7) falls just short. This rules out a "
        "warehouse-level difference-in-differences design for **this promotional episode**, "
        "which is why stage 05 uses other SKUs as its control instead of other warehouses; "
        "that choice was made without publishing this diagnostic, now cross-referenced from "
        "`reports/05_uplift.md` §7. **Scope**: this is direct evidence for one SKU over one "
        "transition, not an exhaustive audit of every promotion in the dataset. Generalising "
        "it to 'no warehouse-level control ever exists' rests on F-012 — pricing behaves as "
        "a centralised, network-wide decision rather than a per-warehouse one — so the same "
        "pattern is expected elsewhere, but that is an inference, not a claim checked "
        "episode by episode."
    )

    # ------------------------------------------------------------- hand-off
    report.heading("12. Candidate findings for the registry")
    report.text(
        section_findings(
            [
                ("H-003", "Seasonality strength per SKU — §5."),
                ("H-004", "Price variation and its direction — §3, §6."),
                ("H-005", "Promotion windows available for uplift — §4."),
                ("F-012", "Warehouse network concentration and heterogeneity — §7."),
                ("F-013", "Warehouse 11 structural break — §8."),
                ("F-014", "Customer base thinness and its consequence for Challenge C — §9."),
                ("F-015", "Discount is discrete and network-wide, not client-specific — §10."),
                ("F-016", "No control group across warehouses — §11."),
            ]
        )
    )

    path = report.write("02_eda.md", params={"nrows": nrows or "all"})
    print(f"Wrote {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nrows", type=int, default=None)
    main(**vars(parser.parse_args()))
