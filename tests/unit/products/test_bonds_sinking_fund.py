from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py.products.bonds.instruments import SinkingFundBond, SinkingFundEntry, SinkingFundSchedule
from fuggers_py.reference.bonds.types import YieldCalculationRules
from fuggers_py.core import Date, Frequency


def _annual_rules() -> YieldCalculationRules:
    return replace(YieldCalculationRules.us_corporate(), frequency=Frequency.ANNUAL)


def _schedule(issue: Date) -> SinkingFundSchedule:
    return SinkingFundSchedule.new(
        [
            SinkingFundEntry(issue.add_years(1), Decimal("0.75")),
            SinkingFundEntry(issue.add_years(2), Decimal("0.50")),
            SinkingFundEntry(issue.add_years(3), Decimal("0.25")),
            SinkingFundEntry(issue.add_years(4), Decimal("0.00")),
        ]
    )


def _bond() -> SinkingFundBond:
    issue = Date.from_ymd(2024, 1, 1)
    return SinkingFundBond.new(
        issue_date=issue,
        maturity_date=issue.add_years(4),
        coupon_rate=Decimal("0.04"),
        frequency=Frequency.ANNUAL,
        sinking_schedule=_schedule(issue),
        rules=_annual_rules(),
    )


def test_sinking_fund_to_amortization() -> None:
    issue = Date.from_ymd(2024, 1, 1)
    amortization = _schedule(issue).to_amortization(notional=Decimal("100"))
    assert [principal for _, principal in amortization] == [Decimal("25.00")] * 4


def test_sinking_fund_bond_creation() -> None:
    bond = _bond()
    assert bond.notional() == Decimal("100")
    assert len(bond.cash_flows()) == 4


def test_sinking_fund_bond_factor() -> None:
    bond = _bond()
    issue = Date.from_ymd(2024, 1, 1)
    assert bond.factor_on(issue) == Decimal("1")
    assert bond.factor_on(issue.add_years(2)) == Decimal("0.50")


def test_sinking_fund_bond_average_life() -> None:
    bond = _bond()
    assert float(bond.average_life()) == pytest.approx(2.5, abs=0.05)


def test_sinking_fund_accrued_interest() -> None:
    bond = _bond()
    accrued = bond.accrued_interest(Date.from_ymd(2024, 7, 1))
    assert float(accrued) == pytest.approx(2.0, abs=0.05)


def test_sinking_fund_cash_flows() -> None:
    bond = _bond()
    flows = bond.cash_flows()
    assert [cf.amount for cf in flows] == [Decimal("29.00"), Decimal("28.0000"), Decimal("27.0000"), Decimal("26.0000")]
    assert sum((cf.amount for cf in flows), Decimal(0)) == Decimal("110.0000")


def test_sinking_fund_yield_to_average_life() -> None:
    bond = _bond()
    ytal = bond.yield_to_average_life(Decimal("99.5"), Date.from_ymd(2024, 1, 1))
    assert Decimal("0.03") < ytal < Decimal("0.06")


def test_amortizing_bond_trait() -> None:
    bond = _bond()
    amortization = bond.amortization_schedule()
    assert sum((principal for _, principal in amortization), Decimal(0)) == Decimal("100.00")
