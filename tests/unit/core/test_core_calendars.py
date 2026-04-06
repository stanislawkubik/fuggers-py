from __future__ import annotations

import pytest

from fuggers_py.core import (
    BusinessDayConvention,
    CalendarData,
    CustomCalendarBuilder,
    DynamicCalendar,
    HolidayBitmap,
    HolidayCalendarBuilder,
    JapanCalendar,
    JointCalendar,
    SIFMACalendar,
    Target2Calendar,
    UKCalendar,
    USGovernmentCalendar,
    WeekendCalendar,
    WeekendType,
)
from fuggers_py.core.calendars import CalendarError, easter_sunday, last_weekday_of_month, nth_weekday_of_month, observed_date
from fuggers_py.core.types import Date


def test_weekend_type_is_weekend() -> None:
    assert WeekendType.SATURDAY_SUNDAY.is_weekend(5) is True
    assert WeekendType.SATURDAY_SUNDAY.is_weekend(6) is True
    assert WeekendType.SATURDAY_SUNDAY.is_weekend(0) is False
    assert WeekendType.NONE.is_weekend(6) is False
    assert str(WeekendType.SATURDAY_SUNDAY) == "Saturday Sunday"
    assert str(BusinessDayConvention.MODIFIED_FOLLOWING) == "Modified Following"


def test_business_day_adjustment_rules_on_weekend_calendar() -> None:
    cal = WeekendCalendar()
    sat = Date.parse("2025-03-01")
    assert cal.adjust(sat, BusinessDayConvention.FOLLOWING) == Date.parse("2025-03-03")
    assert cal.adjust(sat, BusinessDayConvention.PRECEDING) == Date.parse("2025-02-28")

    # Modified following crosses month for 2025-05-31 (Sat) -> 2025-06-02 (Mon) => go preceding.
    eom_sat = Date.parse("2025-05-31")
    assert cal.adjust(eom_sat, BusinessDayConvention.MODIFIED_FOLLOWING) == Date.parse("2025-05-30")

    # Modified preceding for 2025-03-01 (Sat) -> preceding 2025-02-28 (month changes) => go following.
    assert cal.adjust(sat, BusinessDayConvention.MODIFIED_PRECEDING) == Date.parse("2025-03-03")

    assert cal.adjust(sat, BusinessDayConvention.NEAREST) == Date.parse("2025-02-28")
    assert cal.adjust(eom_sat, BusinessDayConvention.END_OF_MONTH) == Date.parse("2025-05-30")


def test_weekend_calendar_business_days_between_semantics() -> None:
    cal = WeekendCalendar()
    start = Date.parse("2025-03-03")  # Monday
    end = Date.parse("2025-03-04")  # Tuesday
    assert cal.business_days_between(start, end) == 1


def test_calendar_helper_functions_cover_observed_dates_and_invalid_inputs() -> None:
    assert easter_sunday(2024) == Date.parse("2024-03-31")
    assert observed_date(Date.parse("2022-01-01")) == Date.parse("2021-12-31")
    assert observed_date(Date.parse("2023-01-01")) == Date.parse("2023-01-02")
    assert last_weekday_of_month(2024, 5, 0) == Date.parse("2024-05-27")
    assert nth_weekday_of_month(2024, 9, 0, 1) == Date.parse("2024-09-02")

    with pytest.raises(CalendarError, match="Invalid month"):
        last_weekday_of_month(2024, 13, 0)

    with pytest.raises(CalendarError, match="occurrence must be >= 1"):
        nth_weekday_of_month(2024, 1, 0, 0)

    with pytest.raises(CalendarError, match="does not exist"):
        nth_weekday_of_month(2024, 2, 0, 5)


