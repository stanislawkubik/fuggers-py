from __future__ import annotations

from decimal import Decimal

from fuggers_py.products.bonds.traits import Bond, BondCashFlow, CashFlowType
from fuggers_py.reference.bonds.types import BondIdentifiers, YieldCalculationRules
from fuggers_py.core import Currency, Date, Frequency


class _StubBond(Bond):
    def __init__(self) -> None:
        self._issue = Date.from_ymd(2024, 1, 1)
        self._maturity = Date.from_ymd(2026, 1, 1)
        self._flows = [
            BondCashFlow(date=Date.from_ymd(2024, 6, 1), amount=Decimal("1.0"), flow_type=CashFlowType.FEE),
            BondCashFlow(date=Date.from_ymd(2024, 7, 1), amount=Decimal("2.0"), flow_type=CashFlowType.COUPON),
            BondCashFlow(
                date=Date.from_ymd(2025, 1, 1),
                amount=Decimal("2.0"),
                flow_type=CashFlowType.COUPON_AND_PRINCIPAL,
            ),
            BondCashFlow(date=Date.from_ymd(2026, 1, 1), amount=Decimal("100.0"), flow_type=CashFlowType.PRINCIPAL),
        ]

    def identifiers(self) -> BondIdentifiers:
        return BondIdentifiers()

    def currency(self) -> Currency:
        return Currency.USD

    def notional(self) -> Decimal:
        return Decimal("100")

    def issue_date(self) -> Date:
        return self._issue

    def maturity_date(self) -> Date:
        return self._maturity

    def frequency(self) -> Frequency:
        return Frequency.SEMI_ANNUAL

    def rules(self) -> YieldCalculationRules:
        return YieldCalculationRules.us_treasury()

    def cash_flows(self, from_date: Date | None = None) -> list[BondCashFlow]:
        if from_date is None:
            return list(self._flows)
        return [flow for flow in self._flows if flow.date >= from_date]

    def accrued_interest(self, settlement_date: Date) -> Decimal:
        return Decimal("0")


def test_bond_trait_max_date_defaults_to_maturity() -> None:
    assert _StubBond().max_date() == Date.from_ymd(2026, 1, 1)


def test_bond_trait_coupon_date_helpers_ignore_non_coupon_flows() -> None:
    bond = _StubBond()

    assert bond.next_coupon_date(Date.from_ymd(2024, 6, 15)) == Date.from_ymd(2024, 7, 1)
    assert bond.next_coupon_date(Date.from_ymd(2025, 1, 1)) is None
    assert bond.previous_coupon_date(Date.from_ymd(2024, 6, 15)) is None
    assert bond.previous_coupon_date(Date.from_ymd(2024, 7, 1)) == Date.from_ymd(2024, 7, 1)
    assert bond.previous_coupon_date(Date.from_ymd(2025, 6, 1)) == Date.from_ymd(2025, 1, 1)
