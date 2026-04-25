from __future__ import annotations

from typing import assert_type

from fuggers_py import (
    BusinessDayConvention,
    CalendarId,
    Compounding,
    Currency,
    Date,
    Frequency,
    Tenor,
    YearMonth,
    YieldCalculationRules,
)
from fuggers_py._core import FuggersError
from fuggers_py._math import BisectionSolver, MathResult, RootFinder
from fuggers_py._runtime import PricingEngineBuilder, ReactiveEngineBuilder
from fuggers_py._storage import (
    InMemoryPortfolioStore,
    PortfolioFilter,
    PortfolioStore,
    StoredPortfolio,
    StoredPosition,
)
from fuggers_py.bonds import BondPricer, BondQuote, FixedBondBuilder, TipsBond
from fuggers_py.credit import Cds, CdsPricer, CdsQuote
from fuggers_py.curves import CurveSpec, YieldCurve
from fuggers_py.funding import HaircutQuote, RepoQuote, RepoTrade
from fuggers_py.inflation import (
    USD_CPI_U_NSA,
    InflationConvention,
    InflationInterpolation,
    TreasuryAuctionedTipsRow,
)
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
from fuggers_py.rates import FixedFloatSwap, SwapPricer, SwapQuote
from fuggers_py.vol_surfaces import (
    InMemoryVolatilitySource,
    VolatilitySurface,
    VolPoint,
    VolQuoteType,
    VolSurfaceSourceType,
    VolSurfaceType,
)

root_date_type = Date
assert_type(root_date_type, type[Date])

root_currency_type = Currency
assert_type(root_currency_type, type[Currency])

root_frequency_type = Frequency
assert_type(root_frequency_type, type[Frequency])

root_compounding_type = Compounding
assert_type(root_compounding_type, type[Compounding])

root_tenor_type = Tenor
assert_type(root_tenor_type, type[Tenor])

root_year_month_type = YearMonth
assert_type(root_year_month_type, type[YearMonth])

root_calendar_id_type = CalendarId
assert_type(root_calendar_id_type, type[CalendarId])

root_business_day_convention_type = BusinessDayConvention
assert_type(root_business_day_convention_type, type[BusinessDayConvention])

root_yield_rules_type = YieldCalculationRules
assert_type(root_yield_rules_type, type[YieldCalculationRules])

core_error = FuggersError("boom")
assert_type(core_error, FuggersError)

solver = BisectionSolver()
assert_type(solver, BisectionSolver)

root_finder: RootFinder = solver
math_result = root_finder.find_root(lambda x: x * x - 2.0, 1.0, 2.0)
assert_type(math_result, MathResult)

runtime_builder = ReactiveEngineBuilder.new()
assert_type(runtime_builder, PricingEngineBuilder)

stored_position_type = StoredPosition
assert_type(stored_position_type, type[StoredPosition])

stored_portfolio_type = StoredPortfolio
assert_type(stored_portfolio_type, type[StoredPortfolio])

portfolio_filter_type = PortfolioFilter
assert_type(portfolio_filter_type, type[PortfolioFilter])

portfolio_store_type = PortfolioStore
assert_type(portfolio_store_type, type[PortfolioStore])

in_memory_portfolio_store_type = InMemoryPortfolioStore
assert_type(in_memory_portfolio_store_type, type[InMemoryPortfolioStore])

curve_spec_type = CurveSpec
assert_type(curve_spec_type, type[CurveSpec])

yield_curve_type = YieldCurve
assert_type(yield_curve_type, type[YieldCurve])

fixed_bond_builder_type = FixedBondBuilder
assert_type(fixed_bond_builder_type, type[FixedBondBuilder])

bond_pricer_type = BondPricer
assert_type(bond_pricer_type, type[BondPricer])

bond_quote_type = BondQuote
assert_type(bond_quote_type, type[BondQuote])

tips_bond_type = TipsBond
assert_type(tips_bond_type, type[TipsBond])

swap_quote_type = SwapQuote
assert_type(swap_quote_type, type[SwapQuote])

fixed_float_swap_type = FixedFloatSwap
assert_type(fixed_float_swap_type, type[FixedFloatSwap])

swap_pricer_type = SwapPricer
assert_type(swap_pricer_type, type[SwapPricer])

inflation_convention_type = InflationConvention
assert_type(inflation_convention_type, type[InflationConvention])

inflation_interpolation_type: type[InflationInterpolation] = InflationInterpolation

usd_cpi_convention = USD_CPI_U_NSA
assert_type(usd_cpi_convention, InflationConvention)

tips_row_type = TreasuryAuctionedTipsRow
assert_type(tips_row_type, type[TreasuryAuctionedTipsRow])

cds_type = Cds
assert_type(cds_type, type[Cds])

cds_pricer_type = CdsPricer
assert_type(cds_pricer_type, type[CdsPricer])

cds_quote_type = CdsQuote
assert_type(cds_quote_type, type[CdsQuote])

repo_trade_type = RepoTrade
assert_type(repo_trade_type, type[RepoTrade])

repo_quote_type = RepoQuote
assert_type(repo_quote_type, type[RepoQuote])

haircut_quote_type = HaircutQuote
assert_type(haircut_quote_type, type[HaircutQuote])

vol_point_type = VolPoint
assert_type(vol_point_type, type[VolPoint])

vol_quote_type: type[VolQuoteType] = VolQuoteType

vol_surface_source_type: type[VolSurfaceSourceType] = VolSurfaceSourceType

vol_surface_type: type[VolSurfaceType] = VolSurfaceType

volatility_surface_type = VolatilitySurface
assert_type(volatility_surface_type, type[VolatilitySurface])

in_memory_volatility_source_type = InMemoryVolatilitySource
assert_type(in_memory_volatility_source_type, type[InMemoryVolatilitySource])

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

etf_pricer_type = EtfPricer
assert_type(etf_pricer_type, type[EtfPricer])

portfolio_analyzer_type = PortfolioAnalyzer
assert_type(portfolio_analyzer_type, type[PortfolioAnalyzer])

portfolio_position_type = PortfolioPosition
assert_type(portfolio_position_type, type[PortfolioPosition])
