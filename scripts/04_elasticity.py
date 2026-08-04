"""Stage 04 — Price elasticity and simulator (Challenge B).

    uv run scripts/04_elasticity.py

Output: reports/04_elasticity.md
"""

from __future__ import annotations

import argparse

import pandas as pd

from analysis import cleaning, config, economics, elasticity, io, plotting
from analysis.reporting import MarkdownReport

# Selection criterion, fixed before estimating: the SKU with the widest observed
# price support, since that is what bounds the simulator's valid domain.
SKU = "1665"


def main(sku: str = SKU) -> None:
    raw = io.load_raw_transactions()
    flagged, _ = cleaning.flag_records(raw)

    rates = economics.sku_margin_rates(flagged)
    margin_rate = economics.margin_rate_for(rates, sku)

    data = elasticity.weekly_price_panel(flagged, sku)
    name = flagged.loc[flagged["product_code"].eq(sku), "product_name"].iloc[0]

    fit = elasticity.estimate_elasticity(data)
    grid = elasticity.simulate(fit, data, margin_rate)
    recommendation = elasticity.recommend_price(grid, fit["elasticity"])
    band_low, band_high = elasticity.observed_price_band(data)

    # Same per-SKU population as the break-even table in section 6, so the two
    # tables are directly comparable.
    price_bands = []
    for row in rates.itertuples():
        panel = elasticity.weekly_price_panel(flagged, row.product_code)
        if panel.empty:
            continue
        low, high = elasticity.observed_price_band(panel)
        price_bands.append(
            {
                "product_code": row.product_code,
                "product_name": row.product_name,
                "weeks": len(panel),
                "raw_min": round(float(panel["price"].min()), 2),
                "raw_max": round(float(panel["price"].max()), 2),
                "band_p05": round(low, 2),
                "band_p95": round(high, 2),
            }
        )
    price_band_table = pd.DataFrame(price_bands)

    report = MarkdownReport(
        title="Stage 04 — Price elasticity and simulator (Challenge B)",
        stage="scripts/04_elasticity.py",
        subtitle=f"SKU {sku} — {name}. Demand response to realised price, and a "
                 "simulator bounded to the p5–p95 observed price band.",
    )

    # ------------------------------------------------------- identification
    report.heading("1. Where the price variation comes from")
    report.text(
        f"SKU {sku} was selected on a criterion fixed before estimating: the widest "
        "observed price support, since that is exactly what bounds the simulator's valid "
        "domain. Two SKUs qualified (finding F-006); this one has the wider range and the "
        "larger volume."
    )
    report.key_values({
        "Weeks in the price panel": len(data),
        "Realised price range": f"{data['price'].min():.2f} – {data['price'].max():.2f}",
        "Median realised price": round(float(data["price"].median()), 2),
        "Median list price": round(float(data["list_price"].median()), 2),
        "Median promo share of units": round(float(data["promo_share"].median()), 3),
    })
    report.note(
        "**This matters more than the coefficient.** This SKU is on promotion in nearly "
        "every week of the history, so its price moves through changes in *discount "
        "depth*, not through list-price changes. What is estimated is therefore the "
        "response to realised price under promotion. That is the right input for a "
        "trade-promotion decision — the actual question being asked — but it is not "
        "evidence about how demand would respond to a permanent list-price change, and "
        "it should not be quoted as such."
    )

    # ------------------------------------------------------------ estimate
    report.heading("2. Elasticity estimate")
    report.text(
        "Log-log demand regression with a linear trend and annual Fourier terms, so the "
        "price coefficient is not absorbing seasonality or drift. Standard errors are "
        "Newey-West (HAC), because weekly demand is autocorrelated and plain OLS errors "
        "would report more confidence than the evidence supports."
    )
    report.key_values({
        "Price elasticity of demand": round(fit["elasticity"], 3),
        "Standard error (HAC)": round(fit["std_error"], 3),
        "95% confidence interval": f"[{fit['ci_low']:.3f}, {fit['ci_high']:.3f}]",
        "p-value": f"{fit['p_value']:.4f}",
        "R²": round(fit["r_squared"], 3),
        "Weeks used": fit["n_weeks"],
    })
    magnitude = abs(fit["elasticity"])
    report.text(
        f"A 1% increase in realised price is associated with a {magnitude:.2f}% change in "
        f"weekly units, in the opposite direction. Demand is "
        f"{'elastic' if magnitude > 1 else 'inelastic'}: "
        + (
            "a price cut raises revenue, because volume grows faster than price falls."
            if magnitude > 1 else
            "a price cut *lowers* revenue, because volume does not grow enough to offset it."
        )
    )

    report.note(
        "**An elasticity near −5 is high for a household staple, and that is informative "
        "rather than suspicious.** This is *sell-in* — shipments to distributors, not "
        "purchases by shoppers. Distributors buy ahead when a discount is offered, so "
        "sell-in absorbs both genuine demand response and forward-buying, and it is "
        "routinely several times more elastic than sell-out. The practical reading: this "
        "number tells you how much distributors will load in when you discount. It does "
        "**not** tell you how many extra units reach consumers, and treating it as "
        "consumer demand would substantially overstate the benefit of a price cut."
    )

    figure = plotting.price_quantity_scatter(
        data.rename(columns={"price": "avg_net_price"}),
        f"{sku} — {name}: weekly realised price vs units",
        f"04_price_quantity_{sku}",
    )
    report.figure(
        figure,
        f"{sku} ({name}): each point is one week. The downward slope on log-log axes is "
        "what a constant-elasticity model assumes; the visible scatter is the "
        "uncertainty the confidence interval quantifies.",
    )

    # ------------------------------------------------------------ economics
    report.heading("3. Unit economics used by the simulator")
    report.text(
        "Margin cannot be read off the file: `product_margin` is absent and `product_cost` "
        "exceeds gross revenue on every row (findings F-001 and F-003, open question Q5). "
        "The adopted reading is stated here so every number below can be re-derived — or "
        "rejected — on its own terms."
    )
    report.table(rates)
    report.key_values({
        "Assumption": economics.ASSUMED_READING,
        f"Recovered margin rate for {sku}": margin_rate,
        "List price anchor (median)": round(float(data["list_price"].median()), 2),
        "Implied unit cost": round(
            economics.unit_cost_from_list(float(data["list_price"].median()), margin_rate), 2
        ),
    })
    literal_cost = float(data["list_price"].median()) * (1 + margin_rate)
    report.note(
        f"**Sensitivity to the assumption.** Taken literally, `product_cost` implies a unit "
        f"cost of {literal_cost:.2f} against a median realised price of "
        f"{float(data['price'].median()):.2f} — every price in the observed range would be "
        "loss-making and no pricing recommendation could be made at all. That the literal "
        "reading yields an impossible business is the argument for the correction, not a "
        "reason to hide it."
    )

    # ------------------------------------------------------------ simulator
    report.heading("4. Simulator")
    report.heading("Price range with evidence behind it", level=3)
    report.text(
        "The raw min and max of realised weekly price are not prices anyone set: the floor "
        "is free bonus product shipped inside a combo (a zero-revenue line still carrying "
        "units), and the ceiling is a handful of weeks where net exceeds gross and the "
        "implied discount is negative (F-004). Both tails are artefacts of how a combo "
        "reconciles, not evidence about a price the business would charge. The simulator is "
        "therefore bounded to the p5–p95 band of realised price instead, and it **refuses** "
        "to price outside that band — `predict_units` raises rather than extrapolating."
    )
    report.table(price_band_table)
    sku_band_row = price_band_table.loc[price_band_table["product_code"].eq(sku)].iloc[0]
    report.note(
        f"**SKU {sku}, concretely.** The raw observed range was "
        f"{sku_band_row['raw_min']:.2f}–{sku_band_row['raw_max']:.2f}. The p5–p95 band used "
        f"from here on is {band_low:.2f}–{band_high:.2f} — narrower at the top, because the "
        "raw ceiling was the artefact tail described above."
    )
    report.text(
        f"Expected weekly demand, revenue and margin across the observed price band "
        f"({recommendation['observed_min']:.2f} – {recommendation['observed_max']:.2f}), "
        "holding season and trend at their average. Every tenth grid point:"
    )
    report.table(grid.iloc[::6].reset_index(drop=True))

    simulator_figure = plotting.simulator_curves(
        grid, f"{sku} — {name}: revenue and margin against price", f"04_simulator_{sku}"
    )
    report.figure(
        simulator_figure,
        f"{sku} ({name}): revenue and margin in currency against realised unit price, with "
        "expected units on the right axis. Where the two curves peak at different prices "
        "is precisely the trade-off the commercial team has to settle.",
    )
    report.note(
        "**The simulator refuses to extrapolate.** Its grid is constructed from the "
        "p5–p95 observed price band and cannot be queried outside it. A constant-elasticity "
        "curve extended past the data is arithmetic, not evidence — and the further it "
        "goes, the more confident it looks."
    )

    # ------------------------------------------------------ recommendation
    report.heading("5. Recommended price")
    if recommendation["revenue_has_interior_optimum"]:
        revenue_row_label = "Revenue-maximising price"
        revenue_row_value: object = recommendation["revenue_max_price"]
    else:
        revenue_row_label = "Revenue objective — NO interior optimum (see note below)"
        revenue_row_value = (
            f"{recommendation['revenue_max_price']:.2f} (band edge, not an optimum)"
        )
    report.key_values({
        revenue_row_label: revenue_row_value,
        "Margin-maximising price": recommendation["margin_max_price"],
        "Recommendation rule": recommendation["recommendation_rule"],
        "Recommended price": recommendation["recommended_price"],
        "Expected units/week at that price": round(recommendation["recommended_units"], 0),
        "Expected weekly revenue": round(recommendation["recommended_revenue"], 0),
        "Expected weekly margin ($)": round(recommendation["recommended_margin_value"], 0),
        "Expected margin (%)": round(recommendation["recommended_margin_pct"] * 100, 1),
    })
    if recommendation["recommendation_rule"] == "margin_only":
        report.text(
            "**Per DR-0007, the recommended price is the margin-maximising price outright, "
            "not a revenue/margin balance.** Demand at this SKU is elastic "
            f"(|elasticity| = {abs(fit['elasticity']):.2f} > 1), so revenue rises without "
            "bound as price falls — there is no price, inside the band or out of it, at "
            "which revenue maximisation has a finite answer. An objective with no interior "
            "optimum anywhere cannot carry half the weight in a compromise, so it is dropped "
            "from the recommendation rather than averaged in."
        )
    else:
        report.text(
            "The balanced price maximises the average of revenue and margin, each normalised "
            "to its own maximum. The rule is stated rather than hidden so the commercial team "
            "can argue with the weighting instead of with a black box — if margin matters more "
            "this quarter, the margin-maximising price is the one to take."
        )

    report.heading("Price / units / revenue / margin trade-off across the band", level=3)
    report.text(
        "The full shape of the trade-off, not just the single price the recommendation "
        "above picks out — a commercial team weighing a different point on this curve "
        "needs to see what it gives up, not only where the model's preferred point sits."
    )
    trade_off = grid[["price", "units", "revenue", "margin_value", "margin_pct"]]
    report.table(trade_off.iloc[::5].reset_index(drop=True))

    break_even = grid.loc[grid["margin_value"].gt(0), "price"]
    break_even_price = float(break_even.min()) if len(break_even) else float("nan")
    loss_weeks = int((data["price"] < break_even_price).sum())
    assumed_cost = economics.unit_cost_from_list(
        float(data["list_price"].median()), margin_rate
    )
    report.note(
        f"**The single most actionable number here is the break-even price: "
        f"{break_even_price:.2f}.** Below it, every additional unit sold loses money under "
        f"the assumed cost of {assumed_cost:.2f}. "
        f"{loss_weeks} of the {len(data)} weeks in the history — {loss_weeks / len(data):.0%} — "
        "were priced below that line. The elastic demand is real, but the volume it buys at "
        "those prices is bought at a loss."
    )
    if not recommendation["revenue_has_interior_optimum"]:
        exponent = 1 + fit["elasticity"]
        report.note(
            "**With demand this elastic, the revenue objective has no finite solution — "
            "not merely none inside the band.** Revenue = price × units, and under a "
            f"constant-elasticity curve, revenue scales as price^({exponent:.3f}). At the "
            f"fitted elasticity of {fit['elasticity']:.3f} that exponent is negative, so "
            "revenue falls monotonically as price rises across the **entire positive price "
            "domain**, not just past the band. There is no interior maximum anywhere to "
            f"miss. The figure {recommendation['revenue_max_price']:.2f} above is nothing "
            "but wherever the grid's lower edge happens to sit — it would move to any other "
            "lower edge chosen, and it is not evidence of an optimal price. The margin "
            f"curve is different: it has a genuine interior maximum at "
            f"{recommendation['margin_max_price']:.2f}, comfortably inside the band, which "
            "is why the recommendation is built on margin, not revenue."
        )
        pull = recommendation["margin_max_price"] - recommendation["balanced_price"]
        report.note(
            "**DR-0007: the revenue-weighted balanced rule is not used as the recommendation "
            "here.** An objective with no interior optimum anywhere cannot carry half the "
            "weight in a compromise — it would vote for the cheapest price in the grid on "
            "every comparison, regardless of the margin curve's shape. The balanced rule "
            f"would have recommended {recommendation['balanced_price']:.2f}, a fixed "
            f"{pull:.2f} discount off the margin optimum with no economic content behind "
            "its size (the finding disclosed in round-1 review). The recommendation above "
            f"is therefore the margin-maximising price, {recommendation['margin_max_price']:.2f}, "
            "directly — see DR-0007 for the alternatives considered and rejected."
        )
    else:
        report.note(
            "**The revenue-maximising price sits on the boundary of the observed price "
            "band**, which is a corner solution: it means revenue was still rising as "
            "price fell at the cheapest price the band admits, so the true revenue "
            "optimum may lie below anything the data has seen. That is precisely where "
            "the simulator refuses to answer, and the refusal is the correct behaviour."
        )

    # -------------------------------------------------------- break-even by SKU
    report.heading("6. Break-even discount by SKU")
    report.text(
        "The break-even price above is specific to a single SKU and a single list-price "
        "anchor. The same identity — cost = list / (1 + margin), so price equals cost at a "
        "discount depth of margin / (1 + margin) — restated as a *depth* generalises to all "
        "six SKUs and is directly comparable across them, even though their list prices "
        "differ by an order of magnitude."
    )
    report.text(
        "**This must be compared against the actual promotional discount, not against the "
        "weekly panel's `discount_depth`.** That panel field is a bruto-vs-net proxy "
        "(1 − avg net price / avg list price), and it is blind to combo-level discounts that "
        "never reach `bruto` line by line — the reconciliation defect finding F-004 "
        "documents. `discount` is the field the data dictionary defines as the promotional "
        "depth, so the comparison below uses it directly: unit-weighted, over promoted lines "
        "with a trustworthy `discount` — excluding zero-quantity, missing-cost/revenue and "
        "negative-`discount` rows (F-004, open question Q6), but **keeping** zero-amount "
        "free-goods lines, since a 100%-discount giveaway is a legitimate, informative "
        "promotional-depth observation, not a data problem, and dropping it would understate "
        "exactly the SKUs that lean most on bonus volume. The table makes the panel's "
        "disagreement with this measure visible rather than asserting it — for SKUs 9304, "
        "1857 and 1858 the panel proxy reads roughly a tenth of the discount that `discount` "
        "itself records, because their combos apply the cut at a level the proxy cannot see."
    )
    null_discount_share = economics.null_discount_unit_share(flagged)
    sku_1283_null_share = float(
        null_discount_share.loc[
            null_discount_share["product_code"].eq("1283"), "null_discount_unit_share"
        ].iloc[0]
    )
    report.text(
        f"**One SKU's figure rests partly on an imputation, and that is disclosed here "
        f"rather than left to the source.** `mean_promo_discount` treats a null `discount` "
        f"as zero rather than dropping the row. For SKU 1283, {sku_1283_null_share:.2f}% of "
        "promoted-line units carry a null `discount` — negligible for every other SKU — so "
        "its figure below is the most exposed to that convention."
    )
    promo_discount = economics.mean_promo_discount(flagged)
    weekly_panel = pd.read_parquet(config.PROCESSED_DIR / "weekly_sku_panel.parquet")
    complete_weeks = weekly_panel[weekly_panel["is_complete_week"]]
    bruto_proxy_depth = (
        complete_weeks.groupby(["product_code", "product_name"])["discount_depth"]
        .mean()
        .round(4)
        .rename("bruto_proxy_discount_depth")
        .reset_index()
    )
    break_even_by_sku = (
        economics.break_even_discount(rates)
        .merge(promo_discount, on=["product_code", "product_name"], how="left")
        .merge(bruto_proxy_depth, on=["product_code", "product_name"], how="left")
        .merge(null_discount_share, on=["product_code", "product_name"], how="left")
    )
    # Positive cushion is distance still available before a promoted line sells under cost;
    # negative means it already has. Stated as its own column so a reader compares one
    # number, not two — round-3 review found a bare True/False table left a near-miss SKU
    # looking like a comfortable no.
    break_even_by_sku["cushion"] = (
        break_even_by_sku["break_even_discount"] - break_even_by_sku["mean_promo_discount"]
    ).round(4)
    break_even_by_sku["already_below_cost"] = break_even_by_sku["cushion"].lt(0)
    report.table(break_even_by_sku)

    at_a_loss = break_even_by_sku[break_even_by_sku["already_below_cost"]]
    if len(at_a_loss):
        called_out = ", ".join(
            f"{row.product_code} ({row.product_name})" for row in at_a_loss.itertuples()
        )
        report.note(
            f"**{called_out} already sell under cost on the typical promoted line, not just "
            "in isolated deep-discount episodes.** For these SKUs, the unit-weighted mean "
            "promotional discount exceeds the break-even depth, so the erosion is a standing "
            "loss built into the ordinary promotional cadence — not an occasional dip that a "
            "few unusually deep weeks explain away."
        )
    else:
        report.note(
            "No SKU's mean promotional discount exceeds its break-even depth: on average, "
            "every SKU still clears cost on a promoted line, even though individual "
            "promotional episodes may not (see the break-even price analysis above for "
            "SKU-level detail)."
        )

    marginal_cushion = 0.02  # within two points of break-even is a close call, not a clear no
    marginal = break_even_by_sku[
        ~break_even_by_sku["already_below_cost"]
        & break_even_by_sku["cushion"].lt(marginal_cushion)
    ]
    if len(marginal):
        called_out_marginal = ", ".join(
            f"{row.product_code} ({row.product_name}, cushion {row.cushion:.2%})"
            for row in marginal.itertuples()
        )
        report.note(
            f"**{called_out_marginal} is a close call, not a comfortable no.** Its cushion "
            "is within two points of the break-even depth, and the underlying figure has "
            "moved by roughly a point across review rounds purely from filtering questions "
            "unrelated to the discount itself (which rows count as price-usable). A cushion "
            "this thin should be treated as marginal — worth re-checking before it is relied "
            "on for a repeat-or-drop call — not as safely clear of cost."
        )

    report.heading("7. Risks and assumptions")
    report.bullets([
        "**Promotional confound.** Price variation comes from discount depth on an "
        "almost-always-promoted SKU. The estimate is a promotional price response, not a "
        "structural list-price elasticity.",
        f"**Reconstructed margin.** Every margin figure rests on `cost = list / (1 + "
        f"{margin_rate})`. If VEMIO answers Q5 differently, the revenue column survives "
        "unchanged and the margin column does not.",
        "**Constant elasticity is an approximation.** A single coefficient assumes the same "
        "percentage response at every price. Over a range this wide the true curve almost "
        "certainly bends; the estimate is most trustworthy near the middle of the observed "
        "range, which is where the recommendation sits.",
        "**Weekly aggregation hides mix.** A week's realised price averages across "
        "warehouses, clients and combo structures. Two weeks with the same average price "
        "can have very different underlying offers.",
        "**No competitor or stock data.** Demand shifts caused by rival pricing or "
        "out-of-stock weeks are absorbed into the residual, which widens the interval and "
        "could bias the coefficient if either correlates with discount timing.",
        f"**{fit['n_weeks']} weekly observations.** Enough for one coefficient with honest "
        "error bars, not enough for interaction effects or a flexible functional form.",
    ])

    path = report.write("04_elasticity.md", params={"sku": sku})
    grid.to_csv(config.REPORTS_DIR / f"04_simulator_grid_{sku}.csv", index=False)
    print(f"Wrote {path}")
    print(f"Elasticity {fit['elasticity']:.3f}  recommended price "
          f"{recommendation['recommended_price']:.2f} ({recommendation['recommendation_rule']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sku", type=str, default=SKU)
    main(**vars(parser.parse_args()))
