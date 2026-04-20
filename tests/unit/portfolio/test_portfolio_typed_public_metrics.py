from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py._core import Date
from fuggers_py.portfolio import (
    BasketAnalysis,
    BasketComponent,
    BasketFlowSummary,
    BucketContribution,
    AggregatedAttribution,
    AttributionInput,
    BucketMetrics,
    ComplianceCheck,
    ComplianceSeverity,
    CreationBasket,
    CreditMetrics,
    CreditQualityMetrics,
    Cs01Contributions,
    CustomDistribution,
    DaysToLiquidate,
    DistributionYield,
    ExpenseMetrics,
    EtfComplianceReport,
    EtfNavMetrics,
    FallenAngelRisk,
    KeyRateProfile,
    KeyRateShiftScenario,
    LiquidityBucket,
    LiquidityDistribution,
    LiquidityMetrics,
    MaturityDistribution,
    MigrationRisk,
    NavBreakdown,
    Portfolio,
    PortfolioAnalytics,
    PremiumDiscountPoint,
    PremiumDiscountStats,
    QualityTiers,
    RateScenario,
    RatingDistribution,
    RiskMetrics,
    RisingStarRisk,
    SecYield,
    SecYieldInput,
    SectorAttribution,
    SectorDistribution,
    SpreadContributions,
    SpreadMetrics,
    SpreadScenario,
    StressScenario,
    StressSummary,
    TenorShift,
    YieldMetrics,
    analyze_etf_basket,
    aggregate_key_rate_profile,
    arbitrage_opportunity,
    build_creation_basket,
    calculate_credit_metrics,
    calculate_credit_quality,
    calculate_attribution,
    aggregated_attribution,
    calculate_distribution_yield,
    calculate_etf_nav_metrics,
    calculate_liquidity_metrics,
    calculate_migration_risk,
    calculate_nav_breakdown,
    calculate_portfolio_analytics,
    calculate_sec_yield,
    calculate_risk_metrics,
    cs01_per_share,
    dv01_per_share,
    duration_difference_by_sector,
    etf_compliance_checks,
    estimate_yield_from_holdings,
    bucket_by_custom_field,
    bucket_by_maturity,
    bucket_by_rating,
    bucket_by_sector,
    calculate_spread_metrics,
    calculate_yield_metrics,
    liquidity_distribution,
    premium_discount,
    premium_discount_stats,
    run_stress_scenario,
    run_stress_scenarios,
    spread_difference_by_sector,
    standard_scenarios,
    stress_scenarios,
    weighted_asw,
    weighted_best_duration,
    weighted_best_spread,
    weighted_best_yield,
    weighted_bid_ask_spread,
    weighted_effective_convexity,
    weighted_effective_duration,
    weighted_g_spread,
    weighted_i_spread,
    weighted_liquidity_score,
    weighted_macaulay_duration,
    weighted_modified_duration,
    weighted_oas,
    weighted_spread_duration,
    weighted_ytc,
    weighted_z_spread,
)
from fuggers_py.portfolio.contribution import attribution_summary
from fuggers_py.portfolio.bucketing import maturity_bucket_metrics, sector_bucket_metrics

from tests.helpers._portfolio_helpers import make_benchmark, make_curve, make_portfolio


def _portfolio_with_bid_ask(ref: Date) -> Portfolio:
    portfolio = make_portfolio(ref)
    positions = list(portfolio.positions)
    positions[0] = replace(positions[0], custom_fields={"bid_ask_spread": "0.0125"})
    positions[1] = replace(positions[1], custom_fields={"bid_ask": "0.0250"})
    positions[2] = replace(positions[2], custom_fields={"bidask_spread": "0.0400"})
    return Portfolio.new(positions, currency=portfolio.currency)


def test_root_portfolio_imports_expose_typed_metric_surface() -> None:
    assert CreditMetrics is CreditQualityMetrics
    assert issubclass(RateScenario, StressScenario)
    assert issubclass(SpreadScenario, StressScenario)


