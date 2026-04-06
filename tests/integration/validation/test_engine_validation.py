from __future__ import annotations

from datetime import UTC, datetime, time
from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date
from fuggers_py.calc import (
    EodScheduler,
    IntervalScheduler,
    NodeId,
    PricingEngineBuilder,
    PricingInput,
    QuoteUpdate,
)
from fuggers_py.calc import QuoteSide
from fuggers_py.core import CurveId, InstrumentId
from fuggers_py.market.quotes import RawQuote
from fuggers_py.market.snapshot import CurveInputs, CurvePoint
from fuggers_py.market.sources import MarketDataProvider
from fuggers_py.reference import BondReferenceData, BondType, IssuerType, ReferenceDataProvider

from ._helpers import D, assert_decimal_close, load_fixture


pytestmark = pytest.mark.validation


class _BondSource:
    def __init__(self, reference: BondReferenceData) -> None:
        self.reference = reference

    def get_bond_reference(self, instrument_id):
        instrument_id = InstrumentId.parse(instrument_id)
        return self.reference if instrument_id == self.reference.instrument_id else None


@pytest.mark.asyncio
async def test_scheduler_reference_flow_matches_fixture() -> None:
    fixture = load_fixture("engine", "scheduler.json")["scheduler_reference"]
    interval = IntervalScheduler([NodeId(fixture["interval_node_id"])], interval_seconds=60.0)
    updates = await interval.tick(now=datetime.fromisoformat(fixture["interval_timestamp"]))
    eod = EodScheduler([NodeId(fixture["eod_node_id"])], run_time=time(17, 0), check_interval_seconds=60.0)
    first = await eod.tick(now=datetime.fromisoformat(fixture["eod_first_run"]))
    second = await eod.tick(now=datetime.fromisoformat(fixture["eod_second_run"]))

    assert updates[0].source.value == fixture["expected_interval_source"]
    assert updates[0].timestamp.isoformat() == fixture["interval_timestamp"]
    assert len(first) == int(fixture["expected_eod_first_count"])
    assert len(second) == int(fixture["expected_eod_second_count"])


@pytest.mark.asyncio
async def test_reactive_engine_reference_flow_matches_fixture() -> None:
    fixture = load_fixture("engine", "reactive.json")["reactive_fixed_bond_case"]
    instrument_id = InstrumentId(fixture["instrument_id"])
    reference = BondReferenceData(
        instrument_id=instrument_id,
        bond_type=BondType.FIXED_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.parse(fixture["issue_date"]),
        maturity_date=Date.parse(fixture["maturity_date"]),
        currency=Currency.USD,
        coupon_rate=D(fixture["coupon_rate"]),
    )
    market_data = MarketDataProvider()
    reference_data = ReferenceDataProvider(bond_source=_BondSource(reference))
    engine = (
        PricingEngineBuilder()
        .with_market_data_provider(market_data)
        .with_reference_data_provider(reference_data)
        .with_settlement_date(Date.parse(fixture["settlement_date"]))
        .build()
    )
    assert engine.reactive_engine is not None
    reactive = engine.reactive_engine
    queue = reactive.subscribe_updates()
    curve_inputs = CurveInputs.from_points(
        CurveId(fixture["curve_id"]),
        Date.parse(fixture["settlement_date"]),
        [
            CurvePoint(D(point["tenor"]), D(point["rate"]))
            for point in fixture["curve_points"]
        ],
    )
    reactive.curve_builder.add_from_inputs(curve_inputs)
    reactive.listener.curve_source.add_curve_inputs(curve_inputs)
    reactive.register_pricing_node(
        NodeId(fixture["pricing_node_id"]),
        PricingInput(
            instrument=instrument_id,
            settlement_date=Date.parse(fixture["settlement_date"]),
            instrument_id=instrument_id,
            curve_roles={"discount": fixture["curve_id"]},
        ),
    )

    await reactive.start()
    await reactive.publish_market_data_update(
        QuoteUpdate(
            quote=RawQuote(
                instrument_id=instrument_id,
                value=D(fixture["market_price"]),
                side=QuoteSide.MID,
                as_of=Date.parse(fixture["settlement_date"]),
                currency=Currency.USD,
            ),
            timestamp=datetime.fromisoformat(fixture["quote_timestamp"]),
        )
    )
    processed = await reactive.process_once(timeout=0.1)
    published = await queue.get()
    cached_value = reactive.calc_graph.get_node_value(fixture["pricing_node_id"])
    await reactive.stop()

    assert len(processed) == int(fixture["expected_processed_updates"])
    assert published.node_id == NodeId(fixture["expected_first_published_node"])
    assert cached_value is not None
    assert_decimal_close(cached_value.value.clean_price, D(fixture["expected_clean_price"]), Decimal("1e-24"))
    assert_decimal_close(cached_value.value.yield_to_maturity, D(fixture["expected_yield_to_maturity"]), Decimal("1e-16"))
