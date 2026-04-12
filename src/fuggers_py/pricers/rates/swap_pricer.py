"""Swap pricing helpers.

Par rates are raw decimals and PVs are in the swap currency. The floating leg
uses the resolved projection curve for its index and tenor.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.market.curve_support import discount_factor_at_date
from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.products.rates import FixedFloatSwap

from ._curve_resolver import forward_rate_from_curve, resolve_discount_curve, resolve_projection_curve


@dataclass(frozen=True, slots=True)
class SwapPricingResult:
    """Swap pricing output.

    ``par_rate`` is a raw decimal fixed rate that zeros the swap PV. All PV
    values are in the swap currency.
    """

    par_rate: Decimal
    present_value: Decimal
    fixed_leg_pv: Decimal
    floating_leg_pv: Decimal
    annuity: Decimal


@dataclass(frozen=True, slots=True)
class SwapPricer:
    """Price fixed-for-floating interest-rate swaps.

    The pricer discounts fixed and floating cash flows in the swap currency
    using the resolved discount and projection curves.
    """

    def annuity(self, swap: FixedFloatSwap, curves: AnalyticsCurves) -> Decimal:
        """Return the discounted fixed-leg annuity.

        The annuity is the discounted sum of fixed-leg accrual factors times
        notional, in swap-currency units.
        """

        discount_curve = resolve_discount_curve(curves, swap.currency())
        annuity = Decimal(0)
        for period in swap.fixed_periods():
            annuity += swap.fixed_leg.notional * period.year_fraction * discount_factor_at_date(
                discount_curve,
                period.payment_date,
            )
        if annuity == Decimal(0):
            raise ValueError("Swap annuity requires at least one discounted fixed-leg period.")
        return annuity

    def fixed_leg_pv(self, swap: FixedFloatSwap, curves: AnalyticsCurves) -> Decimal:
        """Return the discounted PV of the fixed leg.

        The sign follows the leg's pay/receive direction.
        """

        discount_curve = resolve_discount_curve(curves, swap.currency())
        present_value = Decimal(0)
        sign = swap.fixed_leg.pay_receive.sign()
        for period in swap.fixed_periods():
            coupon = swap.fixed_leg.notional * swap.fixed_leg.fixed_rate * period.year_fraction
            present_value += sign * coupon * discount_factor_at_date(discount_curve, period.payment_date)
        return present_value

    def floating_leg_pv(self, swap: FixedFloatSwap, curves: AnalyticsCurves) -> Decimal:
        """Return the discounted PV of the floating leg.

        The floating coupon uses the resolved projection curve for the leg's
        index and tenor, plus the leg spread if present.
        """

        discount_curve = resolve_discount_curve(curves, swap.currency())
        projection_curve = resolve_projection_curve(
            curves,
            currency=swap.floating_leg.currency,
            index_name=swap.floating_leg.index_name,
            index_tenor=swap.floating_leg.index_tenor,
        )
        present_value = Decimal(0)
        sign = swap.floating_leg.pay_receive.sign()
        for period in swap.floating_periods():
            forward = forward_rate_from_curve(
                projection_curve,
                period.start_date,
                period.end_date,
                day_count_convention=swap.floating_leg.day_count_convention,
            )
            coupon = swap.floating_leg.notional * (forward + swap.floating_leg.spread) * period.year_fraction
            present_value += sign * coupon * discount_factor_at_date(discount_curve, period.payment_date)
        return present_value

    def par_rate(self, swap: FixedFloatSwap, curves: AnalyticsCurves) -> Decimal:
        """Return the par swap rate as a raw decimal.

        The rate is the fixed coupon that sets the swap PV to zero.
        """

        annuity = self.annuity(swap, curves)
        floating_leg_pv = self.floating_leg_pv(swap, curves)
        return -floating_leg_pv / (swap.fixed_leg.pay_receive.sign() * annuity)

    def pv(self, swap: FixedFloatSwap, curves: AnalyticsCurves) -> Decimal:
        """Return the total present value of the swap.

        The result is the sum of the signed fixed and floating leg PVs in swap
        currency.
        """

        return self.fixed_leg_pv(swap, curves) + self.floating_leg_pv(swap, curves)

    def price(self, swap: FixedFloatSwap, curves: AnalyticsCurves) -> SwapPricingResult:
        """Return the full swap pricing result.

        The result includes the par rate, total PV, leg PVs, and the fixed-leg
        annuity used to convert between rate and value.
        """

        annuity = self.annuity(swap, curves)
        fixed_leg_pv = self.fixed_leg_pv(swap, curves)
        floating_leg_pv = self.floating_leg_pv(swap, curves)
        return SwapPricingResult(
            par_rate=-floating_leg_pv / (swap.fixed_leg.pay_receive.sign() * annuity),
            present_value=fixed_leg_pv + floating_leg_pv,
            fixed_leg_pv=fixed_leg_pv,
            floating_leg_pv=floating_leg_pv,
            annuity=annuity,
        )


__all__ = ["SwapPricer", "SwapPricingResult"]
