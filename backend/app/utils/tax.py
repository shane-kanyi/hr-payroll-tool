from decimal import ROUND_HALF_UP, Decimal

# Simple progressive monthly tax brackets. Deliberately does not match any
# real country's tax code - see docs/PAYROLL.md for full rationale. Each
# entry is (upper_bound_of_band, rate); the last band's upper_bound is None
# (unbounded top band).
TAX_BRACKETS: list[tuple[Decimal | None, Decimal]] = [
    (Decimal("1000.00"), Decimal("0.00")),
    (Decimal("3000.00"), Decimal("0.10")),
    (Decimal("6000.00"), Decimal("0.20")),
    (None, Decimal("0.25")),
]

_CENTS = Decimal("0.01")


def calculate_progressive_tax(taxable_income: Decimal) -> tuple[Decimal, list[dict]]:
    """Marginal (bracket-by-bracket) tax calculation.

    Only the slice of income inside each band is taxed at that band's rate,
    so a salary one cent above a bracket boundary is never worse off than
    one cent below it - there is no "cliff". Returns (total_tax, breakdown)
    where breakdown documents exactly how each band contributed, so a
    payslip/audit can show its work.
    """
    if taxable_income <= 0:
        return Decimal("0.00"), []

    remaining = taxable_income
    lower = Decimal("0.00")
    total_tax = Decimal("0.00")
    breakdown: list[dict] = []

    for upper, rate in TAX_BRACKETS:
        if remaining <= 0:
            break

        band_width = (upper - lower) if upper is not None else remaining
        amount_in_band = min(remaining, band_width)

        if amount_in_band > 0:
            band_tax = (amount_in_band * rate).quantize(_CENTS, rounding=ROUND_HALF_UP)
            total_tax += band_tax
            breakdown.append(
                {
                    "band_lower": str(lower),
                    "band_upper": str(upper) if upper is not None else None,
                    "rate": float(rate),
                    "amount_taxed": str(amount_in_band.quantize(_CENTS, rounding=ROUND_HALF_UP)),
                    "tax": str(band_tax),
                }
            )

        remaining -= amount_in_band
        if upper is not None:
            lower = upper

    return total_tax.quantize(_CENTS, rounding=ROUND_HALF_UP), breakdown
