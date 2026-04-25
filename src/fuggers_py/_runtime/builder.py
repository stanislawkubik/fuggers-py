"""Builder helpers for composing runtime orchestration components.

The pricing engine is the synchronous research-facing facade. The reactive
engine is the async runtime underneath it. The builder composes both from the
required providers and wires optional schedulers, storage, and output
publishers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fuggers_py._storage.storage import StorageAdapter
from fuggers_py._core.types import Date
from fuggers_py._runtime.sources import MarketDataProvider
from fuggers_py.bonds.reference_data import ReferenceDataProvider

from .calc_graph import CalculationGraph
from .config import EngineConfig
from .errors import EngineConfigurationError
from .market_data_listener import MarketDataPublisher
from .output import OutputPublisher
from .pricing_router import PricingRouter
from .reactive import ReactiveEngine
from .scheduler import EodScheduler, IntervalScheduler

if TYPE_CHECKING:
    from fuggers_py.portfolio.analytics.quote_outputs import PortfolioAnalyzer
    from fuggers_py.portfolio.etf.pricing import EtfPricer


def _default_etf_pricer() -> EtfPricer:
    from fuggers_py.portfolio.etf.pricing import EtfPricer

    return EtfPricer()


def _default_portfolio_analyzer() -> PortfolioAnalyzer:
    from fuggers_py.portfolio.analytics.quote_outputs import PortfolioAnalyzer

    return PortfolioAnalyzer()


@dataclass(slots=True)
class PricingEngine:
    """Synchronous facade that owns the reactive runtime and shared services.

    The facade is the stable entry point for research code. It holds the shared
    config, market-data and reference-data providers, the calculation graph, the
    router, and the optional reactive runtime.
    """

    config: EngineConfig
    market_data_provider: MarketDataProvider
    reference_data_provider: ReferenceDataProvider
    storage_adapter: StorageAdapter = field(default_factory=StorageAdapter)
    output_publisher: OutputPublisher = field(default_factory=OutputPublisher)
    settlement_date: Date | None = None
    calc_graph: CalculationGraph = field(default_factory=CalculationGraph)
    pricing_router: PricingRouter = field(default_factory=PricingRouter)
    etf_pricer: EtfPricer = field(default_factory=_default_etf_pricer)
    portfolio_analyzer: PortfolioAnalyzer = field(default_factory=_default_portfolio_analyzer)
    reactive_engine: ReactiveEngine | None = None

    async def start(self) -> None:
        """Start the underlying reactive runtime if one is attached."""
        if self.reactive_engine is not None:
            await self.reactive_engine.start()

    async def stop(self) -> None:
        """Stop the underlying reactive runtime if one is attached."""
        if self.reactive_engine is not None:
            await self.reactive_engine.stop()

    @classmethod
    def create(
        cls,
        *,
        engine_config: EngineConfig,
        market_data_provider: MarketDataProvider,
        reference_data_provider: ReferenceDataProvider,
        storage_adapter: StorageAdapter | None = None,
        output_publisher: OutputPublisher | None = None,
        settlement_date: Date | None = None,
    ) -> "PricingEngine":
        """Build a pricing engine with the default builder configuration.

        The helper is a convenience wrapper around :class:`PricingEngineBuilder`
        for callers that want the default wiring without using the fluent API.
        """
        return (
            PricingEngineBuilder()
            .with_engine_config(engine_config)
            .with_market_data_provider(market_data_provider)
            .with_reference_data_provider(reference_data_provider)
            .with_storage_adapter(storage_adapter or StorageAdapter())
            .with_output_publisher(output_publisher or OutputPublisher())
            .with_settlement_date(settlement_date)
            .build()
        )


@dataclass(slots=True)
class PricingEngineBuilder:
    """Fluent builder for the pricing-engine and reactive-engine pair.

    The builder keeps construction explicit: required providers must be set
    before build, and optional schedulers and storage/publisher dependencies
    can be layered in before the reactive engine is created.
    """

    engine_config: EngineConfig | None = None
    market_data_provider: MarketDataProvider | None = None
    reference_data_provider: ReferenceDataProvider | None = None
    storage_adapter: StorageAdapter = field(default_factory=StorageAdapter)
    output_publisher: OutputPublisher = field(default_factory=OutputPublisher)
    settlement_date: Date | None = None
    calc_graph: CalculationGraph | None = None
    pricing_router: PricingRouter | None = None
    etf_pricer: EtfPricer | None = None
    portfolio_analyzer: PortfolioAnalyzer | None = None
    market_data_publisher: MarketDataPublisher | None = None
    schedulers: list[object] = field(default_factory=list)

    @classmethod
    def new(cls) -> "PricingEngineBuilder":
        """Return a fresh builder instance."""
        return cls()

    def with_engine_config(self, config: EngineConfig) -> "PricingEngineBuilder":
        """Set the top-level engine configuration."""
        self.engine_config = config
        return self

    def with_market_data_provider(self, provider: MarketDataProvider) -> "PricingEngineBuilder":
        """Set the required market-data provider."""
        self.market_data_provider = provider
        return self

    def with_reference_data_provider(self, provider: ReferenceDataProvider) -> "PricingEngineBuilder":
        """Set the required reference-data provider."""
        self.reference_data_provider = provider
        return self

    def with_storage_adapter(self, adapter: StorageAdapter) -> "PricingEngineBuilder":
        """Set the storage adapter used by the reactive runtime."""
        self.storage_adapter = adapter
        return self

    def with_output_publisher(self, publisher: OutputPublisher) -> "PricingEngineBuilder":
        """Set the output publisher used by the reactive runtime."""
        self.output_publisher = publisher
        return self

    def with_settlement_date(self, settlement_date: Date | None) -> "PricingEngineBuilder":
        """Set the default settlement date used by built engines."""
        self.settlement_date = settlement_date
        return self

    def with_scheduler(self, scheduler: object) -> "PricingEngineBuilder":
        """Attach a scheduler object to the reactive engine."""
        self.schedulers.append(scheduler)
        return self

    def with_default_interval_scheduler(self, node_ids, *, interval_seconds: float, immediate: bool = False) -> "PricingEngineBuilder":
        """Attach an interval scheduler using the built-in scheduler type."""
        self.schedulers.append(IntervalScheduler(node_ids, interval_seconds=interval_seconds, immediate=immediate))
        return self

    def with_default_eod_scheduler(self, node_ids, *, run_time=None) -> "PricingEngineBuilder":
        """Attach an EOD scheduler using the built-in scheduler type."""
        self.schedulers.append(EodScheduler(node_ids, run_time=run_time))
        return self

    def validate(self) -> None:
        """Check that the builder has the required provider dependencies."""
        if self.market_data_provider is None:
            raise EngineConfigurationError("PricingEngineBuilder requires a market_data_provider.")
        if self.reference_data_provider is None:
            raise EngineConfigurationError("PricingEngineBuilder requires a reference_data_provider.")

    def build(self) -> PricingEngine:
        """Build the synchronous pricing engine and its reactive runtime.

        Missing market-data or reference-data providers fail fast through
        :class:`EngineConfigurationError`.
        """
        self.validate()
        assert self.market_data_provider is not None
        assert self.reference_data_provider is not None
        config = self.engine_config or EngineConfig(engine_name="pricing-engine", as_of=self.settlement_date)
        calc_graph = self.calc_graph or CalculationGraph()
        pricing_router = self.pricing_router or PricingRouter()
        etf_pricer = self.etf_pricer or _default_etf_pricer()
        portfolio_analyzer = self.portfolio_analyzer or _default_portfolio_analyzer()
        market_data_publisher = self.market_data_publisher or MarketDataPublisher()

        reactive_engine = ReactiveEngine(
            calc_graph=calc_graph,
            pricing_router=pricing_router,
            market_data_provider=self.market_data_provider,
            reference_data_provider=self.reference_data_provider,
            storage_adapter=self.storage_adapter,
            output_publisher=self.output_publisher,
            market_data_publisher=market_data_publisher,
            schedulers=tuple(self.schedulers),
            settlement_date=self.settlement_date or config.as_of or Date.today(),
        )

        return PricingEngine(
            config=config,
            market_data_provider=self.market_data_provider,
            reference_data_provider=self.reference_data_provider,
            storage_adapter=self.storage_adapter,
            output_publisher=self.output_publisher,
            settlement_date=self.settlement_date or config.as_of,
            calc_graph=calc_graph,
            pricing_router=pricing_router,
            etf_pricer=etf_pricer,
            portfolio_analyzer=portfolio_analyzer,
            reactive_engine=reactive_engine,
        )

    def build_reactive(self) -> ReactiveEngine:
        """Build and return just the reactive runtime."""
        engine = self.build()
        assert engine.reactive_engine is not None
        return engine.reactive_engine


ReactiveEngineBuilder = PricingEngineBuilder


__all__ = ["PricingEngine", "PricingEngineBuilder", "ReactiveEngineBuilder"]
