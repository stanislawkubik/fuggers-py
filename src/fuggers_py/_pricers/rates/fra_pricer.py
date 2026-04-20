"""FRA pricing helpers.

FRA PVs are discounted to the FRA start date. The forward rate and strike are
raw decimals, and the sign follows the FRA holder's pay/receive direction.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._market.curve_support import discount_factor_at_date
from fuggers_py._market.state import AnalyticsCurves
from fuggers_py._products.rates import Fra

from ._curve_resolver import forward_rate_from_curve, resolve_discount_curve, resolve_projection_curve


@dataclass(frozen=True, slots=True)
class FraPricingResult:
    """FRA pricing output."""

    forward_rate: Decimal
    present_value: Decimal
    year_fraction: Decimal
    discount_factor: Decimal


@dataclass(frozen=True, slots=True)
class FraPricer:
    """Price forward-rate agreements against resolved curves."""

    def forward_rate(self, fra: Fra, curves: AnalyticsCurves) -> Decimal:
        """Return the projected forward rate for the FRA accrual window."""

        projection_curve = resolve_projection_curve(
            curves,
            currency=fra.currency,
            index_name=fra.index_name,
            index_tenor=fra.index_tenor,
        )
        return forward_rate_from_curve(
            projection_curve,
            fra.start_date,
            fra.end_date,
            day_count_convention=fra.day_count_convention,
        )

    def pv(self, fra: Fra, curves: AnalyticsCurves) -> Decimal:
        """Return the FRA present value."""

        forward = self.forward_rate(fra, curves)
        tau = fra.year_fraction()
        if tau == Decimal(0):
            return Decimal(0)
        discount_curve = resolve_discount_curve(curves, fra.currency)
        discount_factor = discount_factor_at_date(discount_curve, fra.start_date)
        denominator = Decimal(1) + forward * tau
        if denominator == Decimal(0):
            raise ValueError("FRA PV requires a non-zero settlement denominator.")
        payoff = fra.notional * (forward - fra.fixed_rate) * tau / denominator
        return fra.pay_receive.sign() * payoff * discount_factor

    def price(self, fra: Fra, curves: AnalyticsCurves) -> FraPricingResult:
        """Return the full FRA pricing result."""

        forward = self.forward_rate(fra, curves)
        tau = fra.year_fraction()
        discount_factor = discount_factor_at_date(resolve_discount_curve(curves, fra.currency), fra.start_date)
        denominator = Decimal(1) + forward * tau
        if denominator == Decimal(0):
            raise ValueError("FRA PV requires a non-zero settlement denominator.")
        present_value = fra.pay_receive.sign() * fra.notional * (forward - fra.fixed_rate) * tau / denominator * discount_factor
        return FraPricingResult(
            forward_rate=forward,
            present_value=present_value,
            year_fraction=tau,
            discount_factor=discount_factor,
        )


__all__ = ["FraPricer", "FraPricingResult"]
