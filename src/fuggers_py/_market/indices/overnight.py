"""Overnight fixing conventions and compounding helpers.

The helpers in this module convert overnight fixings into coupon rates using
the index conventions stored on :class:`IndexConventions`.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from fuggers_py._core.calendars import Calendar, WeekendCalendar
from fuggers_py._core.types import Date

from .conventions import IndexConventions, ObservationShiftType

if TYPE_CHECKING:
    from .fixing_store import IndexFixingStore


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class OvernightCompounding(str, Enum):
    """Overnight coupon aggregation method for floating-rate instruments."""

    COMPOUNDED = "COMPOUNDED"
    SIMPLE = "SIMPLE"
    AVERAGED = "AVERAGED"

    def compounded_rate(
        self,
        start_date: Date,
        end_date: Date,
        *,
        index_name: str,
        fixing_store: "IndexFixingStore",
        conventions: IndexConventions,
        calendar: Calendar | None = None,
        fallback_rate: Decimal | None = None,
        forward_curve: object | None = None,
        as_of: Date | None = None,
    ) -> Decimal:
        """Return the compounded overnight rate over an accrual window.

        The result is the gross compounded return over the sub-periods divided
        by the total accrual year fraction.
        """

        schedule = _business_accrual_schedule(start_date, end_date, calendar or WeekendCalendar())
        if not schedule:
            return Decimal(0)

        compound = Decimal(1)
        for index, (fixing_date, segment_end) in enumerate(schedule):
            observed = _observed_schedule_date(schedule, index, conventions, calendar or WeekendCalendar())
            rate = _lookup_or_project_rate(
                index_name=index_name,
                fixing_store=fixing_store,
                observed_date=observed,
                segment_start=fixing_date,
                segment_end=segment_end,
                fallback_rate=fallback_rate,
                forward_curve=forward_curve,
                as_of=as_of,
            )
            compound *= overnight_factor(rate, fixing_date, segment_end, conventions)

        total_accrual = self.accrual_factor(start_date, end_date, conventions=conventions)
        if total_accrual == 0:
            return Decimal(0)
        return (compound - Decimal(1)) / total_accrual

    def simple_average_rate(
        self,
        start_date: Date,
        end_date: Date,
        *,
        index_name: str,
        fixing_store: "IndexFixingStore",
        conventions: IndexConventions,
        calendar: Calendar | None = None,
        fallback_rate: Decimal | None = None,
        forward_curve: object | None = None,
        as_of: Date | None = None,
    ) -> Decimal:
        """Return the simple weighted-average overnight rate over a period.

        Each observed fixing is weighted by the accrual year fraction of its
        sub-period.
        """

        schedule = _business_accrual_schedule(start_date, end_date, calendar or WeekendCalendar())
        if not schedule:
            return Decimal(0)

        weighted = Decimal(0)
        total = Decimal(0)
        for index, (fixing_date, segment_end) in enumerate(schedule):
            observed = _observed_schedule_date(schedule, index, conventions, calendar or WeekendCalendar())
            rate = _lookup_or_project_rate(
                index_name=index_name,
                fixing_store=fixing_store,
                observed_date=observed,
                segment_start=fixing_date,
                segment_end=segment_end,
                fallback_rate=fallback_rate,
                forward_curve=forward_curve,
                as_of=as_of,
            )
            accrual = conventions.day_count.to_day_count().year_fraction(fixing_date, segment_end)
            weighted += rate * accrual
            total += accrual
        if total == 0:
            return Decimal(0)
        return weighted / total

    def required_fixing_dates(
        self,
        start_date: Date,
        end_date: Date,
        *,
        conventions: IndexConventions,
        calendar: Calendar | None = None,
    ) -> list[Date]:
        """Return the fixing dates needed to value the accrual window."""

        schedule = _business_accrual_schedule(start_date, end_date, calendar or WeekendCalendar())
        return [
            _observed_schedule_date(schedule, index, conventions, calendar or WeekendCalendar())
            for index, _ in enumerate(schedule)
        ]

    def accrual_factor(self, start_date: Date, end_date: Date, *, conventions: IndexConventions) -> Decimal:
        """Return the accrual year fraction for the coupon window."""

        if end_date <= start_date:
            return Decimal(0)
        return conventions.day_count.to_day_count().year_fraction(start_date, end_date)


class PublicationTime(str, Enum):
    """Publication timing for daily overnight fixings."""

    SAME_DAY = "SAME_DAY"
    END_OF_DAY = "END_OF_DAY"
    NEXT_BUSINESS_DAY = "NEXT_BUSINESS_DAY"


def _business_accrual_schedule(start_date: Date, end_date: Date, calendar: Calendar) -> list[tuple[Date, Date]]:
    if end_date <= start_date:
        return []
    current = calendar.next_business_day(start_date)
    schedule: list[tuple[Date, Date]] = []
    while current < end_date:
        next_business = calendar.add_business_days(current, 1)
        segment_end = Date.min(next_business, end_date)
        schedule.append((current, segment_end))
        current = next_business
    return schedule


def observation_date(date: Date, conventions: IndexConventions, calendar: Calendar | None = None) -> Date:
    """Return the observed fixing date used for an overnight accrual date."""

    active_calendar = calendar or WeekendCalendar()
    if conventions.observation_shift_type in {ObservationShiftType.LOOKBACK, ObservationShiftType.OBSERVATION_SHIFT}:
        shifted = active_calendar.add_business_days(date, -int(conventions.lookback_days))
        return active_calendar.previous_business_day(shifted)
    return active_calendar.previous_business_day(date)


def _observed_schedule_date(
    schedule: list[tuple[Date, Date]],
    index: int,
    conventions: IndexConventions,
    calendar: Calendar,
) -> Date:
    lockout_days = max(int(conventions.lockout_days or conventions.rate_cutoff_days), 0)
    cutoff_index = index
    if lockout_days > 0 and index >= len(schedule) - lockout_days:
        cutoff_index = max(len(schedule) - lockout_days - 1, 0)
    fixing_date, _ = schedule[cutoff_index]
    return observation_date(fixing_date, conventions, calendar=calendar)


def publication_date(date: Date, conventions: IndexConventions, calendar: Calendar | None = None) -> Date:
    """Return the publication date for a fixing observed on ``date``."""

    active_calendar = calendar or WeekendCalendar()
    lag = int(conventions.publication_lag_days)
    return active_calendar.add_business_days(date, lag)


def overnight_factor(rate: Decimal, start: Date, end: Date, conventions: IndexConventions) -> Decimal:
    """Return the gross overnight accrual factor for one sub-period."""

    year_fraction = conventions.day_count.to_day_count().year_fraction(start, end)
    return Decimal(1) + rate * year_fraction


def _lookup_or_project_rate(
    *,
    index_name: str,
    fixing_store: "IndexFixingStore",
    observed_date: Date,
    segment_start: Date,
    segment_end: Date,
    fallback_rate: Decimal | None,
    forward_curve: object | None,
    as_of: Date | None,
) -> Decimal:
    if as_of is None or observed_date <= as_of:
        fixing = fixing_store.get_rate(index_name, observed_date)
        if fixing is not None:
            return fixing

    if forward_curve is not None:
        if hasattr(forward_curve, "forward_rate"):
            return _to_decimal(forward_curve.forward_rate(segment_start, segment_end))
        if hasattr(forward_curve, "forward_rate_at") and hasattr(forward_curve, "reference_date"):
            reference_date = getattr(forward_curve, "reference_date")
            tenor = max(reference_date.days_between(segment_start), 0) / 365.0
            return _to_decimal(forward_curve.forward_rate_at(tenor))

    if fallback_rate is not None:
        return fallback_rate

    fixing = fixing_store.get_rate(index_name, observed_date)
    if fixing is not None:
        return fixing
    raise KeyError(f"Missing fixing for {index_name} on {observed_date}.")


__all__ = [
    "OvernightCompounding",
    "PublicationTime",
    "observation_date",
    "overnight_factor",
    "publication_date",
]
