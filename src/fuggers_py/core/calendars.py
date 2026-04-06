"""Business-day calendars and holiday generation utilities.

The module provides weekend definitions, standard market calendars, mutable
holiday containers, and builders for custom calendar data.
"""

from __future__ import annotations

import calendar as _calendar
import datetime as _dt
import json as _json
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from .errors import CalendarError
from .types import Date

# Public calendar bounds used across the library.
MIN_YEAR: int = 1900
MAX_YEAR: int = 2200


class BusinessDayConvention(StrEnum):
    """Business-day adjustment convention."""

    UNADJUSTED = "UNADJUSTED"
    FOLLOWING = "FOLLOWING"
    MODIFIED_FOLLOWING = "MODIFIED_FOLLOWING"
    PRECEDING = "PRECEDING"
    MODIFIED_PRECEDING = "MODIFIED_PRECEDING"
    NEAREST = "NEAREST"
    END_OF_MONTH = "END_OF_MONTH"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name.replace("_", " ").title()


class WeekendType(StrEnum):
    """Weekend definition used by a calendar."""

    SATURDAY_SUNDAY = "SATURDAY_SUNDAY"
    FRIDAY_SATURDAY = "FRIDAY_SATURDAY"
    THURSDAY_FRIDAY = "THURSDAY_FRIDAY"
    SUNDAY_ONLY = "SUNDAY_ONLY"
    NONE = "NONE"

    def is_weekend(self, weekday: int) -> bool:
        """Return True if `weekday` is a weekend day under this weekend type.

        `weekday` follows Python's convention: Monday=0 ... Sunday=6.
        """

        wd = int(weekday)
        return {
            WeekendType.SATURDAY_SUNDAY: wd in (5, 6),
            WeekendType.FRIDAY_SATURDAY: wd in (4, 5),
            WeekendType.THURSDAY_FRIDAY: wd in (3, 4),
            WeekendType.SUNDAY_ONLY: wd == 6,
            WeekendType.NONE: False,
        }[self]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name.replace("_", " ").title()


def easter_sunday(year: int) -> Date:
    """Return Easter Sunday for the given year in the Gregorian calendar."""

    y = int(year)
    # Anonymous Gregorian algorithm (Meeus/Jones/Butcher).
    a = y % 19
    b = y // 100
    c = y % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    leap_offset = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * leap_offset) // 451
    month = (h + leap_offset - 7 * m + 114) // 31
    day = ((h + leap_offset - 7 * m + 114) % 31) + 1
    return Date.from_ymd(y, month, day)


def last_weekday_of_month(year: int, month: int, weekday: int) -> Date:
    """Return the last occurrence of a weekday in a month."""

    y, m, wd = int(year), int(month), int(weekday)
    if m < 1 or m > 12:
        raise CalendarError(f"Invalid month: {month}.")
    last_dom = _calendar.monthrange(y, m)[1]
    d = _dt.date(y, m, last_dom)
    while d.weekday() != wd:
        d -= _dt.timedelta(days=1)
    return Date(d)


def nth_weekday_of_month(year: int, month: int, weekday: int, occurrence: int) -> Date:
    """Return the Nth occurrence of a weekday in a month."""

    y, m, wd, occ = int(year), int(month), int(weekday), int(occurrence)
    if occ < 1:
        raise CalendarError("occurrence must be >= 1.")
    if m < 1 or m > 12:
        raise CalendarError(f"Invalid month: {month}.")

    first = _dt.date(y, m, 1)
    offset = (wd - first.weekday()) % 7
    day = 1 + offset + (occ - 1) * 7
    if day > _calendar.monthrange(y, m)[1]:
        raise CalendarError("Requested occurrence does not exist in this month.")
    return Date(_dt.date(y, m, day))


def observed_date(date: Date) -> Date:
    """Return the US-style observed date for a holiday on a weekend.

    - Saturday -> Friday
    - Sunday -> Monday
    """

    wd = date.weekday()
    if wd == 5:
        return date.add_days(-1)
    if wd == 6:
        return date.add_days(1)
    return date


