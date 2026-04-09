"""Parallel zero-rate bump helpers.

Parallel bumps add a raw decimal shift to the continuously compounded zero
rate at every tenor.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.types import Compounding, Date

from ..term_structure import TermStructure
from ..value_type import ValueType


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _tenor_from_date(reference_date: Date, date: Date) -> float:
    return float(reference_date.days_between(date)) / 365.0


@dataclass(frozen=True, slots=True)
class BumpedCurve(TermStructure):
    """Curve with a constant raw decimal zero-rate bump."""

    base_curve: TermStructure
    bump: float
    _value_type = ValueType.continuous_zero()

    def date(self) -> Date:
        """Return the date of the underlying curve."""
        return self.base_curve.date()

    def bump_at_tenor(self, t: float) -> float:
        """Return the constant bump applied to tenor ``t``."""
        return float(self.bump)

    def value_at_tenor(self, t: float) -> float:
        """Return the bumped continuous zero rate at tenor ``t``."""

        tenor = max(float(t), 0.0)
        date = self.tenor_to_date(tenor)
        base_zero = self.base_curve.zero_rate(date).convert_to(Compounding.CONTINUOUS).value()
        return float(base_zero) + float(self.bump)


@dataclass(frozen=True, slots=True)
class ParallelBump:
    """Callable-style factory for a parallel bumped curve."""

    bump: float

    def apply(self, curve: TermStructure) -> BumpedCurve:
        """Apply the stored raw decimal shift to ``curve``."""
        return BumpedCurve(base_curve=curve, bump=self.bump)


__all__ = ["ParallelBump", "BumpedCurve"]
