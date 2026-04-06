"""Derived curves built from a base curve and simple transforms.

Transforms operate on continuously compounded zero rates in raw decimal form.
This makes parallel shifts, multiplicative overlays, and additive spread
overlays explicit and easy to combine.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Callable

from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Compounding, Date, Yield

from .conversion import ValueConverter
from .wrappers import RateCurve


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class CurveTransformKind(str, Enum):
    """Kinds of transform supported by :class:`CurveTransform`."""

    PARALLEL_SHIFT = "PARALLEL_SHIFT"
    MULTIPLICATIVE = "MULTIPLICATIVE"
    SPREAD_OVERLAY = "SPREAD_OVERLAY"
    FUNCTION = "FUNCTION"


@dataclass(frozen=True, slots=True)
class CurveTransform:
    """Single transform applied to a base zero rate.

    Parameters
    ----------
    kind:
        Transform family.
    amount:
        Raw decimal amount used by parallel-shift and multiplicative
        transforms.
    overlay:
        Optional curve whose continuously compounded zero rate is added for
        spread overlays.
    fn:
        Optional callable used for arbitrary transforms.
    """

    kind: CurveTransformKind
    amount: Decimal = Decimal(0)
    overlay: YieldCurve | None = None
    fn: Callable[[float, float], float] | None = None

    @classmethod
    def parallel_shift(cls, amount: object) -> "CurveTransform":
        """Create an additive raw-decimal zero-rate shift."""
        return cls(kind=CurveTransformKind.PARALLEL_SHIFT, amount=_to_decimal(amount))

    @classmethod
    def multiplicative(cls, factor: object) -> "CurveTransform":
        """Create a multiplicative scaling of the base zero rate."""
        return cls(kind=CurveTransformKind.MULTIPLICATIVE, amount=_to_decimal(factor))

    @classmethod
    def spread_overlay(cls, overlay: YieldCurve) -> "CurveTransform":
        """Create an additive overlay using the overlay curve's zero rate."""
        return cls(kind=CurveTransformKind.SPREAD_OVERLAY, overlay=overlay)

    @classmethod
    def function(cls, fn: Callable[[float, float], float]) -> "CurveTransform":
        """Create a custom tenor/base-zero transform."""
        return cls(kind=CurveTransformKind.FUNCTION, fn=fn)

    def apply(self, *, tenor: float, base_zero: float, date: Date) -> float:
        """Apply the transform to a continuously compounded base zero rate.

        The transform always receives the tenor in years and the base zero rate
        in continuous compounding, then returns a transformed continuous zero
        rate.
        """
        if self.kind is CurveTransformKind.PARALLEL_SHIFT:
            return base_zero + float(self.amount)
        if self.kind is CurveTransformKind.MULTIPLICATIVE:
            return base_zero * float(self.amount)
        if self.kind is CurveTransformKind.SPREAD_OVERLAY:
            if self.overlay is None:  # pragma: no cover - defensive
                return base_zero
            overlay_zero = self.overlay.zero_rate(date).convert_to(Compounding.CONTINUOUS).value()
            return base_zero + float(overlay_zero)
        if self.kind is CurveTransformKind.FUNCTION:
            if self.fn is None:  # pragma: no cover - defensive
                return base_zero
            return float(self.fn(float(tenor), float(base_zero)))
        return base_zero


@dataclass(frozen=True, slots=True)
class DerivedCurve(YieldCurve):
    """Curve derived from a base curve via a sequence of transforms.

    The curve keeps the base curve's date anchors and applies each transform in
    order to the base continuously compounded zero rate.
    """

    base_curve: YieldCurve
    transforms: tuple[CurveTransform, ...]

    @classmethod
    def from_curve(cls, base_curve: YieldCurve, *transforms: CurveTransform) -> "DerivedCurve":
        """Construct a derived curve from a base curve and transforms."""
        return cls(base_curve=base_curve, transforms=tuple(transforms))

    @classmethod
    def parallel_shift(cls, base_curve: YieldCurve, amount: object) -> "DerivedCurve":
        """Construct a derived curve with a single parallel shift."""
        return cls.from_curve(base_curve, CurveTransform.parallel_shift(amount))

    @classmethod
    def spread_overlay(cls, base_curve: YieldCurve, overlay: YieldCurve) -> "DerivedCurve":
        """Construct a derived curve with a zero-rate spread overlay."""
        return cls.from_curve(base_curve, CurveTransform.spread_overlay(overlay))

    @classmethod
    def transformed(
        cls,
        base_curve: YieldCurve | RateCurve,
        fn: Callable[[float, float], float],
    ) -> "DerivedCurve":
        """Construct a derived curve backed by an arbitrary callable."""
        curve = base_curve if isinstance(base_curve, YieldCurve) else RateCurve(base_curve)
        return cls.from_curve(curve, CurveTransform.function(fn))

    def reference_date(self) -> Date:
        """Return the reference date of the base curve."""
        return self.base_curve.reference_date()

    def max_date(self) -> Date:
        """Return the maximum date supported by the base curve."""
        return self.base_curve.max_date()

    def zero_rate(self, date: Date) -> Yield:
        """Return the transformed continuously compounded zero rate."""
        tenor = max(float(self.reference_date().days_between(date)) / 365.0, 0.0)
        zero = float(self.base_curve.zero_rate(date).convert_to(Compounding.CONTINUOUS).value())
        for transform in self.transforms:
            zero = transform.apply(tenor=tenor, base_zero=zero, date=date)
        return Yield.new(_to_decimal(zero), Compounding.CONTINUOUS)

    def discount_factor(self, date: Date) -> Decimal:
        """Return the discount factor implied by the transformed zero rate."""
        tenor = max(float(self.reference_date().days_between(date)) / 365.0, 0.0)
        if tenor <= 0.0:
            return Decimal(1)
        zero = float(self.zero_rate(date).value())
        return _to_decimal(ValueConverter.zero_to_df(zero, tenor, Compounding.CONTINUOUS))


__all__ = ["CurveTransform", "CurveTransformKind", "DerivedCurve"]