def test_weekend_calendar_business_day_navigation_and_nearest_tie_break() -> None:
    cal = WeekendCalendar()
    start = Date.parse("2025-02-28")  # Friday

    assert cal.add_business_days(start, 1) == Date.parse("2025-03-03")
    assert cal.add_business_days(start, -1) == Date.parse("2025-02-27")
    assert cal.settlement_date(start, 1) == Date.parse("2025-03-03")
    assert cal.next_business_day(Date.parse("2025-03-01")) == Date.parse("2025-03-03")
    assert cal.previous_business_day(Date.parse("2025-03-02")) == Date.parse("2025-02-28")
    assert cal.business_days_between(Date.parse("2025-03-04"), Date.parse("2025-03-03")) == -1

    dyn = DynamicCalendar.from_calendar_data(CalendarData.new("Tie").with_holiday(Date.parse("2025-03-05")))
    assert dyn.adjust(Date.parse("2025-03-05"), BusinessDayConvention.NEAREST) == Date.parse("2025-03-06")


def test_sifma_known_holidays() -> None:
    sifma = SIFMACalendar.global_()
    assert sifma.is_business_day(Date.parse("2024-07-04")) is False  # Independence Day
    assert sifma.is_business_day(Date.parse("2024-03-29")) is False  # Good Friday (2024)
    assert sifma.is_business_day(Date.parse("2022-06-20")) is False  # Juneteenth observed (2022)
    assert sifma.is_business_day(Date.parse("2021-12-31")) is False  # New Year observed for 2022
    assert SIFMACalendar.global_() is sifma


def test_us_government_calendar_smoke() -> None:
    usg = USGovernmentCalendar.new()
    assert usg.is_business_day(Date.parse("2024-07-04")) is False


def test_target2_calendar_holidays() -> None:
    t2 = Target2Calendar.global_()
    assert t2.is_business_day(Date.parse("2024-05-01")) is False
    assert t2.is_business_day(Date.parse("2024-04-01")) is False  # Easter Monday 2024


def test_uk_calendar_holidays() -> None:
    uk = UKCalendar.global_()
    assert uk.is_business_day(Date.parse("2024-05-06")) is False  # Early May bank holiday 2024
    assert uk.is_business_day(Date.parse("2024-03-29")) is False  # Good Friday


def test_japan_calendar_holidays() -> None:
    jp = JapanCalendar.global_()
    assert jp.is_business_day(Date.parse("2024-01-02")) is False
    assert jp.is_business_day(Date.parse("2024-02-23")) is False
    assert jp.is_business_day(Date.parse("2024-01-08")) is False  # Coming of Age Day (2nd Monday)


def test_joint_calendar_semantics() -> None:
    joint = JointCalendar.new([SIFMACalendar.global_(), Target2Calendar.global_()])
    assert joint.is_business_day(Date.parse("2024-07-04")) is False  # closed in US
    assert joint.is_business_day(Date.parse("2024-05-01")) is False  # closed in TARGET2


def test_holiday_bitmap_and_builders() -> None:
    hb = HolidayBitmap.new("Test")
    d = Date.parse("2024-07-04")
    hb.add_holiday(d)
    assert hb.is_holiday(d) is True
    assert hb.is_business_day_date(d) is False
    hb.remove_holiday(d)
    assert hb.is_holiday(d) is False

    b = HolidayCalendarBuilder.new("Built").year_range(2024, 2024)
    b.add_fixed_holiday(7, 4, observe_weekend=True)
    built = b.build()
    assert built.is_business_day_date(Date.parse("2024-07-04")) is False


def test_calendar_data_and_dynamic_calendar_round_trip() -> None:
    data = CalendarData.new("Dyn").with_weekend(WeekendType.SATURDAY_SUNDAY).with_holiday(Date.parse("2024-07-04"))
    cal = DynamicCalendar.from_calendar_data(data)
    assert cal.is_business_day(Date.parse("2024-07-04")) is False

    text = cal.to_json()
    cal2 = DynamicCalendar.from_json(text)
    assert cal2.is_business_day(Date.parse("2024-07-04")) is False
    assert cal2.holiday_count() == 1


def test_custom_calendar_builder() -> None:
    cal = (
        CustomCalendarBuilder.new("Custom")
        .year_range(2024, 2024)
        .add_fixed_holiday_observed(7, 4)
        .add_good_friday()
        .build()
    )
    assert cal.is_business_day(Date.parse("2024-07-04")) is False
    assert cal.is_business_day(Date.parse("2024-03-29")) is False
