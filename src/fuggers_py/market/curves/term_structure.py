"""Term-structure interface for curve primitives.

The curve layer measures tenors as year fractions from a reference date and
stores node values as raw decimals whose meaning is described by
``ValueType``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Date

from .errors import InvalidCurveInput, TenorOutOfBounds
from .value_type import ValueType


class TermStructure(ABC):
    """Abstract base class for tenor-based curve objects.

    Implementations expose a reference date, a supported tenor range in years,
    and a semantic value type describing what the raw node values represent.
    """

    @abstractmethod
    def reference_date(self) -> Date:
        """Return the anchor date from which tenors are measured."""

    @abstractmethod
    def value_at(self, t: float) -> float:
        """Return the raw curve value at tenor ``t`` in years."""

    @abstractmethod
    def tenor_bounds(self) -> tuple[float, float]:
        """Return the inclusive supported tenor interval in years."""

    @abstractmethod
    def value_type(self) -> ValueType:
        """Return the semantic description of the stored node values."""

    def derivative_at(self, t: float) -> float | None:  # noqa: D401 - part of trait
        """Return the tenor derivative of :meth:`value_at`, if available."""

        return None

    @abstractmethod
    def max_date(self) -> Date:
        """Return the latest calendar date supported by the curve."""

    def in_range(self, t: float) -> bool:
        """Return whether tenor ``t`` lies within the supported bounds."""

        lo, hi = self.tenor_bounds()
        tau = float(t)
        return lo <= tau <= hi

    def has_derivative(self) -> bool:
        """Return whether the curve exposes a tenor derivative."""

        return self.derivative_at(1.0) is not None

    def try_value_at(self, t: float) -> float:
        """Return the curve value at ``t`` or raise for invalid tenor input."""

        tau = float(t)
        if tau < 0.0:
            raise InvalidCurveInput("Tenor must be non-negative.")
        lo, hi = self.tenor_bounds()
        if tau < lo or tau > hi:
            raise TenorOutOfBounds(t=tau, min=lo, max=hi)
        return float(self.value_at(tau))

    def value_at_date(self, date: Date) -> float:
        """Return the raw curve value for a calendar date."""

        return self.value_at(self.date_to_tenor(date))

    def date_to_tenor(self, date: Date, *, day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED) -> float:
        """Convert ``date`` to a year-fraction tenor from the reference date."""

        yf = day_count.to_day_count().year_fraction(self.reference_date(), date)
        return float(yf)

    def tenor_to_date(self, t: float) -> Date:
        """Convert tenor ``t`` in years to an approximate calendar date."""

        days = int(round(float(t) * 365.0))
        return self.reference_date().add_days(days)
