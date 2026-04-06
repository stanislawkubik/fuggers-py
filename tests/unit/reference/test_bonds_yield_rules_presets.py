from __future__ import annotations

from fuggers_py.reference.bonds.types import AccruedConvention, CompoundingKind, YieldCalculationRules, YieldConvention
from fuggers_py.core.daycounts import DayCountConvention


def test_yield_rules_us_treasury_matches_rust_preset_shape() -> None:
    rules = YieldCalculationRules.us_treasury()
    assert rules.convention is YieldConvention.STREET_CONVENTION
    assert rules.compounding.kind is CompoundingKind.PERIODIC
    assert rules.compounding.frequency == 2
    assert rules.accrual_day_count is DayCountConvention.ACT_ACT_ICMA
    assert rules.yield_day_count is DayCountConvention.ACT_ACT_ICMA
    assert rules.discount_day_count is DayCountConvention.ACT_ACT_ICMA
    assert rules.ex_dividend_rules is None
    assert rules.accrued_convention is AccruedConvention.STANDARD


def test_yield_rules_us_corporate_matches_rust_preset_shape() -> None:
    rules = YieldCalculationRules.us_corporate()
    assert rules.convention is YieldConvention.STREET_CONVENTION
    assert rules.compounding.kind is CompoundingKind.PERIODIC
    assert rules.compounding.frequency == 2
    assert rules.accrual_day_count is DayCountConvention.THIRTY_360_US
    assert rules.yield_day_count is DayCountConvention.THIRTY_360_US
    assert rules.discount_day_count is DayCountConvention.THIRTY_360_US
    assert rules.ex_dividend_rules is None
    assert rules.accrued_convention is AccruedConvention.STANDARD


def test_yield_rules_uk_gilt_matches_rust_preset_shape() -> None:
    rules = YieldCalculationRules.uk_gilt()
    assert rules.convention is YieldConvention.ISMA
    assert rules.compounding.kind is CompoundingKind.ACTUAL_PERIOD
    assert rules.compounding.frequency == 2
    assert rules.accrual_day_count is DayCountConvention.ACT_ACT_ICMA
    assert rules.yield_day_count is DayCountConvention.ACT_ACT_ICMA
    assert rules.discount_day_count is DayCountConvention.ACT_ACT_ICMA
    assert rules.ex_dividend_rules is not None
    assert rules.ex_dividend_rules.ex_dividend_days == 7
    assert rules.accrued_convention is AccruedConvention.EX_DIVIDEND
