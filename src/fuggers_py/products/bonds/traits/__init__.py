"""Abstract bond interfaces and analytics mixins.

These protocols define the minimum contract shared by the concrete bond
products, while the analytics mixin provides convenience wrappers around the
pricing and risk layers.
"""

from __future__ import annotations

from .analytics import BondAnalytics
from .bond import Bond
from .cashflow import BondCashFlow, CashFlowType
from .instruments import (
    AmortizingBond,
    EmbeddedOptionBond,
    FixedCouponBond,
    FloatingCouponBond,
    InflationLinkedBond,
)

__all__ = [
    "CashFlowType",
    "BondCashFlow",
    "Bond",
    "BondAnalytics",
    "AmortizingBond",
    "EmbeddedOptionBond",
    "FixedCouponBond",
    "FloatingCouponBond",
    "InflationLinkedBond",
]
