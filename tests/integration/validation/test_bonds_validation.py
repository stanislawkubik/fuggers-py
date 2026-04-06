from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py.measures.functions import convexity, macaulay_duration, modified_duration, yield_to_maturity
from fuggers_py.measures.spreads import DiscountMarginCalculator, OASCalculator, ParParAssetSwap, ProceedsAssetSwap
from fuggers_py.products.bonds.cashflows import AccruedInterestCalculator, AccruedInterestInputs
from fuggers_py.market.indices import BondIndex, IndexConventions, IndexFixingStore, ObservationShiftType, OvernightCompounding
from fuggers_py.products.bonds.instruments import CallableBondBuilder, FixedBond, FixedBondBuilder, FloatingRateNoteBuilder
from fuggers_py.pricers.bonds.options import HullWhiteModel
from fuggers_py.reference.bonds.types import CompoundingMethod, RateIndex, StubPeriodRules, YieldCalculationRules
from fuggers_py.core import Compounding, Currency, Date, Frequency, Price, Yield
from fuggers_py.market.curves import DiscountCurveBuilder

from tests.helpers._engine_scenarios import FIXED_ID, SETTLEMENT, fixed_curves, frn_curves, pricing_specs, router, scenario_a_instrument, scenario_b_instrument, scenario_c_fixing_source, scenario_c_instrument

from ._helpers import (
    D,
    assert_decimal_close,
    load_fixture,
    parse_date,
    periodic_bond_reference,
    periodic_yield_from_price,
)


pytestmark = pytest.mark.validation


def test_fixed_rate_bond_matches_closed_form_and_regression_references() -> None:
    fixture = load_fixture("bonds", "fixed_rate.json")
    exact_case = fixture["closed_form_semianual_bullet"]
    exact_bond = FixedBond.new(
        issue_date=parse_date(exact_case["issue_date"]),
        maturity_date=parse_date(exact_case["maturity_date"]),
        coupon_rate=D(exact_case["coupon_rate"]),
        frequency=Frequency[exact_case["frequency"]],
        currency=Currency.USD,
        notional=D(exact_case["notional"]),
    )
    exact_settlement = parse_date(exact_case["settlement_date"])
    exact_yield = Yield.new(D(exact_case["yield_rate"]), Compounding[exact_case["compounding"]])
    exact_price = exact_bond.price_from_yield(exact_yield, exact_settlement)
    reference = periodic_bond_reference(
        face=D(exact_case["notional"]),
        coupon_rate=D(exact_case["coupon_rate"]),
        yield_rate=D(exact_case["yield_rate"]),
        frequency=int(exact_case["periods_per_year"]),
        periods=int(exact_case["periods"]),
    )
    bumped_up = periodic_bond_reference(
        face=D(exact_case["notional"]),
        coupon_rate=D(exact_case["coupon_rate"]),
        yield_rate=D(exact_case["yield_rate"]) + Decimal("0.0001"),
        frequency=int(exact_case["periods_per_year"]),
        periods=int(exact_case["periods"]),
    )["clean_price"]
    bumped_down = periodic_bond_reference(
        face=D(exact_case["notional"]),
        coupon_rate=D(exact_case["coupon_rate"]),
        yield_rate=D(exact_case["yield_rate"]) - Decimal("0.0001"),
        frequency=int(exact_case["periods_per_year"]),
        periods=int(exact_case["periods"]),
    )["clean_price"]
    finite_difference_modified = -((bumped_up - bumped_down) / Decimal("0.0002")) / reference["clean_price"]
    solved_yield = periodic_yield_from_price(
        face=D(exact_case["notional"]),
        coupon_rate=D(exact_case["coupon_rate"]),
        clean_price=exact_price.clean.as_percentage(),
        frequency=int(exact_case["periods_per_year"]),
        periods=int(exact_case["periods"]),
    )

    assert_decimal_close(exact_price.clean.as_percentage(), D(exact_case["expected_clean_price"]), Decimal("1e-12"))
    assert_decimal_close(modified_duration(exact_bond, exact_yield, exact_settlement), D(exact_case["expected_modified_duration"]), Decimal("1e-12"))
    assert_decimal_close(macaulay_duration(exact_bond, exact_yield, exact_settlement), D(exact_case["expected_macaulay_duration"]), Decimal("1e-12"))
    assert_decimal_close(convexity(exact_bond, exact_yield, exact_settlement), D(exact_case["expected_convexity"]), Decimal("1e-12"))
    assert_decimal_close(exact_price.clean.as_percentage(), reference["clean_price"], Decimal("1e-12"))
    assert_decimal_close(modified_duration(exact_bond, exact_yield, exact_settlement), finite_difference_modified, Decimal("1e-12"))
    assert_decimal_close(macaulay_duration(exact_bond, exact_yield, exact_settlement), reference["macaulay_duration"], Decimal("1e-12"))
    assert_decimal_close(convexity(exact_bond, exact_yield, exact_settlement), reference["convexity"], Decimal("1e-12"))
    assert_decimal_close(yield_to_maturity(exact_bond, exact_price.clean, exact_settlement).value(), solved_yield, Decimal("1e-12"))

    treasury_case = fixture["treasury_regression"]
    treasury = FixedBond.new(
        issue_date=parse_date(treasury_case["issue_date"]),
        maturity_date=parse_date(treasury_case["maturity_date"]),
        coupon_rate=D(treasury_case["coupon_rate"]),
        frequency=Frequency[treasury_case["frequency"]],
        currency=Currency.USD,
        notional=D(treasury_case["notional"]),
        rules=replace(YieldCalculationRules.us_treasury(), frequency=Frequency[treasury_case["frequency"]]),
    )
    treasury_settlement = parse_date(treasury_case["settlement_date"])
    clean_price = Price.new(D(treasury_case["clean_price"]), Currency.USD)
    treasury_ytm = yield_to_maturity(treasury, clean_price, treasury_settlement)

    assert_decimal_close(treasury_ytm.value(), D(treasury_case["expected_ytm"]), Decimal("1e-15"))
    assert_decimal_close(modified_duration(treasury, treasury_ytm, treasury_settlement), D(treasury_case["expected_modified_duration"]), Decimal("1e-12"))
    assert_decimal_close(convexity(treasury, treasury_ytm, treasury_settlement), D(treasury_case["expected_convexity"]), Decimal("1e-12"))
    assert_decimal_close(treasury.accrued_interest(treasury_settlement), D(treasury_case["expected_accrued_interest"]), Decimal("1e-18"))


