"""Reference-rate ladder decomposition helpers.

All ladder legs and adjustments are expressed as raw decimal rates. Positive
ladder spreads mean the next funding rung is more expensive than the previous
one.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .compounding_convexity import compounding_convexity_breakdown


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class ReferenceRateBreakdown:
    """Decomposition from repo to term unsecured funding in raw decimals."""

    repo_rate: Decimal
    general_collateral_rate: Decimal
    unsecured_overnight_rate: Decimal
    term_rate: Decimal
    compounding_adjustment: Decimal
    convexity_adjustment: Decimal
    adjusted_term_rate: Decimal
    repo_vs_gc: Decimal
    gc_vs_unsecured_overnight: Decimal
    unsecured_overnight_vs_term: Decimal
    total_funding_basis: Decimal


def reference_rate_decomposition(
    *,
    repo_rate: object,
    general_collateral_rate: object,
    unsecured_overnight_rate: object,
    term_rate: object,
    year_fraction: object | None = None,
    convexity_adjustment: object = Decimal(0),
) -> ReferenceRateBreakdown:
    """Decompose the ladder from repo to term unsecured funding."""

    repo = _to_decimal(repo_rate)
    gc = _to_decimal(general_collateral_rate)
    unsecured_overnight = _to_decimal(unsecured_overnight_rate)
    term = _to_decimal(term_rate)
    resolved_convexity = _to_decimal(convexity_adjustment)
    if year_fraction is None:
        compounding_adjustment = Decimal(0)
        adjusted_term = term + resolved_convexity
    else:
        breakdown = compounding_convexity_breakdown(
            simple_rate=term,
            year_fraction=year_fraction,
            convexity_adjustment=resolved_convexity,
        )
        compounding_adjustment = breakdown.compounding_adjustment
        adjusted_term = breakdown.adjusted_term_rate

    repo_vs_gc = gc - repo
    gc_vs_unsecured_overnight = unsecured_overnight - gc
    unsecured_overnight_vs_term = adjusted_term - unsecured_overnight
    return ReferenceRateBreakdown(
        repo_rate=repo,
        general_collateral_rate=gc,
        unsecured_overnight_rate=unsecured_overnight,
        term_rate=term,
        compounding_adjustment=compounding_adjustment,
        convexity_adjustment=resolved_convexity,
        adjusted_term_rate=adjusted_term,
        repo_vs_gc=repo_vs_gc,
        gc_vs_unsecured_overnight=gc_vs_unsecured_overnight,
        unsecured_overnight_vs_term=unsecured_overnight_vs_term,
        total_funding_basis=adjusted_term - repo,
    )


__all__ = [
    "ReferenceRateBreakdown",
    "reference_rate_decomposition",
]
