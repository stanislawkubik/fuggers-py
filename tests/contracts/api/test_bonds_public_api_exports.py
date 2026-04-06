from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from fuggers_py.market.curves.bond_instruments import (
    GovernmentCouponBond,
    GovernmentZeroCoupon,
    MarketConvention,
    day_count_factor,
)
from fuggers_py.pricers.bonds import BondPricer, BondResult, TipsPricer
from fuggers_py.pricers.bonds.options import BinomialTree, HullWhiteModel
from fuggers_py.pricers.bonds.risk import DurationResult
from fuggers_py.products.bonds import (
    AccelerationOption,
    CallableBondBuilder,
    FixedBond,
    SinkingFundBondBuilder,
    TipsBond,
)
from fuggers_py.products.bonds.instruments import AccelerationOption as InstrumentAccelerationOption
from fuggers_py.products.bonds.instruments import TipsBond as InstrumentTipsBond
from fuggers_py.pricers.bonds.options import BinomialTree as OptionsBinomialTree
from fuggers_py.pricers.bonds import BondResult as PricingBondResult
from fuggers_py.pricers.bonds import TipsPricer as PricingTipsPricer
from fuggers_py.pricers.bonds.risk import DurationResult as RiskDurationResult
from fuggers_py.reference.bonds.types import YieldCalculationRules
from fuggers_py.core import Compounding, Date, DayCountConvention, Frequency, Yield
from fuggers_py.market.curves import DiscountCurveBuilder, ZeroCurveBuilder


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


def _curve(reference_date: Date):
    return (
        DiscountCurveBuilder(reference_date=reference_date)
        .add_zero_rate(1.0, Decimal("0.03"))
        .add_zero_rate(10.0, Decimal("0.04"))
        .build()
    )


def test_bonds_root_imports_expose_public_aliases() -> None:
    assert AccelerationOption is InstrumentAccelerationOption
    assert TipsBond is InstrumentTipsBond
    assert TipsPricer is PricingTipsPricer
    assert BinomialTree is OptionsBinomialTree
    assert BondResult is PricingBondResult
    assert DurationResult is RiskDurationResult


def test_government_instruments_and_day_count_helper_are_available_at_root() -> None:
    reference_date = Date.from_ymd(2024, 1, 1)
    market = MarketConvention(
        name="UST",
        day_count=DayCountConvention.ACT_365_FIXED,
        frequency=Frequency.SEMI_ANNUAL,
        settlement_days=1,
    )
    maturity = reference_date.add_days(365 * 2)

    zero = GovernmentZeroCoupon(maturity=maturity)
    coupon = GovernmentCouponBond(
        maturity=reference_date.add_days(365 * 5),
        coupon_rate=Decimal("0.035"),
        frequency=market.frequency,
        day_count=market.day_count,
    )

    zero_curve = (
        ZeroCurveBuilder(reference_date=reference_date, compounding=Compounding.SEMI_ANNUAL)
        .add_rate(reference_date.add_days(365), Decimal("0.03"))
        .add_rate(reference_date.add_days(365 * 10), Decimal("0.03"))
        .build()
    )

    factor = day_count_factor(reference_date, maturity, market.day_count)

    assert market.name == "UST"
    assert factor == market.day_count.to_day_count().year_fraction(reference_date, maturity)
    assert zero.repriced_quote(zero_curve, settlement_date=reference_date) > 0
    assert coupon.repriced_quote(zero_curve, settlement_date=reference_date) > 0


def test_binomial_tree_supports_basic_callable_bond_usage_from_root_exports() -> None:
    base = _base_bond(years=5)
    callable_bond = (
        CallableBondBuilder.new()
        .with_base_bond(base)
        .add_call(
            call_date=Date.from_ymd(2027, 2, 20),
            call_price=Decimal("101"),
            call_type=AccelerationOption.EUROPEAN,
        )
        .build()
    )
    model = HullWhiteModel(
        mean_reversion=Decimal("0.03"),
        volatility=Decimal("0.01"),
        term_structure=_curve(base.issue_date()),
    )
    tree = BinomialTree.new(model, list(base.schedule().dates))

    def exercise(date: Date, cashflow: float, continuation: float) -> float:
        call_price = callable_bond.call_price_on(date)
        if call_price is None:
            return cashflow + continuation
        return min(cashflow + continuation, float(call_price))

    non_callable_value = tree.price_cashflows(base.cash_flows())
    callable_value = tree.price_cashflows(callable_bond.cash_flows(), exercise=exercise)

    assert callable_bond.call_price_on(Date.from_ymd(2027, 2, 20)) == Decimal("101")
    assert callable_value > Decimal("0")
    assert callable_value <= non_callable_value


def test_sinking_fund_builder_generates_schedule_and_bond() -> None:
    issue = Date.from_ymd(2024, 1, 1)
    builder = (
        SinkingFundBondBuilder.new()
        .with_issue_date(issue)
        .with_maturity_date(issue.add_years(4))
        .with_coupon_rate("0.04")
        .with_frequency(Frequency.ANNUAL)
        .with_rules(_annual_rules())
    )
    builder.add_sinking_entry(issue.add_years(4), "0.00")
    builder.add_sinking_entry(issue.add_years(2), "0.50")
    builder.add_sinking_entry(issue.add_years(1), "0.75")
    builder.add_sinking_entry(issue.add_years(3), "0.25")

    schedule = builder.build_schedule()
    bond = builder.build()

    assert [entry.factor for entry in schedule.entries] == [
        Decimal("0.75"),
        Decimal("0.50"),
        Decimal("0.25"),
        Decimal("0.00"),
    ]
    assert bond.factor_on(issue.add_years(2)) == Decimal("0.50")
    assert len(bond.cash_flows()) == 4


def test_bond_result_and_duration_result_are_typed_root_exports() -> None:
    bond = _base_bond()
    settlement = Date.from_ymd(2024, 8, 20)
    ytm = Yield.new(Decimal("0.04"), compounding=Compounding.ANNUAL)

    price_result = BondPricer().price_from_yield(bond, ytm, settlement)
    duration_result = bond.risk_metrics(ytm, settlement)

    assert isinstance(price_result, BondResult)
    assert price_result.dirty_price == price_result.dirty
    assert price_result.clean_price == price_result.clean
    assert price_result.accrued_interest == price_result.accrued
    assert price_result.present_value == price_result.dirty.as_percentage()

    assert isinstance(duration_result, DurationResult)
    assert duration_result.duration == duration_result.modified_duration
    assert duration_result.pv01 == duration_result.dv01
