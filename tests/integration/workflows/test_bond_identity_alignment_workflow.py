from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py._calc import PricingInput, PricingRouter

from tests.helpers._engine_scenarios import FIXED_ID, SETTLEMENT, fixed_curves, pricing_specs, scenario_a_instrument


@pytest.mark.feature_slug("bond-identity-alignment")
@pytest.mark.feature_category("workflow")
def test_pricing_input_and_router_preserve_direct_bond_identity_through_pricing_flow() -> None:
    fixed_spec, _ = pricing_specs()
    instrument = replace(scenario_a_instrument(), instrument_id=FIXED_ID)
    pricing_input = PricingInput(
        instrument=instrument,
        settlement_date=SETTLEMENT,
        market_price=Decimal("101.25"),
        pricing_spec=fixed_spec,
        curves=fixed_curves(),
    )

    output = PricingRouter().price(
        pricing_input.instrument,
        pricing_input.settlement_date,
        market_price=pricing_input.market_price,
        pricing_spec=pricing_input.pricing_spec,
        curves=pricing_input.curves,
    )

    assert pricing_input.resolved_instrument_id() == FIXED_ID
    assert output.instrument_id == FIXED_ID
