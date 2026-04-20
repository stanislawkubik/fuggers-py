"""Proceeds asset-swap spread helpers.

This variant scales the corrected par-par spread by the dirty-price proceeds
notional. ``dirty_price`` is supplied in percent-of-par. The public output is
still a raw decimal spread.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._products.bonds.instruments import FixedBond
from fuggers_py._core.types import Date
from fuggers_py._market.curve_support import discount_factor_at_date
from fuggers_py.curves import DiscountingCurve

from .par_par import ParParAssetSwap


@dataclass(frozen=True, slots=True)
class ProceedsAssetSwap:
    """Proceeds-style asset-swap spread calculator."""

    curve: DiscountingCurve

    def calculate(self, bond: FixedBond, dirty_price: object, settlement_date: Date) -> Decimal:
        """Return the proceeds-style asset-swap spread as a raw decimal.

        ``dirty_price`` must be supplied in percent-of-par.
        """

        price = Decimal(str(dirty_price))
        if price <= 0:
            raise ValueError("dirty_price must be positive for proceeds asset-swap spread.")
        par_par_spread = ParParAssetSwap(self.curve).calculate(bond, price, settlement_date)
        return par_par_spread * (Decimal(100) / price)

    def _swap_rate(self, bond: FixedBond, settlement_date: Date) -> Decimal:
        start_df = discount_factor_at_date(self.curve, settlement_date)
        end_df = discount_factor_at_date(self.curve, bond.maturity_date())
        annuity = self._annuity(bond, settlement_date)
        if annuity == 0 or start_df <= 0:
            return Decimal(0)
        return (Decimal(1) - end_df / start_df) / annuity

    def _annuity(self, bond: FixedBond, settlement_date: Date) -> Decimal:
        day_count = bond.rules().accrual_day_count_obj()
        start_df = discount_factor_at_date(self.curve, settlement_date)
        if start_df <= 0:
            raise ValueError("Curve discount factor at settlement must be positive.")
        annuity = Decimal(0)
        for cf in bond.cash_flows(settlement_date):
            if not cf.is_coupon():
                continue
            accrual_start = cf.accrual_start or settlement_date
            accrual_end = cf.accrual_end or cf.date
            tau = day_count.year_fraction(accrual_start, accrual_end)
            annuity += tau * discount_factor_at_date(self.curve, cf.date) / start_df
        return annuity


__all__ = ["ProceedsAssetSwap"]