class Calendar(ABC):
    """Abstract business-day calendar interface.

    Implementations decide whether a `Date` is a business day and inherit the
    standard adjustment and counting rules defined here.
    """

    @abstractmethod
    def name(self) -> str:
        """Return the calendar name."""

    @abstractmethod
    def is_business_day(self, date: Date) -> bool:
        """Return True if `date` is a business day."""

    def is_holiday(self, date: Date) -> bool:
        """Return True if `date` is a holiday."""

        return not self.is_business_day(date)

    def adjust(self, date: Date, convention: BusinessDayConvention) -> Date:
        """Adjust a date according to a business-day convention.

        `FOLLOWING` and `PRECEDING` move forward or backward until a business
        day is found. Modified conventions roll back or forward if the adjusted
        date would cross month-end. `NEAREST` prefers the later date on a tie.
        `END_OF_MONTH` preserves month-end dates by rolling backward if needed.
        """

        if convention == BusinessDayConvention.UNADJUSTED:
            return date

        if convention == BusinessDayConvention.FOLLOWING:
            d = date
            while not self.is_business_day(d):
                d = d.add_days(1)
            return d

        if convention == BusinessDayConvention.PRECEDING:
            d = date
            while not self.is_business_day(d):
                d = d.add_days(-1)
            return d

        if convention == BusinessDayConvention.MODIFIED_FOLLOWING:
            following = self.adjust(date, BusinessDayConvention.FOLLOWING)
            if following.month() != date.month():
                return self.adjust(date, BusinessDayConvention.PRECEDING)
            return following

        if convention == BusinessDayConvention.MODIFIED_PRECEDING:
            preceding = self.adjust(date, BusinessDayConvention.PRECEDING)
            if preceding.month() != date.month():
                return self.adjust(date, BusinessDayConvention.FOLLOWING)
            return preceding

        if convention == BusinessDayConvention.NEAREST:
            if self.is_business_day(date):
                return date
            prev_d = self.adjust(date, BusinessDayConvention.PRECEDING)
            next_d = self.adjust(date, BusinessDayConvention.FOLLOWING)
            dist_prev = abs(prev_d.days_between(date))
            dist_next = abs(date.days_between(next_d))
            # Prefer following on a tie.
            return prev_d if dist_prev < dist_next else next_d

        if convention == BusinessDayConvention.END_OF_MONTH:
            # Preserve EOM-ness for month-end dates; otherwise behave like Modified Following.
            if date.is_end_of_month():
                return self.adjust(date, BusinessDayConvention.PRECEDING)
            return self.adjust(date, BusinessDayConvention.MODIFIED_FOLLOWING)

        raise CalendarError(f"Unknown business-day convention: {convention!r}")

    def add_business_days(self, date: Date, days: int) -> Date:
        """Add business days relative to a calendar.

        The start date is excluded from the count. Positive values move
        forward, negative values move backward, and only business days are
        counted.
        """

        n = int(days)
        if n == 0:
            return date

        step = 1 if n > 0 else -1
        remaining = abs(n)
        current = date
        while remaining > 0:
            current = current.add_days(step)
            if self.is_business_day(current):
                remaining -= 1
        return current

    def settlement_date(self, trade_date: Date, settlement_days: int) -> Date:
        """Return the settlement date for a trade date and business-day lag."""

        return self.add_business_days(trade_date, int(settlement_days))

    def next_business_day(self, date: Date) -> Date:
        """Return `date` if it is open, otherwise the next business day."""

        return date if self.is_business_day(date) else self.adjust(date, BusinessDayConvention.FOLLOWING)

    def previous_business_day(self, date: Date) -> Date:
        """Return `date` if it is open, otherwise the previous business day."""

        return date if self.is_business_day(date) else self.adjust(date, BusinessDayConvention.PRECEDING)

    def business_days_between(self, start: Date, end: Date) -> int:
        """Count business days between dates.

        The count is start-exclusive and end-inclusive. Negative intervals are
        returned as negative counts.
        """

        if start == end:
            return 0
        if start < end:
            count = 0
            current = start
            while current < end:
                current = current.add_days(1)
                if self.is_business_day(current):
                    count += 1
            return count
        return -self.business_days_between(end, start)


class WeekendCalendar(Calendar):
    """Calendar that treats weekends as non-business days and nothing else."""

    def __init__(self, weekend_type: WeekendType = WeekendType.SATURDAY_SUNDAY, name: str = "WeekendCalendar"):
        self._weekend_type = weekend_type
        self._name = name

    def name(self) -> str:
        return self._name

    def weekend_type(self) -> WeekendType:
        """Return the weekend type."""

        return self._weekend_type

    def is_business_day(self, date: Date) -> bool:
        return not self._weekend_type.is_weekend(date.weekday())


def _sifma_holidays_for_year(year: int) -> set[_dt.date]:
    y = int(year)
    holidays: set[_dt.date] = set()

    # New Year's Day (observed) – include cross-year observation.
    holidays.add(observed_date(Date.from_ymd(y, 1, 1)).as_naive_date())
    ny_next = observed_date(Date.from_ymd(y + 1, 1, 1)).as_naive_date()
    if ny_next.year == y:
        holidays.add(ny_next)

    # Martin Luther King Jr. Day: 3rd Monday in January (since 1986; treat as always).
    holidays.add(nth_weekday_of_month(y, 1, 0, 3).as_naive_date())
    # Presidents' Day: 3rd Monday in February.
    holidays.add(nth_weekday_of_month(y, 2, 0, 3).as_naive_date())
    # Good Friday.
    holidays.add(easter_sunday(y).add_days(-2).as_naive_date())
    # Memorial Day: last Monday in May.
    holidays.add(last_weekday_of_month(y, 5, 0).as_naive_date())
    # Juneteenth (since 2021).
    if y >= 2021:
        holidays.add(observed_date(Date.from_ymd(y, 6, 19)).as_naive_date())
    # Independence Day.
    holidays.add(observed_date(Date.from_ymd(y, 7, 4)).as_naive_date())
    # Labor Day: 1st Monday in September.
    holidays.add(nth_weekday_of_month(y, 9, 0, 1).as_naive_date())
    # Columbus Day: 2nd Monday in October.
    holidays.add(nth_weekday_of_month(y, 10, 0, 2).as_naive_date())
    # Veterans Day (observed).
    holidays.add(observed_date(Date.from_ymd(y, 11, 11)).as_naive_date())
    # Thanksgiving Day: 4th Thursday in November.
    holidays.add(nth_weekday_of_month(y, 11, 3, 4).as_naive_date())
    # Christmas Day (observed).
    holidays.add(observed_date(Date.from_ymd(y, 12, 25)).as_naive_date())

    return holidays