def test_callable_bond_oas_duration_and_convexity_match_regression_fixture() -> None:
    fixture = load_fixture("bonds", "callable.json")["scenario_b_regression"]
    model = HullWhiteModel(
        mean_reversion=D(fixture["mean_reversion"]),
        volatility=D(fixture["volatility"]),
        term_structure=fixed_curves().discount_curve,
    )
    calculator = OASCalculator(model=model)
    bond = scenario_b_instrument()
    market_price = D(fixture["market_price"])
    oas = calculator.calculate(bond, market_price, SETTLEMENT)
    duration = calculator.effective_duration(bond, oas, SETTLEMENT)
    convexity_value = calculator.effective_convexity(bond, oas, SETTLEMENT)

    assert_decimal_close(oas, D(fixture["expected_oas"]), Decimal("1e-14"))
    assert_decimal_close(duration, D(fixture["expected_effective_duration"]), Decimal("1e-12"))
    assert_decimal_close(convexity_value, D(fixture["expected_effective_convexity"]), Decimal("1e-12"))
    assert_decimal_close(calculator.price_with_oas(bond, oas, SETTLEMENT), market_price, Decimal("5e-11"))


def test_floating_rate_discount_margin_fixture_covers_lookback_and_lockout_behavior() -> None:
    fixture = load_fixture("bonds", "floating_rate.json")["observation_lookback_case"]
    fixings = {date: D(rate) for date, rate in fixture["fixings"].items()}
    store = IndexFixingStore()
    for date, rate in fixings.items():
        store.add_fixing("SOFR", parse_date(date), rate)

    conventions = IndexConventions(
        overnight_compounding=OvernightCompounding.COMPOUNDED,
        lookback_days=int(fixture["conventions"]["lookback_days"]),
        shift_type=ObservationShiftType[fixture["conventions"]["shift_type"]],
        lockout_days=int(fixture["conventions"]["lockout_days"]),
    )
    index = BondIndex(
        name="SOFR",
        rate_index=RateIndex.SOFR,
        currency=Currency.USD,
        fixing_store=store,
        conventions=conventions,
    )
    note = (
        FloatingRateNoteBuilder.new()
        .with_issue_date(parse_date(fixture["issue_date"]))
        .with_maturity_date(parse_date(fixture["maturity_date"]))
        .with_index(RateIndex.SOFR)
        .with_index_definition(index)
        .with_quoted_spread(D(fixture["quoted_spread"]))
        .with_frequency(Frequency[fixture["frequency"]])
        .with_currency(Currency.USD)
        .with_notional(D(fixture["notional"]))
        .with_rules(replace(YieldCalculationRules.us_treasury(), frequency=Frequency[fixture["frequency"]]))
        .with_current_reference_rate(D(fixture["current_reference_rate"]))
        .build()
    )
    projection_curve = (
        DiscountCurveBuilder(reference_date=parse_date(fixture["settlement_date"]))
        .add_zero_rate(0.25, D(fixture["projection_curve"]["0.25"]))
        .add_zero_rate(1.0, D(fixture["projection_curve"]["1.0"]))
        .add_zero_rate(2.0, D(fixture["projection_curve"]["2.0"]))
        .build()
    )
    start_date = parse_date(fixture["expected_first_period_start"])
    end_date = parse_date(fixture["expected_first_period_end"])
    required = note.required_fixing_dates(start_date, end_date, index_conventions=conventions)
    coupon = note.period_coupon(
        start_date,
        end_date,
        fixing_store=store,
        forward_curve=projection_curve,
        index_conventions=conventions,
        as_of=parse_date(fixture["as_of"]),
    )
    calculator = DiscountMarginCalculator(forward_curve=projection_curve, discount_curve=projection_curve)
    settlement = parse_date(fixture["settlement_date"])
    discount_margin = calculator.calculate(note, D(fixture["dirty_price"]), settlement)

    assert len(required) == int(fixture["expected_required_fixings_count"])
    assert [date.as_naive_date().isoformat() for date in required[:5]] == fixture["expected_required_fixings_first"]
    assert [date.as_naive_date().isoformat() for date in required[-5:]] == fixture["expected_required_fixings_last"]
    assert_decimal_close(coupon, D(fixture["expected_period_coupon"]), Decimal("1e-15"))
    assert note.accrued_interest(
        settlement,
        fixing_store=store,
        forward_curve=projection_curve,
        index_conventions=conventions,
    ) == Decimal(0)
    assert_decimal_close(discount_margin, D(fixture["expected_discount_margin"]), Decimal("1e-15"))
    assert_decimal_close(
        calculator.spread_duration(note, discount_margin, settlement),
        D(fixture["expected_spread_duration"]),
        Decimal("1e-12"),
    )


