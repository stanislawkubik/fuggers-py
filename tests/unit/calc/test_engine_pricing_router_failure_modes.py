from __future__ import annotations

from decimal import Decimal

import pytest

import fuggers_py._runtime.pricing_router as pricing_router_module
from fuggers_py._runtime import PricingSpec
from fuggers_py.bonds.instruments import CallableBond

from tests.helpers._engine_scenarios import FIXED_ID, SETTLEMENT, fixed_curves, router, scenario_a_instrument, scenario_b_instrument


def test_price_propagates_current_yield_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(instrument: object, clean_price: Decimal) -> Decimal:
        raise RuntimeError("boom")

    monkeypatch.setattr(pricing_router_module, "current_yield_from_bond", explode)

    with pytest.raises(RuntimeError, match="boom"):
        router().price(
            scenario_a_instrument(),
            SETTLEMENT,
            instrument_id=FIXED_ID,
            market_price="101.25",
            pricing_spec=PricingSpec(),
            curves=fixed_curves(),
        )


def test_batch_pricing_keeps_current_yield_failures_in_error_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(instrument: object, clean_price: Decimal) -> Decimal:
        raise RuntimeError("boom")

    monkeypatch.setattr(pricing_router_module, "current_yield_from_bond", explode)

    result = router().price_batch(
        [
            pricing_router_module.PricingInput(
                scenario_a_instrument(),
                SETTLEMENT,
                market_price="101.25",
                pricing_spec=PricingSpec(),
                curves=fixed_curves(),
                instrument_id=FIXED_ID,
            )
        ]
    )

    assert FIXED_ID.as_str() not in result.outputs
    failure = result.errors[FIXED_ID.as_str()]
    assert failure.error_type == "RuntimeError"
    assert failure.message == "boom"


def test_price_fixed_propagates_yield_to_worst_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(self: object, clean_price: Decimal, settlement_date) -> Decimal:
        raise RuntimeError("ytw boom")

    monkeypatch.setattr(CallableBond, "yield_to_worst", explode)

    with pytest.raises(RuntimeError, match="ytw boom"):
        router().price_fixed(
            scenario_b_instrument(),
            SETTLEMENT,
            market_price="102.50",
            pricing_spec=PricingSpec(),
            curves=fixed_curves(),
        )
