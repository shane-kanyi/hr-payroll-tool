from decimal import Decimal

from app.utils.tax import calculate_progressive_tax


def test_zero_or_negative_income_has_no_tax():
    tax, breakdown = calculate_progressive_tax(Decimal("0"))
    assert tax == Decimal("0.00")
    assert breakdown == []


def test_income_entirely_within_zero_rate_band():
    tax, _ = calculate_progressive_tax(Decimal("500.00"))
    assert tax == Decimal("0.00")


def test_income_exactly_at_first_boundary_stays_in_zero_band():
    tax, _ = calculate_progressive_tax(Decimal("1000.00"))
    assert tax == Decimal("0.00")


def test_income_spanning_first_two_bands():
    # 1000 @ 0% + 500 @ 10% = 50.00
    tax, breakdown = calculate_progressive_tax(Decimal("1500.00"))
    assert tax == Decimal("50.00")
    assert len(breakdown) == 2  # the 0%-band and the 10%-band both contributed income


def test_income_exactly_at_second_boundary():
    # 1000 @ 0% + 2000 @ 10% = 200.00
    tax, _ = calculate_progressive_tax(Decimal("3000.00"))
    assert tax == Decimal("200.00")


def test_income_spanning_three_bands():
    # 1000@0 + 2000@10%=200 + 100@20%=20 => 220.00
    tax, _ = calculate_progressive_tax(Decimal("3100.00"))
    assert tax == Decimal("220.00")


def test_income_in_top_unbounded_band():
    # 1000@0 + 2000@10%=200 + 3000@20%=600 + 4000@25%=1000 => 1800.00
    tax, _ = calculate_progressive_tax(Decimal("10000.00"))
    assert tax == Decimal("1800.00")


def test_no_cliff_at_bracket_boundary():
    """A marginal/progressive scheme must never make crossing a bracket
    boundary worse than staying just under it - only the incremental slice
    is taxed at the higher rate. A naive 'apply the top rate to the whole
    amount' implementation would jump from 199.90 to ~600.20 here."""
    just_under, _ = calculate_progressive_tax(Decimal("2999.00"))
    at_boundary, _ = calculate_progressive_tax(Decimal("3000.00"))
    just_over, _ = calculate_progressive_tax(Decimal("3001.00"))

    assert just_under == Decimal("199.90")
    assert at_boundary == Decimal("200.00")
    assert just_over == Decimal("200.20")

    # A $2 increase in income should cost a few cents in extra tax, not
    # hundreds of dollars.
    assert (just_over - just_under) < Decimal("1.00")


def test_ten_dollar_increase_past_boundary_only_taxes_the_marginal_slice():
    at_boundary, _ = calculate_progressive_tax(Decimal("3000.00"))
    ten_more, _ = calculate_progressive_tax(Decimal("3010.00"))
    assert ten_more - at_boundary == Decimal("2.00")  # $10 @ 20% marginal rate
