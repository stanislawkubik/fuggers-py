"""Public calc-layer surface for orchestration, routing, and output records.

This package exports the synchronous pricing facade, the reactive runtime
components underneath it, the routing/specification helpers, the graph and
scheduler primitives, and the typed output records used by the engine.

The main public groups are:

- pricing inputs and routing helpers such as ``PricingSpec`` and
  ``PricingRouter``
- typed outputs such as ``BondQuoteOutput`` and ``PortfolioAnalyticsOutput``
- engine assembly/runtime helpers such as ``PricingEngineBuilder`` and
  ``ReactiveEngine``
- scheduling and coordination primitives used by the calc runtime
"""

from __future__ import annotations

from importlib import import_module


_MODULE_EXPORTS = {
    "AlertPublisher": "fuggers_py._calc.output",
    "AnalyticsOutput": "fuggers_py._calc.output",
    "AnalyticsPublisher": "fuggers_py._calc.output",
    "BatchPricingResult": "fuggers_py._calc.pricing_router",
    "BasisSwapQuoteOutput": "fuggers_py._calc.output",
    "BenchmarkReference": "fuggers_py._calc.pricing_specs",
    "BidAskSpreadConfig": "fuggers_py._calc.pricing_specs",
    "BondQuoteOutput": "fuggers_py._calc.output",
    "CalculationGraph": "fuggers_py._calc.calc_graph",
    "CdsQuoteOutput": "fuggers_py._calc.output",
    "CronScheduler": "fuggers_py._calc.scheduler",
    "EngineConfig": "fuggers_py._calc.config",
    "EngineConfigurationError": "fuggers_py._calc.errors",
    "EngineError": "fuggers_py._calc.errors",
    "EodScheduler": "fuggers_py._calc.scheduler",
    "EtfAnalyticsOutput": "fuggers_py._calc.output",
    "EtfPublisher": "fuggers_py._calc.output",
    "FutureQuoteOutput": "fuggers_py._calc.output",
    "FxRateUpdate": "fuggers_py._calc.market_data_listener",
    "InMemoryLeaderElection": "fuggers_py._calc.coordination",
    "InMemoryPartitionRegistry": "fuggers_py._calc.coordination",
    "InMemoryServiceRegistry": "fuggers_py._calc.coordination",
    "IndexFixingUpdate": "fuggers_py._calc.market_data_listener",
    "InflationFixingUpdate": "fuggers_py._calc.market_data_listener",
    "IntervalScheduler": "fuggers_py._calc.scheduler",
    "LeaderElection": "fuggers_py._calc.coordination",
    "MarketDataListener": "fuggers_py._calc.market_data_listener",
    "MarketDataPublisher": "fuggers_py._calc.market_data_listener",
    "MarketDataUpdate": "fuggers_py._calc.market_data_listener",
    "NodeConfig": "fuggers_py._calc.config",
    "NodeId": "fuggers_py._calc.calc_graph",
    "NodeUpdate": "fuggers_py._calc.scheduler",
    "NodeValue": "fuggers_py._calc.calc_graph",
    "OutputPublisher": "fuggers_py._calc.output",
    "PartitionAssignment": "fuggers_py._calc.coordination",
    "PartitionRegistry": "fuggers_py._calc.coordination",
    "PortfolioAnalyticsOutput": "fuggers_py._calc.output",
    "PricingEngine": "fuggers_py._calc.builder",
    "PricingEngineBuilder": "fuggers_py._calc.builder",
    "PricingFailure": "fuggers_py._calc.pricing_router",
    "PricingInput": "fuggers_py._calc.pricing_router",
    "PricingRouter": "fuggers_py._calc.pricing_router",
    "PricingSpec": "fuggers_py._calc.pricing_specs",
    "QuotePublisher": "fuggers_py._calc.output",
    "QuoteSide": "fuggers_py._market.state",
    "QuoteUpdate": "fuggers_py._calc.market_data_listener",
    "ReactiveEngine": "fuggers_py._calc.reactive",
    "ReactiveEngineBuilder": "fuggers_py._calc.builder",
    "RepoPricingResult": "fuggers_py._calc.output",
    "RoutedFraPricingResult": "fuggers_py._calc.output",
    "RoutingError": "fuggers_py._calc.errors",
    "RvSignalOutput": "fuggers_py._calc.output",
    "SchedulerError": "fuggers_py._calc.errors",
    "ServiceRegistration": "fuggers_py._calc.coordination",
    "ServiceRegistry": "fuggers_py._calc.coordination",
    "ShardAssignment": "fuggers_py._calc.calc_graph",
    "ShardConfig": "fuggers_py._calc.calc_graph",
    "ShardStrategy": "fuggers_py._calc.calc_graph",
    "SwapQuoteOutput": "fuggers_py._calc.output",
    "ThrottleManager": "fuggers_py._calc.scheduler",
    "UpdateFrequency": "fuggers_py._calc.config",
    "UpdateSource": "fuggers_py._calc.scheduler",
    "VolSurfaceUpdate": "fuggers_py._calc.market_data_listener",
}

__all__ = list(_MODULE_EXPORTS)


def __getattr__(name: str) -> object:
    module_name = _MODULE_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    return getattr(module, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
