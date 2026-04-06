"""Reactive engine helpers that coexist with the existing sync APIs.

The reactive engine is the async runtime behind the synchronous pricing-engine
facade. It consumes market-data and scheduler events, marks graph nodes dirty,
re-evaluates registered pricing nodes, and publishes resulting outputs. The
implementation keeps its own overlay market-data sources so updates can be
merged with the caller's providers instead of replacing them.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from fuggers_py.adapters.storage import StorageAdapter
from fuggers_py.core.types import Date
from fuggers_py.calc import AnalyticsCurves, OutputPublisher
from fuggers_py.core import CurveId, InstrumentId
from fuggers_py.market.sources import (
    FixingSource,
    InMemoryCurveSource,
    InMemoryFixingSource,
    InMemoryQuoteSource,
    MarketDataProvider,
    QuoteSource,
)
from fuggers_py.reference import BondReferenceData, ReferenceDataProvider

from .curve_builder import CurveBuilder
from .calc_graph import CalculationGraph, NodeId
from .market_data_listener import MarketDataListener, MarketDataPublisher, MarketDataUpdate
from .pricing_router import PricingFailure, PricingInput, PricingRouter
from .scheduler import NodeUpdate, UpdateSource


def _as_analytics_curves(curve_builder: CurveBuilder, curve_roles: dict[str, CurveId | str]) -> AnalyticsCurves | None:
    if not curve_roles:
        return None
    return AnalyticsCurves(
        discount_curve=None if "discount" not in curve_roles else curve_builder.get(curve_roles["discount"]),
        forward_curve=None if "forward" not in curve_roles else curve_builder.get(curve_roles["forward"]),
        government_curve=None if "government" not in curve_roles else curve_builder.get(curve_roles["government"]),
        benchmark_curve=None if "benchmark" not in curve_roles else curve_builder.get(curve_roles["benchmark"]),
        credit_curve=None if "credit" not in curve_roles else curve_builder.get(curve_roles["credit"]),
    )


@dataclass(slots=True)
class _OverlayMarketDataProvider:
    """Overlay market-data provider that prefers in-memory updates over base data.

    The overlay lets the reactive engine merge fresh in-memory updates with the
    caller's provider instead of replacing it outright.
    """
    base_provider: MarketDataProvider | QuoteSource | FixingSource | None = None
    quote_source: InMemoryQuoteSource = field(default_factory=InMemoryQuoteSource)
    curve_input_source: InMemoryCurveSource = field(default_factory=InMemoryCurveSource)
    fixing_source: InMemoryFixingSource = field(default_factory=InMemoryFixingSource)

    def get_quote(self, instrument_id: InstrumentId | str, side) -> object | None:
        quote = self.quote_source.get_quote(instrument_id, side)
        if quote is not None:
            return quote
        if self.base_provider is not None and hasattr(self.base_provider, "get_quote"):
            return getattr(self.base_provider, "get_quote")(instrument_id, side)
        return None

    def get_curve_inputs(self, curve_id: CurveId | str):
        curve_inputs = self.curve_input_source.get_curve_inputs(curve_id)
        if curve_inputs is not None:
            return curve_inputs
        if self.base_provider is not None and hasattr(self.base_provider, "get_curve_inputs"):
            return getattr(self.base_provider, "get_curve_inputs")(curve_id)
        return None

    def get_fixing(self, index_name: str, fixing_date: Date):
        fixing = self.fixing_source.get_fixing(index_name, fixing_date)
        if fixing is not None:
            return fixing
        if self.base_provider is not None and hasattr(self.base_provider, "get_fixing"):
            return getattr(self.base_provider, "get_fixing")(index_name, fixing_date)
        return None

    def to_fixing_store(self):
        if self.fixing_source.fixings:
            return self.fixing_source.to_fixing_store()
        if self.base_provider is not None and hasattr(self.base_provider, "to_fixing_store"):
            return getattr(self.base_provider, "to_fixing_store")()
        return None


@dataclass(slots=True)
class _ReferenceDataCache:
    """Small in-memory reference-data cache layered over an optional provider."""
    base_provider: ReferenceDataProvider | None = None
    cache: dict[InstrumentId, BondReferenceData] = field(default_factory=dict)

    def put(self, reference_data: BondReferenceData) -> None:
        self.cache[reference_data.instrument_id] = reference_data

    def get(self, instrument_id: InstrumentId | str) -> BondReferenceData | None:
        resolved = InstrumentId.parse(instrument_id)
        cached = self.cache.get(resolved)
        if cached is not None:
            return cached
        if self.base_provider is not None:
            reference_data = self.base_provider.get_bond_reference(resolved)
            if reference_data is not None:
                self.cache[resolved] = reference_data
            return reference_data
        return None

    def as_mapping(self) -> dict[InstrumentId, BondReferenceData]:
        return dict(self.cache)


@dataclass(slots=True)
class ReactiveEngine:
    """Async runtime for graph-driven pricing and market-data processing.

    The engine connects the calc graph, listener, curve builder, pricing router,
    storage adapter, and output publishers. It listens for market-data and
    scheduler events, resolves pricing inputs, and publishes any resulting
    updates.
    """

    calc_graph: CalculationGraph
    curve_builder: CurveBuilder
    pricing_router: PricingRouter
    market_data_provider: MarketDataProvider | QuoteSource | FixingSource | None
    reference_data_provider: ReferenceDataProvider | None
    storage_adapter: StorageAdapter = field(default_factory=StorageAdapter)
    output_publisher: OutputPublisher = field(default_factory=OutputPublisher)
    market_data_publisher: MarketDataPublisher = field(default_factory=MarketDataPublisher)
    schedulers: tuple[object, ...] = ()
    settlement_date: Date = field(default_factory=Date.today)
    listener: MarketDataListener = field(init=False)
    _overlay_market_data: _OverlayMarketDataProvider = field(init=False, repr=False)
    _reference_cache: _ReferenceDataCache = field(init=False, repr=False)
    _incoming_queue: asyncio.Queue | None = field(init=False, default=None, repr=False)
    _relay_tasks: list[asyncio.Task] = field(init=False, default_factory=list, repr=False)
    _subscriptions: list[tuple[object, asyncio.Queue]] = field(init=False, default_factory=list, repr=False)
    _subscribers: set[asyncio.Queue] = field(init=False, default_factory=set, repr=False)
    _pricing_nodes: dict[NodeId, PricingInput] = field(init=False, default_factory=dict, repr=False)
    _running: bool = field(init=False, default=False, repr=False)

    def __post_init__(self) -> None:
        """Wire the market-data overlay and the market-data listener."""
        self._overlay_market_data = _OverlayMarketDataProvider(base_provider=self.market_data_provider)
        self._reference_cache = _ReferenceDataCache(base_provider=self.reference_data_provider)
        self.listener = MarketDataListener(
            calc_graph=self.calc_graph,
            curve_builder=self.curve_builder,
            quote_source=self._overlay_market_data.quote_source,
            curve_source=self._overlay_market_data.curve_input_source,
            fixing_source=self._overlay_market_data.fixing_source,
        )
        self._incoming_queue: asyncio.Queue | None = None
        self._relay_tasks = []
        self._subscriptions = []
        self._subscribers = set()
        self._pricing_nodes = {}
        self._running = False

    def cache_reference_data(self, reference_data: BondReferenceData) -> None:
        """Cache bond reference data for later pricing-node evaluation."""
        self._reference_cache.put(reference_data)

    def subscribe_updates(self) -> asyncio.Queue:
        """Return a queue that receives all published node updates."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe_updates(self, queue: asyncio.Queue) -> None:
        """Remove a previously subscribed update queue."""
        self._subscribers.discard(queue)

    async def publish_market_data_update(self, update: MarketDataUpdate) -> None:
        """Publish a market-data update through the shared fanout path."""
        await self.market_data_publisher.publish(update)

    def register_pricing_node(
        self,
        node_id: NodeId | str,
        pricing_input: PricingInput,
        *,
        dependencies: tuple[NodeId | str, ...] = (),
    ) -> NodeId:
        """Register a pricing node and its graph dependencies."""
        resolved = self.calc_graph.add_node(node_id)
        self._pricing_nodes[resolved] = pricing_input
        for dependency in self._infer_dependencies(pricing_input):
            self.calc_graph.add_dependency(resolved, dependency)
        for dependency in dependencies:
            self.calc_graph.add_dependency(resolved, dependency)
        return resolved

    async def start(self) -> None:
        """Start relays and scheduler tasks for the reactive runtime."""
        if self._running:
            return
        self._running = True
        self._incoming_queue = asyncio.Queue()
        market_queue = self.market_data_publisher.subscribe()
        self._subscriptions.append((self.market_data_publisher, market_queue))
        self._relay_tasks.append(asyncio.create_task(self._relay(market_queue), name="ReactiveEngine.market_data"))
        for scheduler in self.schedulers:
            if hasattr(scheduler, "subscribe"):
                queue = scheduler.subscribe()
                self._subscriptions.append((scheduler, queue))
                self._relay_tasks.append(
                    asyncio.create_task(self._relay(queue), name=f"ReactiveEngine.{type(scheduler).__name__}")
                )
            if hasattr(scheduler, "start"):
                await scheduler.start()

    async def stop(self) -> None:
        """Stop relays, schedulers, and subscriptions for the reactive runtime."""
        if not self._running:
            return
        self._running = False
        for scheduler in self.schedulers:
            if hasattr(scheduler, "stop"):
                await scheduler.stop()
        for task in self._relay_tasks:
            task.cancel()
        for task in self._relay_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._relay_tasks.clear()
        for publisher, queue in self._subscriptions:
            if hasattr(publisher, "unsubscribe"):
                publisher.unsubscribe(queue)
        self._subscriptions.clear()
        self._incoming_queue = None

    async def process_once(self, *, timeout: float | None = None) -> tuple[NodeUpdate, ...]:
        """Process one incoming event and evaluate any newly dirty pricing nodes.

        Pricing failures are isolated into :class:`PricingFailure` payloads so a
        single bad node does not abort processing of the rest of the batch. Any
        updates produced while processing the event are fanned out to external
        subscribers before the method returns.
        """
        if self._incoming_queue is None:
            raise RuntimeError("ReactiveEngine.start() must be called before processing updates.")
        if timeout is None:
            event = await self._incoming_queue.get()
        else:
            event = await asyncio.wait_for(self._incoming_queue.get(), timeout=timeout)
        if isinstance(event, NodeUpdate):
            updates = list(await self.listener.handle_scheduler_update(event))
        else:
            updates = list(await self.listener.handle_update(event))
        updates.extend(await self._evaluate_dirty_pricing_nodes())
        for update in updates:
            for queue in tuple(self._subscribers):
                await queue.put(update)
        return tuple(updates)

    async def drain_once(self, *, timeout: float | None = None) -> tuple[NodeUpdate, ...]:
        """Alias for :meth:`process_once` used by the test surface."""
        return await self.process_once(timeout=timeout)

    async def _relay(self, queue: asyncio.Queue) -> None:
        incoming_queue = self._incoming_queue
        if incoming_queue is None:
            return
        while True:
            item = await queue.get()
            await incoming_queue.put(item)

    async def _evaluate_dirty_pricing_nodes(self) -> list[NodeUpdate]:
        updates: list[NodeUpdate] = []
        for node_id in self.calc_graph.query_dirty():
            pricing_input = self._pricing_nodes.get(node_id)
            if pricing_input is None:
                continue
            output, failure = self._price_input(pricing_input)
            if failure is not None:
                self.calc_graph.update_node_value(node_id, failure, source="pricing_failure", mark_clean=True)
                updates.append(NodeUpdate(node_id=node_id, source=UpdateSource.GRAPH, payload=failure))
                continue
            assert output is not None
            self.calc_graph.update_node_value(node_id, output, source="pricing", mark_clean=True)
            self.output_publisher.publish_quote(output)
            self.output_publisher.publish_analytics(output)
            updates.append(NodeUpdate(node_id=node_id, source=UpdateSource.GRAPH, payload=output))
        return updates

    def _price_input(self, pricing_input: PricingInput) -> tuple[object | None, PricingFailure | None]:
        resolved = self._resolve_pricing_input(pricing_input)
        try:
            output = self.pricing_router.price(
                resolved.instrument,
                resolved.settlement_date,
                market_price=resolved.market_price,
                pricing_spec=resolved.pricing_spec,
                curves=resolved.curves,
                market_data=resolved.market_data,
                reference_data=resolved.reference_data,
                instrument_id=resolved.instrument_id,
            )
            return output, None
        except Exception as exc:
            return None, PricingFailure(
                key=resolved.key(0),
                error_type=type(exc).__name__,
                message=str(exc),
            )

    def _resolve_pricing_input(self, pricing_input: PricingInput) -> PricingInput:
        curves = pricing_input.curves or _as_analytics_curves(self.curve_builder, pricing_input.curve_roles)
        reference_data = pricing_input.reference_data
        instrument_id = pricing_input.resolved_instrument_id()
        if reference_data is None and instrument_id is not None:
            cached = self._reference_cache.get(instrument_id)
            if cached is not None:
                reference_data = {instrument_id: cached}
        market_data = pricing_input.market_data or self._overlay_market_data
        return PricingInput(
            instrument=pricing_input.instrument,
            settlement_date=pricing_input.settlement_date,
            market_price=pricing_input.market_price,
            pricing_spec=pricing_input.pricing_spec,
            curves=curves,
            curve_roles=dict(pricing_input.curve_roles),
            market_data=market_data,
            reference_data=reference_data,
            instrument_id=pricing_input.instrument_id,
        )

    def _infer_dependencies(self, pricing_input: PricingInput) -> tuple[NodeId, ...]:
        dependencies: list[NodeId] = []
        instrument_id = pricing_input.resolved_instrument_id()
        if instrument_id is not None:
            dependencies.append(MarketDataListener.quote_node_id(instrument_id))
        for role_curve in pricing_input.curve_roles.values():
            dependencies.append(MarketDataListener.curve_node_id(role_curve))
        return tuple(dict.fromkeys(dependencies))


__all__ = ["ReactiveEngine"]
