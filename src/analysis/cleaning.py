"""Traceable cleaning: flag records, never silently drop them (standard 01).

Every rule here adds a boolean column and an entry to the decision log. Callers
then choose their own filter, which is what keeps "we excluded X rows" auditable
instead of buried inside a loader.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Rule:
    """One cleaning rule: what it flags, and why it exists."""

    flag: str
    description: str
    rationale: str
    predicate: Callable[[pd.DataFrame], pd.Series]


RULES: tuple[Rule, ...] = (
    Rule(
        flag="is_zero_quantity",
        description="sell_in_quantity <= 0",
        rationale=(
            "No units moved, so the row carries no demand signal. Kept for revenue "
            "reconciliation but excluded from any units-based model."
        ),
        predicate=lambda f: f["sell_in_quantity"].le(0),
    ),
    Rule(
        flag="is_zero_amount",
        description="sell_in_amount <= 0 while units moved",
        rationale=(
            "Units shipped at no charge — free goods or a fully-discounted combo leg. "
            "Real demand, so kept for forecasting; excluded from price work because a "
            "zero realised price is not a point on a demand curve."
        ),
        predicate=lambda f: f["sell_in_amount"].le(0) & f["sell_in_quantity"].gt(0),
    ),
    Rule(
        flag="is_missing_money",
        description="bruto or product_cost is null",
        rationale=(
            "Cannot compute list price or margin. Excluded from elasticity; harmless "
            "for unit forecasting."
        ),
        predicate=lambda f: f["bruto"].isna() | f["product_cost"].isna(),
    ),
    Rule(
        flag="is_incomplete_metadata",
        description="category, brand or basket is null",
        rationale=(
            "The record the case statement warns about (F-005). Isolated rather than "
            "deleted so its footprint stays visible."
        ),
        predicate=lambda f: f[["category", "brand", "basket"]].isna().any(axis=1),
    ),
    Rule(
        flag="is_negative_discount",
        description="discount < 0",
        rationale=(
            "A negative discount is a surcharge, which the dictionary does not describe "
            "(F-004, open question Q6). Excluded from price work pending an answer; the "
            "units are still real, so they stay in the demand panel."
        ),
        predicate=lambda f: f["discount"].lt(0),
    ),
    Rule(
        flag="is_promo",
        description="id_combo is not null",
        rationale="Not a defect — the promo marker every challenge depends on.",
        predicate=lambda f: f["id_combo"].notna(),
    ),
)


def flag_records(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add one boolean column per rule and return (flagged frame, decision log)."""
    out = frame.copy()
    entries = []
    for rule in RULES:
        mask = rule.predicate(out).fillna(False)
        out[rule.flag] = mask
        entries.append(
            {
                "flag": rule.flag,
                "rule": rule.description,
                "rows": int(mask.sum()),
                "rows_%": round(float(mask.mean()) * 100, 3),
                "units": float(out.loc[mask, "sell_in_quantity"].sum()),
                "rationale": rule.rationale,
            }
        )

    out["usable_for_demand"] = ~out["is_zero_quantity"]
    out["usable_for_price"] = (
        ~out["is_zero_quantity"]
        & ~out["is_zero_amount"]
        & ~out["is_missing_money"]
        & ~out["is_negative_discount"]
    )

    log = pd.DataFrame(entries)
    for name, mask in (
        ("usable_for_demand", out["usable_for_demand"]),
        ("usable_for_price", out["usable_for_price"]),
    ):
        log.loc[len(log)] = {
            "flag": name,
            "rule": "derived selector",
            "rows": int(mask.sum()),
            "rows_%": round(float(mask.mean()) * 100, 3),
            "units": float(out.loc[mask, "sell_in_quantity"].sum()),
            "rationale": (
                "Rows entering the demand panel."
                if name == "usable_for_demand"
                else "Rows entering price/elasticity work."
            ),
        }
    return out, log
