"""Abstract interfaces ("traits") for `fuggers_py.core`.

These are intentionally lightweight. The core layer defines interfaces that
pricing, curve, and product layers can implement without pulling in heavier
dependencies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from .errors import DayCountError

if TYPE_CHECKING:
    from .types import Date, Price, Spread, Yield


class YieldCurve(ABC):
    """A discount curve interface.

    Implementations should provide discount factors and, where useful, zero
    rates. The interface is expressed in raw decimal units.
    """

    @abstractmethod
    def date(self) -> Date:
        """Return the curve's anchor date."""

    @abstractmethod
    def discount_factor(self, date: Date) -> Decimal:
        """Return the discount factor from `date()` to `date`."""

    @abstractmethod
    def zero_rate(self, date: Date) -> Yield:
        """Return the zero rate from `date()` to `date`."""

    def forward_rate(self, start: Date, end: Date) -> Decimal:
        """Return the annualized simple forward rate implied by discount factors.

        This default implementation uses an ACT/365F year fraction:

            f = (DF(start)/DF(end) - 1) / ((end-start)/365)

        Implementations may override this for a different convention or for
        improved numerical handling.
        """

        day_count = start.days_between(end)
        if day_count == 0:
            raise DayCountError("forward_rate requires distinct start and end dates.")

        df_start = self.discount_factor(start)
        df_end = self.discount_factor(end)
        if df_end == 0:
            raise DayCountError("forward_rate requires a non-zero discount factor at end date.")

        t = Decimal(day_count) / Decimal(365)
        return (df_start / df_end - Decimal(1)) / t


class PricingEngine(ABC):
    """An interface for bond pricing engines."""

    @abstractmethod
    def price(self, bond: Any, curve: YieldCurve, settlement_date: Date) -> Price:
        """Return the bond price at the requested settlement date."""

    @abstractmethod
    def yield_to_maturity(self, bond: Any, price: Price, settlement_date: Date) -> Yield:
        """Return the yield to maturity implied by a price."""


class RiskCalculator(ABC):
    """An interface for standard bond risk measures."""

    @abstractmethod
    def modified_duration(self, bond: Any, curve: YieldCurve, settlement_date: Date) -> Decimal:
        """Return modified duration."""

    @abstractmethod
    def macaulay_duration(self, bond: Any, curve: YieldCurve, settlement_date: Date) -> Decimal:
        """Return Macaulay duration."""

    @abstractmethod
    def convexity(self, bond: Any, curve: YieldCurve, settlement_date: Date) -> Decimal:
        """Return convexity."""

    @abstractmethod
    def dv01(self, bond: Any, curve: YieldCurve, settlement_date: Date) -> Decimal:
        """Return DV01, the dollar value of a basis point."""


class Discountable(ABC):
    """An interface for a dated cash flow that can be discounted."""

    @abstractmethod
    def payment_date(self) -> Date:
        """Return the payment date."""

    @abstractmethod
    def amount(self) -> Decimal:
        """Return the cash-flow amount in currency units."""

    def present_value(self, curve: YieldCurve) -> Decimal:
        """Return present value using the curve's discount factor."""

        return self.amount() * curve.discount_factor(self.payment_date())


class SpreadCalculator(ABC):
    """An interface for spread calculations."""

    @abstractmethod
    def z_spread(self, bond: Any, price: Price, curve: YieldCurve, settlement_date: Date) -> Spread:
        """Return the z-spread implied by a bond price and discount curve."""
