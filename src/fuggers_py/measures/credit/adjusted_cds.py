"""Adjusted CDS spread helpers.

These helpers separate quoted CDS spreads from delivery-option, FX, and other
non-default adjustments, all expressed as raw decimals.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class AdjustedCdsBreakdown:
    """Break down a quoted CDS spread into adjustment components.

    Attributes
    ----------
    quoted_spread
        Quoted CDS spread, as a raw decimal.
    delivery_option_adjustment
        Delivery-option adjustment removed from the quote.
    fx_adjustment
        FX-related adjustment removed from the quote.
    other_adjustment
        Any other non-default-risk adjustment removed from the quote.
    adjusted_spread
        Pure default-risk CDS spread after subtracting the adjustments.
    """

    quoted_spread: Decimal
    delivery_option_adjustment: Decimal
    fx_adjustment: Decimal
    other_adjustment: Decimal
    adjusted_spread: Decimal


def adjusted_cds_breakdown(
    *,
    quoted_spread: object,
    delivery_option_adjustment: object = Decimal(0),
    fx_adjustment: object = Decimal(0),
    other_adjustment: object = Decimal(0),
) -> AdjustedCdsBreakdown:
    """Strip non-default-risk components out of a quoted CDS spread.

    Parameters
    ----------
    quoted_spread
        Quoted CDS spread in raw decimal form.
    delivery_option_adjustment
        Delivery-option premium to remove from the quote.
    fx_adjustment
        FX-related adjustment to remove from the quote.
    other_adjustment
        Any other spread adjustment to remove from the quote.

    Returns
    -------
    AdjustedCdsBreakdown
        Breakdown whose ``adjusted_spread`` is
        ``quoted - delivery_option - fx - other``.
    """

    quoted = _to_decimal(quoted_spread)
    delivery = _to_decimal(delivery_option_adjustment)
    fx = _to_decimal(fx_adjustment)
    other = _to_decimal(other_adjustment)
    return AdjustedCdsBreakdown(
        quoted_spread=quoted,
        delivery_option_adjustment=delivery,
        fx_adjustment=fx,
        other_adjustment=other,
        adjusted_spread=quoted - delivery - fx - other,
    )


def adjusted_cds_spread(
    *,
    quoted_spread: object,
    delivery_option_adjustment: object = Decimal(0),
    fx_adjustment: object = Decimal(0),
    other_adjustment: object = Decimal(0),
) -> Decimal:
    """Return the CDS spread adjusted for delivery-option and FX effects."""

    return adjusted_cds_breakdown(
        quoted_spread=quoted_spread,
        delivery_option_adjustment=delivery_option_adjustment,
        fx_adjustment=fx_adjustment,
        other_adjustment=other_adjustment,
    ).adjusted_spread


__all__ = [
    "AdjustedCdsBreakdown",
    "adjusted_cds_breakdown",
    "adjusted_cds_spread",
]
