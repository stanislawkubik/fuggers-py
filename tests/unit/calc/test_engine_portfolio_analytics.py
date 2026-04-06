from __future__ import annotations

from decimal import Decimal

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


def test_engine_portfolio_analytics_aggregates_positions() -> None:
    fixed_spec, floating_spec = pricing_specs()
    pricer = router()
    quotes = {
        FIXED_ID: pricer.price(scenario_a_instrument(), SETTLEMENT, instrument_id=FIXED_ID, market_price="101.25", pricing_spec=fixed_spec, curves=fixed_curves()),
        CALLABLE_ID: pricer.price(scenario_b_instrument(), SETTLEMENT, instrument_id=CALLABLE_ID, market_price="102.50", curves=fixed_curves()),
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
    positions = portfolio_positions()
    output = PortfolioAnalyzer().analyze(PORTFOLIO_ID, positions, quotes, reference_data=scenario_reference_data())

    expected_market_value = sum((quotes[position.instrument_id].clean_price * position.quantity for position in positions), Decimal(0))
    expected_dv01 = sum((quotes[position.instrument_id].dv01 * position.quantity / Decimal(100) for position in positions), Decimal(0))

    assert output.total_market_value == expected_market_value
    assert output.aggregate_dv01 == expected_dv01
    assert output.weighted_duration is not None and output.weighted_duration > 0
    assert output.weighted_convexity is not None
    assert output.sector_breakdown
    assert output.rating_breakdown
