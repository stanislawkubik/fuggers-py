from __future__ import annotations

from tests.helpers._engine_scenarios import FRN_ID, SETTLEMENT, frn_curves, pricing_specs, router, scenario_c_fixing_source, scenario_c_instrument


def test_engine_pricing_router_floating_rate_path() -> None:
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
    assert output.discount_margin is not None
    assert output.notes == ("historical fixings applied",)
    assert output.projected_next_coupon is not None
    assert output.next_reset_date is not None
    if output.spread_duration is not None:
        assert output.spread_duration > 0
