"""Modified duration (`fuggers_py._measures.risk.duration.modified`).

The returned value is a positive magnitude in year units.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py._pricers.bonds.risk import RiskMetrics
from fuggers_py._products.bonds.traits import Bond
from fuggers_py._core.types import Date, Yield


def modified_duration(bond: Bond, ytm: Yield, settlement_date: Date) -> Decimal:
    """Return modified duration for the supplied bond."""

    metrics = RiskMetrics.from_bond(bond, ytm, settlement_date)
    return metrics.modified_duration


def modified_from_macaulay(macaulay: Decimal, ytm: Yield, *, frequency: int | None = None) -> Decimal:
    """Convert Macaulay duration into modified duration.

    Parameters
    ----------
    macaulay : Decimal
        Macaulay duration as a positive magnitude.
    ytm : Yield
        Yield used to infer the compounding frequency when one is not supplied.
    frequency : int, optional
        Coupon frequency used for the conversion.
    """

    if frequency is None:
        frequency = ytm.compounding().periods_per_year() if hasattr(ytm, "compounding") else 2
    freq = int(frequency) if frequency else 1
    return macaulay / (Decimal(1) + (ytm.value() / Decimal(freq)))


__all__ = ["modified_duration", "modified_from_macaulay"]
