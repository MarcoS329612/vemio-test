"""Figure helpers.

Matplotlib defaults are tuned once here so every figure in the deliverable reads
as one set. Each function returns the saved path, which the report embeds with a
caption carrying the takeaway (standard 02).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display in a script context
import matplotlib.pyplot as plt  # noqa: E402

from . import config  # noqa: E402

INK = "#1f2933"
MUTED = "#8592a0"
ACCENT = "#1f4e5f"
WARM = "#c2683a"
COOL = "#4a7fa5"
SERIES_COLORS = (ACCENT, WARM, COOL, "#7a9e6f", "#9b6a9d", "#b0913b")


def _style(ax: plt.Axes, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=11, color=INK, pad=10, loc="left")
    ax.set_xlabel(xlabel, fontsize=9, color=MUTED)
    ax.set_ylabel(ylabel, fontsize=9, color=MUTED)
    ax.tick_params(labelsize=8, colors=MUTED)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#d8dee4")
    ax.grid(axis="y", color="#eef1f4", linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig: plt.Figure, name: str) -> Path:
    config.ensure_output_dirs()
    path = config.FIGURES_DIR / f"{name}.png"
    fig.savefig(path, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def weekly_series_grid(panel, products: list[str], name: str) -> Path:
    """One weekly-units panel per SKU, sharing an x axis for visual comparison."""
    rows = len(products)
    fig, axes = plt.subplots(rows, 1, figsize=(10, 2.2 * rows), sharex=True)
    axes = [axes] if rows == 1 else list(axes)

    for ax, (code, color) in zip(axes, zip(products, SERIES_COLORS, strict=False), strict=False):
        series = panel[panel["product_code"].eq(code) & panel["is_complete_week"]]
        label = series["product_name"].iloc[0] if len(series) else code
        ax.plot(series["week_start"], series["units"], color=color, linewidth=1.6)
        promo = series[series["promo_share"].gt(0.5)]
        ax.scatter(
            promo["week_start"], promo["units"], s=14, color=WARM, zorder=3,
            label="week >50% promo units",
        )
        _style(ax, f"{code} — {label}", "", "units / week")
        if len(promo):
            ax.legend(fontsize=7, frameon=False, loc="upper left")

    axes[-1].set_xlabel("week", fontsize=9, color=MUTED)
    fig.tight_layout()
    return save(fig, name)


def price_quantity_scatter(frame, title: str, name: str) -> Path:
    """Log-log price vs units, the visual precondition for an elasticity claim."""
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.scatter(
        frame["avg_net_price"], frame["units"],
        s=26, color=ACCENT, alpha=0.75, edgecolor="white", linewidth=0.5,
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    _style(ax, title, "realised net unit price (log)", "units / week (log)")
    fig.tight_layout()
    return save(fig, name)


def forecast_plot(history, actual, forecasts: dict, title: str, name: str) -> Path:
    """History, holdout actuals and each candidate's forecast on one axis."""
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.plot(history["week_start"], history["units"], color=MUTED,
            linewidth=1.4, label="history")
    ax.plot(actual["week_start"], actual["units"], color=INK,
            linewidth=2.0, label="actual (holdout)")
    palette = (WARM, COOL, "#7a9e6f", "#9b6a9d")
    for (label, values), color in zip(forecasts.items(), palette, strict=False):
        ax.plot(actual["week_start"], values, color=color, linewidth=1.6,
                linestyle="--", label=label)
    ax.axvline(actual["week_start"].iloc[0], color="#d8dee4", linewidth=1.0)
    _style(ax, title, "week", "units / week")
    ax.legend(fontsize=8, frameon=False, ncol=2)
    fig.tight_layout()
    return save(fig, name)


def simulator_curves(grid, title: str, name: str) -> Path:
    """Revenue and margin against price, with the observed range shaded."""
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.plot(grid["price"], grid["revenue"], color=ACCENT, linewidth=1.9, label="revenue")
    ax.plot(grid["price"], grid["margin_value"], color=WARM, linewidth=1.9, label="margin ($)")
    _style(ax, title, "net unit price", "per week")
    ax.legend(fontsize=8, frameon=False)

    twin = ax.twinx()
    twin.plot(grid["price"], grid["units"], color=MUTED, linewidth=1.2,
              linestyle=":", label="units")
    twin.set_ylabel("units / week", fontsize=9, color=MUTED)
    twin.tick_params(labelsize=8, colors=MUTED)
    for spine in ("top", "left"):
        twin.spines[spine].set_visible(False)
    fig.tight_layout()
    return save(fig, name)


def uplift_plot(series, window, title: str, name: str) -> Path:
    """Weekly units with the promo window shaded and the counterfactual overlaid."""
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(series["week_start"], series["units"], color=INK, linewidth=1.6, label="actual")
    if "counterfactual" in series:
        ax.plot(series["week_start"], series["counterfactual"], color=WARM,
                linewidth=1.5, linestyle="--", label="counterfactual baseline")
    ax.axvspan(window[0], window[1], color="#f0e6dd", zorder=0, label="promo window")
    _style(ax, title, "week", "units / week")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    return save(fig, name)
