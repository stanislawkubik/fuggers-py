from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.measures.errors import AnalyticsError
from fuggers_py.measures.yields import (
    RollForwardMethod,
    ShortDateCalculator,
    bond_equivalent_yield,
    current_yield_from_bond,
    money_market_yield,
    money_market_yield_with_horizon,
    settlement_adjustment,
    simple_yield_f64,
)
from fuggers_py.measures.yields.solver import YieldSolver
from fuggers_py.reference.bonds.types import YieldConvention


class _BondWithMethods:
    def coupon_rate(self) -> Decimal:
        return Decimal("0.05")

    def notional(self) -> Decimal:
        return Decimal("200")


class _BondWithAttributes:
    coupon_rate = Decimal("0.05")


def test_current_yield_from_bond_supports_methods_attributes_and_default_notional() -> None:
    assert current_yield_from_bond(_BondWithMethods(), Decimal("100")) == Decimal("0.05")
    assert current_yield_from_bond(_BondWithAttributes(), Decimal("80")) == Decimal("0.0625")


def test_current_yield_from_bond_requires_coupon_rate() -> None:
    with pytest.raises(AnalyticsError, match="coupon_rate"):
        current_yield_from_bond(object(), Decimal("100"))


def test_money_market_horizon_wrapper_preserves_base_yield() -> None:
    expected = money_market_yield(100, 98, 90)
    assert money_market_yield_with_horizon(100, 98, 90, 30) == expected
    assert bond_equivalent_yield(100, 98, 90) == expected


def test_short_date_calculator_boundaries_and_settlement_adjustment_helpers() -> None:
    calc = ShortDateCalculator.new(money_market_threshold=0.25, short_date_threshold=1.5)

    assert calc.roll_forward_method(0.25) is RollForwardMethod.USE_MONEY_MARKET
    assert calc.roll_forward_method(1.5) is RollForwardMethod.MONOTONE
    assert calc.roll_forward_method(2.0) is RollForwardMethod.NONE
    assert ShortDateCalculator.bloomberg() == ShortDateCalculator.new()
    assert settlement_adjustment() == Decimal(0)
    assert settlement_adjustment("0.0015") == Decimal("0.0015")


def test_simple_yield_f64_rejects_invalid_inputs() -> None:
    with pytest.raises(AnalyticsError, match="Clean price must be positive"):
        simple_yield_f64(5.0, 0.0, 100.0, 2.0)

    with pytest.raises(AnalyticsError, match="Years to maturity must be positive"):
        simple_yield_f64(5.0, 100.0, 100.0, 0.0)


def test_yield_solver_discount_factor_helpers_cover_convention_branches() -> None:
    solver = YieldSolver()

    assert solver._discount_factor(0.04, 0.0, convention=YieldConvention.ANNUAL, frequency=2) == 1.0
    assert solver._discount_factor_derivative(0.04, 0.0, convention=YieldConvention.ANNUAL, frequency=2) == 0.0
    assert solver._discount_factor(0.04, 2.0, convention=YieldConvention.CONTINUOUS, frequency=2) == pytest.approx(
        0.9231163463866358,
        abs=1e-12,
    )
    assert solver._discount_factor(0.04, 2.0, convention=YieldConvention.SIMPLE_YIELD, frequency=2) == pytest.approx(
        1.0 / 1.08,
        abs=1e-12,
    )
    assert solver._discount_factor_derivative(
        0.04,
        2.0,
        convention=YieldConvention.DISCOUNT_YIELD,
        frequency=2,
    ) == pytest.approx(-2.0 / (1.08**2), abs=1e-12)


def test_yield_solver_estimate_initial_yield_clamps_unreasonable_values() -> None:
    assert YieldSolver._estimate_initial_yield([5.0, 105.0], [0.5, 1.0], dirty_price=0.0) == 0.05
    assert YieldSolver._estimate_initial_yield([500.0], [1.0], dirty_price=1.0) == 1.0
    assert YieldSolver._estimate_initial_yield([0.0], [1.0], dirty_price=1000.0) == 0.0
