"""Bond cash-flow primitives (`fuggers_py._products.bonds.traits.cashflow`).

The primitives capture the payment date, amount, flow classification, and
optional accrual metadata needed by the bond product layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from fuggers_py._core.types import Date


class CashFlowType(str, Enum):
    """Classification of a bond cash flow."""

    COUPON = "COUPON"
    PRINCIPAL = "PRINCIPAL"
    COUPON_AND_PRINCIPAL = "COUPON_AND_PRINCIPAL"
    INFLATION_COUPON = "INFLATION_COUPON"
    INFLATION_PRINCIPAL = "INFLATION_PRINCIPAL"
    FEE = "FEE"


@dataclass(frozen=True, slots=True)
class BondCashFlow:
    """Single bond cash flow with optional accrual metadata.

    Parameters
    ----------
    date:
        Payment date, usually the adjusted coupon or redemption date.
    amount:
        Cash amount before factoring.
    flow_type:
        Classification of the flow.
    accrual_start, accrual_end:
        Optional unadjusted accrual bounds for coupon flows.
    factor:
        Remaining-principal or adjustment factor applied to ``amount``.
    reference_rate:
        Optional projected index or coupon rate attached to floating flows.

    Notes
    -----
    ``factor`` scales the payment amount, which is used for amortizing bonds
    and for cases where projected cash flows should be adjusted by a remaining
    principal fraction.
    """

    date: Date
    amount: Decimal
    flow_type: CashFlowType
    accrual_start: Date | None = None
    accrual_end: Date | None = None
    factor: Decimal = Decimal(1)
    reference_rate: Decimal | None = None

    def is_coupon(self) -> bool:
        """Return whether the cash flow contains coupon cash."""
        return self.flow_type in {
            CashFlowType.COUPON,
            CashFlowType.COUPON_AND_PRINCIPAL,
            CashFlowType.INFLATION_COUPON,
        }

    def is_principal(self) -> bool:
        """Return whether the cash flow contains principal repayment."""
        return self.flow_type in {
            CashFlowType.PRINCIPAL,
            CashFlowType.COUPON_AND_PRINCIPAL,
            CashFlowType.INFLATION_PRINCIPAL,
        }

    def factored_amount(self) -> Decimal:
        """Return the amount after applying the cash-flow factor."""
        return self.amount * self.factor


__all__ = ["CashFlowType", "BondCashFlow"]
