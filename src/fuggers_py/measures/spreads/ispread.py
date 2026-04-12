"""I-spread helpers.

Unsuffixed helpers return raw decimal spreads. Use the explicit ``*_bps``
wrappers for display/reporting values quoted in basis points.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.products.bonds.traits import Bond
from fuggers_py.core.types import Date
from fuggers_py.market.curve_support import zero_rate_at_date
from fuggers_py.market.curves import DiscountingCurve

from .benchmark import _to_decimal
from ..errors import AnalyticsError


def i_spread(bond_yield: object, swap_rate: object) -> Decimal:
    """Return the I-spread as a raw decimal.

    Positive values mean the bond yield is above the swap rate.
    """
    by = _to_decimal(bond_yield)
    sr = _to_decimal(swap_rate)
    return by - sr


def i_spread_bps(bond_yield: object, swap_rate: object) -> Decimal:
    """Return the I-spread in basis points."""

    return i_spread(bond_yield, swap_rate) * Decimal(10_000)


@dataclass(frozen=True, slots=True)
class ISpreadCalculator:
    """Curve-backed I-spread calculator with decimal and bps outputs.

    Parameters
    ----------
    curve:
        Curve used to extract the swap rate at maturity.
    """

    curve: DiscountingCurve

    def spread_decimal(self, bond: Bond, bond_yield: object, settlement_date: Date | None = None) -> Decimal:
        """Return the I-spread as a raw decimal for ``bond``."""
        maturity = bond.maturity_date()
        if settlement_date is not None and settlement_date >= maturity:
            raise AnalyticsError.invalid_settlement("Settlement date must be before maturity for I-spread.")
        swap_rate = zero_rate_at_date(self.curve, maturity)
        return i_spread(bond_yield, swap_rate)

    def spread_bps(self, bond: Bond, bond_yield: object, settlement_date: Date | None = None) -> Decimal:
        """Return the I-spread in basis points for ``bond``."""

        return self.spread_decimal(bond, bond_yield, settlement_date=settlement_date) * Decimal(10_000)

__all__ = ["ISpreadCalculator", "i_spread", "i_spread_bps"]
