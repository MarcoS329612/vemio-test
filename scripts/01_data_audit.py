"""Stage 01 — Data intake & quality audit.

Implements methodology standard 01: verify the grain instead of trusting it,
quantify every quality issue before deciding anything, and leave the numbers in
an artifact so the cleaning decisions that follow are auditable.

This stage detects and reports. It does not clean: filters belong to the next
stage, and each one is logged with its row counts.

    uv run scripts/01_data_audit.py

Output: reports/01_data_quality.md
"""

from __future__ import annotations

import argparse

from analysis import config, io, quality
from analysis.reporting import MarkdownReport, section_findings


def main(nrows: int | None = None) -> None:
    print(f"Loading {config.RAW_DATASET_FILENAME} …")
    frame = io.load_raw_transactions(nrows=nrows)
    print(f"Loaded {len(frame):,} rows × {frame.shape[1]} columns")

    report = MarkdownReport(
        title="Stage 01 — Data quality audit",
        stage="scripts/01_data_audit.py",
        subtitle=(
            "Verification of the delivered dataset against the data dictionary, and "
            "quantification of every quality issue **before** any cleaning decision "
            "(methodology standard 01)."
        ),
    )

    # ---------------------------------------------------------------- shape
    report.heading("1. Shape and schema")
    report.key_values(
        {
            "Rows": len(frame),
            "Columns": frame.shape[1],
            "Columns documented but not delivered": ", ".join(
                config.DOCUMENTED_BUT_MISSING_COLUMNS
            )
            or "none",
        }
    )
    report.table(quality.schema_check(frame))
    report.note(
        "`product_margin` is described in the data dictionary and explicitly required by "
        "Challenge B, but it is not in the delivered file — finding **F-001**, open "
        "question **Q1**. Section 7 tests whether it can be reconstructed (**H-001**)."
    )

    # ------------------------------------------------------------- entities
    report.heading("2. Entity counts vs. the case statement")
    report.table(
        quality.cardinality(
            frame,
            ["product_code", "warehouse", "route", "client_code", "ticket_code",
             "id_combo", "combo", "category", "subcategory", "brand", "basket"],
        )
    )
    report.text(
        "The case states 6 SKUs, 12 warehouses, ~52,500 clients, ~359,000 transactions "
        "and 79 combos. Divergences here are findings, not rounding."
    )

    # ----------------------------------------------------------------- date
    report.heading("3. Date parsing — verified, not assumed")
    report.key_values(quality.date_format_evidence(frame))
    report.note(
        "Dates are read as `dd/mm/yyyy`. The `year` and `month` columns are an "
        "independent witness: under a `mm/dd` misreading they would disagree with the "
        "parsed date wherever the true day exceeds 12. Full agreement plus the presence "
        "of days above 12 is what makes the format claim evidence rather than assumption."
    )

    # ------------------------------------------------------------- coverage
    report.heading("4. Temporal coverage")
    report.key_values(quality.coverage(frame))

    # ---------------------------------------------------------------- grain
    report.heading("5. Grain verification")
    report.key_values(quality.grain_check(frame, config.CLAIMED_GRAIN_KEYS))
    report.key_values(quality.duplicate_rows(frame))
    report.note(
        "The dictionary *claims* the grain is day × client × product × ticket × promo. "
        "A non-unique result is not necessarily a defect — it may mean the same SKU "
        "appears twice on a ticket under different promo lines — but it changes how the "
        "weekly panel must be aggregated, so it is resolved before modelling."
    )

    # ------------------------------------------------------- completeness
    report.heading("6. Completeness and validity")
    report.table(quality.completeness(frame))
    report.text(
        "Implausible-but-structurally-valid records, with the volume and revenue they "
        "carry — the second and third columns are what decide whether excluding them is "
        "material:"
    )
    report.table(quality.validity(frame))
    report.note(
        "Nothing is dropped by this stage. Records are quantified here and handled in "
        "stage 02 by flag columns with a logged rationale, so downstream steps choose "
        "their own filters (standard 01, anti-pattern: over-cleaning)."
    )

    report.heading("7. The incomplete-metadata record")
    incomplete = quality.incomplete_metadata(frame)
    report.text(
        f"The case statement warns of a record with incomplete metadata. "
        f"Rows matching that description: **{len(incomplete)}**."
    )
    report.table(incomplete)

    # ------------------------------------------------------ reconciliation
    report.heading("8. Reconciliation of monetary columns")
    report.text(
        "How `bruto`, `sell_in_amount` and `discount` relate, by segment. Organic rows "
        "match every reading trivially (no discount, no gap), so the rightmost column — "
        "promo rows that actually show a gross/net gap — is the discriminating one:"
    )
    report.table(quality.reconciliation(frame))
    report.text("Value distribution of `discount`, which settles its unit of measure:")
    report.table(quality.discount_profile(frame))
    report.note(
        "`discount` determines the effective unit price, which is the independent "
        "variable of Challenge B — hypothesis **H-002**, open question **Q2**."
    )

    report.heading("9. Cost and margin structure (the missing `product_margin`)")
    report.table(quality.cost_margin_structure(frame))
    report.note(
        "Tests **H-001**. Two readings at once: whether the per-SKU ratio is constant "
        "(deciding whether the missing column can be reconstructed), and whether its "
        "direction implies a positive commercial margin. See finding **F-003**."
    )

    report.heading("10. Realised price variation per SKU (Challenge B selection input)")
    report.table(quality.price_variation(frame))
    report.note(
        "Elasticity requires a SKU whose price actually moved (**H-004**). Counting "
        "distinct realised prices makes the SKU choice a documented criterion rather "
        "than a convenient one. `max/median` flags SKUs with extreme upper tails worth "
        "inspecting before they are treated as price signal."
    )

    # ------------------------------------------------------------- hand-off
    report.heading("11. Candidate findings for the registry")
    report.text(
        section_findings(
            [
                ("F-001", "`product_margin` absent from the delivered CSV — §1, §9."),
                ("F-003", "Direction of the cost/price relationship — §9."),
                ("F-004", "Unit and sign of `discount` — §8."),
                ("F-005", "The incomplete-metadata record — §7."),
                ("H-002", "Which reconciliation reading holds — §8."),
                ("H-004", "Which SKU supports an elasticity estimate — §10."),
            ]
        )
    )
    report.text(
        "Promoting an observation to a registered finding is a human decision "
        "(standard 07). Update `docs/FINDINGS.md` and `docs/HYPOTHESES.md` from the "
        "numbers above before proceeding to stage 02."
    )

    path = report.write("01_data_quality.md", params={"nrows": nrows or "all"})
    print(f"Wrote {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--nrows",
        type=int,
        default=None,
        help="Read only the first N rows (smoke-testing the pipeline).",
    )
    main(**vars(parser.parse_args()))