def test_credit_quality_metrics_are_typed_and_attribute_accessible() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    metrics = calculate_credit_quality(make_portfolio(ref))

    assert isinstance(metrics, CreditQualityMetrics)
    assert calculate_credit_metrics(make_portfolio(ref)) == metrics
    assert isinstance(metrics.quality_tiers, QualityTiers)
    assert isinstance(metrics.migration_risk, MigrationRisk)
    assert isinstance(metrics.migration_risk.fallen_angel, FallenAngelRisk)
    assert isinstance(metrics.migration_risk.rising_star, RisingStarRisk)
    assert metrics.investment_grade_weight > Decimal("0")
    assert metrics.migration_risk.fallen_angel_risk >= Decimal("0")
    assert metrics.quality_tiers.investment_grade == metrics.quality_tiers.investment_grade
    assert metrics.migration_risk.fallen_angel.holdings_count == metrics.migration_risk.fallen_angel.holdings_count


def test_calculate_migration_risk_returns_typed_public_result() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    migration = calculate_migration_risk(portfolio)

    assert isinstance(migration, MigrationRisk)
    assert isinstance(migration.fallen_angel, FallenAngelRisk)
    assert isinstance(migration.rising_star, RisingStarRisk)
    assert migration.fallen_angel_risk > Decimal("0")
    assert migration.rising_star_risk > Decimal("0")
    assert migration.crossover_weight == migration.fallen_angel_risk + migration.rising_star_risk
    assert migration.fallen_angel.holdings_count == 1
    assert migration.rising_star.holdings_count == 1


def test_bucket_metrics_aliases_existing_bucket_results_and_aggregate() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    metrics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=ref)
    buckets = maturity_bucket_metrics(portfolio, curve=curve, settlement_date=ref)

    assert buckets
    assert all(isinstance(bucket, BucketMetrics) for bucket in buckets.values())
    assert float(sum((bucket.dirty_pv for bucket in buckets.values()), Decimal(0))) == pytest.approx(float(metrics.dirty_pv))
    assert float(sum((bucket.weight for bucket in sector_bucket_metrics(portfolio, curve=curve, settlement_date=ref).values()), Decimal(0))) == pytest.approx(1.0)


def test_key_rate_nav_and_distribution_wrappers_are_typed_and_attribute_accessible() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = make_curve(ref)
    base_portfolio = make_portfolio(ref)
    custom_portfolio = Portfolio.new(
        [
            replace(base_portfolio.positions[0], custom_fields={"desk": "ALPHA"}),
            replace(base_portfolio.positions[1], classification=replace(base_portfolio.positions[1].classification, custom_fields={"desk": "BETA"})),
            base_portfolio.positions[2],
        ],
        currency=base_portfolio.currency,
    )

    key_rates = aggregate_key_rate_profile(base_portfolio, curve=curve, settlement_date=ref)
    nav = calculate_nav_breakdown(base_portfolio, curve=curve, settlement_date=ref)
    custom = bucket_by_custom_field(custom_portfolio, "desk")
    maturity = bucket_by_maturity(base_portfolio, settlement_date=ref)
    rating = bucket_by_rating(base_portfolio)
    sector = bucket_by_sector(base_portfolio)
    distribution_yield = calculate_distribution_yield(Decimal("4.0"), Decimal("100.0"))

    assert isinstance(key_rates, KeyRateProfile)
    assert key_rates
    assert key_rates.total_dv01 == sum(key_rates.values(), Decimal(0))
    assert all(isinstance(value, Decimal) for value in key_rates.values())

    assert isinstance(nav, NavBreakdown)
    assert nav.dirty_market_value >= nav.market_value

    assert isinstance(custom, CustomDistribution)
    assert custom.field_name == "desk"
    assert [position.name() for position in custom["ALPHA"]] == ["gov_short"]
    assert [position.name() for position in custom["BETA"]] == ["corp_bbb"]

    assert isinstance(maturity, MaturityDistribution)
    assert maturity.bucket_definition
    assert maturity.holding_count == len(base_portfolio.positions)

    assert isinstance(rating, RatingDistribution)
    assert any(label in rating for label in ("AA", "BBB"))

    assert isinstance(sector, SectorDistribution)
    assert any(label in sector for label in ("GOVERNMENT", "CORPORATE"))

    assert isinstance(distribution_yield, DistributionYield)
    assert distribution_yield == Decimal("0.04")
    assert distribution_yield.distribution_yield_pct == Decimal("4.00")
    assert distribution_yield.as_decimal() == Decimal("0.04")
    assert float(distribution_yield) == pytest.approx(0.04)


