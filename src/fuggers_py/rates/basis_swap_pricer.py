"""Basis-swap pricing helpers.

Par spreads are raw decimals, PVs are in currency units, and the quoted leg is
the leg whose spread is solved from the discounted cash flows.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core import PayReceive
from fuggers_py.curves.date_support import discount_factor_at_date

from ._curve_resolver import forward_rate_from_curve, resolve_discount_curve, resolve_projection_curve
from .basis_swap import BasisSwap
from .common import FloatingLegSpec


@dataclass(frozen=True, slots=True)
class BasisSwapPricingResult:
    """Basis-swap pricing output.

    ``par_spread`` is a raw decimal quoted-leg spread and the PV fields are in
    currency units.
    """

    par_spread: Decimal
    present_value: Decimal
    pay_leg_pv: Decimal
    receive_leg_pv: Decimal
    spread_annuity: Decimal


@dataclass(frozen=True, slots=True)
class BasisSwapPricer:
    """Price same-currency basis swaps.

    The pricer discounts both floating legs in the swap currency and solves
    for the quoted-leg spread that zeroes the PV.
    """

    def _leg_pv(
        self,
        swap: BasisSwap,
        leg: FloatingLegSpec,
        periods,
        curves: object,
        *,
        include_spread: bool,
    ) -> Decimal:
        discount_curve = resolve_discount_curve(curves, swap.currency())
        projection_curve = resolve_projection_curve(
            curves,
            currency=leg.currency,
            index_name=leg.index_name,
            index_tenor=leg.index_tenor,
        )
        present_value = Decimal(0)
        sign = leg.pay_receive.sign()
        spread = leg.spread if include_spread else Decimal(0)
        for period in periods:
            forward = forward_rate_from_curve(
                projection_curve,
                period.start_date,
                period.end_date,
                day_count_convention=leg.day_count_convention,
            )
            coupon = leg.notional * (forward + spread) * period.year_fraction
            present_value += sign * coupon * discount_factor_at_date(discount_curve, period.payment_date)
        return present_value

    def _annuity(self, swap: BasisSwap, leg: FloatingLegSpec, periods, curves: object) -> Decimal:
        discount_curve = resolve_discount_curve(curves, swap.currency())
        annuity = Decimal(0)
        for period in periods:
            annuity += leg.notional * period.year_fraction * discount_factor_at_date(discount_curve, period.payment_date)
        if annuity == Decimal(0):
            raise ValueError("BasisSwap par spread requires a non-zero quoted-leg annuity.")
        return annuity

    def pay_leg_pv(self, swap: BasisSwap, curves: object) -> Decimal:
        """Return the discounted PV of the pay leg."""

        return self._leg_pv(swap, swap.pay_leg, swap.pay_periods(), curves, include_spread=True)

    def receive_leg_pv(self, swap: BasisSwap, curves: object) -> Decimal:
        """Return the discounted PV of the receive leg."""

        return self._leg_pv(swap, swap.receive_leg, swap.receive_periods(), curves, include_spread=True)

    def pv(self, swap: BasisSwap, curves: object) -> Decimal:
        """Return the total present value of the swap."""

        return self.pay_leg_pv(swap, curves) + self.receive_leg_pv(swap, curves)

    def par_spread(self, swap: BasisSwap, curves: object) -> Decimal:
        """Return the par spread on the quoted leg as a raw decimal.

        The quoted leg is whichever leg the contract designates as spread-quoted.
        """

        if swap.quoted_leg is PayReceive.RECEIVE:
            quoted_leg = swap.receive_leg
            quoted_periods = swap.receive_periods()
            other_leg_pv = self.pay_leg_pv(swap, curves)
        else:
            quoted_leg = swap.pay_leg
            quoted_periods = swap.pay_periods()
            other_leg_pv = self.receive_leg_pv(swap, curves)
        quoted_leg_pv_without_spread = self._leg_pv(
            swap,
            quoted_leg,
            quoted_periods,
            curves,
            include_spread=False,
        )
        annuity = self._annuity(swap, quoted_leg, quoted_periods, curves)
        return -(other_leg_pv + quoted_leg_pv_without_spread) / (quoted_leg.pay_receive.sign() * annuity)

    def price(self, swap: BasisSwap, curves: object) -> BasisSwapPricingResult:
        """Return the pricing result for the basis swap.

        The result bundles the quoted-leg par spread, total PV, per-leg PVs,
        and the quoted-leg annuity.
        """

        pay_leg_pv = self.pay_leg_pv(swap, curves)
        receive_leg_pv = self.receive_leg_pv(swap, curves)
        if swap.quoted_leg is PayReceive.RECEIVE:
            quoted_leg = swap.receive_leg
            quoted_periods = swap.receive_periods()
            quoted_leg_pv_without_spread = self._leg_pv(
                swap,
                swap.receive_leg,
                quoted_periods,
                curves,
                include_spread=False,
            )
            other_leg_pv = pay_leg_pv
        else:
            quoted_leg = swap.pay_leg
            quoted_periods = swap.pay_periods()
            quoted_leg_pv_without_spread = self._leg_pv(
                swap,
                swap.pay_leg,
                quoted_periods,
                curves,
                include_spread=False,
            )
            other_leg_pv = receive_leg_pv
        spread_annuity = self._annuity(swap, quoted_leg, quoted_periods, curves)
        par_spread = -(other_leg_pv + quoted_leg_pv_without_spread) / (quoted_leg.pay_receive.sign() * spread_annuity)
        return BasisSwapPricingResult(
            par_spread=par_spread,
            present_value=pay_leg_pv + receive_leg_pv,
            pay_leg_pv=pay_leg_pv,
            receive_leg_pv=receive_leg_pv,
            spread_annuity=spread_annuity,
        )


__all__ = ["BasisSwapPricer", "BasisSwapPricingResult"]
