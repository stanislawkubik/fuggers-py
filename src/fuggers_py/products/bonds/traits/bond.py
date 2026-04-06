"""Bond trait (`fuggers_py.products.bonds.traits.bond`).

The trait defines the minimum bond contract required by pricing, accrual, and
risk code: identifiers, currency, notional, dates, coupon frequency, yield
rules, cash flows, and accrued interest.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from fuggers_py.core.types import Currency, Date, Frequency

from fuggers_py.reference.bonds.types import BondIdentifiers, YieldCalculationRules
from .cashflow import BondCashFlow


class Bond(ABC):
    """Minimal bond interface used by pricing and cash-flow tooling.

    Parameters
    ----------
    None
        This is an abstract contract, not a concrete data object.

    Notes
    -----
    Implementations are expected to return raw-decimal coupons and accrued
    interest in the bond's quoted price basis. Schedule dates may be adjusted
    for payment, but the underlying accrual logic should remain visible through
    the returned cash-flow objects.
    """

    @abstractmethod
    def identifiers(self) -> BondIdentifiers:
        """Return the bond's identifier set, such as ISIN or CUSIP."""

    @abstractmethod
    def currency(self) -> Currency:
        """Return the bond currency."""

    @abstractmethod
    def notional(self) -> Decimal:
        """Return the bond notional used to scale cash flows."""

    @abstractmethod
    def issue_date(self) -> Date:
        """Return the issue/effective date."""

    @abstractmethod
    def maturity_date(self) -> Date:
        """Return the contractual maturity date."""

    @abstractmethod
    def frequency(self) -> Frequency:
        """Return the coupon frequency used to build the schedule."""

    @abstractmethod
    def rules(self) -> YieldCalculationRules:
        """Return the yield and accrual rules used by the bond."""

    @abstractmethod
    def cash_flows(self, from_date: Date | None = None) -> list[BondCashFlow]:
        """Return future cash flows sorted by date.

        Parameters
        ----------
        from_date:
            Optional cutoff date. When supplied, only flows strictly after this
            date are returned.
        """

    @abstractmethod
    def accrued_interest(self, settlement_date: Date) -> Decimal:
        """Return accrued interest in the bond's quoted price basis."""

    def max_date(self) -> Date:
        """Return the latest contractual date used by analytics."""
        return self.maturity_date()

    def next_coupon_date(self, settlement_date: Date) -> Date | None:
        """Return the next coupon date strictly after settlement."""
        flows = [cf for cf in self.cash_flows() if cf.is_coupon()]
        for cf in flows:
            if cf.date > settlement_date:
                return cf.date
        return None

    def previous_coupon_date(self, settlement_date: Date) -> Date | None:
        """Return the most recent coupon date on or before settlement."""
        flows = [cf for cf in self.cash_flows() if cf.is_coupon()]
        prev: Date | None = None
        for cf in flows:
            if cf.date <= settlement_date:
                prev = cf.date
            else:
                break
        return prev


__all__ = ["Bond"]
