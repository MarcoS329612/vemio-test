"""Synthetic fixtures.

Small hand-built frames, not samples of the real data: a test that depends on
the 77 MB input is a test nobody runs.
"""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def transactions() -> pd.DataFrame:
    """Four lines for one SKU with a 25% markup, one of them free goods.

    `product_cost` is built as `bruto * (1 + margin)`, which is what the
    delivered file actually contains (F-003).
    """
    margin = 0.25
    gross = [1000.0, 800.0, 600.0, 500.0]
    net = [1000.0, 680.0, 480.0, 0.0]  # last line is bonus product
    return pd.DataFrame(
        {
            "product_code": ["1665"] * 4,
            "product_name": ["Antitranspirante 150 ml C"] * 4,
            "date": pd.to_datetime(
                ["2025-01-06", "2025-01-13", "2025-01-20", "2025-01-27"]
            ),
            "sell_in_quantity": [20.0, 16.0, 12.0, 10.0],
            "sell_in_amount": net,
            "bruto": gross,
            "product_cost": [g * (1 + margin) for g in gross],
            "is_promo": [False, True, True, True],
            "usable_for_demand": [True] * 4,
            "usable_for_price": [True, True, True, False],
        }
    )