def test_liquidity_metrics_distribution_and_days_are_typed_and_stable() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = make_curve(ref)
    portfolio = _portfolio_with_bid_ask(ref)
    liquid = calculate_liquidity_metrics(portfolio, curve=curve, settlement_date=ref)
    less_liquid = calculate_liquidity_metrics(
        Portfolio.new(
            [replace(position, liquidity_score=Decimal("0.20")) for position in portfolio.positions],
            currency=portfolio.currency,
        ),
        curve=curve,
        settlement_date=ref,
    )

    assert isinstance(liquid, LiquidityMetrics)
    assert isinstance(liquid.days_to_liquidate, DaysToLiquidate)
    assert isinstance(liquid.distribution, LiquidityDistribution)
    assert isinstance(liquid.distribution.values()[0], LiquidityBucket)
    assert float(liquid.distribution.total_weight) == pytest.approx(1.0)
    assert liquid.days_to_liquidate.days < less_liquid.days_to_liquidate.days
    assert liquidity_distribution(portfolio, curve=curve, settlement_date=ref)["high"].holding_count > 0


def test_weighted_bid_ask_spread_uses_position_custom_fields() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = make_curve(ref)
    portfolio = _portfolio_with_bid_ask(ref)
    positions = PortfolioAnalytics(portfolio).position_metrics(curve, ref)
    custom = {
        position.name(): Decimal(next(iter(position.custom_fields.values())))
        for position in portfolio.positions
        if hasattr(position, "custom_fields") and position.custom_fields
    }
    total_dirty = sum((item.dirty_value for item in positions), Decimal(0))
    manual = sum((custom[item.name] * item.dirty_value for item in positions), Decimal(0)) / total_dirty

    assert float(weighted_bid_ask_spread(portfolio, curve=curve, settlement_date=ref)) == pytest.approx(float(manual))


def test_risk_yield_and_spread_metric_wrappers_are_typed_and_match_portfolio_metrics() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    metrics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=ref)

    risk = calculate_risk_metrics(portfolio, curve=curve, settlement_date=ref)
    spread = calculate_spread_metrics(portfolio, curve=curve, settlement_date=ref)
    yield_metrics = calculate_yield_metrics(portfolio, curve=curve, settlement_date=ref)

    assert isinstance(risk, RiskMetrics)
    assert isinstance(spread, SpreadMetrics)
    assert isinstance(yield_metrics, YieldMetrics)
    assert risk.dv01 == metrics.dv01
    assert spread.z_spread == metrics.z_spread
    assert yield_metrics.best_yield == metrics.best_yield
    assert weighted_z_spread(portfolio, curve=curve, settlement_date=ref) == metrics.z_spread
    assert weighted_oas(portfolio, curve=curve, settlement_date=ref) == metrics.oas
    assert weighted_g_spread(portfolio, curve=curve, settlement_date=ref) == metrics.g_spread
    assert weighted_i_spread(portfolio, curve=curve, settlement_date=ref) == metrics.i_spread
    assert weighted_asw(portfolio, curve=curve, settlement_date=ref) == metrics.asw
    assert weighted_spread_duration(portfolio, curve=curve, settlement_date=ref) == metrics.spread_duration
    assert weighted_modified_duration(portfolio, curve=curve, settlement_date=ref) == metrics.modified_duration
    assert weighted_macaulay_duration(portfolio, curve=curve, settlement_date=ref) == metrics.macaulay_duration
    assert weighted_effective_duration(portfolio, curve=curve, settlement_date=ref) == metrics.effective_duration
    assert weighted_effective_convexity(portfolio, curve=curve, settlement_date=ref) == metrics.effective_convexity
    assert weighted_liquidity_score(portfolio, curve=curve, settlement_date=ref) == metrics.liquidity_score
    assert weighted_ytc(portfolio, curve=curve, settlement_date=ref) == metrics.ytc
    assert weighted_best_yield(portfolio, curve=curve, settlement_date=ref) == metrics.best_yield
    assert weighted_best_spread(portfolio, curve=curve, settlement_date=ref) == metrics.best_spread
    assert weighted_best_duration(portfolio, curve=curve, settlement_date=ref) == metrics.effective_duration


