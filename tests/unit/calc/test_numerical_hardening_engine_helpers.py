from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date
from fuggers_py.calc import BuiltCurve, CurveBuilder
from fuggers_py.calc.calc_graph import CalculationGraph, NodeId
from fuggers_py.calc.market_data_listener import (
    CurveUpdate,
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
from fuggers_py.market.snapshot import CurveInputs, CurvePoint, FxRate, InflationFixing
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
async def test_market_data_listener_handles_curve_fx_inflation_and_volatility_paths() -> None:
    graph = CalculationGraph()
    listener = MarketDataListener(calc_graph=graph, curve_builder=CurveBuilder())
    graph.add_dependency("price:curve-user", listener.curve_node_id("usd.discount"))
    graph.add_dependency("price:fx-user", listener.fx_node_id("USD/EUR"))
    graph.add_dependency("price:cpi-user", listener.inflation_node_id("USCPI", "2026-02"))
    graph.add_dependency("price:vol-user", listener.vol_surface_node_id("usd.swaption"))

    reference_date = Date.from_ymd(2026, 3, 14)
    curve_inputs = CurveInputs.from_points(
        "usd.discount",
        reference_date,
        [CurvePoint(Decimal("1.0"), Decimal("0.03"))],
        curve_kind="discount",
    )
    curve_updates = await listener.handle_update(
        CurveUpdate(
            curve_id="usd.discount",
            curve_inputs=curve_inputs,
            curve="curve-object",
            timestamp=datetime(2026, 3, 14, 9, 0, tzinfo=UTC),
        )
    )
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

    assert listener.calc_graph.get_node_value(listener.curve_node_id("usd.discount")).value == "curve-object"
    assert listener.fx_rate_source.get_fx_rate("USD/EUR", side=QuoteSide.MID) is not None
    assert listener.inflation_fixing_source.get_inflation_fixing("USCPI", "2026-02") is not None
    assert listener.volatility_source.get_volatility_surface("usd.swaption") is not None
    assert NodeId("price:curve-user") in graph.query_dirty()
    assert NodeId("price:fx-user") in graph.query_dirty()
    assert NodeId("price:cpi-user") in graph.query_dirty()
    assert NodeId("price:vol-user") in graph.query_dirty()
    assert curve_updates[0].source is UpdateSource.MARKET_DATA
    assert fx_updates[0].source is UpdateSource.MARKET_DATA
    assert inflation_updates[0].source is UpdateSource.MARKET_DATA
    assert vol_updates[0].source is UpdateSource.MARKET_DATA


def test_curve_builder_single_pillar_curves_bundle_and_forward_interval_are_stable() -> None:
    reference_date = Date.from_ymd(2026, 3, 14)
    builder = CurveBuilder()
    discount_curve = builder.add_discount_curve(
        "usd.discount",
        [CurvePoint(Decimal("1.0"), Decimal("0.97"))],
        reference_date,
    )
    zero_curve = builder.add_zero_curve(
        "usd.zero",
        [CurvePoint(Decimal("1.0"), Decimal("0.03"))],
        reference_date,
    )
    forward_curve = builder.add_forward_curve(
        "usd.forward",
        [CurvePoint(Decimal("1.0"), Decimal("0.03")), CurvePoint(Decimal("2.0"), Decimal("0.05"))],
        reference_date,
    )

    start = reference_date.add_days(365)
    end = reference_date.add_days(365 * 2)
    bundle = builder.bundle(discount_curve="usd.discount", forward_curve="usd.forward")

    assert discount_curve.discount_factor_at_tenor(0.5) == pytest.approx(0.97, abs=1e-12)
    assert zero_curve.zero_rate_at_tenor(5.0) == pytest.approx(0.03, abs=1e-12)
    assert forward_curve.forward_rate(start, end) == pytest.approx(0.07, abs=1e-12)
    assert bundle.discount_curve is discount_curve
    assert bundle.forward_curve is forward_curve
    assert builder.inputs_for("usd.forward").curve_kind == "forward"


def test_built_curve_reference_date_falls_back_to_curve_inputs_for_opaque_curves() -> None:
    reference_date = Date.from_ymd(2026, 3, 14)
    curve_inputs = CurveInputs.from_points(
        "opaque.curve",
        reference_date,
        [CurvePoint(Decimal("1.0"), Decimal("0.03"))],
    )
    built = BuiltCurve.of("opaque.curve", object(), curve_inputs=curve_inputs)

    assert built.date() == reference_date
