from __future__ import annotations

from decimal import Decimal

from fuggers_py._calc import PricingInput, PricingRouter

from tests.helpers._engine_scenarios import FIXED_ID, SETTLEMENT, fixed_curves, pricing_specs, scenario_a_instrument


def test_batch_pricing_collects_successes_and_failures() -> None:
    fixed_spec, _ = pricing_specs()
    router = PricingRouter()
    result = router.price_batch(
        [
            PricingInput(
                instrument=scenario_a_instrument(),
                settlement_date=SETTLEMENT,
                market_price=Decimal("101.25"),
                pricing_spec=fixed_spec,
                curves=fixed_curves(),
                instrument_id=FIXED_ID,
            ),
            PricingInput(
                instrument="UNKNOWN-ID",
                settlement_date=SETTLEMENT,
                curves=fixed_curves(),
                instrument_id="UNKNOWN-ID",
            ),
        ]
    )

    assert FIXED_ID.as_str() in result.outputs
    assert result.outputs[FIXED_ID.as_str()].instrument_id == FIXED_ID
    assert "UNKNOWN-ID" in result.errors
    assert result.errors["UNKNOWN-ID"].error_type
    assert result.errors["UNKNOWN-ID"].message

