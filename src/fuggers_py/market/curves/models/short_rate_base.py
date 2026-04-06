"""Base helpers for optional short-rate-inspired curve overlays.

These models intentionally sit beside the default production curve path.
They wrap an existing :class:`~fuggers_py.core.traits.YieldCurve` and expose
the same discount-factor / zero-rate interface, but they do not participate in
the repository's standard bootstrap or fitted-curve workflows.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Compounding, Date, Yield

from ..conversion import ValueConverter


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class ShortRateModelPoint:
    """Diagnostic point for a short-rate-style overlay.

    The point captures the base zero rate, adjusted zero rate, and the overlay
    adjustment at one tenor so callers can inspect the model behavior directly.
    """

    tenor_years: Decimal
    base_zero_rate: Decimal
    adjusted_zero_rate: Decimal
    adjustment: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenor_years", _to_decimal(self.tenor_years))
        object.__setattr__(self, "base_zero_rate", _to_decimal(self.base_zero_rate))
        object.__setattr__(self, "adjusted_zero_rate", _to_decimal(self.adjusted_zero_rate))
        object.__setattr__(self, "adjustment", _to_decimal(self.adjustment))


@dataclass(frozen=True, slots=True)
class ShortRateModelCurve(YieldCurve, ABC):
    """Base class for optional model-based curve overlays.

    Implementations are expected to provide an adjusted continuously
    compounded zero rate. The base curve is left untouched and remains
    available for diagnostics and comparison.
    """

    base_curve: YieldCurve

    def reference_date(self) -> Date:
        """Return the reference date of the base curve."""
        return self.base_curve.reference_date()

    def max_date(self) -> Date:
        """Return the maximum date supported by the base curve."""
        return self.base_curve.max_date()

    def tenor_in_years(self, date: Date) -> Decimal:
        """Return the ACT/365F tenor from the reference date to ``date``."""
        if date <= self.reference_date():
            return Decimal(0)
        return _to_decimal(
            DayCountConvention.ACT_365_FIXED.to_day_count().year_fraction(
                self.reference_date(),
                date,
            )
        )

    def _tenor_to_date(self, tenor_years: object) -> Date:
        tenor = _to_decimal(tenor_years)
        if tenor <= Decimal(0):
            return self.reference_date()
        return self.reference_date().add_days(int(round(float(tenor) * 365.0)))

    def base_zero_rate_at_tenor(self, tenor_years: object) -> Decimal:
        """Return the base curve zero rate in continuous compounding."""
        tenor = _to_decimal(tenor_years)
        if tenor <= Decimal(0):
            return Decimal(0)
        date = self._tenor_to_date(tenor)
        return self.base_curve.zero_rate(date).convert_to(Compounding.CONTINUOUS).value()

    def base_zero_rate(self, date: Date) -> Decimal:
        """Return the base curve zero rate at a date."""
        return self.base_zero_rate_at_tenor(self.tenor_in_years(date))

    @abstractmethod
    def adjusted_zero_rate_at_tenor(self, tenor_years: object) -> Decimal:
        """Return the model-adjusted continuously compounded zero rate."""

    def adjustment_at_tenor(self, tenor_years: object) -> Decimal:
        """Return the model adjustment over the base curve at a tenor."""
        tenor = _to_decimal(tenor_years)
        return self.adjusted_zero_rate_at_tenor(tenor) - self.base_zero_rate_at_tenor(tenor)

    def model_point(self, date: Date) -> ShortRateModelPoint:
        """Return a diagnostic point for the base and adjusted zero rates."""
        tenor = self.tenor_in_years(date)
        base_zero = self.base_zero_rate_at_tenor(tenor)
        adjusted_zero = self.adjusted_zero_rate_at_tenor(tenor)
        return ShortRateModelPoint(
            tenor_years=tenor,
            base_zero_rate=base_zero,
            adjusted_zero_rate=adjusted_zero,
            adjustment=adjusted_zero - base_zero,
        )

    def zero_rate(self, date: Date) -> Yield:
        """Return the adjusted continuously compounded zero rate."""
        tenor = self.tenor_in_years(date)
        if tenor <= Decimal(0):
            return Yield.new(Decimal(0), Compounding.CONTINUOUS)
        return Yield.new(self.adjusted_zero_rate_at_tenor(tenor), Compounding.CONTINUOUS)

    def discount_factor(self, date: Date) -> Decimal:
        """Return the discount factor implied by the adjusted zero rate."""
        tenor = self.tenor_in_years(date)
        if tenor <= Decimal(0):
            return Decimal(1)
        zero_rate = self.adjusted_zero_rate_at_tenor(tenor)
        return _to_decimal(ValueConverter.zero_to_df(float(zero_rate), float(tenor), Compounding.CONTINUOUS))


__all__ = ["ShortRateModelCurve", "ShortRateModelPoint"]