class SIFMACalendar(Calendar):
    """US SIFMA bond-market calendar with rule-based holidays."""

    def __init__(self) -> None:
        self._weekend = WeekendType.SATURDAY_SUNDAY

    @classmethod
    def new(cls) -> SIFMACalendar:
        """Create a new SIFMA calendar."""

        return cls()

    @classmethod
    @lru_cache(maxsize=1)
    def global_(cls) -> SIFMACalendar:
        """Return a cached singleton instance.

        Notes
        -----
        Python reserves the keyword `global`, so this API uses `global_()`
        for the cached singleton constructor.
        """

        return cls()

    def name(self) -> str:
        return "SIFMA"

    @lru_cache(maxsize=256)
    def _holidays(self, year: int) -> set[_dt.date]:
        return _sifma_holidays_for_year(int(year))

    def is_business_day(self, date: Date) -> bool:
        if self._weekend.is_weekend(date.weekday()):
            return False
        return date.as_naive_date() not in self._holidays(date.year())


class USGovernmentCalendar(SIFMACalendar):
    """US Government calendar.

    For the current core layer this intentionally matches the SIFMA holiday set.
    This keeps US government and bond-market settlement logic aligned until the
    repo adds a distinct government-market calendar.
    """

    @classmethod
    def new(cls) -> USGovernmentCalendar:
        """Create a new US Government calendar."""

        return cls()

    def name(self) -> str:
        return "USGovernment"


class USCalendar(SIFMACalendar):
    """US calendar alias that currently matches the SIFMA holiday set."""

    def name(self) -> str:
        return "US"


def _target2_holidays_for_year(year: int) -> set[_dt.date]:
    y = int(year)
    holidays: set[_dt.date] = set()
    holidays.add(Date.from_ymd(y, 1, 1).as_naive_date())
    holidays.add(easter_sunday(y).add_days(-2).as_naive_date())  # Good Friday
    holidays.add(easter_sunday(y).add_days(1).as_naive_date())  # Easter Monday
    holidays.add(Date.from_ymd(y, 5, 1).as_naive_date())  # Labour Day
    holidays.add(Date.from_ymd(y, 12, 25).as_naive_date())
    holidays.add(Date.from_ymd(y, 12, 26).as_naive_date())
    return holidays


class Target2Calendar(Calendar):
    """TARGET2 euro-system calendar with the standard holiday set."""

    def __init__(self) -> None:
        self._weekend = WeekendType.SATURDAY_SUNDAY

    @classmethod
    def new(cls) -> Target2Calendar:
        """Create a new TARGET2 calendar."""

        return cls()

    @classmethod
    @lru_cache(maxsize=1)
    def global_(cls) -> Target2Calendar:
        """Return a cached singleton instance.

        See `SIFMACalendar.global_()` for the naming rationale.
        """

        return cls()

    def name(self) -> str:
        return "TARGET2"

    @lru_cache(maxsize=256)
    def _holidays(self, year: int) -> set[_dt.date]:
        return _target2_holidays_for_year(int(year))

    def is_business_day(self, date: Date) -> bool:
        if self._weekend.is_weekend(date.weekday()):
            return False
        return date.as_naive_date() not in self._holidays(date.year())


