from __future__ import annotations

from decimal import Decimal

from fuggers_py._core import Date
from fuggers_py._core.daycounts import (
    Act360,
    Act365,
    Act365Fixed,
    Act365Leap,
    ActActAfb,
    ActActIcma,
    ActActIsda,
    DayCountConvention,
    Thirty360,
    Thirty360E,
    Thirty360EIsda,
    Thirty360German,
    Thirty360US,
)
from fuggers_py._core.types import Frequency


def test_act_daycounts_basic() -> None:
    start = Date.parse("2024-01-01")
    end = Date.parse("2024-02-01")  # 31 days

    assert Act360().day_count(start, end) == 31
    assert Act360().year_fraction(start, end) == Decimal(31) / Decimal(360)

    assert Act365Fixed().year_fraction(start, end) == Decimal(31) / Decimal(365)


def test_act365_leap_denominator_switch() -> None:
    # (Feb 28, Mar 1] contains Feb 29 in a leap year => denom 366
    start = Date.parse("2024-02-28")
    end = Date.parse("2024-03-01")
    assert Act365Leap().day_count(start, end) == 2
    assert Act365Leap().year_fraction(start, end) == Decimal(2) / Decimal(366)


def test_act_act_isda_cross_year_single_day() -> None:
    start = Date.parse("2024-12-31")
    end = Date.parse("2025-01-01")
    assert ActActIsda().day_count(start, end) == 1
    # Single day in 2025.
    assert ActActIsda().year_fraction(start, end) == Decimal(1) / Decimal(365)


def test_thirty_360_conventions() -> None:
    start = Date.parse("2024-01-31")
    end = Date.parse("2024-02-28")

    assert Thirty360E().day_count(start, end) == 28  # 30E clamps start day to 30
    assert Thirty360EIsda().day_count(start, end) == 28
    assert Thirty360German().day_count(start, end) == 28
    assert Thirty360US().day_count(start, end) == 28


def test_daycount_convention_factory_and_aliases() -> None:
    dc = DayCountConvention.ACT_360.to_day_count()
    assert dc.name() == "ACT/360"
    assert str(DayCountConvention.ACT_360) == "DayCountConvention.ACT_360"

    assert Act365 is Act365Fixed
    assert Thirty360 is Thirty360US


def test_act_act_icma_helpers() -> None:
    icma = ActActIcma.new(Frequency.SEMI_ANNUAL)
    a_start = Date.parse("2025-01-01")
    a_end = Date.parse("2025-07-01")
    p_start = Date.parse("2025-01-01")
    p_end = Date.parse("2025-07-01")

    assert icma.accrued_days(a_start, a_end) == 181
    assert icma.year_fraction_with_period(a_start, a_end, p_start, p_end) == Decimal("0.5")
