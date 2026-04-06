from __future__ import annotations

from typing import TYPE_CHECKING, assert_type, cast

from fuggers_py.adapters import (
    PortfolioFilter,
    PortfolioStore,
    StoredPortfolio,
    StoredPosition,
)
from fuggers_py.adapters.storage import PortfolioFilter as AdapterPortfolioFilter
from fuggers_py.adapters.storage import StoredPortfolio as AdapterStoredPortfolio
from fuggers_py.adapters.storage import StoredPosition as AdapterStoredPosition
from fuggers_py.calc import ReactiveEngineBuilder
from fuggers_py.core import FuggersError
from fuggers_py.market.curves import Compounding
from fuggers_py.math import BisectionSolver, MathResult, RootFinder
from fuggers_py.portfolio import (
    ActiveWeights,
    AggregatedAttribution,
    AttributionInput,
    BasketAnalysis,
    BasketComponent,
    BasketFlowSummary,
    BucketContribution,
    ClassifierDistribution,
    CreationBasket,
    CustomDistribution,
    DistributionYield,
    EtfNavMetrics,
    EtfPricer,
    ExpenseMetrics,
    KeyRateProfile,
    MaturityDistribution,
    MigrationRisk,
    NavBreakdown,
    Portfolio,
    PortfolioAnalyzer,
    PortfolioPosition,
    Position,
    PremiumDiscountPoint,
    RatingDistribution,
    RiskMetrics,
    SectorAttribution,
    SectorDistribution,
    SecYield,
    SecYieldInput,
    SpreadContributions,
    StressSummary,
)
from fuggers_py.reference import Tenor

if TYPE_CHECKING:
    from fuggers_py.adapters.storage import (
        PortfolioFilter as PortfolioFilterType,
    )
    from fuggers_py.adapters.storage import PortfolioStore as PortfolioStoreType
    from fuggers_py.adapters.storage import StoredPortfolio as StoredPortfolioType
    from fuggers_py.adapters.storage import StoredPosition as StoredPositionType
    from fuggers_py.calc.builder import (
        ReactiveEngineBuilder as ReactiveEngineBuilderType,
    )
    from fuggers_py.reference.bonds.types import Tenor as TenorType

core_error = FuggersError("boom")
assert_type(core_error, FuggersError)

solver = BisectionSolver()
assert_type(solver, BisectionSolver)

root_finder: RootFinder = solver
math_result = root_finder.find_root(lambda x: x * x - 2.0, 1.0, 2.0)
assert_type(math_result, MathResult)

builder = cast("type[ReactiveEngineBuilderType]", ReactiveEngineBuilder).new()
assert_type(builder, ReactiveEngineBuilderType)

portfolio_type = Portfolio
assert_type(portfolio_type, type[Portfolio])

position_type = Position
assert_type(position_type, type[Position])

active_weights_type = ActiveWeights
assert_type(active_weights_type, type[ActiveWeights])

aggregated_attribution_type = AggregatedAttribution
assert_type(aggregated_attribution_type, type[AggregatedAttribution])

attribution_input_type = AttributionInput
assert_type(attribution_input_type, type[AttributionInput])

bucket_contribution_type = BucketContribution
assert_type(bucket_contribution_type, type[BucketContribution])

risk_metrics_type = RiskMetrics
assert_type(risk_metrics_type, type[RiskMetrics])

migration_risk_type = MigrationRisk
assert_type(migration_risk_type, type[MigrationRisk])

sec_yield_type = SecYield
assert_type(sec_yield_type, type[SecYield])

sec_yield_input_type = SecYieldInput
assert_type(sec_yield_input_type, type[SecYieldInput])

basket_analysis_type = BasketAnalysis
assert_type(basket_analysis_type, type[BasketAnalysis])

basket_component_type = BasketComponent
assert_type(basket_component_type, type[BasketComponent])

basket_flow_summary_type = BasketFlowSummary
assert_type(basket_flow_summary_type, type[BasketFlowSummary])

creation_basket_type = CreationBasket
assert_type(creation_basket_type, type[CreationBasket])

expense_metrics_type = ExpenseMetrics
assert_type(expense_metrics_type, type[ExpenseMetrics])

etf_nav_metrics_type = EtfNavMetrics
assert_type(etf_nav_metrics_type, type[EtfNavMetrics])

premium_discount_point_type = PremiumDiscountPoint
assert_type(premium_discount_point_type, type[PremiumDiscountPoint])

stress_summary_type = StressSummary
assert_type(stress_summary_type, type[StressSummary])

key_rate_profile_type = KeyRateProfile
assert_type(key_rate_profile_type, type[KeyRateProfile])

nav_breakdown_type = NavBreakdown
assert_type(nav_breakdown_type, type[NavBreakdown])

custom_distribution_type = CustomDistribution
assert_type(custom_distribution_type, type[CustomDistribution])

classifier_distribution_type = ClassifierDistribution
assert_type(classifier_distribution_type, type[ClassifierDistribution])

maturity_distribution_type = MaturityDistribution
assert_type(maturity_distribution_type, type[MaturityDistribution])

rating_distribution_type = RatingDistribution
assert_type(rating_distribution_type, type[RatingDistribution])

sector_distribution_type = SectorDistribution
assert_type(sector_distribution_type, type[SectorDistribution])

sector_attribution_type = SectorAttribution
assert_type(sector_attribution_type, type[SectorAttribution])

spread_contributions_type = SpreadContributions
assert_type(spread_contributions_type, type[SpreadContributions])

distribution_yield_type = DistributionYield
assert_type(distribution_yield_type, type[DistributionYield])

curve_compounding_type = Compounding
assert_type(curve_compounding_type, type[Compounding])

traits_tenor_type = cast("type[TenorType]", Tenor)
assert_type(traits_tenor_type, type[TenorType])

stored_position_type = cast("type[StoredPositionType]", StoredPosition)
assert_type(stored_position_type, type[StoredPositionType])

stored_portfolio_type = cast("type[StoredPortfolioType]", StoredPortfolio)
assert_type(stored_portfolio_type, type[StoredPortfolioType])

portfolio_filter_type = cast("type[PortfolioFilterType]", PortfolioFilter)
assert_type(portfolio_filter_type, type[PortfolioFilterType])

portfolio_store_type = cast("type[PortfolioStoreType]", PortfolioStore)
assert_type(portfolio_store_type, type[PortfolioStoreType])

adapter_stored_position_type = AdapterStoredPosition
assert_type(adapter_stored_position_type, type[AdapterStoredPosition])

adapter_stored_portfolio_type = AdapterStoredPortfolio
assert_type(adapter_stored_portfolio_type, type[AdapterStoredPortfolio])

adapter_portfolio_filter_type = AdapterPortfolioFilter
assert_type(adapter_portfolio_filter_type, type[AdapterPortfolioFilter])

etf_pricer_type = EtfPricer
assert_type(etf_pricer_type, type[EtfPricer])

portfolio_analyzer_type = PortfolioAnalyzer
assert_type(portfolio_analyzer_type, type[PortfolioAnalyzer])

portfolio_position_type = PortfolioPosition
assert_type(portfolio_position_type, type[PortfolioPosition])
