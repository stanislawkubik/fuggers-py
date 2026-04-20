"""Small shared interfaces for `fuggers_py._core`.

The core layer does not define its own curve type. Public curve objects live
in `fuggers_py.curves`. The traits here stay generic and accept caller-supplied
objects where pricing code needs a curve.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .types import Date, Price, Spread, Yield


class PricingEngine(ABC):
    """An interface for bond pricing engines."""

    @abstractmethod
    def price(self, bond: Any, curve: Any, settlement_date: Date) -> Price:
        """Return the bond price at the requested settlement date."""

    @abstractmethod
    def yield_to_maturity(self, bond: Any, price: Price, settlement_date: Date) -> Yield:
        """Return the yield to maturity implied by a price."""


class RiskCalculator(ABC):
    """An interface for standard bond risk measures."""

    @abstractmethod
    def modified_duration(self, bond: Any, curve: Any, settlement_date: Date) -> Decimal:
        """Return modified duration."""

    @abstractmethod
    def macaulay_duration(self, bond: Any, curve: Any, settlement_date: Date) -> Decimal:
        """Return Macaulay duration."""

    @abstractmethod
    def convexity(self, bond: Any, curve: Any, settlement_date: Date) -> Decimal:
        """Return convexity."""

    @abstractmethod
    def dv01(self, bond: Any, curve: Any, settlement_date: Date) -> Decimal:
        """Return DV01, the dollar value of a basis point."""


class Discountable(ABC):
    """An interface for a dated cash flow that can be discounted."""

    @abstractmethod
    def payment_date(self) -> Date:
        """Return the payment date."""

    @abstractmethod
    def amount(self) -> Decimal:
        """Return the cash-flow amount in currency units."""

    def present_value(self, curve: Any) -> Decimal:
        """Return present value using a curve-like object's discount factor."""

        return self.amount() * curve.discount_factor(self.payment_date())


class SpreadCalculator(ABC):
    """An interface for spread calculations."""

    @abstractmethod
    def z_spread(self, bond: Any, price: Price, curve: Any, settlement_date: Date) -> Spread:
        """Return the z-spread implied by a bond price and discount curve."""
