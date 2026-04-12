"""Benchmark tracking helpers.

Tracking error is a heuristic blend of active duration, active spread, and
portfolio dispersion, reported as a raw decimal estimate.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.types import Date
from fuggers_py.market.curves import DiscountingCurve

from .comparison import PortfolioBenchmark


@dataclass(frozen=True, slots=True)
class TrackingErrorEstimate:
    """Heuristic tracking-error estimate and its components.

    The estimate is a heuristic decimal value, not a statistically fitted
    tracking-error model.
    """

    estimate: Decimal
    duration_component: Decimal = Decimal(0)
    spread_component: Decimal = Decimal(0)
    dispersion_component: Decimal = Decimal(0)

    def __getattr__(self, name: str):
        """Delegate numeric operations to the raw estimate."""

        return getattr(self.estimate, name)

    def __float__(self) -> float:
        return float(self.estimate)

    def __str__(self) -> str:
        return str(self.estimate)

    def __repr__(self) -> str:
        return f"TrackingErrorEstimate(estimate={self.estimate!r})"

    def _coerce_other(self, other: object) -> Decimal:
        if isinstance(other, TrackingErrorEstimate):
            return other.estimate
        if isinstance(other, Decimal):
            return other
        return Decimal(str(other))

    def __eq__(self, other: object) -> bool:
        try:
            return self.estimate == self._coerce_other(other)
        except Exception:
            return False

    def __lt__(self, other: object) -> bool:
        return self.estimate < self._coerce_other(other)

    def __le__(self, other: object) -> bool:
        return self.estimate <= self._coerce_other(other)

    def __gt__(self, other: object) -> bool:
        return self.estimate > self._coerce_other(other)

    def __ge__(self, other: object) -> bool:
        return self.estimate >= self._coerce_other(other)

    def as_decimal(self) -> Decimal:
        """Return the tracking-error estimate as a decimal."""

        return self.estimate


def estimate_tracking_error(
    benchmark: PortfolioBenchmark,
    curve: DiscountingCurve,
    settlement_date: Date,
) -> TrackingErrorEstimate:
    """Estimate tracking error from active risk and holding dispersion.

    The result combines active duration, active spread, and a simple
    dispersion term derived from active weights.
    """

    comparison = benchmark.compare(curve, settlement_date)
    active_weights = benchmark.active_weights(curve, settlement_date)
    dispersion = sum((abs(value) for value in active_weights.values()), Decimal(0))
    duration_component = abs(comparison.active_duration) * Decimal("0.01")
    spread_component = abs(comparison.active_z_spread) * Decimal("0.001")
    dispersion_component = dispersion * Decimal("0.005")
    return TrackingErrorEstimate(
        estimate=duration_component + spread_component + dispersion_component,
        duration_component=duration_component,
        spread_component=spread_component,
        dispersion_component=dispersion_component,
    )


__all__ = ["TrackingErrorEstimate", "estimate_tracking_error"]
