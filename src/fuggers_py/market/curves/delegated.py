"""Delegated curves that fall back to a secondary source.

The primary curve is queried first and the fallback curve is used when the
primary curve is out of range or produces a missing value, depending on the
selected fallback mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isnan

from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Date

from .term_structure import TermStructure
from .value_type import ValueType
from .wrappers import RateCurve


class DelegationFallback(str, Enum):
    """Fallback policy for :class:`DelegatedCurve`."""

    OUT_OF_RANGE = "OUT_OF_RANGE"
    MISSING_VALUE = "MISSING_VALUE"
    OUT_OF_RANGE_OR_MISSING = "OUT_OF_RANGE_OR_MISSING"
    ALWAYS_FALLBACK = "ALWAYS_FALLBACK"


@dataclass(frozen=True, slots=True)
class _YieldCurveTermStructure(TermStructure):
    curve: YieldCurve

    def reference_date(self) -> Date:
        return self.curve.reference_date()

    def value_at(self, t: float) -> float:
        date = self.tenor_to_date(t)
        return float(self.curve.zero_rate(date).value())

    def tenor_bounds(self) -> tuple[float, float]:
        return 0.0, self.date_to_tenor(self.curve.max_date())

    def value_type(self) -> ValueType:
        return ValueType.zero_rate()

    def max_date(self) -> Date:
        return self.curve.max_date()


def _as_term_structure(source: TermStructure | YieldCurve) -> TermStructure:
    if isinstance(source, TermStructure):
        return source
    if isinstance(source, RateCurve):
        return source.curve
    return _YieldCurveTermStructure(source)


@dataclass(frozen=True, slots=True)
class DelegatedCurve(TermStructure):
    """Curve that delegates to a fallback curve when the primary fails.

    The wrapper lets callers define a primary curve and a fallback source while
    choosing whether out-of-range tenors, missing values, or both should trigger
    the fallback.
    """

    primary: TermStructure | YieldCurve
    fallback: TermStructure | YieldCurve
    fallback_mode: DelegationFallback = DelegationFallback.OUT_OF_RANGE_OR_MISSING
    _primary_curve: TermStructure = field(init=False, repr=False)
    _fallback_curve: TermStructure = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_primary_curve", _as_term_structure(self.primary))
        object.__setattr__(self, "_fallback_curve", _as_term_structure(self.fallback))

    def reference_date(self) -> Date:
        """Return the primary curve reference date."""
        return self._primary_curve.reference_date()

    def tenor_bounds(self) -> tuple[float, float]:
        """Return the combined tenor span of the primary and fallback curves."""
        p_lo, p_hi = self._primary_curve.tenor_bounds()
        f_lo, f_hi = self._fallback_curve.tenor_bounds()
        return min(p_lo, f_lo), max(p_hi, f_hi)

    def value_type(self) -> ValueType:
        """Return the value type of the primary curve."""
        return self._primary_curve.value_type()

    def max_date(self) -> Date:
        """Return the latest date supported by either underlying curve."""
        return max(self._primary_curve.max_date(), self._fallback_curve.max_date())

    def _use_fallback_for_tenor(self, tenor: float) -> bool:
        if self.fallback_mode is DelegationFallback.ALWAYS_FALLBACK:
            return True
        if self.fallback_mode in {
            DelegationFallback.OUT_OF_RANGE,
            DelegationFallback.OUT_OF_RANGE_OR_MISSING,
        } and not self._primary_curve.in_range(tenor):
            return True
        return False

    def _primary_value_missing(self, tenor: float) -> bool:
        value = float(self._primary_curve.value_at(tenor))
        return isnan(value)

    def value_at(self, t: float) -> float:
        """Return the primary value unless the fallback policy is triggered."""
        tenor = float(t)
        if self._use_fallback_for_tenor(tenor):
            return float(self._fallback_curve.value_at(tenor))

        if self.fallback_mode in {
            DelegationFallback.MISSING_VALUE,
            DelegationFallback.OUT_OF_RANGE_OR_MISSING,
        } and self._primary_value_missing(tenor):
            return float(self._fallback_curve.value_at(tenor))
        return float(self._primary_curve.value_at(tenor))

    def derivative_at(self, t: float) -> float | None:
        """Return the primary derivative unless the fallback policy is triggered."""
        tenor = float(t)
        if self._use_fallback_for_tenor(tenor):
            return self._fallback_curve.derivative_at(tenor)
        derivative = self._primary_curve.derivative_at(tenor)
        if derivative is None and self.fallback_mode in {
            DelegationFallback.MISSING_VALUE,
            DelegationFallback.OUT_OF_RANGE_OR_MISSING,
        }:
            return self._fallback_curve.derivative_at(tenor)
        return derivative


__all__ = ["DelegatedCurve", "DelegationFallback"]
