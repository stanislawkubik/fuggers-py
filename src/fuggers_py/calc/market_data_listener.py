"""Async market-data fanout and graph integration helpers.

The listener stores incoming market-data payloads, updates the calculation
graph, and marks dependent nodes dirty so the reactive engine can refresh
pricing outputs deterministically. Quote, curve, fixing, FX, and volatility
updates are all translated into graph nodes with stable identifiers.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fuggers_py.core import CurveId, CurrencyPair, InstrumentId, VolSurfaceId, YearMonth
from fuggers_py.market.quotes import RawQuote
from fuggers_py.market.snapshot import CurveInputs, EtfQuote, FxRate, IndexFixing, InflationFixing
from fuggers_py.market.sources import (
    InMemoryCurveSource,
    InMemoryFixingSource,
    InMemoryFxRateSource,
    InMemoryInflationFixingSource,
    InMemoryQuoteSource,
)
from fuggers_py.market.vol_surfaces import InMemoryVolatilitySource, VolatilitySurface

from .calc_graph import CalculationGraph, NodeId
from .curve_builder import CurveBuilder
from .scheduler import NodeUpdate, ThrottleManager, UpdateSource


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketDataUpdate:
    """Base record for a market-data event."""

    timestamp: datetime = field(default_factory=_now)
    source: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class QuoteUpdate(MarketDataUpdate):
    """Update carrying a new quote."""

    quote: RawQuote


@dataclass(frozen=True, slots=True, kw_only=True)
class CurveInputUpdate(MarketDataUpdate):
    """Update carrying new raw curve inputs."""

    curve_inputs: CurveInputs


@dataclass(frozen=True, slots=True, kw_only=True)
class CurveUpdate(MarketDataUpdate):
    """Update carrying a finished curve and optional raw inputs."""

    curve_id: CurveId
    curve: object | None = None
    curve_inputs: CurveInputs | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class IndexFixingUpdate(MarketDataUpdate):
    """Update carrying an index fixing."""

    fixing: IndexFixing


@dataclass(frozen=True, slots=True, kw_only=True)
class InflationFixingUpdate(MarketDataUpdate):
    """Update carrying an inflation fixing."""

    fixing: InflationFixing


@dataclass(frozen=True, slots=True, kw_only=True)
class FxRateUpdate(MarketDataUpdate):
    """Update carrying an FX rate."""

    fx_rate: FxRate


@dataclass(frozen=True, slots=True, kw_only=True)
class VolSurfaceUpdate(MarketDataUpdate):
    """Update carrying a volatility surface."""

    surface: VolatilitySurface


class MarketDataPublisher:
    """Async fanout helper for broadcasting market-data updates."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        """Create and register a subscriber queue."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a previously registered subscriber queue."""
        self._subscribers.discard(queue)

    async def publish(self, update: MarketDataUpdate) -> None:
        """Publish an update to all current subscribers."""
        for queue in tuple(self._subscribers):
            await queue.put(update)


