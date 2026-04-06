"""Settlement invoice (`fuggers_py.measures.yas.invoice`).

Clean price and accrued interest are expressed in percent-of-par terms.
Principal, accrued amount, and settlement amount are currency cash amounts.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.types import Date

from ..cashflows import SettlementCalculator, SettlementRules


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def calculate_accrued_amount(face_value: object, accrued_interest: object) -> Decimal:
    """Convert accrued interest from percent-of-par into currency units."""

    return _to_decimal(face_value) * _to_decimal(accrued_interest) / Decimal(100)


def calculate_proceeds(principal_amount: object, accrued_amount: object) -> Decimal:
    """Return the settlement cash amount from principal and accrued cash."""

    return _to_decimal(principal_amount) + _to_decimal(accrued_amount)


def calculate_settlement_date(trade_date: Date, rules: SettlementRules) -> Date:
    """Return the settlement date using the supplied settlement rules."""

    return SettlementCalculator(rules).settlement_date(trade_date)


@dataclass(frozen=True, slots=True)
class SettlementInvoice:
    """Settlement invoice values for a bond trade.

    Attributes
    ----------
    settlement_date:
        Calculated settlement date.
    clean_price:
        Clean price in percent of par.
    accrued_interest:
        Accrued interest in percent of par.
    dirty_price:
        Clean price plus accrued interest in percent of par.
    accrued_days:
        Number of accrued days.
    principal_amount:
        Principal cash amount.
    accrued_amount:
        Accrued cash amount.
    settlement_amount:
        Total settlement cash amount.
    face_value:
        Face amount used for the calculation.
    """

    settlement_date: Date
    clean_price: Decimal
    accrued_interest: Decimal
    dirty_price: Decimal
    accrued_days: int
    principal_amount: Decimal
    accrued_amount: Decimal
    settlement_amount: Decimal
    face_value: Decimal


@dataclass(frozen=True, slots=True)
class SettlementInvoiceBuilder:
    """Build a settlement invoice from clean price and accrued interest.

    Parameters
    ----------
    settlement_date:
        Settlement date to record on the invoice.
    clean_price:
        Clean price in percent of par.
    accrued_interest:
        Accrued interest in percent of par.
    face_value:
        Face amount used to compute cash values.
    accrued_days:
        Number of accrued days to store on the invoice.
    principal_amount:
        Optional explicit principal cash amount.
    """

    settlement_date: Date
    clean_price: Decimal
    accrued_interest: Decimal
    face_value: Decimal = Decimal(100)
    accrued_days: int = 0
    principal_amount: Decimal | None = None

    def build(self) -> SettlementInvoice:
        """Construct the invoice with percent-of-par and cash fields."""

        dirty = _to_decimal(self.clean_price) + _to_decimal(self.accrued_interest)
        principal = (
            _to_decimal(self.principal_amount)
            if self.principal_amount is not None
            else _to_decimal(self.face_value) * _to_decimal(self.clean_price) / Decimal(100)
        )
        accrued_amount = calculate_accrued_amount(self.face_value, self.accrued_interest)
        settlement_amount = calculate_proceeds(principal, accrued_amount)
        return SettlementInvoice(
            settlement_date=self.settlement_date,
            clean_price=_to_decimal(self.clean_price),
            accrued_interest=_to_decimal(self.accrued_interest),
            dirty_price=dirty,
            accrued_days=int(self.accrued_days),
            principal_amount=principal,
            accrued_amount=accrued_amount,
            settlement_amount=settlement_amount,
            face_value=_to_decimal(self.face_value),
        )


__all__ = [
    "SettlementInvoice",
    "SettlementInvoiceBuilder",
    "calculate_accrued_amount",
    "calculate_proceeds",
    "calculate_settlement_date",
]
