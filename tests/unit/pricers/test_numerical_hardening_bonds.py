from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py.bonds.risk import analytical_convexity
from fuggers_py.bonds.cashflows import AccruedInterestCalculator, AccruedInterestInputs
from fuggers_py.bonds.instruments import FixedBond, FixedBondBuilder
from fuggers_py.bonds import BondPricer
from fuggers_py.bonds._pricing_yield_engine import _prepare_cashflows
from fuggers_py.bonds import RiskMetrics
from fuggers_py.bonds.types import CompoundingMethod, StubPeriodRules
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core import Compounding, Date, Frequency, Yield


def test_analytical_convexity_matches_closed_form_periodic_cashflow_formula() -> None:
    bond = (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2024, 1, 1))
        .with_maturity_date(Date.from_ymd(2027, 1, 1))
        .with_coupon_rate(Decimal("0.045"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_rules(YieldCalculationRules.us_treasury())
        .build()
    )
    settlement = Date.from_ymd(2024, 1, 1)
    ytm = Yield.new(Decimal("0.05"), Compounding.SEMI_ANNUAL)

    pricer = BondPricer()
    rules = bond.rules()
    yield_rate = float(pricer._yield_to_engine_rate(ytm, rules=rules))
    cashflows = _prepare_cashflows(bond.cash_flows(), settlement_date=settlement, rules=rules)
    frequency = float(rules.compounding.frequency or 0)
    base = 1.0 + yield_rate / frequency

    dirty_price = sum(cf.amount * (base ** (-cf.years * frequency)) for cf in cashflows)
    second_derivative = sum(
        cf.amount * cf.years * (cf.years + 1.0 / frequency) * (base ** (-cf.years * frequency - 2.0))
        for cf in cashflows
    )
    expected_convexity = second_derivative / dirty_price

    assert float(analytical_convexity(bond, ytm, settlement)) == pytest.approx(expected_convexity, rel=1e-12)


def test_macaulay_duration_uses_discounted_cashflow_average_under_simple_compounding() -> None:
    rules = replace(YieldCalculationRules.us_treasury(), compounding=CompoundingMethod.simple())
    bond = FixedBond.new(
        issue_date=Date.from_ymd(2024, 1, 1),
        maturity_date=Date.from_ymd(2027, 1, 1),
        coupon_rate=Decimal("0.04"),
        frequency=Frequency.SEMI_ANNUAL,
        rules=rules,
    )
    settlement = Date.from_ymd(2024, 1, 1)
    ytm = Yield.new(Decimal("0.05"), Compounding.SIMPLE)

    pricer = BondPricer()
    yield_rate = float(pricer._yield_to_engine_rate(ytm, rules=rules))
    cashflows = _prepare_cashflows(bond.cash_flows(), settlement_date=settlement, rules=rules)
    dirty_price = sum(cf.amount / (1.0 + yield_rate * cf.years) for cf in cashflows)
    expected_macaulay = sum(
        cf.years * cf.amount / (1.0 + yield_rate * cf.years)
        for cf in cashflows
    ) / dirty_price

    metrics = RiskMetrics.from_bond(bond, ytm, settlement)

    assert float(metrics.macaulay_duration) == pytest.approx(expected_macaulay, rel=1e-12)
    assert metrics.macaulay_duration > metrics.modified_duration


def test_ex_dividend_accrued_interest_subtracts_full_coupon_in_ex_window() -> None:
    rules = YieldCalculationRules.uk_gilt()
    inputs = AccruedInterestInputs(
        settlement_date=Date.from_ymd(2024, 1, 8),
        accrual_start=Date.from_ymd(2023, 7, 15),
        accrual_end=Date.from_ymd(2024, 1, 15),
        coupon_amount=Decimal("2.0"),
        coupon_date=Date.from_ymd(2024, 1, 15),
        full_coupon_amount=Decimal("2.0"),
        period_start=Date.from_ymd(2023, 7, 15),
        period_end=Date.from_ymd(2024, 1, 15),
    )

    standard = AccruedInterestCalculator.standard(inputs, rules=rules)
    ex_dividend = AccruedInterestCalculator.ex_dividend(inputs, rules=rules)

    assert ex_dividend == standard - inputs.full_coupon_amount


def test_fixed_bond_accrued_interest_uses_reference_period_for_front_stub() -> None:
    rules = replace(
        YieldCalculationRules.us_treasury(),
        frequency=Frequency.QUARTERLY,
        compounding=CompoundingMethod.periodic(4),
    )
    stub_rules = StubPeriodRules(first_regular_date=Date.from_ymd(2024, 2, 15))
    bond = FixedBond.new(
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2025, 1, 15),
        coupon_rate=Decimal("0.04"),
        frequency=Frequency.QUARTERLY,
        rules=rules,
        stub_rules=stub_rules,
    )
    settlement = Date.from_ymd(2024, 2, 1)

    day_count = rules.accrual_day_count_obj()
    coupon_amount = Decimal("100") * Decimal("0.04") * day_count.year_fraction(
        Date.from_ymd(2024, 1, 15),
        Date.from_ymd(2024, 2, 15),
    )
    numerator = day_count.year_fraction_with_period(
        Date.from_ymd(2024, 1, 15),
        settlement,
        Date.from_ymd(2023, 11, 15),
        Date.from_ymd(2024, 2, 15),
    )
    denominator = day_count.year_fraction_with_period(
        Date.from_ymd(2024, 1, 15),
        Date.from_ymd(2024, 2, 15),
        Date.from_ymd(2023, 11, 15),
        Date.from_ymd(2024, 2, 15),
    )
    expected = coupon_amount * numerator / denominator

    assert float(bond.accrued_interest(settlement)) == pytest.approx(float(expected), rel=1e-12)
