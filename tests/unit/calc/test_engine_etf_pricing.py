from __future__ import annotations

from decimal import Decimal

from fuggers_py.portfolio import EtfPricer

from tests.helpers._engine_scenarios import (
    CALLABLE_ID,
    ETF_ID,
    FIXED_ID,
    FRN_ID,
    SETTLEMENT,
    etf_holdings,
    fixed_curves,
    frn_curves,
    pricing_specs,
    router,
    scenario_a_instrument,
    scenario_b_instrument,
    scenario_c_fixing_source,
    scenario_c_instrument,
)


def test_engine_etf_pricing_aggregates_underlyings() -> None:
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
    output = EtfPricer().price(ETF_ID, etf_holdings(), quotes, shares_outstanding=Decimal("10000"))
    aggregate_value = sum((quotes[item.instrument_id].dirty_price * item.quantity for item in etf_holdings()), Decimal(0))

    assert output.gross_market_value == aggregate_value
    assert output.inav == aggregate_value / Decimal("10000")
    assert output.weighted_duration is not None and output.weighted_duration > 0
    assert output.fully_priced is True
