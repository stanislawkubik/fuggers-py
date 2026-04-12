"""Analytics pricing helpers.

The pricing API mirrors the bond-layer pricer but returns analytics-facing
results. In particular, price outputs are expressed as percentage-of-par
``Price`` objects and the present value field is the settlement-relative dirty
price in percentage-of-par units, not a currency amount.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.types import Date, Price, Yield
from fuggers_py.market.curve_support import discount_factor_at_date
from fuggers_py.market.curves import DiscountingCurve

from fuggers_py.pricers.bonds import BondPricer as _BondPricer
from fuggers_py.pricers.bonds import TipsPricer as _TipsPricer
from fuggers_py.products.bonds.traits import Bond

from ..errors import AnalyticsError


@dataclass(frozen=True, slots=True)
class PriceResult:
    """Pricing result returned by the analytics pricer.

    Attributes
    ----------
    clean:
        Clean price expressed as a percentage-of-par ``Price``.
    dirty:
        Dirty price expressed as a percentage-of-par ``Price``.
    accrued:
        Accrued interest in the bond's currency.
    present_value:
        Settlement-relative present value in percentage-of-par units.
    """

    clean: Price
    dirty: Price
    accrued: Decimal
    present_value: Decimal


@dataclass(frozen=True, slots=True)
class BondPricer:
    """Analytics wrapper around :class:`fuggers_py.pricers.bonds.BondPricer`."""

    _delegate: _BondPricer = _BondPricer()

    def price_from_curve(self, bond: Bond, curve: DiscountingCurve, settlement_date: Date) -> PriceResult:
        """Price a bond off a curve using settlement-relative discounting.

        The resulting dirty price is computed relative to settlement by
        dividing all future cashflows by the settlement-date discount factor.
        """

        if settlement_date > bond.maturity_date():
            raise AnalyticsError.invalid_settlement("Settlement date is after maturity.")

        cashflows = [cf for cf in bond.cash_flows() if cf.date > settlement_date]
        if not cashflows:
            raise AnalyticsError.pricing_failed("No future cashflows found for curve pricing.")

        df_settle = discount_factor_at_date(curve, settlement_date)
        if df_settle == 0:
            raise AnalyticsError.pricing_failed("Discount factor at settlement is zero.")

        pv = Decimal(0)
        for cf in cashflows:
            df = discount_factor_at_date(curve, cf.date)
            pv += cf.factored_amount() * df / df_settle

        accrued = bond.accrued_interest(settlement_date)
        clean = pv - accrued

        ccy = bond.currency()
        return PriceResult(
            clean=Price.new(clean, ccy),
            dirty=Price.new(pv, ccy),
            accrued=accrued,
            present_value=pv,
        )

    def price_from_yield(
        self,
        bond: Bond,
        ytm: Yield,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> PriceResult:
        """Price a bond from yield using the bond-layer pricer.

        The analytics wrapper keeps the bond-layer clean and dirty prices but
        re-expresses ``present_value`` as the dirty price in percentage-of-par
        units.
        """

        res = self._delegate.price_from_yield(
            bond,
            ytm,
            settlement_date,
            fixing_source=fixing_source,
        )
        pv = res.dirty.as_percentage()
        return PriceResult(
            clean=res.clean,
            dirty=res.dirty,
            accrued=res.accrued,
            present_value=pv,
        )

    def yield_to_maturity(
        self,
        bond: Bond,
        clean_price: Price,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> Yield:
        """Return yield to maturity from a clean price.

        This is a convenience wrapper over the bond-layer pricing engine.
        """

        res = self._delegate.yield_from_price(
            bond,
            clean_price,
            settlement_date,
            fixing_source=fixing_source,
        )
        return res.ytm


@dataclass(frozen=True, slots=True)
class TipsPricer:
    """Analytics wrapper around :class:`fuggers_py.pricers.bonds.TipsPricer`."""

    _delegate: _TipsPricer = _TipsPricer()

    def price_from_real_yield(
        self,
        bond,
        real_yield: Yield,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> PriceResult:
        """Return analytics-facing prices from a TIPS real yield."""

        res = self._delegate.price_from_real_yield(
            bond,
            real_yield,
            settlement_date,
            fixing_source=fixing_source,
        )
        pv = res.dirty.as_percentage()
        return PriceResult(
            clean=res.clean,
            dirty=res.dirty,
            accrued=res.accrued,
            present_value=pv,
        )

    def real_yield_from_clean_price(
        self,
        bond,
        clean_price: Price,
        settlement_date: Date,
        *,
        fixing_source: object | None = None,
    ) -> Yield:
        """Return the real yield implied by a clean TIPS price."""

        return self._delegate.real_yield_from_clean_price(
            bond,
            clean_price,
            settlement_date,
            fixing_source=fixing_source,
        ).ytm


__all__ = ["BondPricer", "PriceResult", "TipsPricer"]
