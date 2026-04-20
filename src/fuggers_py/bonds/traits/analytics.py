"""Analytics mixins (`fuggers_py.bonds.traits.analytics`).

These wrappers bridge the bond contracts to the pricer layer without adding
new economic assumptions.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from fuggers_py._core.types import Date, Price, Yield

from .bond import Bond

if TYPE_CHECKING:  # pragma: no cover
    from fuggers_py.bonds.pricing import BondPricer, PriceResult, YieldResult
    from fuggers_py.bonds.pricing import RiskMetrics


class BondAnalytics:
    """Convenience mixin providing common bond analytics wrappers.

    The mixin keeps pricing, yield, and risk calls close to the bond object
    while delegating the actual calculations to the pricing engine.
    """

    def price_from_yield(self: Bond, ytm: Yield, settlement_date: Date) -> "PriceResult":
        """Return the settlement-date price implied by ``ytm``."""
        from fuggers_py.bonds.pricing import BondPricer

        return BondPricer().price_from_yield(self, ytm, settlement_date)

    def yield_from_price(self: Bond, clean_price: Price, settlement_date: Date) -> "YieldResult":
        """Return the yield implied by a clean price."""
        from fuggers_py.bonds.pricing import BondPricer

        return BondPricer().yield_from_price(self, clean_price, settlement_date)

    def risk_metrics(self: Bond, ytm: Yield, settlement_date: Date) -> "RiskMetrics":
        """Return duration, convexity, and DV01 for the bond."""
        from fuggers_py.bonds.pricing import RiskMetrics

        return RiskMetrics.from_bond(self, ytm, settlement_date)

    def modified_duration(self: Bond, ytm: Yield, settlement_date: Date) -> Decimal:
        """Return modified duration as a positive sensitivity magnitude."""
        return self.risk_metrics(ytm, settlement_date).modified_duration


__all__ = ["BondAnalytics"]
