from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py.bonds.risk import aggregate_portfolio_risk, duration_hedge_ratio, dv01_hedge_ratio
from fuggers_py.bonds.risk import Position as HedgePosition
from fuggers_py.bonds.risk import historical_var, parametric_var
from fuggers_py.bonds.spreads import ParParAssetSwap, ProceedsAssetSwap
from fuggers_py.bonds.cashflows import AccruedInterestCalculator, AccruedInterestInputs
from fuggers_py.bonds.errors import InvalidBondSpec
from fuggers_py.bonds.types import AccruedConvention
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core import Date

from tests.helpers._portfolio_helpers import make_curve, make_fixed_bond


def test_var_helpers_cover_empty_singleton_and_confidence_monotonicity() -> None:
    assert parametric_var([], confidence=0.95).value == Decimal(0)
    assert historical_var([], confidence=0.95).value == Decimal(0)
    assert parametric_var([-0.02], confidence=0.95).value == Decimal("0.02")
    assert historical_var([-0.02], confidence=0.95).value == Decimal("0.02")

    returns = [-0.03, -0.01, 0.0, 0.02, 0.04]

    assert parametric_var(returns, confidence=0.99).value >= parametric_var(returns, confidence=0.90).value
    assert historical_var(returns, confidence=0.99).value >= historical_var(returns, confidence=0.90).value


def test_hedging_helpers_cover_zero_ratios_and_abs_market_value_weighting() -> None:
    assert duration_hedge_ratio(5, 100, 0, 100) == Decimal(0)
    assert dv01_hedge_ratio(Decimal("12.5"), Decimal("0")) == Decimal(0)

    with pytest.raises(ValueError):
        duration_hedge_ratio(5, 100, 5, 100, target_face=0)

    risk = aggregate_portfolio_risk(
        [
            HedgePosition(modified_duration=Decimal("8"), dirty_price=Decimal("-50"), face=Decimal("100")),
            HedgePosition(modified_duration=Decimal("2"), dirty_price=Decimal("150"), face=Decimal("100")),
        ]
    )

    expected_weighted_duration = (Decimal("8") * Decimal("50") + Decimal("2") * Decimal("150")) / Decimal("200")
    assert float(risk.weighted_duration) == pytest.approx(float(expected_weighted_duration), abs=1e-12)


def test_proceeds_asset_swap_matches_scaled_par_par_formula_and_validates_price() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    bond = make_fixed_bond(ref, years=5, coupon="0.05")
    curve = make_curve(ref)
    dirty_price = Decimal("97.25")
    par_par = ParParAssetSwap(curve).calculate(bond, dirty_price, ref)
    proceeds = ProceedsAssetSwap(curve).calculate(bond, dirty_price, ref)

    assert float(proceeds) == pytest.approx(float(par_par * (Decimal(100) / dirty_price)), abs=1e-12)
    assert proceeds > par_par

    with pytest.raises(ValueError):
        ProceedsAssetSwap(curve).calculate(bond, Decimal("0"), ref)


def test_accrued_interest_validates_boundaries_and_none_convention() -> None:
    rules = YieldCalculationRules.us_treasury()
    inputs = AccruedInterestInputs(
        settlement_date=Date.from_ymd(2024, 3, 1),
        accrual_start=Date.from_ymd(2024, 1, 1),
        accrual_end=Date.from_ymd(2024, 7, 1),
        coupon_amount=Decimal("2.0"),
        coupon_date=Date.from_ymd(2024, 7, 1),
        full_coupon_amount=Decimal("2.0"),
        period_start=Date.from_ymd(2024, 1, 1),
        period_end=Date.from_ymd(2024, 7, 1),
    )

    assert AccruedInterestCalculator.standard(replace(inputs, settlement_date=Date.from_ymd(2024, 1, 1)), rules=rules) == Decimal(0)
    assert AccruedInterestCalculator.standard(replace(inputs, settlement_date=Date.from_ymd(2024, 7, 1)), rules=rules) == Decimal(0)
    assert (
        AccruedInterestCalculator.standard(
            inputs,
            rules=replace(rules, accrued_convention=AccruedConvention.NONE),
        )
        == Decimal(0)
    )

    with pytest.raises(InvalidBondSpec):
        AccruedInterestCalculator.standard(
            replace(inputs, accrual_end=Date.from_ymd(2023, 12, 31)),
            rules=rules,
        )


def test_ex_dividend_and_icma_reference_period_edge_cases() -> None:
    rules = YieldCalculationRules.uk_gilt()
    inputs = AccruedInterestInputs(
        settlement_date=Date.from_ymd(2024, 1, 2),
        accrual_start=Date.from_ymd(2023, 7, 15),
        accrual_end=Date.from_ymd(2024, 1, 15),
        coupon_amount=Decimal("2.0"),
        coupon_date=Date.from_ymd(2024, 1, 15),
        full_coupon_amount=Decimal("2.0"),
        period_start=Date.from_ymd(2023, 7, 15),
        period_end=Date.from_ymd(2024, 1, 15),
    )

    assert AccruedInterestCalculator.ex_dividend(inputs, rules=rules) == AccruedInterestCalculator.standard(inputs, rules=rules)
    assert (
        AccruedInterestCalculator.irregular_period(
            replace(inputs, settlement_date=Date.from_ymd(2023, 7, 15)),
            rules=rules,
        )
        == Decimal(0)
    )

    with pytest.raises(InvalidBondSpec):
        AccruedInterestCalculator.standard(
            replace(
                inputs,
                period_start=Date.from_ymd(2024, 1, 15),
                period_end=Date.from_ymd(2024, 1, 15),
            ),
            rules=rules,
        )
