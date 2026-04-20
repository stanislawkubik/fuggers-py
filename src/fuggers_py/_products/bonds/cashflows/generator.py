"""Cashflow generators (`fuggers_py._products.bonds.cashflows.generator`).

The generator turns a schedule plus yield rules into deterministic bond cash
flows with adjusted payment dates and unadjusted accrual metadata.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py._core.types import Date, Frequency

from ..traits import BondCashFlow, CashFlowType
from fuggers_py._core import YieldCalculationRules
from .schedule import Schedule


class CashFlowGenerator:
    """Generate deterministic bond cashflow schedules from bond metadata."""

    @staticmethod
    def fixed_rate_bond_cashflows(
        *,
        schedule: Schedule,
        coupon_rate: Decimal,
        notional: Decimal,
        rules: YieldCalculationRules,
    ) -> list[BondCashFlow]:
        """Build coupon and principal cashflows for a fixed-rate bond.

        Returns
        -------
        list[BondCashFlow]
            Cash flows ordered by payment date. Coupon-bearing instruments
            return coupon flows plus a final coupon-and-principal redemption
            amount. Zero-coupon schedules return principal repayment only.
        """

        if schedule.config.frequency.is_zero():
            # Zero coupon, repay notional at maturity.
            return [
                BondCashFlow(
                    date=schedule.dates[-1],
                    amount=notional,
                    flow_type=CashFlowType.PRINCIPAL,
                    accrual_start=None,
                    accrual_end=None,
                )
            ]

        day_count = rules.accrual_day_count_obj()
        flows: list[BondCashFlow] = []
        unadj = schedule.unadjusted_dates
        adj = schedule.dates
        freq: Frequency = schedule.config.frequency
        periods_per_year = freq.periods_per_year()
        if periods_per_year <= 0:
            periods_per_year = 1

        for i in range(1, len(unadj)):
            accrual_start = unadj[i - 1]
            accrual_end = unadj[i]
            pay_date = adj[i]

            accrual_factor = day_count.year_fraction(accrual_start, accrual_end)
            coupon_amount = notional * coupon_rate * accrual_factor

            is_last = i == len(unadj) - 1
            if is_last:
                flows.append(
                    BondCashFlow(
                        date=pay_date,
                        amount=coupon_amount + notional,
                        flow_type=CashFlowType.COUPON_AND_PRINCIPAL,
                        accrual_start=accrual_start,
                        accrual_end=accrual_end,
                    )
                )
            else:
                flows.append(
                    BondCashFlow(
                        date=pay_date,
                        amount=coupon_amount,
                        flow_type=CashFlowType.COUPON,
                        accrual_start=accrual_start,
                        accrual_end=accrual_end,
                    )
                )

        flows.sort(key=lambda cf: cf.date)
        return flows

    @staticmethod
    def future_cashflows(cashflows: list[BondCashFlow], from_date: Date | None) -> list[BondCashFlow]:
        """Filter cash flows strictly after ``from_date`` when provided."""

        if from_date is None:
            return list(cashflows)
        return [cf for cf in cashflows if cf.date > from_date]


__all__ = ["CashFlowGenerator"]
