from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from fuggers_py.calc import (
    MarketDataPublisher,
    NodeId,
    PricingEngineBuilder,
    PricingInput,
    QuoteUpdate,
)
from fuggers_py.core import Currency, Date
from fuggers_py.calc import QuoteSide
from fuggers_py.core import CurveId, InstrumentId
from fuggers_py.market.quotes import RawQuote
from fuggers_py.market.snapshot import CurveInputs, CurvePoint
from fuggers_py.market.sources import MarketDataProvider
from fuggers_py.reference import BondReferenceData, BondType, IssuerType, ReferenceDataProvider


class _BondSource:
    def __init__(self, reference: BondReferenceData) -> None:
        self.reference = reference

    def get_bond_reference(self, instrument_id):
        instrument_id = InstrumentId.parse(instrument_id)
        return self.reference if instrument_id == self.reference.instrument_id else None


@pytest.mark.asyncio
async def test_reactive_engine_processes_updates_without_background_hangs() -> None:
    fixed_id = InstrumentId("REACTIVE-FIXED")
    reference = BondReferenceData(
        instrument_id=fixed_id,
        bond_type=BondType.FIXED_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2031, 1, 15),
        currency=Currency.USD,
        coupon_rate=Decimal("0.0450"),
    )
    market_data = MarketDataProvider()
    reference_data = ReferenceDataProvider(bond_source=_BondSource(reference))
    engine = (
        PricingEngineBuilder()
        .with_market_data_provider(market_data)
        .with_reference_data_provider(reference_data)
        .with_settlement_date(Date.from_ymd(2026, 3, 14))
        .build()
    )
    assert engine.reactive_engine is not None
    reactive = engine.reactive_engine
    updates_queue = reactive.subscribe_updates()

    curve_inputs = CurveInputs.from_points(
        CurveId("usd.discount"),
        Date.from_ymd(2026, 3, 14),
        [CurvePoint(Decimal("1.0"), Decimal("0.0425")), CurvePoint(Decimal("5.0"), Decimal("0.0390"))],
    )
    reactive.curve_builder.add_from_inputs(curve_inputs)
    reactive.listener.curve_source.add_curve_inputs(curve_inputs)
    reactive.register_pricing_node(
        NodeId("price:REACTIVE-FIXED"),
        PricingInput(
            instrument=fixed_id,
            settlement_date=Date.from_ymd(2026, 3, 14),
            instrument_id=fixed_id,
            curve_roles={"discount": "usd.discount"},
        ),
    )

    await reactive.start()
    await reactive.publish_market_data_update(
        QuoteUpdate(
            quote=RawQuote(
                instrument_id=fixed_id,
                value=Decimal("101.25"),
                side=QuoteSide.MID,
                as_of=Date.from_ymd(2026, 3, 14),
                currency=Currency.USD,
            ),
            timestamp=datetime(2026, 3, 14, 9, 0, tzinfo=UTC),
        )
    )
    processed = await reactive.process_once(timeout=0.1)
    published = await updates_queue.get()
    cached_value = reactive.calc_graph.get_node_value("price:REACTIVE-FIXED")

    await reactive.stop()

    assert any(update.node_id == NodeId("price:REACTIVE-FIXED") for update in processed)
    assert published.node_id in tuple(update.node_id for update in processed)
    assert cached_value is not None
    assert cached_value.value.clean_price is not None
