"""Parallel zero-rate bump helpers.

Parallel bumps add a raw decimal shift to the continuously compounded zero
rate at every tenor.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Compounding, Date, Yield

from ..conversion import ValueConverter


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _tenor_from_date(reference_date: Date, date: Date) -> float:
    return float(reference_date.days_between(date)) / 365.0


@dataclass(frozen=True, slots=True)
class BumpedCurve(YieldCurve):
    """Curve with a constant raw decimal zero-rate bump."""

    base_curve: YieldCurve
    bump: float

    def date(self) -> Date:
        """Return the date of the underlying curve."""
        return self.base_curve.date()

    def bump_at_tenor(self, t: float) -> float:
        """Return the constant bump applied to tenor ``t``."""
        return float(self.bump)

    def zero_rate_at_tenor(self, t: float) -> float:
        """Return the bumped continuous zero rate at tenor ``t``."""
        date = self.date().add_days(int(round(float(t) * 365.0)))
        return float(self.zero_rate(date).value())

    def zero_rate(self, date: Date) -> Yield:
        """Return the continuously compounded bumped zero rate."""
        base_zero = self.base_curve.zero_rate(date).convert_to(Compounding.CONTINUOUS).value()
        bumped = float(base_zero) + float(self.bump)
        return Yield.new(_to_decimal(bumped), Compounding.CONTINUOUS)

    def discount_factor(self, date: Date) -> Decimal:
        """Return the discount factor implied by the bumped zero rate."""
        t = _tenor_from_date(self.date(), date)
        if t <= 0.0:
            return Decimal(1)
        zero = self.zero_rate(date).value()
        df = ValueConverter.zero_to_df(float(zero), float(t), Compounding.CONTINUOUS)
        return _to_decimal(df)


@dataclass(frozen=True, slots=True)
class ParallelBump:
    """Callable-style factory for a parallel bumped curve."""

    bump: float

    def apply(self, curve: YieldCurve) -> BumpedCurve:
        """Apply the stored raw decimal shift to ``curve``."""
        return BumpedCurve(base_curve=curve, bump=self.bump)


__all__ = ["ParallelBump", "BumpedCurve"]
