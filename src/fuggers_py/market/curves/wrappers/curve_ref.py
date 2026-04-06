"""Lightweight wrapper for curve references.

The reference object preserves a curve-like input while providing convenience
methods for callers that expect either the raw term structure or a
``RateCurve`` wrapper.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..term_structure import TermStructure
from .rate_curve import RateCurve


CurveLike = TermStructure | RateCurve


@dataclass(frozen=True, slots=True)
class CurveRef:
    """Store a curve or yield-curve wrapper behind a stable reference.

    The reference is useful when callers need to preserve the original curve
    object but still accept either a raw term structure or an already wrapped
    yield curve.

    Attributes
    ----------
    curve
        Stored curve-like object.
    """

    curve: CurveLike

    @classmethod
    def of(cls, curve: CurveLike | "CurveRef") -> "CurveRef":
        """Return ``curve`` as a :class:`CurveRef`."""

        if isinstance(curve, cls):
            return curve
        return cls(curve=curve)

    def unwrap(self) -> CurveLike:
        """Return the stored curve-like object."""

        return self.curve

    def as_curve(self) -> TermStructure:
        """Return the wrapped term structure without any yield-curve adapter."""

        if isinstance(self.curve, RateCurve):
            return self.curve.curve
        return self.curve

    def as_discount_curve(self) -> RateCurve:
        """Return the curve as a :class:`RateCurve` wrapper."""

        if isinstance(self.curve, RateCurve):
            return self.curve
        return RateCurve(self.curve)

    def reference_date(self):
        """Forward :meth:`reference_date` to the wrapped object."""

        return self.curve.reference_date()

    def max_date(self):
        """Forward :meth:`max_date` to the wrapped object."""

        return self.curve.max_date()

    def __getattr__(self, name: str):
        """Delegate unknown attributes to the wrapped object."""

        return getattr(self.curve, name)


__all__ = ["CurveRef", "CurveLike"]
