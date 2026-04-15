"""Exception hierarchy for :mod:`fuggers_py.market.curves`.

The curve layer uses these exceptions to signal invalid input, curve-building
failures, tenor-range errors, unsupported value-type conversions, and a small
set of legacy builder errors kept for older code paths.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.core.errors import FuggersError


class CurvesError(FuggersError):
    """Base exception for all curve-layer failures."""


class CurveConstructionError(CurvesError):
    """Raised when building a curve fails."""


class InvalidCurveInput(CurvesError):
    """Raised when curve inputs are invalid or inconsistent."""


@dataclass(frozen=True, slots=True)
class TenorOutOfBounds(CurvesError):
    """Raised when a tenor falls outside the supported interval.

    Attributes
    ----------
    t
        Requested tenor in years.
    min
        Inclusive lower tenor bound in years.
    max
        Inclusive upper tenor bound in years.
    """

    t: float
    min: float
    max: float

    def __str__(self) -> str:
        return f"Tenor {self.t:.6g} out of bounds (range=[{self.min:.6g}, {self.max:.6g}])."


class UnsupportedValueType(CurvesError):
    """Raised when a curve value type is not supported for an operation."""


class MissingCurveError(CurvesError):
    """Raised when a requested discount or projection curve is missing."""


class BuilderError(CurveConstructionError):
    """Legacy builder error kept for older builder-style APIs."""


class MixedPillarTypes(BuilderError):
    """Legacy builder error for mixing discount-factor and zero-rate inputs."""


__all__ = [
    "CurvesError",
    "CurveConstructionError",
    "InvalidCurveInput",
    "TenorOutOfBounds",
    "UnsupportedValueType",
    "MissingCurveError",
    "BuilderError",
    "MixedPillarTypes",
]
