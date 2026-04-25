from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py.bonds.errors import InvalidBondSpec
from fuggers_py.bonds.instruments import (
    CallEntry,
    CallSchedule,
    CallType,
    CallableBondBuilder,
    FixedBond,
)
from fuggers_py.bonds.types import StubPeriodRules, StubType
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core import Date, Frequency


def _annual_rules() -> YieldCalculationRules:
    return replace(YieldCalculationRules.us_corporate(), frequency=Frequency.ANNUAL)


def _base_bond(*, years: int = 5, coupon: str = "0.05") -> FixedBond:
    issue = Date.from_ymd(2024, 2, 20)
    return FixedBond.new(
        issue_date=issue,
        maturity_date=issue.add_years(years),
        coupon_rate=Decimal(coupon),
        frequency=Frequency.ANNUAL,
        rules=_annual_rules(),
    )


def test_make_whole_bond() -> None:
    base = _base_bond(years=10, coupon="0.06")
    callable_bond = (
        CallableBondBuilder.new()
        .with_base_bond(base)
        .add_call(
            call_date=Date.from_ymd(2029, 2, 20),
            call_price=Decimal("100"),
            call_type=CallType.MAKE_WHOLE,
            make_whole_spread=Decimal("0.0025"),
        )
        .build()
    )

    make_whole_price = callable_bond.call_price_on(Date.from_ymd(2029, 2, 20), benchmark_yield=Decimal("0.03"))
    assert make_whole_price is not None
    assert make_whole_price > Decimal("100")


def test_step_down_schedule() -> None:
    base = _base_bond()
    callable_bond = (
        CallableBondBuilder.new()
        .with_base_bond(base)
        .add_call(call_date=Date.from_ymd(2026, 2, 20), call_price=Decimal("102"))
        .add_call(call_date=Date.from_ymd(2027, 2, 22), call_price=Decimal("101"))
        .add_call(call_date=Date.from_ymd(2028, 2, 21), call_price=Decimal("100"))
        .build()
    )

    assert callable_bond.call_price_on(Date.from_ymd(2026, 2, 20)) == Decimal("102")
    assert callable_bond.call_price_on(Date.from_ymd(2027, 2, 22)) == Decimal("101")
    assert callable_bond.call_price_on(Date.from_ymd(2028, 2, 21)) == Decimal("100")


def test_protection_period() -> None:
    base = _base_bond()
    schedule = CallSchedule.new(
        [
            CallEntry(call_date=Date.from_ymd(2025, 1, 1), call_price=Decimal("101")),
            CallEntry(call_date=Date.from_ymd(2026, 1, 1), call_price=Decimal("100.5")),
        ],
        protection_end_date=Date.from_ymd(2025, 6, 1),
    )
    callable_bond = CallableBondBuilder.new().with_base_bond(base).with_call_schedule(schedule).build()

    assert callable_bond.call_price_on(Date.from_ymd(2025, 1, 1)) is None
    assert callable_bond.call_price_on(Date.from_ymd(2026, 1, 1)) == Decimal("100.5")


def test_callable_cash_flows() -> None:
    base = _base_bond(coupon="0.05")
    callable_bond = (
        CallableBondBuilder.new()
        .with_base_bond(base)
        .add_call(call_date=Date.from_ymd(2026, 2, 20), call_price=Decimal("101"))
        .build()
    )

    flows = callable_bond.cash_flows_to_call(Date.from_ymd(2026, 2, 20))

    assert [cf.date for cf in flows] == [Date.from_ymd(2025, 2, 20), Date.from_ymd(2026, 2, 20)]
    assert flows[-1].amount == Decimal("106")


def test_builder_validation() -> None:
    with pytest.raises(InvalidBondSpec):
        CallableBondBuilder.new().build()

    with pytest.raises(InvalidBondSpec):
        CallableBondBuilder.new().with_base_bond(_base_bond()).build()


def test_yield_calculations_annual_callable_short_first_coupon() -> None:
    issue = Date.from_ymd(2024, 3, 15)
    maturity = Date.from_ymd(2029, 9, 15)
    stub_rules = StubPeriodRules(
        stub_type=StubType.FRONT_SHORT,
        first_regular_date=Date.from_ymd(2025, 3, 15),
    )
    base = FixedBond.new(
        issue_date=issue,
        maturity_date=maturity,
        coupon_rate=Decimal("0.0475"),
        frequency=Frequency.ANNUAL,
        rules=_annual_rules(),
        stub_rules=stub_rules,
    )
    callable_bond = (
        CallableBondBuilder.new()
        .with_base_bond(base)
        .add_call(call_date=Date.from_ymd(2027, 9, 15), call_price=Decimal("100.5"))
        .build()
    )

    settlement = Date.from_ymd(2024, 8, 1)
    clean_price = Decimal("101.25")

    ytm = callable_bond.yield_to_maturity(clean_price, settlement)
    ytfc = callable_bond.yield_to_first_call(clean_price, settlement)
    ytw = callable_bond.yield_to_worst(clean_price, settlement)
    accrued = callable_bond.accrued_interest(settlement)

    assert Decimal("0.00") < ytm < Decimal("0.08")
    assert Decimal("0.00") < ytfc < Decimal("0.10")
    assert ytw <= max(ytm, ytfc)
    assert Decimal("1.00") < accrued < Decimal("3.00")