def test_etf_public_results_are_typed_and_attribute_accessible() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)

    nav_metrics = calculate_etf_nav_metrics(
        portfolio,
        curve=curve,
        settlement_date=ref,
        shares_outstanding=Decimal("1000"),
        liabilities=Decimal("10"),
        market_price=Decimal("30"),
    )
    basket = analyze_etf_basket(portfolio)
    creation_basket = build_creation_basket(
        portfolio,
        curve=curve,
        settlement_date=ref,
        shares_outstanding=Decimal("1000"),
        creation_unit_shares=Decimal("100"),
        liabilities=Decimal("10"),
    )
    opportunity = arbitrage_opportunity(
        portfolio,
        curve=curve,
        settlement_date=ref,
        shares_outstanding=Decimal("1000"),
        liabilities=Decimal("10"),
        market_price=Decimal("30"),
    )
    holdings_yield = estimate_yield_from_holdings(
        portfolio,
        curve=curve,
        settlement_date=ref,
        gross_expense_ratio=Decimal("0.0020"),
        fee_waiver_ratio=Decimal("0.0005"),
    )
    compliance = etf_compliance_checks(
        holdings_weight_sum=Decimal("1.00005"),
        max_issuer_weight=Decimal("0.26"),
    )
    sec_yield = calculate_sec_yield(
        SecYieldInput(
            net_investment_income=Decimal("2.40"),
            average_shares_outstanding=Decimal("10"),
            max_offering_price=Decimal("120"),
            gross_expenses=Decimal("0.90"),
            fee_waivers=Decimal("0.40"),
            as_of_date=ref,
        )
    )

    sec_denominator = Decimal("10") * Decimal("120")
    sec_ratio = Decimal("2.40") / sec_denominator
    unsubsidized_ratio = Decimal("2.00") / sec_denominator
    expected_sec_yield = Decimal(2) * (((Decimal(1) + sec_ratio) ** 6) - Decimal(1))
    expected_unsubsidized = Decimal(2) * (((Decimal(1) + unsubsidized_ratio) ** 6) - Decimal(1))

    assert isinstance(nav_metrics, EtfNavMetrics)
    assert isinstance(nav_metrics.premium_discount, PremiumDiscountStats)
    assert nav_metrics.dv01_per_share == dv01_per_share(
        portfolio,
        curve=curve,
        settlement_date=ref,
        shares_outstanding=Decimal("1000"),
    )
    assert nav_metrics.cs01_per_share == cs01_per_share(portfolio, curve=curve, settlement_date=ref, shares_outstanding=Decimal("1000"))
    assert nav_metrics.premium_discount_dollars == Decimal("30") - nav_metrics.nav_per_share
    assert nav_metrics.premium_discount.premium_discount_pct == nav_metrics.premium_discount_pct
    assert nav_metrics.is_premium()

    assert isinstance(basket, BasketAnalysis)
    assert basket.num_positions == basket.security_count == len(portfolio.positions)
    assert basket.sector_counts["CORPORATE"] == 1

    assert isinstance(creation_basket, CreationBasket)
    assert isinstance(creation_basket[0], BasketComponent)
    assert isinstance(creation_basket.flow_summary, BasketFlowSummary)
    assert creation_basket.flow_summary.component_count == creation_basket.component_count
    assert creation_basket.flow_summary.liabilities_component == Decimal("1")
    assert creation_basket.by_name("corp_bbb") is not None

    assert isinstance(opportunity, PremiumDiscountPoint)
    assert opportunity.premium_discount_bps == opportunity.premium_discount.premium_discount_bps
    assert opportunity.direction == "create"
    assert opportunity.is_actionable is True

    assert isinstance(holdings_yield, ExpenseMetrics)
    assert holdings_yield.expense_drag == holdings_yield.gross_yield - holdings_yield.net_yield
    assert holdings_yield.net_expense_ratio == Decimal("0.0015")
    assert holdings_yield.net_yield == holdings_yield.yield_after_expenses

    assert isinstance(compliance, EtfComplianceReport)
    assert all(isinstance(check, ComplianceCheck) for check in compliance.checks)
    assert compliance.weights_sum_to_one
    assert not compliance.issuer_limit_ok
    issuer_limit = compliance.by_name("issuer_limit_ok")
    assert issuer_limit is not None
    assert issuer_limit.severity is ComplianceSeverity.WARNING
    assert not compliance.passed

    assert isinstance(sec_yield, SecYield)
    assert sec_yield.unsubsidized_yield is not None
    assert sec_yield.sec_30_day_yield == expected_sec_yield
    assert sec_yield.unsubsidized_yield == expected_unsubsidized
    assert sec_yield.fee_waiver_impact() == expected_sec_yield - expected_unsubsidized
    assert sec_yield.as_of_date == ref


