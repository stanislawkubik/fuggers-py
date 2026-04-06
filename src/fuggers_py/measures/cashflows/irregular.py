"""Irregular-period helpers for analytics.

These helpers expose the small amount of analytics-specific logic used for
irregular coupon periods while relying on the core day-count conventions for
all year-fraction calculations.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Date

from ..errors import AnalyticsError


@dataclass(frozen=True, slots=True)
class IrregularPeriodHandler:
    """Helper for irregular coupon-period calculations.

    Parameters
    ----------
    day_count:
        Day-count convention used to compute day counts and year fractions.
    """

    day_count: DayCountConvention = DayCountConvention.ACT_360

    @classmethod
    def new(cls, day_count: DayCountConvention) -> IrregularPeriodHandler:
        """Construct a handler for ``day_count``."""

        return cls(day_count=day_count)

    def days_between(self, start: Date, end: Date) -> int:
        """Return the number of days between ``start`` and ``end``."""

        return int(self.day_count.to_day_count().day_count(start, end))

    def year_fraction(self, start: Date, end: Date) -> float:
        """Return the year fraction between ``start`` and ``end``."""

        return float(self.day_count.to_day_count().year_fraction(start, end))

    def annual_factor(self, start: Date, end: Date) -> float:
        """Return the annualization factor for the irregular period.

        The factor is the reciprocal of the year fraction and raises an
        analytics input error when the period length is not strictly positive.
        """

        frac = self.year_fraction(start, end)
        if frac <= 0.0:
            raise AnalyticsError.invalid_input("Irregular period year fraction must be positive.")
        return 1.0 / float(frac)


__all__ = ["IrregularPeriodHandler"]
