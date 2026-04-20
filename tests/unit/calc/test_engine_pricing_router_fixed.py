from __future__ import annotations

from decimal import Decimal

from fuggers_py._calc import BondQuoteOutput

from tests.helpers._engine_scenarios import FIXED_ID, SETTLEMENT, fixed_curves, pricing_specs, router, scenario_a_instrument


def test_engine_pricing_router_fixed_path() -> None:
    fixed_spec, _ = pricing_specs()
    output = router().price(
        scenario_a_instrument(),
        SETTLEMENT,
        instrument_id=FIXED_ID,
        market_price="101.25",
        pricing_spec=fixed_spec,
        curves=fixed_curves(),
    )

    assert isinstance(output, BondQuoteOutput)
    assert output.clean_price == Decimal("101.25")
    assert output.dirty_price is not None and output.dirty_price >= output.clean_price
    assert output.yield_to_maturity is not None and output.yield_to_maturity > 0
    assert output.modified_duration is not None and output.modified_duration > 0
    assert output.dv01 is not None and output.dv01 > 0
    assert output.convexity is not None and output.convexity > 0
    assert output.z_spread is not None
    assert output.g_spread is not None
    assert output.i_spread is not None
    assert output.oas is None
    assert output.discount_margin is None
