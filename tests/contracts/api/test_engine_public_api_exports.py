from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date
import fuggers_py.calc as calc
from fuggers_py.calc import (
    IntervalScheduler,
    MarketDataPublisher,
    NodeId,
    PricingEngineBuilder,
    PricingInput,
    QuoteUpdate,
    ReactiveEngine,
    ReactiveEngineBuilder,
    UpdateSource,
)
from fuggers_py.portfolio import Portfolio, Position
from fuggers_py.portfolio import Portfolio as PortfolioType
from fuggers_py.portfolio import Position as PositionType
from fuggers_py.calc import QuoteSide
from fuggers_py.core import InstrumentId
from fuggers_py.market.curves import CurveType
from fuggers_py.market.quotes import RawQuote
from fuggers_py.market.snapshot import CurvePoint
from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.market.sources import MarketDataProvider
from fuggers_py.reference import BondReferenceData, BondType, IssuerType, ReferenceDataProvider
from tests.helpers._public_curve_helpers import linear_zero_curve


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


def test_engine_root_imports_expose_public_aliases(fixed_rate_2025_bond) -> None:
    position = Position(fixed_rate_2025_bond, quantity=Decimal("2"), label="bond")
    portfolio = Portfolio.new([position], currency=fixed_rate_2025_bond.currency())

    assert ReactiveEngineBuilder is PricingEngineBuilder
    assert Portfolio is PortfolioType
    assert Position is PositionType
    assert portfolio.total_quantity() == Decimal("2")


def test_engine_root_no_longer_exports_calc_curve_registry_helpers() -> None:
    assert not hasattr(calc, "AnalyticsCurves")
    assert not hasattr(calc, "BuiltCurve")
    assert not hasattr(calc, "CurveBuilder")
    assert not hasattr(calc, "FundingPricingRouter")
    assert not hasattr(calc, "CurvePublisher")
    assert not hasattr(calc, "CurveInputUpdate")
    assert not hasattr(calc, "RatesPricingRouter")
    assert not hasattr(calc, "CurveUpdate")


def test_reactive_engine_builder_constructs_pricing_and_reactive_engines() -> None:
    instrument_id = InstrumentId("ENGINE-SURFACE")
    market_data = MarketDataProvider()
    reference_data = ReferenceDataProvider(bond_source=_BondSource(_reference_data(instrument_id)))

    builder = (
        ReactiveEngineBuilder.new()
        .with_market_data_provider(market_data)
        .with_reference_data_provider(reference_data)
        .with_settlement_date(Date.from_ymd(2026, 3, 14))
        .with_default_interval_scheduler([NodeId("price:ENGINE-SURFACE")], interval_seconds=60.0)
    )

    engine = builder.build()
    reactive = builder.build_reactive()

    assert engine.reactive_engine is not None
    assert isinstance(engine.reactive_engine, ReactiveEngine)
    assert isinstance(reactive, ReactiveEngine)
    assert len(reactive.schedulers) == 1
    assert isinstance(reactive.schedulers[0], IntervalScheduler)


@pytest.mark.asyncio
async def test_scheduler_and_market_data_public_surface_is_accessible_from_engine_root() -> None:
    scheduler = IntervalScheduler([NodeId("price:ABC")], interval_seconds=60.0)
    scheduler_queue = scheduler.subscribe()
    publisher = MarketDataPublisher()
    publisher_queue = publisher.subscribe()

    updates = await scheduler.tick(now=datetime(2026, 3, 14, 9, 0, tzinfo=UTC))
    update = QuoteUpdate(
        quote=RawQuote(
            instrument_id=InstrumentId("ABC"),
            value=Decimal("101.25"),
            as_of=Date.from_ymd(2026, 3, 14),
            currency=Currency.USD,
        ),
        timestamp=datetime(2026, 3, 14, 9, 0, tzinfo=UTC),
    )
    await publisher.publish(update)

    assert updates[0].source is UpdateSource.INTERVAL
    assert await scheduler_queue.get() == updates[0]
    assert await publisher_queue.get() == update


@pytest.mark.asyncio
async def test_reactive_engine_flow_works_through_root_public_surface() -> None:
    instrument_id = InstrumentId("REACTIVE-SURFACE")
    settlement = Date.from_ymd(2026, 3, 14)
    market_data = MarketDataProvider()
    reference_data = ReferenceDataProvider(bond_source=_BondSource(_reference_data(instrument_id)))
    reactive = (
        ReactiveEngineBuilder.new()
        .with_market_data_provider(market_data)
        .with_reference_data_provider(reference_data)
        .with_settlement_date(settlement)
        .build_reactive()
    )
    reactive.register_pricing_node(
        NodeId("price:REACTIVE-SURFACE"),
        PricingInput(
            instrument=instrument_id,
            settlement_date=settlement,
            instrument_id=instrument_id,
            curves=AnalyticsCurves(
                discount_curve=linear_zero_curve(
                    "usd.discount",
                    settlement,
                    (
                        CurvePoint(Decimal("1.0"), Decimal("0.0425")),
                        CurvePoint(Decimal("5.0"), Decimal("0.0390")),
                    ),
                    curve_type=CurveType.OVERNIGHT_DISCOUNT,
                )
            ),
        ),
    )

    await reactive.start()
    try:
        updates_queue = reactive.subscribe_updates()
        await reactive.publish_market_data_update(
            QuoteUpdate(
                quote=RawQuote(
                    instrument_id=instrument_id,
                    value=Decimal("101.25"),
                    as_of=settlement,
                    currency=Currency.USD,
                ),
                timestamp=datetime(2026, 3, 14, 9, 0, tzinfo=UTC),
            )
        )
        processed = await reactive.process_once(timeout=0.1)
        published = await updates_queue.get()
        cached_value = reactive.calc_graph.get_node_value("price:REACTIVE-SURFACE")
    finally:
        await reactive.stop()

    assert any(update.node_id == NodeId("price:REACTIVE-SURFACE") for update in processed)
    assert published.node_id in tuple(update.node_id for update in processed)
    assert cached_value is not None
    assert cached_value.value.clean_price is not None