def _uk_holidays_for_year(year: int) -> set[_dt.date]:
    y = int(year)
    holidays: set[_dt.date] = set()

    # New Year's Day (substitute on next Monday).
    new_year = _dt.date(y, 1, 1)
    if new_year.weekday() in (5, 6):  # Sat/Sun
        # Next Monday.
        shift = 7 - new_year.weekday()
        holidays.add(new_year + _dt.timedelta(days=shift))
    else:
        holidays.add(new_year)

    # Good Friday / Easter Monday.
    easter = easter_sunday(y).as_naive_date()
    holidays.add(easter - _dt.timedelta(days=2))
    holidays.add(easter + _dt.timedelta(days=1))

    # Early May bank holiday: 1st Monday in May.
    holidays.add(nth_weekday_of_month(y, 5, 0, 1).as_naive_date())
    # Spring bank holiday: last Monday in May.
    holidays.add(last_weekday_of_month(y, 5, 0).as_naive_date())
    # Summer bank holiday: last Monday in August.
    holidays.add(last_weekday_of_month(y, 8, 0).as_naive_date())

    # Christmas / Boxing Day with substitute rules.
    christmas = _dt.date(y, 12, 25)
    boxing = _dt.date(y, 12, 26)

    holidays.add(christmas)
    holidays.add(boxing)

    # Substitute for Christmas if on weekend.
    if christmas.weekday() in (5, 6):
        sub = christmas + _dt.timedelta(days=1)
        while sub.weekday() in (5, 6) or sub in holidays:
            sub += _dt.timedelta(days=1)
        holidays.add(sub)

    # Substitute for Boxing if on weekend.
    if boxing.weekday() in (5, 6):
        sub = boxing + _dt.timedelta(days=1)
        while sub.weekday() in (5, 6) or sub in holidays:
            sub += _dt.timedelta(days=1)
        holidays.add(sub)

    return holidays


class UKCalendar(Calendar):
    """UK calendar using England and Wales bank holidays."""

    def __init__(self) -> None:
        self._weekend = WeekendType.SATURDAY_SUNDAY

    @classmethod
    def new(cls) -> UKCalendar:
        """Create a new UK calendar."""

        return cls()

    @classmethod
    @lru_cache(maxsize=1)
    def global_(cls) -> UKCalendar:
        """Return a cached singleton instance.

        See `SIFMACalendar.global_()` for the naming rationale.
        """

        return cls()

    def name(self) -> str:
        return "UK"

    @lru_cache(maxsize=256)
    def _holidays(self, year: int) -> set[_dt.date]:
        return _uk_holidays_for_year(int(year))

    def is_business_day(self, date: Date) -> bool:
        if self._weekend.is_weekend(date.weekday()):
            return False
        return date.as_naive_date() not in self._holidays(date.year())


