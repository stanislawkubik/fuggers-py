from __future__ import annotations

from fuggers_py.calc import BondQuoteOutput, PricingSpec

from tests.helpers._engine_scenarios import CALLABLE_ID, SETTLEMENT, fixed_curves, router, scenario_b_instrument


def test_engine_pricing_router_callable_path() -> None:
    output = router().price(
        scenario_b_instrument(),
        SETTLEMENT,
        instrument_id=CALLABLE_ID,
        market_price="102.50",
        pricing_spec=PricingSpec(callable_mean_reversion="0.03", callable_volatility="0.01"),
        curves=fixed_curves(),
    )

    assert isinstance(output, BondQuoteOutput)
    assert output.pricing_path == "callable"
    assert output.oas is not None
    assert output.effective_duration is not None and output.effective_duration > 0
    assert output.effective_convexity is not None
    assert output.option_value is not None and output.option_value >= 0
