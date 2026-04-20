from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from fuggers_py._measures.functions import modified_duration, yield_to_maturity
from fuggers_py._products.bonds.instruments import FixedBond
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core import Currency, Date, Frequency, Price
from fuggers_py.portfolio import PortfolioAnalyzer

from tests.helpers._engine_scenarios import (
    CALLABLE_ID,
    FIXED_ID,
    FRN_ID,
    PORTFOLIO_ID,
    SETTLEMENT,
    fixed_curves,
    frn_curves,
    portfolio_positions,
    pricing_specs,
    router,
    scenario_a_instrument,
    scenario_b_instrument,
    scenario_c_fixing_source,
    scenario_c_instrument,
    scenario_reference_data,
)


def _assert_close(actual: Decimal | None, expected: Decimal, tolerance: Decimal) -> None:
    assert actual is not None
    assert abs(actual - expected) <= tolerance


def test_golden_treasury_price_yield_and_duration_case() -> None:
    settlement = Date.from_ymd(2026, 3, 14)
    treasury = FixedBond.new(
        issue_date=Date.from_ymd(2021, 2, 15),
        maturity_date=Date.from_ymd(2031, 2, 15),
        coupon_rate=Decimal("0.0375"),
        frequency=Frequency.SEMI_ANNUAL,
        currency=Currency.USD,
        notional=Decimal("100"),
        rules=replace(YieldCalculationRules.us_treasury(), frequency=Frequency.SEMI_ANNUAL),
    )
    clean_price = Decimal("99.125")

    ytm = yield_to_maturity(treasury, Price.new(clean_price, Currency.USD), settlement)
    duration = modified_duration(treasury, ytm, settlement)

    assert clean_price == Decimal("99.125")
    _assert_close(ytm.value(), Decimal("0.039466946925887925"), Decimal("1e-15"))
    _assert_close(duration, Decimal("4.441197762001207"), Decimal("1e-12"))


def test_golden_corporate_z_spread_case() -> None:
    fixed_spec, _ = pricing_specs()
    output = router().price(
        scenario_a_instrument(),
        SETTLEMENT,
        instrument_id=FIXED_ID,
        market_price="101.25",
        pricing_spec=fixed_spec,
        curves=fixed_curves(),
    )

    assert output.clean_price == Decimal("101.25")
    _assert_close(output.yield_to_maturity, Decimal("0.042197129698318375"), Decimal("1e-15"))
    _assert_close(output.modified_duration, Decimal("4.4430487343973954"), Decimal("1e-12"))
    _assert_close(output.z_spread, Decimal("0.0021019276358698"), Decimal("1e-15"))


def test_golden_callable_oas_and_effective_duration_case() -> None:
    output = router().price(
        scenario_b_instrument(),
        SETTLEMENT,
        instrument_id=CALLABLE_ID,
        market_price="102.50",
        curves=fixed_curves(),
    )

    assert output.pricing_path == "callable"
    _assert_close(output.oas, Decimal("-0.00911378870537117"), Decimal("1e-14"))
    _assert_close(output.effective_duration, Decimal("1.4237533188225182"), Decimal("1e-12"))


def test_golden_floating_rate_discount_margin_case() -> None:
    _, floating_spec = pricing_specs()
    output = router().price(
        scenario_c_instrument(),
        SETTLEMENT,
        instrument_id=FRN_ID,
        market_price="100.15",
        pricing_spec=floating_spec,
        curves=frn_curves(),
        market_data=scenario_c_fixing_source(),
    )

    assert output.pricing_path == "floating_rate"
    _assert_close(output.discount_margin, Decimal("0.011396719301261201"), Decimal("1e-15"))
    _assert_close(output.spread_duration, Decimal("1.918139362577253696498849673"), Decimal("1e-12"))


def test_golden_portfolio_weighted_duration_and_dv01_case() -> None:
    fixed_spec, floating_spec = pricing_specs()
    pricer = router()
    quotes = {
        FIXED_ID: pricer.price(
            scenario_a_instrument(),
            SETTLEMENT,
            instrument_id=FIXED_ID,
            market_price="101.25",
            pricing_spec=fixed_spec,
            curves=fixed_curves(),
        ),
        CALLABLE_ID: pricer.price(
            scenario_b_instrument(),
            SETTLEMENT,
            instrument_id=CALLABLE_ID,
            market_price="102.50",
            curves=fixed_curves(),
        ),
        FRN_ID: pricer.price(
            scenario_c_instrument(),
            SETTLEMENT,
            instrument_id=FRN_ID,
            market_price="100.15",
            pricing_spec=floating_spec,
            curves=frn_curves(),
            market_data=scenario_c_fixing_source(),
        ),
    }

    portfolio = PortfolioAnalyzer().analyze(
        PORTFOLIO_ID,
        portfolio_positions(),
        quotes,
        reference_data=scenario_reference_data(),
    )

    _assert_close(portfolio.weighted_duration, Decimal("3.831412692405649419879922078"), Decimal("1e-12"))
    _assert_close(portfolio.aggregate_dv01, Decimal("0.1167665229331368496882099596"), Decimal("1e-12"))