def test_accrued_interest_edge_cases_match_reference_fixtures() -> None:
    fixture = load_fixture("bonds", "accrued_interest.json")
    basic = fixture["basic_half_coupon"]
    basic_bond = (
        FixedBondBuilder.new()
        .with_issue_date(parse_date(basic["issue_date"]))
        .with_maturity_date(parse_date(basic["maturity_date"]))
        .with_coupon_rate(D(basic["coupon_rate"]))
        .with_frequency(Frequency[basic["frequency"]])
        .build()
    )
    assert_decimal_close(basic_bond.accrued_interest(parse_date(basic["settlement_date"])), D(basic["expected_accrued"]), Decimal("1e-12"))
    assert basic_bond.accrued_interest(parse_date(basic["boundary_start"])) == Decimal(0)
    assert basic_bond.accrued_interest(parse_date(basic["boundary_coupon"])) == Decimal(0)

    ex_case = fixture["ex_dividend_gilt"]
    ex_inputs = AccruedInterestInputs(
        settlement_date=parse_date(ex_case["settlement_date"]),
        accrual_start=parse_date(ex_case["accrual_start"]),
        accrual_end=parse_date(ex_case["accrual_end"]),
        coupon_amount=D(ex_case["coupon_amount"]),
        coupon_date=parse_date(ex_case["coupon_date"]),
        full_coupon_amount=D(ex_case["full_coupon_amount"]),
        period_start=parse_date(ex_case["period_start"]),
        period_end=parse_date(ex_case["period_end"]),
    )
    ex_rules = YieldCalculationRules.uk_gilt()
    assert_decimal_close(AccruedInterestCalculator.standard(ex_inputs, rules=ex_rules), D(ex_case["expected_standard"]), Decimal("1e-24"))
    assert_decimal_close(AccruedInterestCalculator.ex_dividend(ex_inputs, rules=ex_rules), D(ex_case["expected_ex_dividend"]), Decimal("1e-24"))

    stub_case = fixture["front_stub_us_treasury"]
    rules = replace(
        YieldCalculationRules.us_treasury(),
        frequency=Frequency[stub_case["frequency"]],
        compounding=CompoundingMethod.periodic(int(stub_case["periods_per_year"])),
    )
    stub_bond = FixedBond.new(
        issue_date=parse_date(stub_case["issue_date"]),
        maturity_date=parse_date(stub_case["maturity_date"]),
        coupon_rate=D(stub_case["coupon_rate"]),
        frequency=Frequency[stub_case["frequency"]],
        rules=rules,
        stub_rules=StubPeriodRules(first_regular_date=parse_date(stub_case["first_regular_date"])),
    )
    assert_decimal_close(
        stub_bond.accrued_interest(parse_date(stub_case["settlement_date"])),
        D(stub_case["expected_accrued"]),
        Decimal("1e-24"),
    )


