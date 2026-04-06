"""Coupon schedule generation (`fuggers_py.products.bonds.cashflows.schedule`).

It produces both unadjusted and calendar-adjusted schedules. The unadjusted
dates drive accrual calculations while the adjusted dates are used for payment.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.core.calendars import BusinessDayConvention
from fuggers_py.core.types import Date, Frequency

from fuggers_py.reference.bonds.errors import ScheduleError
from fuggers_py.reference.bonds.types import CalendarId, StubPeriodRules, StubType


@dataclass(frozen=True, slots=True)
class ScheduleConfig:
    """Configuration for coupon-schedule generation.

    Parameters
    ----------
    start_date, end_date
        Unadjusted schedule endpoints. The generated schedule always includes
        both dates.
    frequency
        Coupon frequency used to step between regular dates.
    calendar
        Calendar applied when adjusted payment dates are produced.
    business_day_convention
        Adjustment rule for turning unadjusted dates into payment dates.
    end_of_month
        Whether end-of-month anchors are preserved when rolling by months.
    stub_rules
        Explicit front-stub or back-stub instructions, including regular-date
        anchors where applicable.
    """

    start_date: Date
    end_date: Date
    frequency: Frequency
    calendar: CalendarId = CalendarId.weekend_only()
    business_day_convention: BusinessDayConvention = BusinessDayConvention.MODIFIED_FOLLOWING
    end_of_month: bool = True
    stub_rules: StubPeriodRules = StubPeriodRules.default()

    def first_regular_date(self) -> Date | None:
        """Return the explicit first regular coupon date, if any."""

        return self.stub_rules.first_regular_date

    def penultimate_date(self) -> Date | None:
        """Return the explicit penultimate coupon date, if any."""

        return self.stub_rules.penultimate_date

    def stub_type(self) -> StubType | None:
        """Return the configured stub type, if present."""

        return self.stub_rules.stub_type

    def uses_forward_generation(self) -> bool:
        """Return whether the schedule should be rolled forward from ``start_date``."""

        stub_type = self.stub_type()
        if stub_type is not None and stub_type.is_front_stub():
            return True
        return self.first_regular_date() is not None


@dataclass(frozen=True, slots=True)
class Schedule:
    """Generated coupon schedule with unadjusted and adjusted dates."""

    unadjusted_dates: list[Date]
    dates: list[Date]
    config: ScheduleConfig

    @classmethod
    def generate(cls, config: ScheduleConfig) -> "Schedule":
        """Generate a schedule from the supplied configuration."""

        if config.end_date <= config.start_date:
            raise ScheduleError(reason="Schedule end_date must be after start_date.")

        if config.frequency.is_zero():
            unadjusted = [config.start_date, config.end_date]
        elif config.uses_forward_generation():
            unadjusted = _generate_forward(config)
        else:
            unadjusted = _generate_backward(config)

        if not unadjusted or unadjusted[0] != config.start_date or unadjusted[-1] != config.end_date:
            raise ScheduleError(reason="Generated schedule missing start/end date.")

        # Sort + deduplicate.
        seen: set[Date] = set()
        unique_sorted: list[Date] = []
        for d in sorted(unadjusted):
            if d not in seen:
                seen.add(d)
                unique_sorted.append(d)

        cal = config.calendar.to_calendar()
        adjusted = [cal.adjust(d, config.business_day_convention) for d in unique_sorted]
        return cls(unadjusted_dates=unique_sorted, dates=adjusted, config=config)


def _generate_backward(config: ScheduleConfig) -> list[Date]:
    months_per_period = config.frequency.months_per_period()
    if months_per_period <= 0:
        raise ScheduleError(reason="Frequency must be non-zero for coupon schedules.")

    end_date = config.end_date
    dates: list[Date] = [end_date]

    current = end_date
    while current > config.start_date:
        current = current.add_months(-months_per_period)
        if config.end_of_month and end_date.is_end_of_month():
            current = current.end_of_month()

        penultimate = config.penultimate_date()
        if penultimate is not None and current <= penultimate and current > config.start_date:
            dates.append(penultimate)
            current = penultimate
            continue

        if current > config.start_date:
            dates.append(current)

    dates.append(config.start_date)
    dates.reverse()
    return dates


def _generate_forward(config: ScheduleConfig) -> list[Date]:
    months_per_period = config.frequency.months_per_period()
    if months_per_period <= 0:
        raise ScheduleError(reason="Frequency must be non-zero for coupon schedules.")

    start_date = config.start_date
    end_date = config.end_date

    dates: list[Date] = [start_date]
    start_point = config.first_regular_date() or start_date
    if start_point != start_date:
        dates.append(start_point)

    current = start_point
    while current < end_date:
        current = current.add_months(months_per_period)
        if config.end_of_month and start_point.is_end_of_month():
            current = current.end_of_month()
        if current < end_date:
            dates.append(current)

    dates.append(end_date)
    return dates


__all__ = ["ScheduleConfig", "Schedule"]
