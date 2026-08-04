import pytest

from analysis import economics, quality


def _with_price_validity_flags(frame):
    """Mirror the `cleaning.py` predicates `mean_promo_discount` composes from.

    The synthetic `transactions` fixture deliberately carries no `id_combo`,
    `category` etc. (conftest.py), so `cleaning.flag_records` cannot run on it
    directly. These three flags are exactly `cleaning.py`'s rule predicates,
    reproduced here rather than reimplemented differently, so a test frame
    behaves the way a real cleaned frame would for the columns
    `mean_promo_discount` actually reads.
    """
    frame = frame.copy()
    frame["is_zero_quantity"] = frame["sell_in_quantity"].le(0)
    frame["is_missing_money"] = frame["bruto"].isna() | frame["product_cost"].isna()
    frame["is_negative_discount"] = frame["discount"].lt(0)
    return frame


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


def test_break_even_discount_is_the_markup_identity(transactions):
    rates = economics.sku_margin_rates(transactions)
    table = economics.break_even_discount(rates)

    # margin / (1 + margin) — 0.25 / 1.25
    assert table.loc[0, "break_even_discount"] == 0.2


def test_at_the_break_even_discount_price_equals_cost(transactions):
    rates = economics.sku_margin_rates(transactions)
    depth = float(economics.break_even_discount(rates).loc[0, "break_even_discount"])

    list_price = 50.0
    cost = economics.unit_cost_from_list(list_price, 0.25)
    assert list_price * (1 - depth) == pytest.approx(cost)


def test_mean_promo_discount_reflects_discount_field_not_bruto_versus_net(transactions):
    """Must fail against the weekly panel's bruto/net proxy — the F-004 defect.

    Sets `bruto == sell_in_amount` on every promo line, which is exactly what
    the panel's `discount_depth` (1 − net/gross) would read as zero discount,
    while `discount` itself records a real, constant 0.2 combo discount that
    never reached `bruto` line by line — the pattern documented for combo 9590.
    A version of `mean_promo_discount` that derived its answer from bruto vs.
    net instead of from `discount` would report 0.0 here, not 0.2.
    """
    frame = transactions.copy()
    frame["discount"] = 0.0
    promo_rows = frame["is_promo"]
    frame.loc[promo_rows, "sell_in_amount"] = frame.loc[promo_rows, "bruto"]
    frame.loc[promo_rows, "discount"] = 0.2
    frame = _with_price_validity_flags(frame)

    result = economics.mean_promo_discount(frame)

    assert result.loc[0, "mean_promo_discount"] == pytest.approx(0.2)


def test_mean_promo_discount_excludes_negative_discount_rows(transactions):
    """Must fail against a version that includes negative-`discount` rows.

    A negative `discount` is an unexplained surcharge, not a promotional depth
    (F-004, open question Q6), and `cleaning.py`'s `is_negative_discount` rule
    exists precisely to flag such rows — round-2 review found 9,928 of the
    dataset's 10,084 negative-`discount` promo rows concentrate on a single
    SKU. Here one promo row is given a wildly negative `discount`; if it were
    still included, its -5.0 discount would drag the weighted mean far below
    0.2. Excluding it must leave the mean at exactly the remaining rows' 0.2.
    """
    frame = transactions.copy()
    frame["discount"] = 0.2
    frame.loc[1, "discount"] = -5.0
    frame = _with_price_validity_flags(frame)

    result = economics.mean_promo_discount(frame)

    assert result.loc[0, "mean_promo_discount"] == pytest.approx(0.2)


def test_mean_promo_discount_includes_free_goods_lines(transactions):
    """Must fail against a version that filters on `usable_for_price`.

    A 100%-discount free-goods line is a legitimate, informative promotional
    observation — arguably the deepest one there is — not a data problem.
    `usable_for_price` excludes it via `is_zero_amount` (`sell_in_amount <= 0`
    while units moved), which is the right rule for price/quantity regression
    but irrelevant to whether `discount` can be trusted (round-3 review).
    The fixture's bonus-product row (`sell_in_amount == 0`, quantity 10, the
    last of the three promo rows) is given `discount = 1.0`; a version that
    reused `usable_for_price` would drop it and report 0.2, not the blended
    value that includes it.
    """
    frame = transactions.copy()
    frame["discount"] = 0.2
    frame.loc[3, "discount"] = 1.0  # bonus-product row: sell_in_amount == 0, quantity 10
    frame = _with_price_validity_flags(frame)

    result = economics.mean_promo_discount(frame)

    expected = (0.2 * 16 + 0.2 * 12 + 1.0 * 10) / (16 + 12 + 10)
    assert result.loc[0, "mean_promo_discount"] == pytest.approx(expected, abs=1e-4)
