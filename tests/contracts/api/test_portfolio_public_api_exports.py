from __future__ import annotations

from decimal import Decimal
import inspect
from pathlib import Path

import pytest

from fuggers_py import Date
import fuggers_py.portfolio as portfolio_pkg
from fuggers_py.portfolio import (
    ActiveWeight,
    ActiveWeights,
    AggregatedAttribution,
    BenchmarkComparison,
    BenchmarkMetrics,
    AttributionInput,
    BasketComponent,
    BasketFlowSummary,
    BucketContribution,
    ClassifierDistribution,
    CreationBasket,
    CreditRating,
    ExpenseMetrics,
    PremiumDiscountPoint,
    aggregate_key_rate_profile,
    calculate_portfolio_analytics,
    Cs01Contributions,
    DurationComparison,
    DurationContributions,
    Dv01Contributions,
    HoldingAttribution,
    HoldingContribution,
    PortfolioAttribution,
    PortfolioBenchmark,
    RatingInfo,
    RatingComparison,
    RiskComparison,
    SectorAttribution,
    Sector,
    SectorInfo,
    SectorComparison,
    Seniority,
    SeniorityInfo,
    SpreadContributions,
    SpreadComparison,
    TrackingErrorEstimate,
    YieldComparison,
    active_weights,
    aggregated_attribution,
    arbitrage_opportunity,
    attribution_summary,
    best_case,
    benchmark_comparison,
    bucket_by_classifier,
    build_creation_basket,
    cs01_per_share,
    dv01_per_share,
    duration_difference_by_sector,
    duration_contributions,
    dv01_contributions,
    estimate_income_returns,
    estimate_days_to_liquidate,
    estimate_rate_returns,
    estimate_spread_returns,
    estimate_tracking_error,
    estimate_yield_from_holdings,
    parallel_shift_impact,
    compare_portfolios,
    spread_contributions,
    spread_difference_by_sector,
    summarize_results,
    top_contributors,
    worst_case,
)

from tests.helpers._portfolio_helpers import make_benchmark, make_curve, make_portfolio


def test_portfolio_exports_resolve_under_portfolio() -> None:
    root = Path(portfolio_pkg.__file__).resolve().parent
    source_less_constants = {"DEFAULT_BUCKETS"}

    for name in portfolio_pkg.__all__:
        try:
            source = inspect.getsourcefile(getattr(portfolio_pkg, name))
        except TypeError:
            source = None

        if source is None:
            assert name in source_less_constants
            continue

        assert Path(source).resolve().is_relative_to(root), name


def test_portfolio_root_imports_expose_typed_comparison_and_contribution_surface() -> None:
    assert BenchmarkMetrics is BenchmarkComparison
    assert CreditRating.BBB.score() == 4
    assert RatingInfo(CreditRating.A, agency="S&P").agency == "S&P"
    assert Sector.CORPORATE.value == "CORPORATE"
    assert SectorInfo(Sector.CORPORATE, issuer="ACME").issuer == "ACME"
    assert Seniority.SENIOR_UNSECURED.value == "SENIOR_UNSECURED"
    assert SeniorityInfo(Seniority.SENIOR_UNSECURED).secured is False


def test_active_weights_return_typed_mapping_with_zero_net_active_weight() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    result = active_weights(make_portfolio(ref), make_benchmark(ref), make_curve(ref), ref)

    assert isinstance(result, ActiveWeights)
    assert isinstance(result.entries[0], ActiveWeight)
    assert result.dimension == "holding"
    assert float(sum(result.values(), Decimal(0))) == pytest.approx(0.0)
    assert result.by_name("gov_short") is not None


def test_benchmark_comparison_returns_typed_nested_results() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    comparison = benchmark_comparison(make_portfolio(ref), make_benchmark(ref), make_curve(ref), ref)

    assert isinstance(comparison, BenchmarkComparison)
    assert isinstance(comparison.duration, DurationComparison)
    assert isinstance(comparison.risk, RiskComparison)
    assert isinstance(comparison.yields, YieldComparison)
    assert isinstance(comparison.spread, SpreadComparison)
    assert isinstance(comparison.sector, SectorComparison)
    assert isinstance(comparison.rating, RatingComparison)
    assert comparison.duration.active_duration == comparison.active_duration
    assert comparison.risk.active_dv01 == comparison.active_dv01
    assert comparison.sector.active_weights.dimension == "sector"
    assert comparison.rating.active_weights.dimension == "rating"


def test_tracking_error_estimate_is_typed_and_decimal_compatible() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    result = estimate_tracking_error(PortfolioBenchmark(make_portfolio(ref), make_benchmark(ref)), make_curve(ref), ref)

    assert isinstance(result, TrackingErrorEstimate)
    assert result > Decimal("0")
    assert result.estimate == result.duration_component + result.spread_component + result.dispersion_component


def test_duration_contributions_are_typed_and_sum_back_to_portfolio_duration() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    contributions = duration_contributions(portfolio, curve=make_curve(ref), settlement_date=ref)
    total = sum((entry["duration_contribution"] for entry in contributions), Decimal(0))
    comparison = benchmark_comparison(portfolio, make_benchmark(ref), make_curve(ref), ref)

    assert isinstance(contributions, DurationContributions)
    assert isinstance(contributions[0], HoldingContribution)
    assert float(total) == pytest.approx(float(comparison.duration.portfolio_duration))
    assert float(contributions.total) == pytest.approx(float(comparison.duration.portfolio_duration))