def test_spread_regression_fixture_covers_z_g_i_and_asset_swap_outputs() -> None:
    fixture = load_fixture("bonds", "spreads.json")["scenario_a_corporate_curve_case"]
    fixed_spec, floating_spec = pricing_specs()
    pricer = router()
    fixed_output = pricer.price(
        scenario_a_instrument(),
        SETTLEMENT,
        instrument_id=FIXED_ID,
        market_price=fixture["market_price"],
        pricing_spec=fixed_spec,
        curves=fixed_curves(),
    )
    floating_output = pricer.price(
        scenario_c_instrument(),
        SETTLEMENT,
        instrument_id=fixture["frn_instrument_id"],
        market_price=fixture["frn_market_price"],
        pricing_spec=floating_spec,
        curves=frn_curves(),
        market_data=scenario_c_fixing_source(),
    )
    par_par = ParParAssetSwap(fixed_curves().benchmark_curve).calculate(
        scenario_a_instrument(),
        fixed_output.dirty_price,
        SETTLEMENT,
    )
    proceeds = ProceedsAssetSwap(fixed_curves().benchmark_curve).calculate(
        scenario_a_instrument(),
        fixed_output.dirty_price,
        SETTLEMENT,
    )

    assert_decimal_close(fixed_output.z_spread, D(fixture["expected_z_spread"]), Decimal("1e-15"))
    assert_decimal_close(fixed_output.g_spread, D(fixture["expected_g_spread"]), Decimal("1e-12"))
    assert_decimal_close(fixed_output.i_spread, D(fixture["expected_i_spread"]), Decimal("1e-12"))
    assert_decimal_close(fixed_output.asset_swap_spread, D(fixture["expected_asset_swap_par_par"]), Decimal("1e-18"))
    assert_decimal_close(par_par, D(fixture["expected_asset_swap_par_par"]), Decimal("1e-18"))
    assert_decimal_close(proceeds, D(fixture["expected_asset_swap_proceeds"]), Decimal("1e-18"))
    assert_decimal_close(floating_output.discount_margin, D(fixture["expected_floating_discount_margin"]), Decimal("1e-15"))
