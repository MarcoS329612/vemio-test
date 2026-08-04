"""Paths, dataset resolution, and shared constants.

Every module and script resolves data locations through here. Hardcoding a path
anywhere else breaks the provenance guarantee in DR-0002.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

# --------------------------------------------------------------------------- paths

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

DOCS_DIR = PROJECT_ROOT / "docs"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# --------------------------------------------------------------- source dataset

# Original filename as delivered by VEMIO, kept verbatim so provenance is
# self-evident. Checksum recorded in docs/case/README.md.
RAW_DATASET_FILENAME = "20260701_Prueba_tecnica_AI Engineer.csv"
RAW_DATASET_SHA256 = (
    "a8a9b8a3d5c91955719d755c3d1e2778980088831a9e49af07ef838bbf12ef86"
)

# The delivered CSV writes dates as dd/mm/yyyy. Parsing this wrong silently
# reorders 17 months of history, so the format is pinned rather than inferred
# and is re-verified against the `month` column in the data audit.
DATE_FORMAT = "%d/%m/%Y"

# Columns as delivered (21). `product_margin` is documented in the data
# dictionary and required by Challenge B, but is NOT delivered — see finding
# F-001 and open question Q1 before relying on it.
EXPECTED_COLUMNS: tuple[str, ...] = (
    "year",
    "month",
    "warehouse",
    "route",
    "client_code",
    "client_name",
    "product_code",
    "product_name",
    "date",
    "ticket_code",
    "sell_in_quantity",
    "sell_in_amount",
    "basket",
    "category",
    "brand",
    "id_combo",
    "combo",
    "bruto",
    "subcategory",
    "discount",
    "product_cost",
)

DOCUMENTED_BUT_MISSING_COLUMNS: tuple[str, ...] = ("product_margin",)

# Grain claimed by the data dictionary: day x client x product x ticket x promo.
# Verified (not assumed) in the data audit.
CLAIMED_GRAIN_KEYS: tuple[str, ...] = (
    "date",
    "client_code",
    "product_code",
    "ticket_code",
    "id_combo",
)

NUMERIC_COLUMNS: tuple[str, ...] = (
    "sell_in_quantity",
    "sell_in_amount",
    "bruto",
    "discount",
    "product_cost",
)

# --------------------------------------------------------------------- helpers


def resolve_raw_dataset() -> Path:
    """Return the path to the raw dataset, with an actionable error if absent."""
    path = RAW_DIR / RAW_DATASET_FILENAME
    if not path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at {path}.\n"
            "The dataset is git-ignored (client data, 77 MB — see DR-0002).\n"
            f"Place the file delivered by VEMIO at: {path}"
        )
    return path


def sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    """Streaming SHA-256, so an 80 MB file does not land in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_raw_checksum() -> tuple[bool, str]:
    """Check the raw file against the recorded checksum.

    Returns (matches, actual_digest). A mismatch means results are no longer
    comparable to earlier runs — the report says so rather than failing silently.
    """
    actual = sha256(resolve_raw_dataset())
    return actual == RAW_DATASET_SHA256, actual


def ensure_output_dirs() -> None:
    """Create the generated-output directories if they do not exist."""
    for directory in (PROCESSED_DIR, REPORTS_DIR, FIGURES_DIR):
        directory.mkdir(parents=True, exist_ok=True)
