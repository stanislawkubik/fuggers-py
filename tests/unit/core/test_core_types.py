from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from fuggers_py._core import (
    CashFlow,
    CashFlowSchedule,
    CashFlowType,
    Compounding,
    Currency,
    Date,
    Price,
    Spread,
    SpreadType,
    Yield,
)
from fuggers_py._core.errors import InvalidSpreadError


def test_date_constructors_and_accessors() -> None:
    d = Date.from_ymd(2024, 2, 29)
    assert str(d) == "2024-02-29"
    assert d.year() == 2024
    assert d.month() == 2
    assert d.day() == 29
    assert d.is_leap_year() is True
    assert d.days_in_month() == 29
    assert d.days_in_year() == 366

    parsed = Date.parse("2024-02-29")
    assert parsed == d

    today = Date.today()
    assert today.as_naive_date() == dt.date.today()


def test_date_arithmetic_and_clamping() -> None:
    d = Date.parse("2023-01-31").add_months(1)
    assert str(d) == "2023-02-28"

    d2 = Date.parse("2024-01-31").add_months(1)
    assert str(d2) == "2024-02-29"

    leap = Date.parse("2024-02-29").add_years(1)
    assert str(leap) == "2025-02-28"

    assert str(Date.parse("2024-03-01").add_days(-1)) == "2024-02-29"


def test_weekday_weekend_helpers() -> None:
    sat = Date.parse("2025-03-01")
    assert sat.is_weekend() is True
    assert sat.next_weekday() == Date.parse("2025-03-03")
    assert sat.prev_weekday() == Date.parse("2025-02-28")

    mon = Date.parse("2025-03-03")
    assert mon.is_weekday() is True
    assert mon.next_weekday() == mon
    assert mon.prev_weekday() == mon

    assert mon.add_business_days(1) == Date.parse("2025-03-04")
    assert mon.add_business_days(-1) == Date.parse("2025-02-28")
    assert mon.business_days_between(Date.parse("2025-03-04")) == 1


def test_price_conversions() -> None:
    p = Price.new(98.50, Currency.USD)
    assert p.as_percentage() == Decimal("98.50")
    assert p.as_decimal() == Decimal("0.985")

    p2 = Price.from_decimal(Decimal("0.985"), Currency.USD)
    assert p2.as_percentage() == Decimal("98.5")
    assert p2.currency() == Currency.USD

    assert Price.par(Currency.EUR).as_percentage() == Decimal("100")


def test_yield_conversions_and_compounding() -> None:
    y = Yield.from_percentage(5, Compounding.ANNUAL)
    assert y.value() == Decimal("0.05")
    assert y.as_bps() == 500

    y2 = Yield.from_bps(250, Compounding.SEMI_ANNUAL)
    assert y2.value() == Decimal("0.025")
    assert y2.as_percentage() == Decimal("2.5")

    y_sa = y.convert_to(Compounding.SEMI_ANNUAL)
    # Equivalent annual accumulation must match closely.
    a1 = (Decimal(1) + y.value())  # annual periodic
    a2 = (Decimal(1) + y_sa.value() / Decimal(2)) ** Decimal(2)
    assert abs(a1 - a2) < Decimal("1e-12")

    y_cont = y.convert_to(Compounding.CONTINUOUS)
    assert abs(y_cont.value().exp() - a1) < Decimal("1e-12")


def test_spread_conversions_and_arithmetic() -> None:
    s = Spread.new(125, SpreadType.Z_SPREAD)
    assert s.as_decimal() == Decimal("0.0125")
    assert s.as_percentage() == Decimal("1.25")
    assert s.is_positive() is True

    s2 = Spread.from_decimal(Decimal("0.005"), SpreadType.Z_SPREAD)
    assert s2.as_bps() == Decimal("50")
    assert (s + s2).as_bps() == Decimal("175")

    with pytest.raises(InvalidSpreadError):
        _ = s + Spread.new(10, SpreadType.G_SPREAD)


def test_cashflow_constructors_and_metadata() -> None:
    pay = Date.parse("2025-06-30")
    a_start = Date.parse("2025-01-01")
    a_end = Date.parse("2025-06-30")

    cf = CashFlow.coupon_with_accrual(pay, "1.23", a_start, a_end)
    assert cf.cf_type() == CashFlowType.COUPON
    assert cf.accrual_start() == a_start
    assert cf.accrual_end() == a_end
    assert cf.is_coupon() is True
    assert cf.is_principal() is False

    fl = CashFlow.floating_coupon(pay, 1, reference_rate="0.0325")
    assert fl.is_floating() is True
    assert fl.reference_rate() == Decimal("0.0325")

    pp = CashFlow.partial_principal(pay, "10.0", notional_after="90.0")
    assert pp.cf_type() == CashFlowType.PARTIAL_PRINCIPAL
    assert pp.notional_after() == Decimal("90.0")

    fp = CashFlow.final_payment(pay, "2.0", "100.0")
    assert fp.cf_type() == CashFlowType.COUPON_AND_PRINCIPAL
    assert fp.amount() == Decimal("102.0")
    assert fp.notional_after() == Decimal("0")


def test_cashflow_schedule_container() -> None:
    cfs = CashFlowSchedule.new()
    d1 = Date.parse("2025-01-01")
    d2 = Date.parse("2025-02-01")
    d3 = Date.parse("2025-03-01")

    cfs.push(CashFlow.coupon(d2, "2.0"))
    cfs.push(CashFlow.coupon(d1, "1.0"))
    cfs.push(CashFlow.principal(d3, "100.0"))

    assert len(cfs) == 3
    assert cfs.total() == Decimal("103.0")

    cfs.sort_by_date()
    dates = [cf.date() for cf in cfs]
    assert dates == [d1, d2, d3]

    after = cfs.after(d1)
    assert [cf.date() for cf in after] == [d2, d3]

