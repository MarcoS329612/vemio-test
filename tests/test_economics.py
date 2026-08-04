import pytest

from analysis import economics, quality


def test_recovered_margin_rate_matches_the_constructed_markup(transactions):
    rates = economics.sku_margin_rates(transactions)
    assert rates.loc[0, "margin_rate"] == 0.25
    assert bool(rates.loc[0, "in_documented_band"])


def test_free_goods_carry_a_negative_margin_under_the_adopted_reading(transactions):
    rates = economics.sku_margin_rates(transactions)
    result = quality.check_margin_convention(transactions, rates)

    assert result["free_goods_rows"] == 1
    assert result["free_goods_units"] == 10.0
    assert result["free_goods_null_cost_rows"] == 0
    assert result["applicable"] is True
    # Giving product away costs money.
    assert result["adopted_margin"] < 0
    # The rejected reading would make giveaways the most profitable lines.
    assert result["rejected_margin"] > 0
    assert result["passes"] is True


def test_check_is_not_applicable_when_there_are_no_free_goods_rows(transactions):
    """Zero free-goods rows (e.g. a small `--nrows` smoke run) must not read as a FAIL.

    `passes` alone must never be mistaken for a verdict here — callers gate on
    `applicable`, not on `passes` in isolation (round-1 review finding 1).
    """
    no_free_goods = transactions.iloc[:3].reset_index(drop=True)
    rates = economics.sku_margin_rates(no_free_goods)
    result = quality.check_margin_convention(no_free_goods, rates)

    assert result["free_goods_rows"] == 0
    assert result["applicable"] is False
    assert result["passes"] is False


def test_null_product_cost_on_a_free_goods_row_is_excluded_and_counted(
    transactions_with_null_cost_free_good,
):
    """A null `product_cost` must be dropped explicitly, not by pandas' skipna default.

    Round-1 review finding 2: silently relying on `Series.sum(skipna=True)` would
    let a null-cost free-goods row vanish from `rejected_margin` while still
    being counted in `free_goods_rows` — in the extreme (all free-goods rows
    null-cost) that turns a genuine "cannot compute" into a spurious `0.0`.
    """
    frame = transactions_with_null_cost_free_good
    rates = economics.sku_margin_rates(frame)
    result = quality.check_margin_convention(frame, rates)

    assert result["free_goods_rows"] == 2
    assert result["free_goods_units"] == 20.0
    assert result["free_goods_null_cost_rows"] == 1
    assert result["applicable"] is True
    # The margin sums reflect only the one priced free-goods row, not both.
    assert result["adopted_margin"] == pytest.approx(-400.0)
    assert result["rejected_margin"] == pytest.approx(625.0)
    assert result["passes"] is True


def test_rejected_margin_is_nan_not_zero_when_every_free_good_lacks_cost(transactions):
    """The extreme case from finding 2: all free-goods rows null-cost.

    `rejected_margin` must come out `NaN` (cannot be computed), never `0.0` —
    a `0.0` would silently flip `passes` to False for a reason unrelated to the
    margin convention.
    """
    frame = transactions.copy()
    frame.loc[frame["sell_in_amount"].le(0), "product_cost"] = float("nan")
    rates = economics.sku_margin_rates(frame)
    result = quality.check_margin_convention(frame, rates)

    assert result["free_goods_rows"] == 1
    assert result["free_goods_null_cost_rows"] == 1
    assert result["adopted_margin"] != result["adopted_margin"]  # NaN
    assert result["rejected_margin"] != result["rejected_margin"]  # NaN
    assert result["applicable"] is True
    assert result["passes"] is False