@dataclass(slots=True)
class MarketDataListener:
    """Translate market-data updates into graph updates and cache writes."""

    calc_graph: CalculationGraph
    curve_builder: CurveBuilder | None = None
    quote_source: InMemoryQuoteSource = field(default_factory=InMemoryQuoteSource)
    curve_source: InMemoryCurveSource = field(default_factory=InMemoryCurveSource)
    fixing_source: InMemoryFixingSource = field(default_factory=InMemoryFixingSource)
    fx_rate_source: InMemoryFxRateSource = field(default_factory=InMemoryFxRateSource)
    inflation_fixing_source: InMemoryInflationFixingSource = field(default_factory=InMemoryInflationFixingSource)
    volatility_source: InMemoryVolatilitySource = field(default_factory=InMemoryVolatilitySource)
    throttle_manager: ThrottleManager | None = None

    @staticmethod
    def quote_node_id(instrument_id: InstrumentId | str) -> NodeId:
        """Return the graph node identifier for a quote."""
        return NodeId.parse(f"quote:{InstrumentId.parse(instrument_id).as_str()}")

    @staticmethod
    def curve_input_node_id(curve_id: CurveId | str) -> NodeId:
        """Return the graph node identifier for curve inputs."""
        return NodeId.parse(f"curve_input:{CurveId.parse(curve_id).as_str()}")

    @staticmethod
    def curve_node_id(curve_id: CurveId | str) -> NodeId:
        """Return the graph node identifier for a built curve."""
        return NodeId.parse(f"curve:{CurveId.parse(curve_id).as_str()}")

    @staticmethod
    def fixing_node_id(index_name: str, fixing_date) -> NodeId:
        """Return the graph node identifier for a fixing."""
        return NodeId.parse(f"fixing:{index_name.strip().upper()}:{fixing_date}")

    @staticmethod
    def inflation_node_id(index_name: str, observation_month: YearMonth | str) -> NodeId:
        """Return the graph node identifier for an inflation fixing."""
        return NodeId.parse(f"inflation:{index_name.strip().upper()}:{YearMonth.parse(observation_month).as_str()}")

    @staticmethod
    def fx_node_id(currency_pair: CurrencyPair | str) -> NodeId:
        """Return the graph node identifier for an FX rate."""
        return NodeId.parse(f"fx:{CurrencyPair.parse(currency_pair).as_str()}")

    @staticmethod
    def vol_surface_node_id(surface_id: VolSurfaceId | str) -> NodeId:
        """Return the graph node identifier for a volatility surface."""
        return NodeId.parse(f"vol:{VolSurfaceId.parse(surface_id).as_str()}")

    async def handle_update(self, update: MarketDataUpdate) -> tuple[NodeUpdate, ...]:
        """Apply a market-data update to the caches and dependency graph."""
        if isinstance(update, QuoteUpdate):
            return self._handle_quote_update(update)
        if isinstance(update, CurveInputUpdate):
            return self._handle_curve_input_update(update)
        if isinstance(update, CurveUpdate):
            return self._handle_curve_update(update)
        if isinstance(update, IndexFixingUpdate):
            return self._handle_fixing_update(update)
        if isinstance(update, InflationFixingUpdate):
            return self._handle_inflation_update(update)
        if isinstance(update, FxRateUpdate):
            return self._handle_fx_update(update)
        if isinstance(update, VolSurfaceUpdate):
            return self._handle_vol_surface_update(update)
        return ()

    async def handle_scheduler_update(self, update: NodeUpdate) -> tuple[NodeUpdate, ...]:
        """Mark a scheduler-triggered node and its dependents dirty."""
        self.calc_graph.add_node(update.node_id)
        dirty = self.calc_graph.mark_dirty(update.node_id, include_self=True)
        return tuple(
            NodeUpdate(node_id=node_id, source=update.source, timestamp=update.timestamp, payload=update.payload, detail=update.detail)
            for node_id in dirty
        )

    async def drain_once(self, queue: asyncio.Queue) -> tuple[NodeUpdate, ...]:
        """Drain a single item from a queue and route it through the listener."""
        item = await queue.get()
        if isinstance(item, NodeUpdate):
            return await self.handle_scheduler_update(item)
        return await self.handle_update(item)

    def _allow(self, key: str, timestamp: datetime) -> bool:
        if self.throttle_manager is None:
            return True
        return self.throttle_manager.allow(key, now=timestamp)

    def _handle_quote_update(self, update: QuoteUpdate) -> tuple[NodeUpdate, ...]:
        node_id = self.quote_node_id(update.quote.instrument_id)
        if not self._allow(node_id.as_str(), update.timestamp):
            return ()
        self.quote_source.add_quote(update.quote)
        self.calc_graph.add_node(node_id)
        self.calc_graph.update_node_value(node_id, update.quote, source=update.source or "market_data", mark_clean=True)
        dirty = self.calc_graph.mark_dependents_dirty(node_id)
        return self._updates((node_id, *dirty), UpdateSource.MARKET_DATA, update)

    def _handle_curve_input_update(self, update: CurveInputUpdate) -> tuple[NodeUpdate, ...]:
        input_node = self.curve_input_node_id(update.curve_inputs.curve_id)
        if not self._allow(input_node.as_str(), update.timestamp):
            return ()
        self.curve_source.add_curve_inputs(update.curve_inputs)
        self.calc_graph.add_node(input_node)
        self.calc_graph.update_node_value(input_node, update.curve_inputs, source=update.source or "market_data", mark_clean=True)
        dirty = list(self.calc_graph.mark_dependents_dirty(input_node))
        if self.curve_builder is not None:
            self.curve_builder.add_from_inputs(update.curve_inputs)
        return self._updates(tuple(dict.fromkeys((input_node, *dirty))), UpdateSource.MARKET_DATA, update)

    def _handle_curve_update(self, update: CurveUpdate) -> tuple[NodeUpdate, ...]:
        node_id = self.curve_node_id(update.curve_id)
        if not self._allow(node_id.as_str(), update.timestamp):
            return ()
        touched: list[NodeId] = []
        dirty: list[NodeId] = []
        if update.curve_inputs is not None:
            input_node = self.curve_input_node_id(update.curve_inputs.curve_id)
            self.curve_source.add_curve_inputs(update.curve_inputs)
            self.calc_graph.add_node(input_node)
            self.calc_graph.update_node_value(
                input_node,
                update.curve_inputs,
                source=update.source or "market_data",
                mark_clean=True,
            )
            dirty.extend(self.calc_graph.mark_dependents_dirty(input_node))
            touched.append(input_node)
            if self.curve_builder is not None:
                self.curve_builder.add_from_inputs(update.curve_inputs)
        self.calc_graph.add_node(node_id)
        self.calc_graph.update_node_value(node_id, update.curve, source=update.source or "market_data", mark_clean=True)
        dirty.extend(self.calc_graph.mark_dependents_dirty(node_id))
        touched.append(node_id)
        if self.curve_builder is not None and update.curve is not None:
            self.curve_builder.add_curve(update.curve_id, update.curve, curve_inputs=update.curve_inputs)
        return self._updates(tuple(dict.fromkeys((*touched, *dirty))), UpdateSource.MARKET_DATA, update)

    def _handle_fixing_update(self, update: IndexFixingUpdate) -> tuple[NodeUpdate, ...]:
        node_id = self.fixing_node_id(update.fixing.index_name, update.fixing.fixing_date)
        if not self._allow(node_id.as_str(), update.timestamp):
            return ()
        self.fixing_source.add_fixing(update.fixing)
        self.calc_graph.add_node(node_id)
        self.calc_graph.update_node_value(node_id, update.fixing, source=update.source or "market_data", mark_clean=True)
        dirty = self.calc_graph.mark_dependents_dirty(node_id)
        return self._updates((node_id, *dirty), UpdateSource.MARKET_DATA, update)

    def _handle_inflation_update(self, update: InflationFixingUpdate) -> tuple[NodeUpdate, ...]:
        node_id = self.inflation_node_id(update.fixing.index_name, update.fixing.observation_month)
        if not self._allow(node_id.as_str(), update.timestamp):
            return ()
        self.inflation_fixing_source.add_inflation_fixing(update.fixing)
        self.calc_graph.add_node(node_id)
        self.calc_graph.update_node_value(node_id, update.fixing, source=update.source or "market_data", mark_clean=True)
        dirty = self.calc_graph.mark_dependents_dirty(node_id)
        return self._updates((node_id, *dirty), UpdateSource.MARKET_DATA, update)

    def _handle_fx_update(self, update: FxRateUpdate) -> tuple[NodeUpdate, ...]:
        node_id = self.fx_node_id(update.fx_rate.currency_pair)
        if not self._allow(node_id.as_str(), update.timestamp):
            return ()
        self.fx_rate_source.add_fx_rate(update.fx_rate)
        self.calc_graph.add_node(node_id)
        self.calc_graph.update_node_value(node_id, update.fx_rate, source=update.source or "market_data", mark_clean=True)
        dirty = self.calc_graph.mark_dependents_dirty(node_id)
        return self._updates((node_id, *dirty), UpdateSource.MARKET_DATA, update)

    def _handle_vol_surface_update(self, update: VolSurfaceUpdate) -> tuple[NodeUpdate, ...]:
        node_id = self.vol_surface_node_id(update.surface.surface_id)
        if not self._allow(node_id.as_str(), update.timestamp):
            return ()
        self.volatility_source.add_surface(update.surface)
        self.calc_graph.add_node(node_id)
        self.calc_graph.update_node_value(node_id, update.surface, source=update.source or "market_data", mark_clean=True)
        dirty = self.calc_graph.mark_dependents_dirty(node_id)
        return self._updates((node_id, *dirty), UpdateSource.MARKET_DATA, update)

    def _updates(self, node_ids: tuple[NodeId, ...], source: UpdateSource, payload: object) -> tuple[NodeUpdate, ...]:
        return tuple(
            NodeUpdate(node_id=node_id, source=source, timestamp=getattr(payload, "timestamp", _now()), payload=payload)
            for node_id in node_ids
        )


__all__ = [
    "CurveInputUpdate",
    "CurveUpdate",
    "FxRateUpdate",
    "IndexFixingUpdate",
    "InflationFixingUpdate",
    "MarketDataListener",
    "MarketDataPublisher",
    "MarketDataUpdate",
    "QuoteUpdate",
    "VolSurfaceUpdate",
]
