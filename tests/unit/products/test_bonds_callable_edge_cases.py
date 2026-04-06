from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py.reference.bonds.errors import InvalidBondSpec
from fuggers_py.products.bonds.instruments import CallEntry, CallSchedule, CallType, CallableBondBuilder, FixedBond
from fuggers_py.reference.bonds.types import PutType, YieldCalculationRules
from fuggers_py.core import Date, Frequency


def _annual_rules() -> YieldCalculationRules:
    return replace(YieldCalculationRules.us_corporate(), frequency=Frequency.ANNUAL)


def _base_bond(*, years: int = 5) -> FixedBond:
    issue = Date.from_ymd(2024, 1, 1)
    return FixedBond.new(
        issue_date=issue,
        maturity_date=issue.add_years(years),
        coupon_rate=Decimal("0.05"),
        frequency=Frequency.ANNUAL,
        rules=_annual_rules(),
    )


def test_call_entry_american_window_uses_end_date_and_next_call_date() -> None:
    entry = CallEntry(
        call_date=Date.from_ymd(2026, 1, 1),
        call_price=Decimal("101"),
        call_type=CallType.AMERICAN,
        call_end_date=Date.from_ymd(2026, 3, 1),
    )

    assert entry.is_exercisable_on(Date.from_ymd(2025, 12, 31)) is False
    assert entry.is_exercisable_on(Date.from_ymd(2026, 2, 1)) is True
    assert entry.is_exercisable_on(Date.from_ymd(2026, 3, 2)) is False
    assert CallEntry(
        call_date=Date.from_ymd(2026, 1, 1),
        call_price=Decimal("101"),
        call_type=CallType.AMERICAN,
    ).is_exercisable_on(
        Date.from_ymd(2026, 2, 1),
        next_call_date=Date.from_ymd(2026, 3, 1),
    ) is True


def test_cash_flows_to_call_adds_principal_when_call_date_is_not_coupon_date() -> None:
    callable_bond = (
        CallableBondBuilder.new()
        .with_base_bond(_base_bond())
        .add_call(call_date=Date.from_ymd(2026, 6, 1), call_price=Decimal("101"))
        .build()
    )

    flows = callable_bond.cash_flows_to_call(Date.from_ymd(2026, 6, 1))

    assert flows[-1].date == Date.from_ymd(2026, 6, 1)
    assert flows[-1].amount == Decimal("101")


def test_callable_bond_workout_helpers_include_calls_puts_and_maturity_in_order() -> None:
    bond = (
        CallableBondBuilder.new()
        .with_base_bond(_base_bond(years=6))
        .add_call(call_date=Date.from_ymd(2027, 1, 1), call_price=Decimal("101"))
        .add_put(put_date=Date.from_ymd(2026, 1, 1), put_price=Decimal("102"), put_type=PutType.EUROPEAN)
        .build()
    )
    settlement = Date.from_ymd(2024, 6, 1)

    assert bond.workout_dates(settlement) == [
        Date.from_ymd(2026, 1, 1),
        Date.from_ymd(2027, 1, 1),
        Date.from_ymd(2030, 1, 1),
    ]
    assert bond.first_workout_date(settlement) == Date.from_ymd(2026, 1, 1)
    assert bond.yield_to_first_workout(Decimal("100"), settlement) == bond.yield_to_put(
        Decimal("100"),
        settlement,
        Date.from_ymd(2026, 1, 1),
    )


def test_callable_bond_validation_rejects_dates_before_issue_or_at_maturity() -> None:
    base = _base_bond()

    with pytest.raises(InvalidBondSpec, match="after the issue date"):
        CallableBondBuilder.new().with_base_bond(base).add_call(
            call_date=base.issue_date(),
            call_price=Decimal("101"),
        ).build()

    with pytest.raises(InvalidBondSpec, match="before maturity"):
        CallableBondBuilder.new().with_base_bond(base).add_put(
            put_date=base.maturity_date(),
            put_price=Decimal("101"),
        ).build()


def test_call_schedule_returns_none_during_protection_and_uses_next_call_as_american_end() -> None:
    schedule = CallSchedule.new(
        [
            CallEntry(
                call_date=Date.from_ymd(2026, 1, 1),
                call_price=Decimal("101"),
                call_type=CallType.AMERICAN,
            ),
            CallEntry(
                call_date=Date.from_ymd(2027, 1, 1),
                call_price=Decimal("100.5"),
            ),
        ],
        protection_end_date=Date.from_ymd(2025, 12, 31),
    )

    assert schedule.entry_for_date(Date.from_ymd(2025, 6, 1), maturity_date=Date.from_ymd(2029, 1, 1)) is None
    assert schedule.call_price_on(Date.from_ymd(2026, 6, 1), maturity_date=Date.from_ymd(2029, 1, 1)) == Decimal("101")
    assert schedule.call_price_on(Date.from_ymd(2027, 1, 1), maturity_date=Date.from_ymd(2029, 1, 1)) == Decimal("101")
