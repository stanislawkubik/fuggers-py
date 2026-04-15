from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date
from fuggers_py.calc.calc_graph import CalculationGraph, NodeId
from fuggers_py.calc.market_data_listener import (
    FxRateUpdate,
    InflationFixingUpdate,
    MarketDataListener,
    MarketDataPublisher,
    QuoteUpdate,
    VolSurfaceUpdate,
)
from fuggers_py.calc.scheduler import NodeUpdate, ThrottleManager, UpdateSource
from fuggers_py.core import CurrencyPair, InstrumentId, VolSurfaceId, YearMonth
from fuggers_py.market.quotes import RawQuote
from fuggers_py.calc.pricing_specs import QuoteSide
from fuggers_py.market.snapshot import FxRate, InflationFixing
from fuggers_py.market.vol_surfaces import VolSurfaceType, VolatilitySurface


@pytest.mark.asyncio
async def test_market_data_publisher_unsubscribe_stops_delivery() -> None:
    publisher = MarketDataPublisher()
    primary = publisher.subscribe()
    removed = publisher.subscribe()
    publisher.unsubscribe(removed)
    update = QuoteUpdate(
        quote=RawQuote(
            instrument_id=InstrumentId("PUBLISHER"),
            value=Decimal("101.25"),
            as_of=Date.from_ymd(2026, 3, 14),
            currency=Currency.USD,
        ),
        timestamp=datetime(2026, 3, 14, 9, 0, tzinfo=UTC),
    )

    await publisher.publish(update)

    assert await primary.get() == update
    assert removed.empty()


@pytest.mark.asyncio
async def test_market_data_listener_drain_scheduler_update_preserves_payload_and_marks_dependents_dirty() -> None:
    graph = CalculationGraph()
    trigger = NodeId("curve:usd.discount")
    dependent = NodeId("price:scheduled")
    graph.add_dependency(dependent, trigger)
    listener = MarketDataListener(calc_graph=graph)
    queue: asyncio.Queue = asyncio.Queue()
    update = NodeUpdate(
        node_id=trigger,
        source=UpdateSource.CRON,
        timestamp=datetime(2026, 3, 14, 10, 0, tzinfo=UTC),
        payload={"trigger": "cron"},
        detail="0 * * * *",
    )
    queue.put_nowait(update)

    processed = await listener.drain_once(queue)

    assert {item.node_id for item in processed} == {trigger, dependent}
    assert all(item.payload == {"trigger": "cron"} for item in processed)
    assert all(item.detail == "0 * * * *" for item in processed)
    assert dependent in graph.query_dirty()


@pytest.mark.asyncio
async def test_market_data_listener_throttles_repeated_quote_updates() -> None:
    graph = CalculationGraph()
    listener = MarketDataListener(
        calc_graph=graph,
        throttle_manager=ThrottleManager(min_interval_seconds=60.0),
    )
    timestamp = datetime(2026, 3, 14, 9, 0, tzinfo=UTC)
    update = QuoteUpdate(
        quote=RawQuote(
            instrument_id=InstrumentId("THROTTLED"),
            value=Decimal("101.25"),
            as_of=Date.from_ymd(2026, 3, 14),
            currency=Currency.USD,
        ),
        timestamp=timestamp,
    )

    first = await listener.handle_update(update)
    second = await listener.handle_update(update)

    assert len(first) == 1
    assert second == ()
    assert listener.quote_source.get_quote("THROTTLED", side=QuoteSide.MID) is not None


@pytest.mark.asyncio
async def test_market_data_listener_handles_fx_inflation_and_volatility_paths() -> None:
    graph = CalculationGraph()
    listener = MarketDataListener(calc_graph=graph)
    graph.add_dependency("price:fx-user", listener.fx_node_id("USD/EUR"))
    graph.add_dependency("price:cpi-user", listener.inflation_node_id("USCPI", "2026-02"))
    graph.add_dependency("price:vol-user", listener.vol_surface_node_id("usd.swaption"))

    reference_date = Date.from_ymd(2026, 3, 14)
    fx_updates = await listener.handle_update(
        FxRateUpdate(
            fx_rate=FxRate(
                currency_pair=CurrencyPair.parse("USD/EUR"),
                rate=Decimal("0.91"),
                side=QuoteSide.MID,
                as_of=reference_date,
            ),
            timestamp=datetime(2026, 3, 14, 9, 1, tzinfo=UTC),
        )
    )
    inflation_updates = await listener.handle_update(
        InflationFixingUpdate(
            fixing=InflationFixing(
                index_name="uscpi",
                observation_month=YearMonth.parse("2026-02"),
                value=Decimal("312.4"),
                publication_date=reference_date,
            ),
            timestamp=datetime(2026, 3, 14, 9, 2, tzinfo=UTC),
        )
    )
    vol_updates = await listener.handle_update(
        VolSurfaceUpdate(
            surface=VolatilitySurface(
                surface_id=VolSurfaceId.parse("usd.swaption"),
                surface_type=VolSurfaceType.SWAPTION,
                as_of=reference_date,
            ),
            timestamp=datetime(2026, 3, 14, 9, 3, tzinfo=UTC),
        )
    )

    assert listener.fx_rate_source.get_fx_rate("USD/EUR", side=QuoteSide.MID) is not None
    assert listener.inflation_fixing_source.get_inflation_fixing("USCPI", "2026-02") is not None
    assert listener.volatility_source.get_volatility_surface("usd.swaption") is not None
    assert NodeId("price:fx-user") in graph.query_dirty()
    assert NodeId("price:cpi-user") in graph.query_dirty()
    assert NodeId("price:vol-user") in graph.query_dirty()
    assert fx_updates[0].source is UpdateSource.MARKET_DATA
    assert inflation_updates[0].source is UpdateSource.MARKET_DATA
    assert vol_updates[0].source is UpdateSource.MARKET_DATA
