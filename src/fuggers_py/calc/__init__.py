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
    "AlertPublisher": "fuggers_py.calc.output",
    "AnalyticsCurves": "fuggers_py.market.state",
    "AnalyticsOutput": "fuggers_py.calc.output",
    "AnalyticsPublisher": "fuggers_py.calc.output",
    "BatchPricingResult": "fuggers_py.calc.pricing_router",
    "BasisSwapQuoteOutput": "fuggers_py.calc.output",
    "BenchmarkReference": "fuggers_py.calc.pricing_specs",
    "BidAskSpreadConfig": "fuggers_py.calc.pricing_specs",
    "BondQuoteOutput": "fuggers_py.calc.output",
    "BuiltCurve": "fuggers_py.calc.curve_builder",
    "CalculationGraph": "fuggers_py.calc.calc_graph",
    "CdsQuoteOutput": "fuggers_py.calc.output",
    "CronScheduler": "fuggers_py.calc.scheduler",
    "CurveBuilder": "fuggers_py.calc.curve_builder",
    "CurveInputUpdate": "fuggers_py.calc.market_data_listener",
    "CurveNotFoundError": "fuggers_py.calc.errors",
    "CurvePublisher": "fuggers_py.calc.output",
    "CurveUpdate": "fuggers_py.calc.market_data_listener",
    "EngineConfig": "fuggers_py.calc.config",
    "EngineConfigurationError": "fuggers_py.calc.errors",
    "EngineError": "fuggers_py.calc.errors",
    "EodScheduler": "fuggers_py.calc.scheduler",
    "EtfAnalyticsOutput": "fuggers_py.calc.output",
    "EtfPublisher": "fuggers_py.calc.output",
    "FundingPricingRouter": "fuggers_py.calc.funding_pricing_router",
    "FutureQuoteOutput": "fuggers_py.calc.output",
    "FxRateUpdate": "fuggers_py.calc.market_data_listener",
    "InMemoryLeaderElection": "fuggers_py.calc.coordination",
    "InMemoryPartitionRegistry": "fuggers_py.calc.coordination",
    "InMemoryServiceRegistry": "fuggers_py.calc.coordination",
    "IndexFixingUpdate": "fuggers_py.calc.market_data_listener",
    "InflationFixingUpdate": "fuggers_py.calc.market_data_listener",
    "IntervalScheduler": "fuggers_py.calc.scheduler",
    "LeaderElection": "fuggers_py.calc.coordination",
    "MarketDataListener": "fuggers_py.calc.market_data_listener",
    "MarketDataPublisher": "fuggers_py.calc.market_data_listener",
    "MarketDataUpdate": "fuggers_py.calc.market_data_listener",
    "NodeConfig": "fuggers_py.calc.config",
    "NodeId": "fuggers_py.calc.calc_graph",
    "NodeUpdate": "fuggers_py.calc.scheduler",
    "NodeValue": "fuggers_py.calc.calc_graph",
    "OutputPublisher": "fuggers_py.calc.output",
    "PartitionAssignment": "fuggers_py.calc.coordination",
    "PartitionRegistry": "fuggers_py.calc.coordination",
    "PortfolioAnalyticsOutput": "fuggers_py.calc.output",
    "PricingEngine": "fuggers_py.calc.builder",
    "PricingEngineBuilder": "fuggers_py.calc.builder",
    "PricingFailure": "fuggers_py.calc.pricing_router",
    "PricingInput": "fuggers_py.calc.pricing_router",
    "PricingRouter": "fuggers_py.calc.pricing_router",
    "PricingSpec": "fuggers_py.calc.pricing_specs",
    "QuotePublisher": "fuggers_py.calc.output",
    "QuoteSide": "fuggers_py.market.state",
    "QuoteUpdate": "fuggers_py.calc.market_data_listener",
    "ReactiveEngine": "fuggers_py.calc.reactive",
    "ReactiveEngineBuilder": "fuggers_py.calc.builder",
    "RatesPricingRouter": "fuggers_py.calc.rates_pricing_router",
    "RepoPricingResult": "fuggers_py.calc.output",
    "RoutedFraPricingResult": "fuggers_py.calc.output",
    "RoutingError": "fuggers_py.calc.errors",
    "RvSignalOutput": "fuggers_py.calc.output",
    "SchedulerError": "fuggers_py.calc.errors",
    "ServiceRegistration": "fuggers_py.calc.coordination",
    "ServiceRegistry": "fuggers_py.calc.coordination",
    "ShardAssignment": "fuggers_py.calc.calc_graph",
    "ShardConfig": "fuggers_py.calc.calc_graph",
    "ShardStrategy": "fuggers_py.calc.calc_graph",
    "SwapQuoteOutput": "fuggers_py.calc.output",
    "ThrottleManager": "fuggers_py.calc.scheduler",
    "UpdateFrequency": "fuggers_py.calc.config",
    "UpdateSource": "fuggers_py.calc.scheduler",
    "VolSurfaceUpdate": "fuggers_py.calc.market_data_listener",
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
