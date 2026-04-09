"""Term-structure interface for curve primitives.

The curve layer measures tenors as year fractions from a curve date and
evaluates raw decimal values at those tenors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Date


class TermStructure(ABC):
    """Abstract base class for tenor-based curve objects.

    Implementations expose a curve date and a tenor-based value function.
    """

    @abstractmethod
    def date(self) -> Date:
        """Return the anchor date from which tenors are measured."""

    @abstractmethod
    def value_at_tenor(self, tenor_years: float) -> float:
        """Return the raw curve value at tenor ``t`` in years."""

    def derivative_at_tenor(self, tenor_years: float) -> float | None:  # noqa: D401 - part of trait
        """Return the tenor derivative of :meth:`value_at`, if available."""

        return None

    def value_at_date(self, date: Date) -> float:
        """Return the raw curve value for a calendar date."""

        return self.value_at_tenor(self.date_to_tenor(date))

    def date_to_tenor(self, date: Date, *, day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED) -> float:
        """Convert ``date`` to a year-fraction tenor from the reference date."""

        yf = day_count.to_day_count().year_fraction(self.date(), date)
        return float(yf)

    def tenor_to_date(self, t: float) -> Date:
        """Convert tenor ``t`` in years to an approximate calendar date."""

        days = int(round(float(t) * 365.0))
        return self.date().add_days(days)
