"""Delegated curves that fall back to a secondary source.

The primary curve is queried first and the fallback curve is used when the
primary curve is out of range or produces a missing value, depending on the
selected fallback mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isnan
from fuggers_py.core.types import Date

from .term_structure import TermStructure


class DelegationFallback(str, Enum):
    """Fallback policy for :class:`DelegatedCurve`."""

    OUT_OF_RANGE = "OUT_OF_RANGE"
    MISSING_VALUE = "MISSING_VALUE"
    OUT_OF_RANGE_OR_MISSING = "OUT_OF_RANGE_OR_MISSING"
    ALWAYS_FALLBACK = "ALWAYS_FALLBACK"


def _as_term_structure(source: TermStructure) -> TermStructure:
    return source


def _supports_tenor(curve: TermStructure, tenor: float) -> bool:
    bounds = getattr(curve, "_bounds", None)
    if isinstance(bounds, tuple) and len(bounds) == 2:
        lo, hi = bounds
        return float(lo) <= tenor <= float(hi)

    if hasattr(curve, "tenors"):
        tenors_getter = getattr(curve, "tenors")
        if callable(tenors_getter):
            try:
                tenors = tenors_getter()
            except Exception:
                tenors = None
            if tenors is not None and len(tenors) > 0:
                return float(tenors[0]) <= tenor <= float(tenors[-1])

    if hasattr(curve, "segments"):
        segments = getattr(curve, "segments")
        try:
            if segments:
                return float(segments[0].start) <= tenor <= float(segments[-1].end)
        except Exception:
            pass

    return True


@dataclass(frozen=True, slots=True)
class DelegatedCurve(TermStructure):
    """Curve that delegates to a fallback curve when the primary fails.

    The wrapper lets callers define a primary curve and a fallback source while
    choosing whether out-of-range tenors, missing values, or both should trigger
    the fallback.
    """

    primary: TermStructure
    fallback: TermStructure
    fallback_mode: DelegationFallback = DelegationFallback.OUT_OF_RANGE_OR_MISSING
    _primary_curve: TermStructure = field(init=False, repr=False)
    _fallback_curve: TermStructure = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_primary_curve", _as_term_structure(self.primary))
        object.__setattr__(self, "_fallback_curve", _as_term_structure(self.fallback))

    def date(self) -> Date:
        """Return the primary curve date."""
        return self._primary_curve.date()

    def value_type(self):
        """Return the primary value semantics when available."""

        return self._primary_curve.value_type() or self._fallback_curve.value_type()

    def _use_fallback_for_tenor(self, tenor: float) -> bool:
        if self.fallback_mode is DelegationFallback.ALWAYS_FALLBACK:
            return True
        if self.fallback_mode in {DelegationFallback.OUT_OF_RANGE, DelegationFallback.OUT_OF_RANGE_OR_MISSING}:
            if not _supports_tenor(self._primary_curve, tenor):
                return True
            try:
                self._primary_curve.value_at_tenor(tenor)
            except Exception:
                return True
        return False

    def _primary_value_missing(self, tenor: float) -> bool:
        value = float(self._primary_curve.value_at_tenor(tenor))
        return isnan(value)

    def value_at_tenor(self, t: float) -> float:
        """Return the primary value unless the fallback policy is triggered."""
        tenor = float(t)
        if self._use_fallback_for_tenor(tenor):
            return float(self._fallback_curve.value_at_tenor(tenor))

        if self.fallback_mode in {
            DelegationFallback.MISSING_VALUE,
            DelegationFallback.OUT_OF_RANGE_OR_MISSING,
        } and self._primary_value_missing(tenor):
            return float(self._fallback_curve.value_at_tenor(tenor))
        return float(self._primary_curve.value_at_tenor(tenor))

    def derivative_at_tenor(self, t: float) -> float | None:
        """Return the primary derivative unless the fallback policy is triggered."""
        tenor = float(t)
        if self._use_fallback_for_tenor(tenor):
            return self._fallback_curve.derivative_at_tenor(tenor)
        derivative = self._primary_curve.derivative_at_tenor(tenor)
        if derivative is None and self.fallback_mode in {
            DelegationFallback.MISSING_VALUE,
            DelegationFallback.OUT_OF_RANGE_OR_MISSING,
        }:
            return self._fallback_curve.derivative_at_tenor(tenor)
        return derivative


__all__ = ["DelegatedCurve", "DelegationFallback"]
