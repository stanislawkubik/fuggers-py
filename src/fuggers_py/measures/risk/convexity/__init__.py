"""Convexity analytics (`fuggers_py.measures.risk.convexity`).

Convexity outputs follow the same positive-magnitude convention as duration.
The price-change helper applies the second-order approximation for a yield
shock.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .analytical import analytical_convexity
from .effective import effective_convexity


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class Convexity:
    """Wrapper for a convexity value.

    Parameters
    ----------
    value:
        Convexity magnitude in the analytics unit convention.
    """

    value: Decimal

    def as_decimal(self) -> Decimal:
        """Return the convexity value as a Decimal."""

        return self.value


def price_change_with_convexity(
    modified_duration: object,
    convexity: object,
    price: object,
    yield_change: object,
) -> Decimal:
    """Approximate price change from duration and convexity.

    Returns
    -------
    Decimal
        Second-order price change estimate for the supplied yield shock.
    """

    md = _to_decimal(modified_duration)
    cx = _to_decimal(convexity)
    px = _to_decimal(price)
    dy = _to_decimal(yield_change)
    return -md * px * dy + Decimal("0.5") * cx * px * dy * dy


__all__ = [
    "Convexity",
    "analytical_convexity",
    "effective_convexity",
    "price_change_with_convexity",
]
