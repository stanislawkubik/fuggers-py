from __future__ import annotations

from decimal import Decimal

from fuggers_py.portfolio import EtfPricer, PortfolioAnalyzer

from tests.helpers._engine_scenarios import (
    CALLABLE_ID,
    ETF_ID,
    FIXED_ID,
    FRN_ID,
    PORTFOLIO_ID,
    SETTLEMENT,
    etf_holdings,
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


def test_engine_integration_research_workflow() -> None:
    fixed_curve_bundle = fixed_curves()
    floating_curve_bundle = frn_curves()
    fixed_spec, floating_spec = pricing_specs()
    pricer = router()

    assert fixed_curve_bundle.discount_curve is not None

    quotes = {
        FIXED_ID: pricer.price(scenario_a_instrument(), SETTLEMENT, instrument_id=FIXED_ID, market_price="101.25", pricing_spec=fixed_spec, curves=fixed_curve_bundle),
        CALLABLE_ID: pricer.price(scenario_b_instrument(), SETTLEMENT, instrument_id=CALLABLE_ID, market_price="102.50", curves=fixed_curve_bundle),
        FRN_ID: pricer.price(
            scenario_c_instrument(),
            SETTLEMENT,
            instrument_id=FRN_ID,
            market_price="100.15",
            pricing_spec=floating_spec,
            curves=floating_curve_bundle,
            market_data=scenario_c_fixing_source(),
        ),
    }

    etf_output = EtfPricer().price(ETF_ID, etf_holdings(), quotes, shares_outstanding=Decimal("10000"))
    portfolio_output = PortfolioAnalyzer().analyze(PORTFOLIO_ID, portfolio_positions(), quotes, reference_data=scenario_reference_data())

    assert all(quotes[key].dirty_price is not None for key in [FIXED_ID, CALLABLE_ID, FRN_ID])
    assert etf_output.fully_priced is True
    assert portfolio_output.fully_priced is True
    assert portfolio_output.total_market_value > 0
    assert portfolio_output.total_market_value <= etf_output.gross_market_value
