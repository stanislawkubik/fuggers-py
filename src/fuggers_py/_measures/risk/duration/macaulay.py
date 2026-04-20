"""Macaulay duration (`fuggers_py._measures.risk.duration.macaulay`).

The returned value is a positive magnitude in year units.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py._pricers.bonds.risk import RiskMetrics
from fuggers_py._products.bonds.traits import Bond
from fuggers_py._core.types import Date, Yield


def macaulay_duration(bond: Bond, ytm: Yield, settlement_date: Date) -> Decimal:
    """Return Macaulay duration for the supplied bond."""

    metrics = RiskMetrics.from_bond(bond, ytm, settlement_date)
    return metrics.macaulay_duration


__all__ = ["macaulay_duration"]
