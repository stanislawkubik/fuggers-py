"""Optional shadow-rate curve overlays.

The base curve is treated as an unconstrained "shadow" rate term structure.
The exported curve applies a smooth lower bound to produce an observable rate
curve while preserving the standard :class:`YieldCurve` interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import exp, log1p

from .short_rate_base import ShortRateModelCurve


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _softplus_floor(value: float, lower_bound: float, smoothing: float) -> float:
    scaled = (value - lower_bound) / smoothing
    if scaled >= 40.0:
        return value
    if scaled <= -40.0:
        return lower_bound + smoothing * exp(scaled)
    return lower_bound + smoothing * log1p(exp(scaled))


@dataclass(frozen=True, slots=True)
class ShadowRateCurve(ShortRateModelCurve):
    """Smooth lower-bound transform of a base curve.

    Parameters
    ----------
    lower_bound:
        Effective lower bound for the observable zero rate.
    smoothing:
        Positive smoothing scale. Smaller values behave more like a hard floor.
    """

    lower_bound: Decimal = Decimal("-0.005")
    smoothing: Decimal = Decimal("0.0025")

    def __post_init__(self) -> None:
        object.__setattr__(self, "lower_bound", _to_decimal(self.lower_bound))
        object.__setattr__(self, "smoothing", _to_decimal(self.smoothing))
        if self.smoothing <= Decimal(0):
            raise ValueError("ShadowRateCurve smoothing must be positive.")

    def shadow_zero_rate_at_tenor(self, tenor_years: object) -> Decimal:
        """Return the unconstrained shadow zero rate from the base curve."""
        return self.base_zero_rate_at_tenor(tenor_years)

    def adjusted_zero_rate_at_tenor(self, tenor_years: object) -> Decimal:
        """Return the shadow rate after applying the smooth lower bound."""
        shadow_rate = float(self.shadow_zero_rate_at_tenor(tenor_years))
        adjusted = _softplus_floor(
            shadow_rate,
            float(self.lower_bound),
            float(self.smoothing),
        )
        return Decimal(str(adjusted))


__all__ = ["ShadowRateCurve"]
