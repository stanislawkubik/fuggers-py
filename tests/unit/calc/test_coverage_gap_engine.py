from __future__ import annotations

from datetime import UTC, datetime, time
from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date
from fuggers_py.calc import (
    CronScheduler,
    EodScheduler,
    IntervalScheduler,
    NodeId,
    NodeUpdate,
    PricingEngineBuilder,
    PricingInput,
    QuoteUpdate,
    ThrottleManager,
    UpdateSource,
)
from fuggers_py.calc.errors import SchedulerError
from fuggers_py.calc.pricing_router import PricingFailure
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


def _reference_data(instrument_id: InstrumentId) -> BondReferenceData:
    return BondReferenceData(
        instrument_id=instrument_id,
        bond_type=BondType.FIXED_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2031, 1, 15),
        currency=Currency.USD,
        coupon_rate=Decimal("0.0450"),
    )


def _reactive_engine(*, instrument_id: str = "REACTIVE-COVERAGE"):
    resolved_id = InstrumentId(instrument_id)
    settlement = Date.from_ymd(2026, 3, 14)
    market_data = MarketDataProvider()
    reference_data = ReferenceDataProvider(bond_source=_BondSource(_reference_data(resolved_id)))
    reactive = (
        PricingEngineBuilder()
        .with_market_data_provider(market_data)
        .with_reference_data_provider(reference_data)
        .with_settlement_date(settlement)
        .build_reactive()
    )
    curve_inputs = CurveInputs.from_points(
        CurveId("usd.discount"),
        settlement,
        [CurvePoint(Decimal("1.0"), Decimal("0.0425")), CurvePoint(Decimal("5.0"), Decimal("0.0390"))],
    )
    reactive.curve_builder.add_from_inputs(curve_inputs)
    reactive.listener.curve_source.add_curve_inputs(curve_inputs)
    return reactive, resolved_id, settlement


def _quote_update(instrument_id: InstrumentId, settlement: Date, *, value: str = "101.25") -> QuoteUpdate:
    return QuoteUpdate(
        quote=RawQuote(
            instrument_id=instrument_id,
            value=Decimal(value),
            as_of=settlement,
            currency=Currency.USD,
        ),
        timestamp=datetime(2026, 3, 14, 9, 0, tzinfo=UTC),
    )


def test_scheduler_validation_node_update_parsing_and_throttle_reset() -> None:
    with pytest.raises(ValueError):
        IntervalScheduler([NodeId("price:ABC")], interval_seconds=0.0)

    with pytest.raises(ValueError):
        EodScheduler([NodeId("nav:portfolio")], run_time=time(17, 0), check_interval_seconds=0.0)

    with pytest.raises(SchedulerError):
        CronScheduler([NodeId("curve:usd")], expression="not a cron")

    update = NodeUpdate(node_id="price:ABC", source=UpdateSource.MANUAL)
    throttle = ThrottleManager(min_interval_seconds=10.0)
    now = datetime(2026, 3, 14, 9, 0, tzinfo=UTC)

    assert update.node_id == NodeId("price:ABC")
    assert throttle.allow("quote:ABC", now=now) is True
    assert throttle.allow("quote:ABC", now=now) is False
    throttle.reset("quote:ABC")
    assert throttle.allow("quote:ABC", now=now) is True
    throttle.reset()
    assert throttle.remaining("quote:ABC", now=now) == 0.0


@pytest.mark.asyncio
async def test_reactive_engine_process_once_requires_start_and_unsubscribe_is_respected() -> None:
    reactive, instrument_id, settlement = _reactive_engine()
    reactive.register_pricing_node(
        NodeId(f"price:{instrument_id.as_str()}"),
        PricingInput(
            instrument=instrument_id,
            settlement_date=settlement,
            instrument_id=instrument_id,
            curve_roles={"discount": "usd.discount"},
        ),
    )

    with pytest.raises(RuntimeError):
        await reactive.process_once(timeout=0.0)

    await reactive.start()
    try:
        queue = reactive.subscribe_updates()
        reactive.unsubscribe_updates(queue)
        await reactive.publish_market_data_update(_quote_update(instrument_id, settlement))
        processed = await reactive.process_once(timeout=0.1)
    finally:
        await reactive.stop()

    assert processed
    assert queue.empty()


@pytest.mark.asyncio
async def test_reactive_engine_surfaces_pricing_failures_for_dirty_nodes_without_inputs() -> None:
    reactive, instrument_id, settlement = _reactive_engine(instrument_id="REACTIVE-FAILURE")
    pricing_node = reactive.register_pricing_node(
        NodeId("price:REACTIVE-FAILURE"),
        PricingInput(
            instrument=instrument_id,
            settlement_date=settlement,
            instrument_id=instrument_id,
        ),
    )

    await reactive.start()
    try:
        reactive.calc_graph.mark_dirty(pricing_node)
        await reactive.publish_market_data_update(_quote_update(InstrumentId("UNRELATED"), settlement))
        processed = await reactive.process_once(timeout=0.1)
        cached = reactive.calc_graph.get_node_value(pricing_node)
    finally:
        await reactive.stop()

    failures = [update for update in processed if isinstance(update.payload, PricingFailure)]
    assert failures
    assert cached is not None
    assert isinstance(cached.value, PricingFailure)
    assert cached.value.error_type == "RoutingError"
