"""Par-par asset-swap spread helpers.

The returned spread is a raw decimal par-par ASW spread derived from a
``dirty_price`` quoted in percent-of-par and a curve annuity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._products.bonds.instruments import FixedBond
from fuggers_py._core.types import Date
from fuggers_py._market.curve_support import discount_factor_at_date
from fuggers_py.curves import DiscountingCurve


@dataclass(frozen=True, slots=True)
class ParParAssetSwap:
    """Par-par asset-swap spread calculator."""

    curve: DiscountingCurve

    def calculate(self, bond: FixedBond, dirty_price: object, settlement_date: Date) -> Decimal:
        """Return the par-par asset-swap spread as a raw decimal.

        ``dirty_price`` must be supplied in percent-of-par.
        """
        annuity = self._annuity(bond, settlement_date)
        if annuity == 0:
            return Decimal(0)
        swap_rate = self._swap_rate(bond, settlement_date)
        price = Decimal(str(dirty_price))
        return ((Decimal(100) - price) / (annuity * Decimal(100))) + bond.coupon_rate() - swap_rate

    def _swap_rate(self, bond: FixedBond, settlement_date: Date) -> Decimal:
        start_df = discount_factor_at_date(self.curve, settlement_date)
        end_df = discount_factor_at_date(self.curve, bond.maturity_date())
        annuity = self._annuity(bond, settlement_date)
        if annuity == 0 or start_df <= 0:
            return Decimal(0)
        return (Decimal(1) - end_df / start_df) / annuity

    def _annuity(self, bond: FixedBond, settlement_date: Date) -> Decimal:
        day_count = bond.rules().accrual_day_count_obj()
        annuity = Decimal(0)
        for cf in bond.cash_flows(settlement_date):
            if not cf.is_coupon():
                continue
            accrual_start = cf.accrual_start or settlement_date
            accrual_end = cf.accrual_end or cf.date
            tau = day_count.year_fraction(accrual_start, accrual_end)
            annuity += tau * discount_factor_at_date(self.curve, cf.date) / discount_factor_at_date(
                self.curve,
                settlement_date,
            )
        return annuity


__all__ = ["ParParAssetSwap"]
