from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py.calc import BondQuoteOutput, PricingRouter

from tests.helpers._engine_scenarios import FIXED_ID, SETTLEMENT, fixed_curves, pricing_specs, scenario_a_instrument


@pytest.mark.feature_slug("bond-identity-alignment")
@pytest.mark.feature_category("unit")
def test_pricing_router_uses_direct_bond_instrument_identity_when_present() -> None:
    fixed_spec, _ = pricing_specs()
    instrument = replace(scenario_a_instrument(), instrument_id=FIXED_ID)

    output = PricingRouter().price(
        instrument,
        SETTLEMENT,
        market_price=Decimal("101.25"),
        pricing_spec=fixed_spec,
        curves=fixed_curves(),
    )

    assert isinstance(output, BondQuoteOutput)
    assert output.instrument_id == FIXED_ID
