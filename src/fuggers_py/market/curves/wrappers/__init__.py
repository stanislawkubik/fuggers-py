"""Convenience wrappers for curve primitives.

The wrappers adapt term structures to the yield-curve and credit-curve traits
used by the rest of the library.
"""

from __future__ import annotations

from .credit_curve import CreditCurve
from .curve_ref import CurveRef
from .rate_curve import RateCurve

DiscountCurve = RateCurve

__all__ = ["RateCurve", "DiscountCurve", "CreditCurve", "CurveRef"]
