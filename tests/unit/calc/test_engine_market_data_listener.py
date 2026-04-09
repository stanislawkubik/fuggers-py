from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date
from fuggers_py.calc import CurveBuilder
from fuggers_py.calc.calc_graph import CalculationGraph, NodeId
from fuggers_py.calc.market_data_listener import CurveInputUpdate, IndexFixingUpdate, MarketDataListener, QuoteUpdate
from fuggers_py.calc import QuoteSide
from fuggers_py.core import CurveId, InstrumentId
from fuggers_py.market.quotes import RawQuote
from fuggers_py.market.snapshot import CurveInputs, CurvePoint, IndexFixing


@pytest.mark.asyncio
async def test_market_data_listener_marks_dependents_dirty_for_quote_updates() -> None:
    graph = CalculationGraph()
    listener = MarketDataListener(calc_graph=graph)
    graph.add_node("price:US1234567890")
    graph.add_dependency("price:US1234567890", listener.quote_node_id("US1234567890"))

    updates = await listener.handle_update(
        QuoteUpdate(
            quote=RawQuote(
                instrument_id=InstrumentId("US1234567890"),
                value=Decimal("101.25"),
                as_of=Date.from_ymd(2026, 3, 14),
                currency=Currency.USD,
            ),
            timestamp=datetime(2026, 3, 14, 9, 0, tzinfo=UTC),
        )
    )

    assert updates[0].node_id == listener.quote_node_id("US1234567890")
    assert NodeId("price:US1234567890") in graph.query_dirty()
    assert graph.get_node_value(listener.quote_node_id("US1234567890")).value.instrument_id == InstrumentId("US1234567890")


@pytest.mark.asyncio
async def test_market_data_listener_builds_curve_and_marks_curve_dependents_dirty() -> None:
    graph = CalculationGraph()
    builder = CurveBuilder()
    listener = MarketDataListener(calc_graph=graph, curve_builder=builder)
    graph.add_node("price:curve-user")
    graph.add_dependency("price:curve-user", listener.curve_node_id("usd.discount"))

    curve_inputs = CurveInputs.from_points(
        CurveId("usd.discount"),
        Date.from_ymd(2026, 3, 14),
        [CurvePoint(Decimal("1.0"), Decimal("0.0425")), CurvePoint(Decimal("5.0"), Decimal("0.0390"))],
    )
    updates = await listener.handle_update(CurveInputUpdate(curve_inputs=curve_inputs, timestamp=datetime(2026, 3, 14, 9, 0, tzinfo=UTC)))

    assert listener.curve_node_id("usd.discount") in tuple(update.node_id for update in updates)
    assert builder.get("usd.discount") is not None
    assert NodeId("price:curve-user") in graph.query_dirty()


@pytest.mark.asyncio
async def test_market_data_listener_marks_fixing_dependents_dirty() -> None:
    graph = CalculationGraph()
    listener = MarketDataListener(calc_graph=graph)
    fixing_node = listener.fixing_node_id("SOFR", Date.from_ymd(2026, 3, 14))
    graph.add_node("price:frn")
    graph.add_dependency("price:frn", fixing_node)

    await listener.handle_update(
        IndexFixingUpdate(
            fixing=IndexFixing("SOFR", Date.from_ymd(2026, 3, 14), Decimal("0.0411")),
            timestamp=datetime(2026, 3, 14, 9, 1, tzinfo=UTC),
        )
    )

    assert NodeId("price:frn") in graph.query_dirty()
