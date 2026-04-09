"""Repo-curve helpers built on a term structure."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Date
from fuggers_py.market.curves.term_structure import TermStructure


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class RepoCurve:
    """Wrap a curve and expose repo-style forward-rate calculations.

    The wrapper normalizes a curve-like object into a repo-facing interface so
    callers can ask for discount factors, zero rates, and forward repo rates
    from a single object.

    Parameters
    ----------
    curve
        Underlying curve object supporting discount-factor and zero-rate
        access.
    forward_day_count
        Day-count convention used to annualize forward repo rates.
    """

    curve: TermStructure
    forward_day_count: DayCountConvention = DayCountConvention.ACT_360

    @classmethod
    def of(cls, curve: TermStructure | "RepoCurve") -> "RepoCurve":
        """Return ``curve`` unchanged when already wrapped."""

        if isinstance(curve, cls):
            return curve
        return cls(curve=curve)

    def date(self) -> Date:
        """Return the curve date."""

        return self.curve.date()

    def discount_factor(self, date: Date) -> Decimal:
        """Return the discount factor on ``date`` as a raw decimal."""

        return _to_decimal(self.curve.discount_factor(date))

    def zero_rate(self, date: Date) -> Decimal:
        """Return the curve zero rate on ``date`` as a raw decimal."""

        resolved = self.curve.zero_rate(date)
        if hasattr(resolved, "value"):
            return _to_decimal(resolved.value())
        return _to_decimal(resolved)

    def forward_rate(self, start: Date, end: Date) -> Decimal:
        """Return the forward repo rate between two dates as a raw decimal.

        The rate is annualized using ``forward_day_count`` and derived from the
        ratio of the start and end discount factors.
        """

        tau = self.forward_day_count.to_day_count().year_fraction(start, end)
        if tau == Decimal(0):
            raise ValueError("forward_rate requires distinct start and end dates.")
        df_start = self.discount_factor(start)
        df_end = self.discount_factor(end)
        if df_end == Decimal(0):
            raise ValueError("forward_rate requires a non-zero end-date discount factor.")
        return (df_start / df_end - Decimal(1)) / tau


__all__ = ["RepoCurve"]