def _japan_vernal_equinox(year: int) -> _dt.date:
    # Approximation valid for 1900-2099.
    y = int(year)
    day = int(20.8431 + 0.242194 * (y - 1980) - (y - 1980) // 4)
    return _dt.date(y, 3, day)


def _japan_autumnal_equinox(year: int) -> _dt.date:
    y = int(year)
    day = int(23.2488 + 0.242194 * (y - 1980) - (y - 1980) // 4)
    return _dt.date(y, 9, day)


def _japan_holidays_for_year(year: int) -> set[_dt.date]:
    y = int(year)
    holidays: set[_dt.date] = set()

    def add_fixed(month: int, day: int) -> None:
        holidays.add(_dt.date(y, month, day))

    # New Year holidays (common market practice).
    add_fixed(1, 1)
    add_fixed(1, 2)
    add_fixed(1, 3)

    # Coming of Age Day: 2nd Monday of January.
    holidays.add(nth_weekday_of_month(y, 1, 0, 2).as_naive_date())
    # National Foundation Day.
    add_fixed(2, 11)
    # Emperor's Birthday (current era).
    add_fixed(2, 23)
    # Vernal Equinox.
    holidays.add(_japan_vernal_equinox(y))
    # Showa Day.
    add_fixed(4, 29)
    # Constitution / Greenery / Children's Day.
    add_fixed(5, 3)
    add_fixed(5, 4)
    add_fixed(5, 5)
    # Marine Day: 3rd Monday of July.
    holidays.add(nth_weekday_of_month(y, 7, 0, 3).as_naive_date())
    # Mountain Day.
    add_fixed(8, 11)
    # Respect for the Aged Day: 3rd Monday of September.
    holidays.add(nth_weekday_of_month(y, 9, 0, 3).as_naive_date())
    # Autumnal Equinox.
    holidays.add(_japan_autumnal_equinox(y))
    # Sports Day: 2nd Monday of October.
    holidays.add(nth_weekday_of_month(y, 10, 0, 2).as_naive_date())
    # Culture Day.
    add_fixed(11, 3)
    # Labor Thanksgiving Day.
    add_fixed(11, 23)

    # Substitute holiday: if a holiday falls on Sunday, next weekday is also holiday.
    extra: set[_dt.date] = set()
    for h in sorted(holidays):
        if h.weekday() == 6:
            sub = h + _dt.timedelta(days=1)
            while sub.weekday() in (5, 6) or sub in holidays or sub in extra:
                sub += _dt.timedelta(days=1)
            extra.add(sub)
    holidays |= extra

    return holidays


class JapanCalendar(Calendar):
    """Japan calendar with a simplified rule-based holiday set."""

    def __init__(self) -> None:
        self._weekend = WeekendType.SATURDAY_SUNDAY

    @classmethod
    def new(cls) -> JapanCalendar:
        """Create a new Japan calendar."""

        return cls()

    @classmethod
    @lru_cache(maxsize=1)
    def global_(cls) -> JapanCalendar:
        """Return a cached singleton instance.

        See `SIFMACalendar.global_()` for the naming rationale.
        """

        return cls()

    def name(self) -> str:
        return "Japan"

    @lru_cache(maxsize=256)
    def _holidays(self, year: int) -> set[_dt.date]:
        return _japan_holidays_for_year(int(year))

    def is_business_day(self, date: Date) -> bool:
        if self._weekend.is_weekend(date.weekday()):
            return False
        return date.as_naive_date() not in self._holidays(date.year())


class JointCalendar(Calendar):
    """Calendar that is open only when all component calendars are open."""

    def __init__(self, calendars: Sequence[Calendar]) -> None:
        self._calendars = list(calendars)
        if not self._calendars:
            raise CalendarError("JointCalendar requires at least one component calendar.")

    @classmethod
    def new(cls, calendars: Sequence[Calendar]) -> JointCalendar:
        """Create a joint calendar from component calendars."""

        return cls(calendars)

    def name(self) -> str:
        joined = "+".join(c.name() for c in self._calendars)
        return f"Joint({joined})"

    def is_business_day(self, date: Date) -> bool:
        return all(c.is_business_day(date) for c in self._calendars)


class HolidayBitmap:
    """Mutable holiday container backed by a Python set.

    Weekend handling is separate from the stored holiday set, so callers can
    use this type for holiday-only logic or combine it with a weekend rule.
    """

    def __init__(self, name: str, weekend_type: WeekendType = WeekendType.SATURDAY_SUNDAY) -> None:
        self._name = str(name)
        self._weekend_type = weekend_type
        self._holidays: set[_dt.date] = set()

    @classmethod
    def new(cls, name: str, weekend_type: WeekendType = WeekendType.SATURDAY_SUNDAY) -> HolidayBitmap:
        """Create an empty holiday container."""

        return cls(name=name, weekend_type=weekend_type)

    @classmethod
    def from_holidays(
        cls, name: str, holidays: Iterable[Date], weekend_type: WeekendType = WeekendType.SATURDAY_SUNDAY
    ) -> HolidayBitmap:
        """Create a holiday container from an iterable of holidays."""

        hb = cls.new(name=name, weekend_type=weekend_type)
        hb.add_holidays(holidays)
        return hb

    def name(self) -> str:
        """Return the name."""

        return self._name

    def weekend_type(self) -> WeekendType:
        """Return the weekend type."""

        return self._weekend_type

    def add_holiday(self, date: Date) -> None:
        """Add a holiday."""

        self._holidays.add(date.as_naive_date())

    def add_holidays(self, dates: Iterable[Date]) -> None:
        """Add multiple holidays."""

        for d in dates:
            self.add_holiday(d)

    def remove_holiday(self, date: Date) -> None:
        """Remove a holiday if present."""

        self._holidays.discard(date.as_naive_date())

    def is_holiday(self, date: Date) -> bool:
        """Return True if the date is a holiday (ignores weekends)."""

        return date.as_naive_date() in self._holidays

    def is_business_day(self, year: int, month: int, day: int) -> bool:
        """Return True if the Y/M/D is a business day."""

        return self.is_business_day_date(Date.from_ymd(int(year), int(month), int(day)))

    def is_business_day_date(self, date: Date) -> bool:
        """Return True if the date is a business day."""

        if self._weekend_type.is_weekend(date.weekday()):
            return False
        return date.as_naive_date() not in self._holidays

    def count_holidays(self) -> int:
        """Return the number of stored holidays."""

        return len(self._holidays)


class HolidayCalendarBuilder:
    """Builder for `HolidayBitmap` objects.

    The builder collects explicit dates and year-based holiday rules, then
    evaluates them over an optional inclusive year range.
    """

    def __init__(self, name: str) -> None:
        self._name = str(name)
        self._weekend = WeekendType.SATURDAY_SUNDAY
        self._year_start: int | None = None
        self._year_end: int | None = None
        self._explicit: set[Date] = set()
        self._rules: list[Callable[[int], Iterable[Date]]] = []

    @classmethod
    def new(cls, name: str) -> HolidayCalendarBuilder:
        """Create a new builder."""

        return cls(name)

    def weekend(self, weekend_type: WeekendType) -> HolidayCalendarBuilder:
        """Set the weekend rule used by the built calendar."""

        self._weekend = weekend_type
        return self

    def year_range(self, start: int, end: int) -> HolidayCalendarBuilder:
        """Set the inclusive year range used when materializing rules."""

        s, e = int(start), int(end)
        if s > e:
            raise CalendarError("year_range requires start <= end.")
        self._year_start, self._year_end = s, e
        return self

    def add_holiday(self, date: Date) -> HolidayCalendarBuilder:
        """Add an explicit holiday date."""

        self._explicit.add(date)
        return self

    def add_holidays(self, dates: Iterable[Date]) -> HolidayCalendarBuilder:
        """Add explicit holiday dates."""

        for d in dates:
            self._explicit.add(d)
        return self

    def add_fixed_holiday(self, month: int, day: int, observe_weekend: bool) -> HolidayCalendarBuilder:
        """Add a fixed-date holiday for each year in range."""

        m, d = int(month), int(day)

        def rule(y: int) -> Iterable[Date]:
            dt = Date.from_ymd(y, m, d)
            if observe_weekend:
                return [observed_date(dt)]
            return [dt]

        self._rules.append(rule)
        return self

    def add_fixed_holiday_from(
        self, month: int, day: int, from_year: int, observe_weekend: bool
    ) -> HolidayCalendarBuilder:
        """Add a fixed-date holiday for each year starting at `from_year`."""

        m, d, fy = int(month), int(day), int(from_year)

        def rule(y: int) -> Iterable[Date]:
            if y < fy:
                return []
            dt = Date.from_ymd(y, m, d)
            if observe_weekend:
                return [observed_date(dt)]
            return [dt]

        self._rules.append(rule)
        return self

    def add_nth_weekday_holiday(self, month: int, weekday: int, occurrence: int) -> HolidayCalendarBuilder:
        """Add an Nth-weekday holiday such as a third Monday."""

        m, wd, occ = int(month), int(weekday), int(occurrence)
        self._rules.append(lambda y: [nth_weekday_of_month(y, m, wd, occ)])
        return self

    def add_last_weekday_holiday(self, month: int, weekday: int) -> HolidayCalendarBuilder:
        """Add a last-weekday holiday such as the last Monday."""

        m, wd = int(month), int(weekday)
        self._rules.append(lambda y: [last_weekday_of_month(y, m, wd)])
        return self

    def add_easter_holiday(self, offset_days: int) -> HolidayCalendarBuilder:
        """Add an Easter-relative holiday offset from Easter Sunday."""

        off = int(offset_days)
        self._rules.append(lambda y: [easter_sunday(y).add_days(off)])
        return self

    def add_custom_holidays(self, generator: Callable[[int], Iterable[Date]]) -> HolidayCalendarBuilder:
        """Add custom holidays from a per-year generator."""

        self._rules.append(generator)
        return self

    def build(self) -> HolidayBitmap:
        """Build the `HolidayBitmap` from explicit dates and year rules."""

        hb = HolidayBitmap.new(self._name, weekend_type=self._weekend)

        for d in self._explicit:
            hb.add_holiday(d)

        if self._year_start is not None and self._year_end is not None:
            for year in range(self._year_start, self._year_end + 1):
                for rule in self._rules:
                    for d in rule(year):
                        hb.add_holiday(d)

        return hb


@dataclass(frozen=True)
class CalendarData:
    """Serializable snapshot of a calendar definition.

    The snapshot captures the calendar name, weekend rule, and explicit
    holiday dates in a form that can be serialized to JSON.
    """

    name: str
    weekend: WeekendType = WeekendType.SATURDAY_SUNDAY
    holidays: tuple[Date, ...] = ()

    @classmethod
    def new(cls, name: str) -> CalendarData:
        """Create an empty calendar data container."""

        return cls(name=str(name))

    def with_weekend(self, weekend_type: WeekendType) -> CalendarData:
        """Return a copy with the weekend rule updated."""

        return replace(self, weekend=weekend_type)

    def with_holiday(self, date: Date) -> CalendarData:
        """Return a copy with an added holiday."""

        return replace(self, holidays=self.holidays + (date,))

    def with_holidays(self, dates: Iterable[Date]) -> CalendarData:
        """Return a copy with added holidays."""

        return replace(self, holidays=self.holidays + tuple(dates))

    def build(self) -> CalendarData:
        """Return the built `CalendarData` unchanged."""

        return self

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dictionary."""

        return {
            "name": self.name,
            "weekend": self.weekend.value,
            "holidays": [str(d) for d in sorted(self.holidays)],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CalendarData:
        """Parse `CalendarData` from a dictionary."""

        name = str(data.get("name", ""))
        weekend_raw = str(data.get("weekend", WeekendType.SATURDAY_SUNDAY.value))
        try:
            weekend = WeekendType(weekend_raw)
        except ValueError as exc:
            raise CalendarError(f"Invalid weekend type: {weekend_raw!r}") from exc

        holidays_raw = data.get("holidays", [])
        if not isinstance(holidays_raw, list):
            raise CalendarError("CalendarData.holidays must be a list of ISO date strings.")
        holidays = tuple(Date.parse(str(x)) for x in holidays_raw)
        return cls(name=name, weekend=weekend, holidays=holidays)


class DynamicCalendar(Calendar):
    """A mutable calendar loaded or assembled at runtime."""

    def __init__(self, name: str, weekend_type: WeekendType = WeekendType.SATURDAY_SUNDAY) -> None:
        self._name = str(name)
        self._weekend_type = weekend_type
        self._holidays: set[_dt.date] = set()

    @classmethod
    def new(cls, name: str, weekend_type: WeekendType = WeekendType.SATURDAY_SUNDAY) -> DynamicCalendar:
        """Create an empty dynamic calendar."""

        return cls(name=name, weekend_type=weekend_type)

    @classmethod
    def from_dates(
        cls, name: str, dates: Iterable[Date], weekend_type: WeekendType = WeekendType.SATURDAY_SUNDAY
    ) -> DynamicCalendar:
        """Create a calendar from `Date` holidays."""

        cal = cls.new(name=name, weekend_type=weekend_type)
        cal.add_holidays(dates)
        return cal

    @classmethod
    def from_naive_dates(
        cls, name: str, dates: Iterable[_dt.date], weekend_type: WeekendType = WeekendType.SATURDAY_SUNDAY
    ) -> DynamicCalendar:
        """Create a calendar from `datetime.date` holidays."""

        cal = cls.new(name=name, weekend_type=weekend_type)
        cal.add_holidays_naive(dates)
        return cal

    @classmethod
    def from_json(cls, text: str) -> DynamicCalendar:
        """Load a calendar from JSON text."""

        try:
            raw = _json.loads(text)
        except Exception as exc:
            raise CalendarError("Invalid JSON for DynamicCalendar.") from exc
        if not isinstance(raw, dict):
            raise CalendarError("DynamicCalendar JSON must be an object.")
        return cls.from_calendar_data(CalendarData.from_dict(raw))

    @classmethod
    def from_json_file(cls, path: str | Path) -> DynamicCalendar:
        """Load a calendar from a JSON file."""

        p = Path(path)
        return cls.from_json(p.read_text(encoding="utf-8"))

    @classmethod
    def from_calendar_data(cls, calendar_data: CalendarData) -> DynamicCalendar:
        """Create a calendar from `CalendarData`."""

        cal = cls.new(calendar_data.name, weekend_type=calendar_data.weekend)
        cal.add_holidays(calendar_data.holidays)
        return cal

    @classmethod
    def from_loader(cls, loader_callable: Callable[[], CalendarData | dict[str, object]]) -> DynamicCalendar:
        """Create a calendar from a loader callable."""

        loaded = loader_callable()
        if isinstance(loaded, CalendarData):
            return cls.from_calendar_data(loaded)
        if isinstance(loaded, dict):
            return cls.from_calendar_data(CalendarData.from_dict(loaded))
        raise CalendarError("loader_callable must return CalendarData or a dict.")

    def calendar_name(self) -> str:
        """Return the calendar name."""

        return self._name

    def name(self) -> str:
        return self._name

    def weekend_type(self) -> WeekendType:
        """Return the weekend type."""

        return self._weekend_type

    def add_holiday(self, date: Date) -> None:
        """Add a holiday."""

        self._holidays.add(date.as_naive_date())

    def add_holiday_naive(self, date: _dt.date) -> None:
        """Add a holiday using a `datetime.date`."""

        self._holidays.add(date)

    def add_holidays(self, dates: Iterable[Date]) -> None:
        """Add multiple holidays."""

        for d in dates:
            self.add_holiday(d)

    def add_holidays_naive(self, dates: Iterable[_dt.date]) -> None:
        """Add multiple `datetime.date` holidays."""

        for d in dates:
            self.add_holiday_naive(d)

    def remove_holiday(self, date: Date) -> None:
        """Remove a holiday if present."""

        self._holidays.discard(date.as_naive_date())

    def remove_holiday_naive(self, date: _dt.date) -> None:
        """Remove a `datetime.date` holiday if present."""

        self._holidays.discard(date)

    def add_holidays_for_year(self, year: int, generator: Callable[[int], Iterable[Date | _dt.date]]) -> None:
        """Add holidays for a given year from a generator."""

        for d in generator(int(year)):
            if isinstance(d, Date):
                self.add_holiday(d)
            elif isinstance(d, _dt.date):
                self.add_holiday_naive(d)
            else:
                raise CalendarError("Holiday generator must yield Date or datetime.date.")

    def holiday_count(self) -> int:
        """Return the number of stored holidays."""

        return len(self._holidays)

    def is_holiday_date(self, date: Date) -> bool:
        """Return True if the given `Date` is a holiday, ignoring weekends."""

        return date.as_naive_date() in self._holidays

    def is_holiday_naive(self, date: _dt.date) -> bool:
        """Return True if the given `datetime.date` is a holiday, ignoring weekends."""

        return date in self._holidays

    def is_business_day(self, date: Date) -> bool:
        if self._weekend_type.is_weekend(date.weekday()):
            return False
        return date.as_naive_date() not in self._holidays

    def merge(self, other: DynamicCalendar) -> DynamicCalendar:
        """Return a new calendar that is the union of this calendar and `other`."""

        merged = DynamicCalendar.new(self._name, weekend_type=self._weekend_type)
        merged._holidays = set(self._holidays) | set(other._holidays)
        return merged

    def merge_from(self, other: DynamicCalendar) -> None:
        """Merge `other` into this calendar in place."""

        self._holidays |= other._holidays

    def to_calendar_data(self) -> CalendarData:
        """Convert the calendar to `CalendarData`."""

        holidays = tuple(Date(d) for d in sorted(self._holidays))
        return CalendarData(name=self._name, weekend=self._weekend_type, holidays=holidays)

    def to_json(self) -> str:
        """Serialize to JSON."""

        return _json.dumps(self.to_calendar_data().to_dict(), indent=2, sort_keys=True)

    def to_json_file(self, path: str | Path) -> None:
        """Serialize to a JSON file."""

        p = Path(path)
        p.write_text(self.to_json() + "\n", encoding="utf-8")


class CustomCalendarBuilder:
    """Convenience builder for `DynamicCalendar`.

    This builder mirrors `HolidayCalendarBuilder` but materializes a mutable
    calendar object instead of an immutable holiday container.
    """

    def __init__(self, name: str) -> None:
        self._name = str(name)
        self._weekend = WeekendType.SATURDAY_SUNDAY
        self._year_start: int | None = None
        self._year_end: int | None = None
        self._explicit: set[Date] = set()
        self._rules: list[Callable[[int], Iterable[Date]]] = []

    @classmethod
    def new(cls, name: str) -> CustomCalendarBuilder:
        """Create a builder."""

        return cls(name)

    def weekend(self, weekend_type: WeekendType) -> CustomCalendarBuilder:
        """Set the weekend rule used by the built calendar."""

        self._weekend = weekend_type
        return self

    def year_range(self, start: int, end: int) -> CustomCalendarBuilder:
        """Set the inclusive year range used when materializing rules."""

        s, e = int(start), int(end)
        if s > e:
            raise CalendarError("year_range requires start <= end.")
        self._year_start, self._year_end = s, e
        return self

    def add_date(self, date: Date) -> CustomCalendarBuilder:
        """Add an explicit holiday date."""

        self._explicit.add(date)
        return self

    def add_dates(self, dates: Iterable[Date]) -> CustomCalendarBuilder:
        """Add explicit holiday dates."""

        for d in dates:
            self._explicit.add(d)
        return self

    def add_fixed_holiday(self, month: int, day: int) -> CustomCalendarBuilder:
        """Add a fixed holiday without weekend observation."""

        m, d = int(month), int(day)
        self._rules.append(lambda y: [Date.from_ymd(y, m, d)])
        return self

    def add_fixed_holiday_observed(self, month: int, day: int) -> CustomCalendarBuilder:
        """Add a fixed holiday with US-style weekend observation."""

        m, d = int(month), int(day)
        self._rules.append(lambda y: [observed_date(Date.from_ymd(y, m, d))])
        return self

    def add_fixed_holiday_from(self, month: int, day: int, from_year: int) -> CustomCalendarBuilder:
        """Add a fixed holiday from `from_year` inclusive with weekend observation."""

        m, d, fy = int(month), int(day), int(from_year)

        def rule(y: int) -> Iterable[Date]:
            if y < fy:
                return []
            return [observed_date(Date.from_ymd(y, m, d))]

        self._rules.append(rule)
        return self

    def add_nth_weekday(self, month: int, weekday: int, occurrence: int) -> CustomCalendarBuilder:
        """Add an Nth-weekday holiday such as a third Monday."""

        m, wd, occ = int(month), int(weekday), int(occurrence)
        self._rules.append(lambda y: [nth_weekday_of_month(y, m, wd, occ)])
        return self

    def add_last_weekday(self, month: int, weekday: int) -> CustomCalendarBuilder:
        """Add a last-weekday holiday such as the last Monday."""

        m, wd = int(month), int(weekday)
        self._rules.append(lambda y: [last_weekday_of_month(y, m, wd)])
        return self

    def add_easter_offset(self, offset_days: int) -> CustomCalendarBuilder:
        """Add an Easter-relative holiday offset from Easter Sunday."""

        off = int(offset_days)
        self._rules.append(lambda y: [easter_sunday(y).add_days(off)])
        return self

    def add_good_friday(self) -> CustomCalendarBuilder:
        """Add Good Friday."""

        return self.add_easter_offset(-2)

    def add_easter_monday(self) -> CustomCalendarBuilder:
        """Add Easter Monday."""

        return self.add_easter_offset(1)

    def add_custom(self, generator: Callable[[int], Iterable[Date]]) -> CustomCalendarBuilder:
        """Add a custom per-year holiday generator."""

        self._rules.append(generator)
        return self

    def build(self) -> DynamicCalendar:
        """Build the dynamic calendar from the configured rules."""

        cal = DynamicCalendar.new(self._name, weekend_type=self._weekend)
        cal.add_holidays(self._explicit)

        if self._year_start is not None and self._year_end is not None:
            for year in range(self._year_start, self._year_end + 1):
                for rule in self._rules:
                    cal.add_holidays(rule(year))
        return cal
