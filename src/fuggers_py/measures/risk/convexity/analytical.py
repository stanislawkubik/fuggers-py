"""Analytical convexity (`fuggers_py.measures.risk.convexity.analytical`)."""

from __future__ import annotations

from decimal import Decimal

from fuggers_py.reference.bonds.errors import InvalidBondSpec
from fuggers_py.pricers.bonds.risk.metrics import _analytical_risk_components
from fuggers_py.products.bonds.traits import Bond
from fuggers_py.core.types import Date, Yield

from .effective import effective_convexity


def analytical_convexity(bond: Bond, ytm: Yield, settlement_date: Date) -> Decimal:
    """Return exact yield convexity for the supported bond compounding rules.

    The primary path differentiates the dirty-price/yield relation analytically
    from the discounted cash flows used by the bond yield engine. The effective
    convexity bump-and-reprice path is retained only as an explicit fallback if
    the analytical domain is not valid for the requested yield convention.
    """

    try:
        return Decimal(str(_analytical_risk_components(bond, ytm, settlement_date).convexity))
    except (InvalidBondSpec, OverflowError, ZeroDivisionError):
        return effective_convexity(bond, ytm, settlement_date)


__all__ = ["analytical_convexity"]
