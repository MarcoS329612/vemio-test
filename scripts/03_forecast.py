"""Stage 03 — Weekly demand forecasting (Challenge A).

Baseline-first, rolling-origin validation, and a metric chosen for replenishment
rather than by habit (standard 04).

    uv run scripts/03_forecast.py

Output: reports/03_forecast.md
"""

from __future__ import annotations

import argparse

import pandas as pd

from analysis import config, forecasting, plotting
from analysis.reporting import MarkdownReport

# Chosen for coverage of the failure modes, not for convenience:
#   1857 — largest volume, promoted only in the final quarter → the clean case
#   1283 — 26x swing between its trough and peak months → the seasonal case
#   1665 — promoted in ~95% of weeks → the promo-saturated case
SKUS = ("1857", "1283", "1665")
HORIZON = 12


def main(horizon: int = HORIZON, origins: int = 5) -> None:
    panel = pd.read_parquet(config.PROCESSED_DIR / "weekly_sku_panel.parquet")
    panel = panel[panel["is_complete_week"]].copy()

    report = MarkdownReport(
        title="Stage 03 — Demand forecasting (Challenge A)",
        stage="scripts/03_forecast.py",
        subtitle=(
            f"Weekly unit demand for three SKUs, {horizon} weeks ahead, validated on "
            f"{origins} rolling origins with no future information available to any model."
        ),
    )

    report.heading("1. How the models are validated")
    report.text(
        f"Every model sees only weeks 1…t and is scored on weeks t+1…t+{horizon}, for "
        f"{origins} different values of t spaced three weeks apart. Nothing in a model's "
        "input can be computed from the period it is being scored on."
    )
    report.bullets([
        "**naive (last week)** and **moving average (4w)** — the floor. A model that "
        "cannot beat these is not earning its complexity.",
        "**seasonal naive (52w)** — repeats the same week of last year. With ~1.4 years "
        "of history this is the only way an annual pattern can be used at all.",
        "**ETS (damped trend)** — exponential smoothing. Seasonality is deliberately "
        "switched off: a 52-week period needs two full cycles to estimate, and this "
        "history has 1.4.",
        "**harmonic ridge** — linear trend plus Fourier terms for the annual cycle, on "
        "log units. Deterministic in the future, so there is nothing to feed back "
        "recursively and no path for leakage.",
        "**damped drift** — recent level plus a geometrically damped continuation of the "
        "recent slope. Added after a first pass showed every level-only model "
        "under-forecasting by 13–30%: the series drift upward and a flat forecast cannot "
        "follow. Damping prevents that slope being extrapolated indefinitely.",
        "**ensemble (MA + drift + ETS)** — the mean of three forecasts that fail "
        "differently. The cheapest reliable improvement in forecasting practice, because "
        "no single component has to be right.",
    ])
    report.note(
        "**Why WAPE is the headline metric.** MAPE divides by each week's actual, so a "
        "quiet 20-unit week can contribute a 300% error and dominate the average, and it "
        "structurally rewards under-forecasting — an over-forecast's error is unbounded "
        "while an under-forecast caps at 100%. For replenishment, being short is at least "
        "as costly as being long, and cost is incurred per unit. WAPE weights every unit "
        "equally. MASE is reported alongside because it answers the stakeholder's actual "
        "question: is this better than doing nothing? Below 1.0 means yes."
    )

    chosen: dict[str, str] = {}
    forecast_rows: list[dict] = []

    for code in SKUS:
        series = panel[panel["product_code"].eq(code)].sort_values("week_start")
        name = series["product_name"].iloc[0]
        units = series["units"].to_numpy(dtype=float)
        weeks = series["week_of_year"].to_numpy(dtype=float)

        scores = forecasting.evaluate(units, weeks, horizon, n_origins=origins)
        aggregate = forecasting.aggregate_scores(scores)
        best = aggregate.iloc[0]["model"]
        chosen[code] = best

        report.heading(f"2.{SKUS.index(code) + 1} SKU {code} — {name}")
        report.key_values({
            "Weeks of history": len(units),
            "Median weekly units": round(float(pd.Series(units).median()), 0),
            "Coefficient of variation": round(float(units.std() / units.mean()), 3),
            "Median promo share": round(float(series["promo_share"].median()), 3),
        })
        report.text(
            f"Mean scores across {origins} rolling origins, best WAPE first. "
            "`skill_vs_best_baseline` below 1.0 means the model beat every baseline:"
        )
        report.table(aggregate)

        baseline_wape = float(
            aggregate.loc[aggregate["model"].isin(forecasting.BASELINES), "WAPE"].min()
        )
        best_wape = float(aggregate.iloc[0]["WAPE"])
        improvement = (baseline_wape - best_wape) / baseline_wape * 100

        if best in forecasting.BASELINES:
            verdict = (
                f"**No candidate beat the baselines.** `{best}` wins at WAPE "
                f"{best_wape:.3f}, so that is what is used — the honest answer is that "
                "this series does not support anything more elaborate."
            )
        else:
            verdict = (
                f"**`{best}` is selected**, at WAPE {best_wape:.3f} against the best "
                f"baseline's {baseline_wape:.3f} — an improvement of {improvement:.1f}%."
            )
        report.text(verdict)

        # Illustrative holdout: the most recent origin, shown rather than described.
        split = len(units) - horizon
        history = series.iloc[:split]
        actual = series.iloc[split:]
        curves = {
            label: forecasting.MODELS[label](
                units[:split], horizon, weeks[:split]
            )
            for label in dict.fromkeys([best, "seasonal naive (52w)", "moving average (4w)"])
        }
        figure = plotting.forecast_plot(
            history, actual, curves,
            f"{code} — {name}: most recent {horizon}-week holdout",
            f"03_holdout_{code}",
        )
        report.figure(
            figure,
            f"{code} ({name}): the final {horizon} weeks held out, with the selected "
            f"model and two baselines. The vertical line is the forecast origin — "
            "everything to its right was unavailable to every model shown.",
        )

        forward = forecasting.forecast_forward(units, weeks, horizon, best)
        future_weeks = pd.date_range(
            series["week_start"].max() + pd.Timedelta(weeks=1), periods=horizon, freq="7D"
        )
        for week, value in zip(future_weeks, forward, strict=True):
            forecast_rows.append({
                "product_code": code,
                "product_name": name,
                "week_start": week.date(),
                "forecast_units": round(float(value), 0),
                "model": best,
            })

    # ------------------------------------------------------------- forward
    report.heading("3. Forward forecast")
    report.text(
        f"Each SKU's selected model, refit on the full history, projected {horizon} weeks "
        f"beyond the last complete week ({panel['week_start'].max().date()}):"
    )
    forward_frame = pd.DataFrame(forecast_rows)
    report.table(
        forward_frame.pivot_table(
            index="week_start", columns="product_code", values="forecast_units"
        ).reset_index()
    )
    report.key_values({
        f"Total forecast units, {code}": float(
            forward_frame.loc[forward_frame["product_code"].eq(code), "forecast_units"].sum()
        )
        for code in SKUS
    })

    report.heading("4. What limits these numbers")
    report.bullets([
        "**17 months is not two seasons.** Any annual pattern is observed roughly once, "
        "so a seasonal model cannot separate a genuine yearly cycle from a one-off event. "
        "This is the binding constraint on SKU 1283, whose demand swings 26-fold between "
        "its trough and peak months.",
        "**Promotions are not in the model.** Promotional pressure drives a large share of "
        "weekly variation, but future promo plans are not in the dataset. Including a "
        "promo covariate would require assuming the plan is known — defensible in "
        "production, where trade marketing sets the calendar in advance, and leakage in a "
        "backtest. The forecast is therefore a demand expectation under a promotional "
        "pattern resembling the recent past.",
        "**Point forecasts, not intervals.** A replenishment decision needs a service "
        "level, which needs a distribution. Prediction intervals are the first thing to "
        "add with more time.",
        "**The last week may be soft.** Extracts often catch the final period mid-settlement; "
        "partial weeks are already excluded, but a systematically under-reported final "
        "week would bias every model's level downward.",
        "**Warehouse 11's shutdown sits inside the training window, not at its edge "
        "(F-013).** Every other warehouse sells through the last observed week; warehouse "
        "11's ticket count tapers from 324/month in Jan 2025 to 9 in Aug 2025 and then to "
        "zero for the remaining ~9.5 months — an 8-month wind-down, not a data cut. These "
        "national SKU-week totals include that decline, so a model reading the taper alone "
        "would see it as demand collapsing rather than one warehouse exiting. Stage 06's "
        "warehouse allocation already excludes warehouse 11 from its share base for exactly "
        "this reason; the forecast above is at the national level and does not separate the "
        "two.",
    ])

    path = report.write("03_forecast.md", params={"horizon": horizon, "origins": origins})
    forward_frame.to_csv(config.REPORTS_DIR / "03_forecast_next_12_weeks.csv", index=False)
    print(f"Wrote {path}")
    print("Selected models:", chosen)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--horizon", type=int, default=HORIZON)
    parser.add_argument("--origins", type=int, default=5)
    main(**vars(parser.parse_args()))
