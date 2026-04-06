"""Analytics-layer bond protocols.

The protocols define the narrow interfaces consumed by the pricing and risk
layers for fixed, floating, amortizing, embedded-option, and inflation-linked
bonds.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fuggers_py.core.types import Date

from fuggers_py.reference.bonds.types import AmortizationSchedule, InflationIndexType, PutSchedule, RateIndex


@runtime_checkable
class FixedCouponBond(Protocol):
    """Protocol for bonds exposing a fixed coupon rate."""

    def coupon_rate(self):
        """Return the raw decimal coupon rate."""
        ...


@runtime_checkable
class FloatingCouponBond(Protocol):
    """Protocol for floating-rate bonds with spread and reset semantics."""

    def index(self) -> RateIndex:
        """Return the reference index used by the bond."""
        ...

    def quoted_spread(self):
        """Return the raw decimal spread over the reference index."""
        ...

    def current_coupon_rate(self):
        """Return the current effective coupon rate after spread and bounds."""
        ...


@runtime_checkable
class AmortizingBond(Protocol):
    """Protocol for bonds with a principal amortization schedule."""

    def amortization_schedule(self) -> AmortizationSchedule:
        """Return the scheduled principal reductions."""
        ...


@runtime_checkable
class EmbeddedOptionBond(Protocol):
    """Protocol for bonds that expose workout yields and put schedules."""

    def yield_to_worst(self, clean_price: object, settlement_date: Date):
        """Return the lowest raw decimal yield across all workouts."""
        ...

    def put_schedule(self) -> PutSchedule | None:
        """Return the embedded put schedule, if any."""
        ...


@runtime_checkable
class InflationLinkedBond(Protocol):
    """Protocol for inflation-linked bond references."""

    def inflation_index_type(self) -> InflationIndexType:
        """Return the inflation index family used by the bond."""
        ...


__all__ = [
    "AmortizingBond",
    "EmbeddedOptionBond",
    "FixedCouponBond",
    "FloatingCouponBond",
    "InflationLinkedBond",
]