def test_dv01_and_spread_contributions_are_typed_and_aggregate_cleanly() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    comparison = benchmark_comparison(portfolio, make_benchmark(ref), curve, ref)
    metrics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=ref)
    dv01 = dv01_contributions(portfolio, curve=curve, settlement_date=ref)
    spread = spread_contributions(portfolio, curve=curve, settlement_date=ref)

    assert isinstance(dv01, Dv01Contributions)
    assert isinstance(spread, Cs01Contributions)
    assert float(sum((entry["dv01_contribution"] for entry in dv01), Decimal(0))) == pytest.approx(float(comparison.risk.portfolio_dv01))
    assert float(sum((entry["spread_contribution"] for entry in spread), Decimal(0))) == pytest.approx(float(metrics.cs01))
    assert float(spread.total) == pytest.approx(float(sum((entry.amount for entry in spread), Decimal(0))))


def test_portfolio_attribution_is_typed_and_retains_sequence_compatibility() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    attribution = attribution_summary(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref)

    assert isinstance(attribution, PortfolioAttribution)
    assert isinstance(attribution[0], HoldingAttribution)
    assert float(sum((entry["pv_pct"] for entry in attribution), Decimal(0))) == pytest.approx(1.0)
    assert float(attribution.total_pv_pct) == pytest.approx(1.0)
    assert float(attribution.total_dv01_pct) == pytest.approx(1.0)


def test_top_contributors_accepts_typed_contribution_entries() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    ranked = top_contributors(
        dv01_contributions(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref),
        value_key="dv01_contribution",
        absolute=True,
    )

    assert ranked
    assert isinstance(ranked[0], HoldingContribution)


def test_recent_portfolio_gap_closure_helpers_are_root_importable_and_typed() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    summary = benchmark_comparison(portfolio, make_benchmark(ref), curve, ref)
    stress = summarize_results({})

    assert summary is not None
    assert isinstance(bucket_by_classifier(portfolio, "sector"), ClassifierDistribution)
    assert aggregate_key_rate_profile(portfolio, curve=curve, settlement_date=ref)
    assert estimate_days_to_liquidate(portfolio, curve=curve, settlement_date=ref).days > 0
    assert dv01_per_share(portfolio, curve=curve, settlement_date=ref, shares_outstanding=Decimal("100")) > 0
    assert cs01_per_share(portfolio, curve=curve, settlement_date=ref, shares_outstanding=Decimal("100")) >= 0
    assert parallel_shift_impact(portfolio, curve=curve, settlement_date=ref, bump_bps=Decimal("10")).scenario_name is not None
    assert best_case(stress) is None
    assert worst_case(stress) is None


def test_attribution_decomposition_surface_is_root_importable_and_typed() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    benchmark = make_benchmark(ref)
    curve = make_curve(ref)
    assumptions = AttributionInput(
        income_horizon_years=Decimal("0.5"),
        rate_change_bps=Decimal("10"),
        spread_change_bps=Decimal("20"),
    )
    aggregated = aggregated_attribution(
        portfolio,
        curve=curve,
        settlement_date=ref,
        assumptions=assumptions,
        benchmark=benchmark,
    )

    assert isinstance(aggregated, AggregatedAttribution)
    assert isinstance(duration_difference_by_sector(portfolio, benchmark, curve=curve, settlement_date=ref), SectorAttribution)
    assert isinstance(spread_difference_by_sector(portfolio, benchmark, curve=curve, settlement_date=ref)["CORPORATE"], BucketContribution)
    assert spread_contributions(portfolio, curve=curve, settlement_date=ref).__class__ is SpreadContributions
    assert SpreadContributions is Cs01Contributions
    assert estimate_income_returns(portfolio, curve=curve, settlement_date=ref, assumptions=assumptions) >= Decimal("0")
    assert estimate_rate_returns(portfolio, curve=curve, settlement_date=ref, assumptions=assumptions) != Decimal("0")
    assert estimate_spread_returns(portfolio, curve=curve, settlement_date=ref, assumptions=assumptions) != Decimal("0")


def test_etf_gap_closure_surface_is_root_importable_and_typed() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)

    basket = build_creation_basket(
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
        market_price=Decimal("30"),
        liabilities=Decimal("10"),
    )
    yield_metrics = estimate_yield_from_holdings(
        portfolio,
        curve=curve,
        settlement_date=ref,
        gross_expense_ratio=Decimal("0.0020"),
        fee_waiver_ratio=Decimal("0.0005"),
    )

    assert isinstance(basket, CreationBasket)
    assert isinstance(basket.flow_summary, BasketFlowSummary)
    assert isinstance(basket[0], BasketComponent)
    assert basket.by_name("gov_short") is not None

    assert isinstance(opportunity, PremiumDiscountPoint)
    assert opportunity.direction == "create"
    assert opportunity.premium_discount_bps > Decimal("0")

    assert isinstance(yield_metrics, ExpenseMetrics)
    assert yield_metrics.net_expense_ratio == Decimal("0.0015")
    assert yield_metrics.net_yield < yield_metrics.gross_yield
