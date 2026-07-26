from datetime import date, timedelta
from decimal import Decimal


def count_business_days(start: date, end: date) -> Decimal:
    """Inclusive count of Mon-Fri days between start and end.

    No public-holiday calendar is considered - see docs/LEAVE.md for why
    that's an explicit, documented simplification rather than an oversight.
    """
    if end < start:
        return Decimal(0)

    total_days = (end - start).days + 1
    full_weeks, remainder = divmod(total_days, 7)
    business_days = full_weeks * 5

    current = start + timedelta(days=full_weeks * 7)
    for _ in range(remainder):
        if current.weekday() < 5:  # Mon-Fri
            business_days += 1
        current += timedelta(days=1)

    return Decimal(business_days)


def add_business_days(start: date, business_days: int) -> date:
    """Returns the date `business_days` business days after `start`."""
    current = start
    remaining = business_days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def ranges_overlap(start_a: date, end_a: date, start_b: date, end_b: date) -> bool:
    return start_a <= end_b and end_a >= start_b


def clip_range(start: date, end: date, window_start: date, window_end: date) -> tuple[date, date] | None:
    """Clips [start, end] to [window_start, window_end]. None if disjoint."""
    clipped_start = max(start, window_start)
    clipped_end = min(end, window_end)
    if clipped_start > clipped_end:
        return None
    return clipped_start, clipped_end
