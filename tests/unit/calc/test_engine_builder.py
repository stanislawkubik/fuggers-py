from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date, Frequency
from fuggers_py.calc import PricingEngineBuilder
from fuggers_py.calc.errors import EngineConfigurationError
from fuggers_py.calc.errors import CurveNotFoundError
from fuggers_py.core import CurveId, InstrumentId
from fuggers_py.market.snapshot import CurveInputs, CurvePoint
from fuggers_py.market.sources import InMemoryCurveSource, MarketDataProvider
from fuggers_py.reference import BondReferenceData, BondType, IssuerType, ReferenceDataProvider
from fuggers_py.calc import EngineConfig, NodeConfig, UpdateFrequency


class _BondSource:
    def __init__(self, reference: BondReferenceData) -> None:
        self.reference = reference

    def get_bond_reference(self, instrument_id):
        instrument_id = InstrumentId.parse(instrument_id)
        return self.reference if instrument_id == self.reference.instrument_id else None


def test_builder_rejects_missing_required_providers() -> None:
    with pytest.raises(EngineConfigurationError):
        PricingEngineBuilder().build()


def test_builder_constructs_engine_and_preloads_curve_inputs() -> None:
    reference = BondReferenceData(
        instrument_id=InstrumentId("US1234567890"),
        bond_type=BondType.FIXED_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2031, 1, 15),
        currency=Currency.USD,
        coupon_rate=Decimal("0.0450"),
        frequency=Frequency.SEMI_ANNUAL,
    )
    market_data = MarketDataProvider(
        curve_input_source=InMemoryCurveSource(
            [
                CurveInputs.from_points(
                    CurveId("usd.discount"),
                    Date.from_ymd(2026, 3, 14),
                    [CurvePoint(Decimal("1.0"), Decimal("0.0425"))],
                )
            ]
        )
    )
    reference_data = ReferenceDataProvider(bond_source=_BondSource(reference))
    engine = (
        PricingEngineBuilder()
        .with_engine_config(
            EngineConfig(
                engine_name="reactive-pricer",
                update_frequency=UpdateFrequency.INTRADAY,
                nodes=(NodeConfig(node_id="node-1", service_name="pricing"),),
            )
        )
        .with_market_data_provider(market_data)
        .with_reference_data_provider(reference_data)
        .with_settlement_date(Date.from_ymd(2026, 3, 14))
        .build()
    )

    assert engine.reactive_engine is not None
    assert engine.curve_builder.inputs_for("usd.discount") is not None
    with pytest.raises(CurveNotFoundError):
        engine.curve_builder.get("usd.discount")
    assert engine.config.engine_name == "reactive-pricer"
