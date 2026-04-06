from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from fuggers_py.products.bonds.instruments import CallEntry, CallSchedule, CallableBondBuilder, FixedBond
from fuggers_py.reference.bonds.types import BondType, PutType, YieldCalculationRules
from fuggers_py.core import Date, Frequency


def _base_bond() -> FixedBond:
    issue = Date.from_ymd(2024, 2, 20)
    return FixedBond.new(
        issue_date=issue,
        maturity_date=issue.add_years(7),
        coupon_rate=Decimal("0.055"),
        frequency=Frequency.ANNUAL,
        rules=replace(YieldCalculationRules.us_corporate(), frequency=Frequency.ANNUAL),
    )


def _callable_puttable():
    base = _base_bond()
    return (
        CallableBondBuilder.new()
        .with_base_bond(base)
        .add_call(call_date=Date.from_ymd(2027, 2, 20), call_price=Decimal("101.0"))
        .add_put(put_date=Date.from_ymd(2026, 2, 20), put_price=Decimal("102.0"), put_type=PutType.EUROPEAN)
        .build()
    )


def test_callable_bond_creation() -> None:
    bond = _callable_puttable()
    assert bond.call_schedule is not None
    assert bond.put_schedule() is not None
    assert bond.bond_type() is BondType.CALLABLE_AND_PUTTABLE


def test_call_schedule_methods() -> None:
    schedule = CallSchedule.new([CallEntry(call_date=Date.from_ymd(2027, 2, 20), call_price=Decimal("101.0"))])
    entry = schedule.first_call_after(Date.from_ymd(2025, 1, 1))
    assert entry is not None
    assert entry.call_price == Decimal("101.0")


def test_callable_puttable() -> None:
    bond = _callable_puttable()
    assert bond.first_call(Date.from_ymd(2024, 8, 1)) is not None
    assert bond.first_put(Date.from_ymd(2024, 8, 1)) is not None


def test_yield_to_call() -> None:
    bond = _callable_puttable()
    ytc = bond.yield_to_call(Decimal("101.5"), Date.from_ymd(2024, 8, 1), Date.from_ymd(2027, 2, 20))
    assert Decimal("0") < ytc < Decimal("0.10")


def test_yield_to_maturity() -> None:
    bond = _callable_puttable()
    ytm = bond.yield_to_maturity(Decimal("101.5"), Date.from_ymd(2024, 8, 1))
    assert Decimal("0") < ytm < Decimal("0.10")


def test_yield_to_worst() -> None:
    bond = _callable_puttable()
    settlement = Date.from_ymd(2024, 8, 1)
    clean_price = Decimal("101.5")
    assert bond.yield_to_worst(clean_price, settlement) == min(
        bond.yield_to_maturity(clean_price, settlement),
        bond.yield_to_call(clean_price, settlement, Date.from_ymd(2027, 2, 20)),
        bond.yield_to_put(clean_price, settlement, Date.from_ymd(2026, 2, 20)),
    )


def test_workout_dates() -> None:
    bond = _callable_puttable()
    dates = bond.workout_dates(Date.from_ymd(2024, 8, 1))
    assert dates[0] == Date.from_ymd(2026, 2, 20)
    assert dates[-1] == bond.maturity_date()


def test_annual_callable_bond_ytw() -> None:
    bond = _callable_puttable()
    settlement = Date.from_ymd(2024, 8, 1)
    clean_price = Decimal("102.0")
    assert bond.yield_to_worst(clean_price, settlement) <= bond.yield_to_maturity(clean_price, settlement)
