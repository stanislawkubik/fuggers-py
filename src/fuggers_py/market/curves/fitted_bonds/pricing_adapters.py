"""Pricing adapters for fitted bond curves.

The fitted-bond optimizer stays generic and delegates quote normalization,
yield conversion, and curve-space pricing to these adapters. The nominal
government adapter is the preferred default path. The TIPS adapter projects
inflation-linked cash flows from a supplied CPI fixing source and fits the
real discount or zero curve with the same generic engine.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Date, Price
from fuggers_py.market.quotes import BondQuote
from fuggers_py.market.sources import InflationFixingSource
from fuggers_py.pricers.bonds import BondPricer, TipsPricer
from fuggers_py.products.bonds import TipsBond
from fuggers_py.products.bonds.traits import Bond

from .fair_value import dirty_price_from_curve


_PRICE_IDENTITY_TOLERANCE = Decimal("1e-8")


def _require_positive_price(value: Decimal, *, label: str) -> Decimal:
    if value <= Decimal(0):
        raise ValueError(f"{label} must be positive.")
    return value


def _nominal_prices(quote: BondQuote, *, bond: Bond, settlement_date: Date) -> tuple[Decimal, Decimal]:
    clean_price = quote.clean_price
    dirty_price = quote.dirty_price
    if clean_price is None and dirty_price is None:
        raise ValueError("Nominal bond quotes require clean_price or dirty_price.")
    accrued_interest = bond.accrued_interest(settlement_date)
    if clean_price is not None:
        clean_price = _require_positive_price(clean_price, label="BondQuote clean_price")
    if dirty_price is not None:
        dirty_price = _require_positive_price(dirty_price, label="BondQuote dirty_price")
    if clean_price is not None and dirty_price is not None:
        expected_dirty = clean_price + accrued_interest
        if abs(dirty_price - expected_dirty) > _PRICE_IDENTITY_TOLERANCE:
            raise ValueError("Nominal BondQuote clean_price and dirty_price must match accrued interest.")
        return clean_price, dirty_price
    if clean_price is not None:
        return clean_price, clean_price + accrued_interest
    assert dirty_price is not None
    return dirty_price - accrued_interest, dirty_price


def _tips_real_prices(quote: BondQuote, *, accrued_interest: Decimal) -> tuple[Decimal, Decimal]:
    clean_price = quote.clean_price
    dirty_price = quote.dirty_price
    if clean_price is None:
        raise ValueError("TipsRealBondPricingAdapter requires BondQuote.clean_price as the real clean price input.")
    clean_price = _require_positive_price(clean_price, label="BondQuote clean_price")
    if dirty_price is None:
        return clean_price, clean_price + accrued_interest
    dirty_price = _require_positive_price(dirty_price, label="BondQuote dirty_price")
    expected_dirty = clean_price + accrued_interest
    if abs(dirty_price - expected_dirty) > _PRICE_IDENTITY_TOLERANCE:
        raise ValueError("TIPS BondQuote clean_price and dirty_price must match accrued interest.")
    return clean_price, dirty_price


class BondCurvePricingAdapter(Protocol):
    """Protocol that maps bond quotes into the fitter pricing space."""

    def observed_clean_price(self, quote: BondQuote, *, bond: Bond, settlement_date: Date) -> Decimal:
        """Return the observed clean price."""

    def observed_dirty_price(self, quote: BondQuote, *, bond: Bond, settlement_date: Date) -> Decimal:
        """Return the observed dirty price."""

    def observed_yield(self, quote: BondQuote, *, bond: Bond, settlement_date: Date) -> Decimal:
        """Return the observed yield implied by the quote."""

    def curve_dirty_price(self, quote: BondQuote, curve: YieldCurve, *, bond: Bond, settlement_date: Date) -> Decimal:
        """Return the curve-implied dirty price."""

    def fitted_yield(
        self,
        quote: BondQuote,
        fitted_clean_price: Decimal,
        curve: YieldCurve,
        *,
        bond: Bond,
        settlement_date: Date,
    ) -> Decimal:
        """Return the fitted yield implied by the fitted clean price."""


class NominalGovernmentBondPricingAdapter:
    """Pricing adapter for nominal government bond quotes."""

    def __init__(self, pricer: BondPricer | None = None) -> None:
        self._pricer = pricer or BondPricer()

    def _validate_bond(self, bond: Bond) -> Bond:
        if isinstance(bond, TipsBond):
            raise TypeError("NominalGovernmentBondPricingAdapter does not accept TipsBond quotes.")
        return bond

    def observed_clean_price(self, quote: BondQuote, *, bond: Bond, settlement_date: Date) -> Decimal:
        bond = self._validate_bond(bond)
        clean_price, _ = _nominal_prices(quote, bond=bond, settlement_date=settlement_date)
        return clean_price

    def observed_dirty_price(self, quote: BondQuote, *, bond: Bond, settlement_date: Date) -> Decimal:
        bond = self._validate_bond(bond)
        _, dirty_price = _nominal_prices(quote, bond=bond, settlement_date=settlement_date)
        return dirty_price

    def observed_yield(self, quote: BondQuote, *, bond: Bond, settlement_date: Date) -> Decimal:
        bond = self._validate_bond(bond)
        clean_price = self.observed_clean_price(quote, bond=bond, settlement_date=settlement_date)
        return self._pricer.yield_from_price(
            bond,
            Price.new(clean_price, bond.currency()),
            settlement_date,
        ).ytm.value()

    def curve_dirty_price(self, quote: BondQuote, curve: YieldCurve, *, bond: Bond, settlement_date: Date) -> Decimal:
        del quote
        bond = self._validate_bond(bond)
        return dirty_price_from_curve(bond, curve, settlement_date)

    def fitted_yield(
        self,
        quote: BondQuote,
        fitted_clean_price: Decimal,
        curve: YieldCurve,
        *,
        bond: Bond,
        settlement_date: Date,
    ) -> Decimal:
        del quote
        del curve
        bond = self._validate_bond(bond)
        return self._pricer.yield_from_price(
            bond,
            Price.new(fitted_clean_price, bond.currency()),
            settlement_date,
        ).ytm.value()


class TipsRealBondPricingAdapter:
    """Pricing adapter for TIPS quotes fitted in real clean-price space."""

    def __init__(
        self,
        fixing_source: InflationFixingSource,
        *,
        bond_pricer: BondPricer | None = None,
        tips_pricer: TipsPricer | None = None,
    ) -> None:
        self._fixing_source = fixing_source
        self._bond_pricer = bond_pricer or BondPricer()
        self._tips_pricer = tips_pricer or TipsPricer()

    def _tips_bond(self, bond: Bond) -> TipsBond:
        if not isinstance(bond, TipsBond):
            raise TypeError("TipsRealBondPricingAdapter requires a TipsBond input.")
        return bond

    def _accrued_interest(self, bond: Bond, *, settlement_date: Date) -> Decimal:
        tips_bond = self._tips_bond(bond)
        return tips_bond.accrued_interest(
            settlement_date,
            fixing_source=self._fixing_source,
        )

    def observed_clean_price(self, quote: BondQuote, *, bond: Bond, settlement_date: Date) -> Decimal:
        self._tips_bond(bond)
        clean_price, _ = _tips_real_prices(quote, accrued_interest=self._accrued_interest(bond, settlement_date=settlement_date))
        return clean_price

    def observed_dirty_price(self, quote: BondQuote, *, bond: Bond, settlement_date: Date) -> Decimal:
        self._tips_bond(bond)
        _, dirty_price = _tips_real_prices(quote, accrued_interest=self._accrued_interest(bond, settlement_date=settlement_date))
        return dirty_price

    def observed_yield(self, quote: BondQuote, *, bond: Bond, settlement_date: Date) -> Decimal:
        tips_bond = self._tips_bond(bond)
        clean_price = self.observed_clean_price(quote, bond=tips_bond, settlement_date=settlement_date)
        return self._bond_pricer.yield_from_price(
            tips_bond,
            Price.new(clean_price, tips_bond.currency()),
            settlement_date,
            fixing_source=self._fixing_source,
        ).ytm.value()

    def curve_dirty_price(self, quote: BondQuote, curve: YieldCurve, *, bond: Bond, settlement_date: Date) -> Decimal:
        del quote
        tips_bond = self._tips_bond(bond)
        present_value = Decimal(0)
        for cash_flow in tips_bond.projected_cash_flows(
            fixing_source=self._fixing_source,
            settlement_date=settlement_date,
        ):
            present_value += cash_flow.factored_amount() * curve.discount_factor(cash_flow.date)
        return present_value

    def fitted_yield(
        self,
        quote: BondQuote,
        fitted_clean_price: Decimal,
        curve: YieldCurve,
        *,
        bond: Bond,
        settlement_date: Date,
    ) -> Decimal:
        del quote
        del curve
        tips_bond = self._tips_bond(bond)
        return self._tips_pricer.real_yield_from_clean_price(
            tips_bond,
            Price.new(fitted_clean_price, tips_bond.currency()),
            settlement_date,
            fixing_source=self._fixing_source,
        ).ytm.value()
__all__ = [
    "BondCurvePricingAdapter",
    "NominalGovernmentBondPricingAdapter",
    "TipsRealBondPricingAdapter",
]
