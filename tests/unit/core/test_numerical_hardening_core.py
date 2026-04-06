from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import CalendarData, DynamicCalendar, Frequency, WeekendCalendar
from fuggers_py.core.calendars import last_weekday_of_month, nth_weekday_of_month, observed_date
from fuggers_py.core.daycounts import ActActAfb, ActActIcma, Thirty360E, Thirty360EIsda, Thirty360German, Thirty360US
from fuggers_py.core.errors import CalendarError, DayCountError
from fuggers_py.core.types import Date


def test_act_act_afb_counts_whole_years_then_remaining_leap_days() -> None:
    start = Date.parse("2023-02-28")
    end = Date.parse("2024-03-01")

    assert ActActAfb().year_fraction(start, end) == Decimal(1) + (Decimal(2) / Decimal(366))


def test_act_act_icma_validates_frequency_periods_and_negative_sign() -> None:
    with pytest.raises(DayCountError, match="non-zero frequency"):
        ActActIcma.new(Frequency.ZERO)

    icma = ActActIcma.semi_annual()
    accrual_start = Date.parse("2025-01-01")
    accrual_end = Date.parse("2025-07-01")

    with pytest.raises(DayCountError, match="period_start < period_end"):
        icma.year_fraction_with_period(accrual_start, accrual_end, accrual_end, accrual_start)

    assert icma.year_fraction_with_period(accrual_end, accrual_start, accrual_start, accrual_end) == Decimal("-0.5")


def test_thirty_360_variants_diverge_on_february_end_of_month_edges() -> None:
    start = Date.parse("2024-02-29")
    end = Date.parse("2024-03-31")

    assert Thirty360E().day_count(start, end) == 31
    assert Thirty360EIsda().day_count(start, end) == 30
    assert Thirty360German().day_count(start, end) == 30
    assert Thirty360US().day_count(start, end) == 30


def test_observed_and_weekday_helpers_validate_edge_inputs() -> None:
    assert observed_date(Date.parse("2025-07-05")) == Date.parse("2025-07-04")
    assert observed_date(Date.parse("2025-07-06")) == Date.parse("2025-07-07")
    assert observed_date(Date.parse("2025-07-07")) == Date.parse("2025-07-07")

    assert nth_weekday_of_month(2025, 5, 0, 1) == Date.parse("2025-05-05")
    assert last_weekday_of_month(2025, 5, 0) == Date.parse("2025-05-26")

    with pytest.raises(CalendarError, match="occurrence must be >= 1"):
        nth_weekday_of_month(2025, 5, 0, 0)

    with pytest.raises(CalendarError, match="Invalid month"):
        last_weekday_of_month(2025, 13, 0)


def test_weekend_calendar_negative_business_day_operations_are_stable() -> None:
    calendar = WeekendCalendar()
    monday = Date.parse("2025-03-03")

    previous = calendar.add_business_days(monday, -1)
    forward = calendar.add_business_days(monday, 3)

    assert previous == Date.parse("2025-02-28")
    assert forward == Date.parse("2025-03-06")
    assert calendar.business_days_between(previous, monday) == 1
    assert calendar.business_days_between(monday, forward) == 3


def test_dynamic_calendar_loader_generator_and_merge_paths_are_validated() -> None:
    with pytest.raises(CalendarError, match="loader_callable must return CalendarData or a dict"):
        DynamicCalendar.from_loader(lambda: "bad loader")

    with pytest.raises(CalendarError, match="holidays must be a list"):
        CalendarData.from_dict({"name": "Dyn", "holidays": "2024-07-04"})

    calendar = DynamicCalendar.new("Dyn")
    with pytest.raises(CalendarError, match="Holiday generator must yield Date or datetime.date"):
        calendar.add_holidays_for_year(2024, lambda year: ["2024-07-04"])

    left = DynamicCalendar.from_dates("Left", [Date.parse("2024-07-04")])
    right = DynamicCalendar.from_dates("Right", [Date.parse("2024-12-25")])
    merged = left.merge(right)

    assert merged.holiday_count() == 2
    assert merged.is_business_day(Date.parse("2024-07-04")) is False
    assert merged.is_business_day(Date.parse("2024-12-25")) is False
