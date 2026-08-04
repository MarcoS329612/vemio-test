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
    # Giving product away costs money.
    assert result["adopted_margin"] < 0
    # The rejected reading would make giveaways the most profitable lines.
    assert result["rejected_margin"] > 0
    assert result["passes"] is True
