"""Compounding and convexity adjustment helpers for reference-rate ladders.

Rates and adjustments are handled as raw decimals. The helpers convert a simple
rate into its compounded equivalent and then layer any convexity adjustment on
top.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def simple_to_compounded_equivalent_rate(simple_rate: object, year_fraction: object) -> Decimal:
    """Convert a simple rate into its compounded-equivalent raw decimal rate.

    Parameters
    ----------
    simple_rate:
        Simple rate in raw decimal form.
    year_fraction:
        Accrual fraction used for the conversion.
    """
    rate = _to_decimal(simple_rate)
    tau = _to_decimal(year_fraction)
    if tau <= Decimal(0):
        raise ValueError("year_fraction must be positive.")
    base = Decimal(1) + rate * tau
    if base <= Decimal(0):
        raise ValueError("simple_rate is outside the valid compounding domain.")
    return Decimal(str(float(base) ** (1.0 / float(tau)) - 1.0))


@dataclass(frozen=True, slots=True)
class CompoundingConvexityBreakdown:
    """Breakdown of compounding and convexity adjustments in raw decimals.

    Attributes
    ----------
    simple_rate:
        Input simple rate.
    year_fraction:
        Accrual fraction used in the conversion.
    compounded_equivalent_rate:
        Compounded-equivalent rate.
    compounding_adjustment:
        Difference between compounded-equivalent and simple rate.
    convexity_adjustment:
        Additional convexity adjustment.
    adjusted_term_rate:
        Final adjusted term rate.
    """

    simple_rate: Decimal
    year_fraction: Decimal
    compounded_equivalent_rate: Decimal
    compounding_adjustment: Decimal
    convexity_adjustment: Decimal
    adjusted_term_rate: Decimal


def compounding_convexity_breakdown(
    *,
    simple_rate: object,
    year_fraction: object,
    convexity_adjustment: object = Decimal(0),
) -> CompoundingConvexityBreakdown:
    """Return the compounding and convexity adjustment breakdown."""
    resolved_rate = _to_decimal(simple_rate)
    resolved_tau = _to_decimal(year_fraction)
    resolved_convexity = _to_decimal(convexity_adjustment)
    compounded_equivalent = simple_to_compounded_equivalent_rate(resolved_rate, resolved_tau)
    compounding_adjustment = compounded_equivalent - resolved_rate
    return CompoundingConvexityBreakdown(
        simple_rate=resolved_rate,
        year_fraction=resolved_tau,
        compounded_equivalent_rate=compounded_equivalent,
        compounding_adjustment=compounding_adjustment,
        convexity_adjustment=resolved_convexity,
        adjusted_term_rate=resolved_rate + compounding_adjustment + resolved_convexity,
    )


def adjusted_term_rate(
    *,
    simple_rate: object,
    year_fraction: object,
    convexity_adjustment: object = Decimal(0),
) -> Decimal:
    """Return the adjusted term rate as a raw decimal."""
    return compounding_convexity_breakdown(
        simple_rate=simple_rate,
        year_fraction=year_fraction,
        convexity_adjustment=convexity_adjustment,
    ).adjusted_term_rate


__all__ = [
    "CompoundingConvexityBreakdown",
    "adjusted_term_rate",
    "compounding_convexity_breakdown",
    "simple_to_compounded_equivalent_rate",
]