def test_alias_helpers_match_existing_public_helpers() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    scenario = standard_scenarios()[0]

    assert calculate_attribution(portfolio, curve=curve, settlement_date=ref) == attribution_summary(
        portfolio,
        curve=curve,
        settlement_date=ref,
    )
    assert premium_discount(Decimal("100"), Decimal("101")) == premium_discount_stats(Decimal("100"), Decimal("101"))
    assert run_stress_scenario(portfolio, curve=curve, settlement_date=ref, scenario=scenario) == run_stress_scenarios(
        portfolio,
        curve=curve,
        settlement_date=ref,
        scenarios=[scenario],
    )[scenario.name]


def test_return_decomposition_helpers_are_typed_and_reconcile() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    benchmark = make_benchmark(ref)
    curve = make_curve(ref)
    assumptions = AttributionInput(
        income_horizon_years=Decimal("0.5"),
        rate_change_bps=Decimal("10"),
        spread_change_bps=Decimal("25"),
    )
    aggregated = aggregated_attribution(
        portfolio,
        curve=curve,
        settlement_date=ref,
        assumptions=assumptions,
        benchmark=benchmark,
    )
    duration = duration_difference_by_sector(portfolio, benchmark, curve=curve, settlement_date=ref)
    spread = spread_difference_by_sector(portfolio, benchmark, curve=curve, settlement_date=ref)

    assert isinstance(aggregated, AggregatedAttribution)
    assert aggregated.total_return == aggregated.income_return + aggregated.rate_return + aggregated.spread_return
    assert isinstance(duration, SectorAttribution)
    assert isinstance(spread, SectorAttribution)
    assert isinstance(duration["CORPORATE"], BucketContribution)
    assert SpreadContributions is Cs01Contributions


def test_stress_summaries_and_scenarios_are_typed() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    scenarios = standard_scenarios()
    summary = stress_scenarios(portfolio, curve=curve, settlement_date=ref, scenarios=scenarios)
    key_rate = next(scenario for scenario in scenarios if isinstance(scenario, KeyRateShiftScenario))

    assert isinstance(summary, StressSummary)
    assert all(isinstance(scenario, StressScenario) for scenario in scenarios)
    assert all(isinstance(shift, TenorShift) for shift in key_rate.tenor_shifts)
    assert summary.scenario_count == len(scenarios)
    assert summary.aggregate_change == sum((result.actual_change for result in summary.values()), Decimal(0))
    assert summary["+10bps parallel"].scenario_name == "+10bps parallel"
