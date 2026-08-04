"""Loading the raw dataset.

One loader, used by every stage, so that dtype and date-parsing decisions are
made once and are visible in a single place.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config

# Read identifiers as strings: client/product/ticket codes are labels, not
# quantities, and letting pandas infer them invites silent type drift across
# stages (and drops leading zeros if any exist).
_DTYPES: dict[str, str] = {
    "year": "Int64",
    "month": "Int64",
    "warehouse": "string",
    "route": "string",
    "client_code": "string",
    "client_name": "string",
    "product_code": "string",
    "product_name": "string",
    "ticket_code": "string",
    "basket": "string",
    "category": "string",
    "subcategory": "string",
    "brand": "string",
    "id_combo": "string",
    "combo": "string",
    "sell_in_quantity": "float64",
    "sell_in_amount": "float64",
    "bruto": "float64",
    "discount": "float64",
    "product_cost": "float64",
}


def load_raw_transactions(nrows: int | None = None) -> pd.DataFrame:
    """Load the delivered transactions CSV with pinned dtypes and date format.

    Nothing is cleaned here. Filtering and imputation are the audit stage's job
    and must be logged with row counts (standard 01) — a loader that quietly
    drops rows would make that log a lie.
    """
    path = config.resolve_raw_dataset()
    frame = pd.read_csv(
        path,
        dtype=_DTYPES,
        nrows=nrows,
        keep_default_na=True,
    )
    frame["date"] = pd.to_datetime(
        frame["date"], format=config.DATE_FORMAT, errors="coerce"
    )
    return frame


def save_processed(frame: pd.DataFrame, name: str) -> Path:
    """Persist a derived dataset as Parquet under data/processed/."""
    config.ensure_output_dirs()
    path = config.PROCESSED_DIR / f"{name}.parquet"
    frame.to_parquet(path, index=False)
    return path
