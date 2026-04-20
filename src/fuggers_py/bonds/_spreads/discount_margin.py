"""Discount-margin helpers.

Discount margins are returned as raw decimal spreads. The sensitivity helpers
express price impact per 1 bp spread bump, with positive DV01 defined as
``(price_down - price_up) / 2``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import exp

from fuggers_py.curves import DiscountingCurve
from ...curves.date_support import discount_factor_at_date
from fuggers_py.bonds.instruments import FloatingRateNote
from fuggers_py._core.types import Date, Price
from fuggers_py._math import SolverConfig, brent, newton_raphson
from fuggers_py._math.errors import ConvergenceFailed, DivisionByZero, InvalidBracket

from ..analytics_errors import AnalyticsError


DEFAULT_SOLVER_CONFIG = SolverConfig(tolerance=1e-10, max_iterations=200)


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, Price):
        return value.as_percentage()
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class DiscountMarginCalculator:
    """Discount-margin solver and spread-sensitivity helper.

    Parameters
    ----------
    forward_curve:
        Curve used for projected floating coupons.
    discount_curve:
        Curve used for discounting future cash flows.
    solver_config:
        Numerical solver configuration.
    """

    forward_curve: object
    discount_curve: DiscountingCurve
    solver_config: SolverConfig = DEFAULT_SOLVER_CONFIG

    def calculate(self, frn: FloatingRateNote, dirty_price: object, settlement_date: Date) -> Decimal:
        """Solve the discount margin as a raw decimal spread."""
        if settlement_date >= frn.maturity_date():
            raise AnalyticsError.invalid_settlement("Settlement date is on or after maturity.")

        target = float(_to_decimal(dirty_price))
        future_flows = frn.projected_cash_flows(self.forward_curve, settlement_date)
        if not future_flows:
            raise AnalyticsError.invalid_settlement("No future cash flows remain after settlement.")

        def objective(dm: float) -> float:
            return float(self.price_with_dm(frn, Decimal(str(dm)), settlement_date)) - target

        def derivative(dm: float) -> float:
            return self._dm_derivative(future_flows, Decimal(str(dm)), settlement_date)

        guess = float(simple_margin(_to_decimal(dirty_price), frn.current_coupon_rate(), Decimal(0), 90))
        try:
            result = newton_raphson(objective, derivative, guess, config=self.solver_config)
            return Decimal(str(result.root))
        except (ConvergenceFailed, DivisionByZero):
            pass

        for lower, upper in [(-0.1, 0.1), (-0.2, 0.2), (-0.5, 0.5)]:
            try:
                result = brent(objective, lower, upper, config=self.solver_config)
                return Decimal(str(result.root))
            except (ConvergenceFailed, InvalidBracket):
                continue

        raise AnalyticsError.spread_failed("Discount margin solver failed to converge.")

    def price_with_dm(self, frn: FloatingRateNote, dm_decimal: object, settlement_date: Date) -> Decimal:
        """Return the dirty price implied by a raw-decimal discount margin."""
        if settlement_date >= frn.maturity_date():
            raise AnalyticsError.invalid_settlement("Settlement date is on or after maturity.")

        dm = _to_decimal(dm_decimal)
        df_settle = discount_factor_at_date(self.discount_curve, settlement_date)
        if df_settle == 0:
            raise AnalyticsError.pricing_failed("Discount factor at settlement is zero.")

        present_value = Decimal(0)
        for cf in frn.projected_cash_flows(self.forward_curve, settlement_date):
            t = float(settlement_date.days_between(cf.date)) / 365.0
            base_df = discount_factor_at_date(self.discount_curve, cf.date) / df_settle
            spread_df = Decimal(str(exp(-float(dm) * t)))
            present_value += cf.factored_amount() * base_df * spread_df
        return present_value

    def spread_dv01(self, frn: FloatingRateNote, dm_decimal: object, settlement_date: Date) -> Decimal:
        """Return price change for a 1 bp discount-margin move."""
        dm = _to_decimal(dm_decimal)
        bump = Decimal("0.0001")
        price_down = self.price_with_dm(frn, dm - bump, settlement_date)
        price_up = self.price_with_dm(frn, dm + bump, settlement_date)
        return (price_down - price_up) / Decimal(2)

    def spread_duration(self, frn: FloatingRateNote, dm_decimal: object, settlement_date: Date) -> Decimal:
        """Return spread duration in spread-basis-point units."""
        price = self.price_with_dm(frn, dm_decimal, settlement_date)
        if price == 0:
            return Decimal(0)
        dv01 = self.spread_dv01(frn, dm_decimal, settlement_date)
        return dv01 / (price * Decimal("0.0001"))

    def _dm_derivative(self, projected_flows, dm_decimal: Decimal, settlement_date: Date) -> float:
        df_settle = discount_factor_at_date(self.discount_curve, settlement_date)
        derivative = 0.0
        for cf in projected_flows:
            years = float(settlement_date.days_between(cf.date)) / 365.0
            base_df = float(discount_factor_at_date(self.discount_curve, cf.date) / df_settle)
            derivative += -years * float(cf.factored_amount()) * base_df * exp(-float(dm_decimal) * years)
        return derivative


def simple_margin(
    dirty_price: object,
    next_coupon: object,
    reference_rate: object,
    days_to_reset: int | object,
) -> Decimal:
    """Approximate the discount margin from dirty price and next reset.

    The approximation is a short-reset, dirty-price formulation using the next
    coupon, reference rate, and days to reset.
    """
    price = _to_decimal(dirty_price)
    coupon = _to_decimal(next_coupon)
    ref_rate = _to_decimal(reference_rate)
    reset_days = Decimal(str(days_to_reset))
    if reset_days <= 0:
        raise AnalyticsError.invalid_input("days_to_reset must be positive.")
    capital_change = (Decimal(100) - price) * Decimal(360) / reset_days
    average_price = (Decimal(100) + price) / Decimal(2)
    simple_yield = (coupon + capital_change) / average_price
    return simple_yield - ref_rate


def z_discount_margin(
    frn: FloatingRateNote,
    dirty_price: object,
    settlement_date: Date,
    *,
    forward_curve: object,
    discount_curve: object,
) -> Decimal:
    """Solve the discount margin using the curve-backed calculator."""
    return DiscountMarginCalculator(forward_curve=forward_curve, discount_curve=discount_curve).calculate(
        frn,
        dirty_price,
        settlement_date,
    )


__all__ = ["DiscountMarginCalculator", "simple_margin", "z_discount_margin"]
