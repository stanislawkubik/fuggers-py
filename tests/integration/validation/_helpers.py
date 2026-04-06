from __future__ import annotations

import json
from decimal import Decimal, getcontext

from fuggers_py.core import Date
from tests.helpers._paths import FIXTURES_ROOT


getcontext().prec = 50

FIXTURE_ROOT = FIXTURES_ROOT / "validation"


def load_fixture(*parts: str) -> dict[str, object]:
    fixture_path = FIXTURE_ROOT.joinpath(*parts)
    with fixture_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def D(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def parse_date(value: str) -> Date:
    return Date.parse(value)


def assert_decimal_close(actual: Decimal, expected: Decimal, tolerance: Decimal) -> None:
    assert abs(actual - expected) <= tolerance, f"{actual} !~= {expected} (tol={tolerance})"


def periodic_bond_reference(
    *,
    face: Decimal,
    coupon_rate: Decimal,
    yield_rate: Decimal,
    frequency: int,
    periods: int,
) -> dict[str, Decimal]:
    coupon = face * coupon_rate / Decimal(frequency)
    base = Decimal(1) + yield_rate / Decimal(frequency)
    price = Decimal(0)
    macaulay_numerator = Decimal(0)
    convexity_numerator = Decimal(0)
    for period in range(1, periods + 1):
        t = Decimal(period) / Decimal(frequency)
        cashflow = coupon + (face if period == periods else Decimal(0))
        discount = base ** period
        present_value = cashflow / discount
        price += present_value
        macaulay_numerator += t * present_value
        convexity_numerator += cashflow * t * (t + Decimal(1) / Decimal(frequency)) / (base ** (period + 2))
    macaulay = macaulay_numerator / price
    modified = macaulay / base
    convexity = convexity_numerator / price
    return {
        "clean_price": price,
        "macaulay_duration": macaulay,
        "modified_duration": modified,
        "convexity": convexity,
    }


def periodic_yield_from_price(
    *,
    face: Decimal,
    coupon_rate: Decimal,
    clean_price: Decimal,
    frequency: int,
    periods: int,
    lower: Decimal = Decimal("-0.50"),
    upper: Decimal = Decimal("0.50"),
    iterations: int = 200,
) -> Decimal:
    def price_at(yield_rate: Decimal) -> Decimal:
        return periodic_bond_reference(
            face=face,
            coupon_rate=coupon_rate,
            yield_rate=yield_rate,
            frequency=frequency,
            periods=periods,
        )["clean_price"]

    lo = lower
    hi = upper
    for _ in range(iterations):
        mid = (lo + hi) / Decimal(2)
        mid_price = price_at(mid)
        if mid_price > clean_price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / Decimal(2)


def is_business_day(date: Date) -> bool:
    return date.is_weekday()


def next_business_day(date: Date) -> Date:
    current = date
    while not is_business_day(current):
        current = current.add_days(1)
    return current


def previous_business_day(date: Date) -> Date:
    current = date
    while not is_business_day(current):
        current = current.add_days(-1)
    return current


def add_business_days(date: Date, days: int) -> Date:
    current = date
    remaining = abs(days)
    step = 1 if days >= 0 else -1
    while remaining > 0:
        current = current.add_days(step)
        if is_business_day(current):
            remaining -= 1
    return current


def business_accrual_schedule(start_date: Date, end_date: Date) -> list[tuple[Date, Date]]:
    if end_date <= start_date:
        return []
    current = next_business_day(start_date)
    schedule: list[tuple[Date, Date]] = []
    while current < end_date:
        next_business = add_business_days(current, 1)
        segment_end = Date.min(next_business, end_date)
        schedule.append((current, segment_end))
        current = next_business
    return schedule


def observed_fixing_date(
    schedule: list[tuple[Date, Date]],
    index: int,
    *,
    lookback_days: int,
    shift_type: str,
    lockout_days: int,
) -> Date:
    cutoff_index = index
    if lockout_days > 0 and index >= len(schedule) - lockout_days:
        cutoff_index = max(len(schedule) - lockout_days - 1, 0)
    fixing_date, _ = schedule[cutoff_index]
    if shift_type in {"LOOKBACK", "OBSERVATION_SHIFT"}:
        return previous_business_day(add_business_days(fixing_date, -lookback_days))
    return previous_business_day(fixing_date)


def manual_required_fixings(
    start_date: Date,
    end_date: Date,
    *,
    lookback_days: int,
    shift_type: str,
    lockout_days: int,
) -> list[Date]:
    schedule = business_accrual_schedule(start_date, end_date)
    return [
        observed_fixing_date(
            schedule,
            index,
            lookback_days=lookback_days,
            shift_type=shift_type,
            lockout_days=lockout_days,
        )
        for index, _ in enumerate(schedule)
    ]


def act_360_year_fraction(start_date: Date, end_date: Date) -> Decimal:
    return Decimal(start_date.days_between(end_date)) / Decimal(360)


def manual_overnight_coupon(
    *,
    start_date: Date,
    end_date: Date,
    quoted_spread: Decimal,
    notional: Decimal,
    fixings: dict[str, Decimal],
    lookback_days: int,
    shift_type: str,
    lockout_days: int,
) -> Decimal:
    schedule = business_accrual_schedule(start_date, end_date)
    compound = Decimal(1)
    for index, (segment_start, segment_end) in enumerate(schedule):
        observed = observed_fixing_date(
            schedule,
            index,
            lookback_days=lookback_days,
            shift_type=shift_type,
            lockout_days=lockout_days,
        )
        rate = fixings[observed.as_naive_date().isoformat()]
        compound *= Decimal(1) + rate * act_360_year_fraction(segment_start, segment_end)
    total_accrual = act_360_year_fraction(start_date, end_date)
    compounded_rate = (compound - Decimal(1)) / total_accrual
    return notional * (compounded_rate + quoted_spread) * total_accrual
