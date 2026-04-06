from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Date
from fuggers_py.portfolio import (
    AggregatedAttribution,
    AttributionInput,
    BucketContribution,
    Cs01Contributions,
    PortfolioBenchmark,
    SectorAttribution,
    SpreadContributions,
    benchmark_comparison,
    calculate_portfolio_analytics,
    duration_difference_by_sector,
    estimate_income_returns,
    estimate_rate_returns,
    estimate_spread_returns,
    parallel_shift_impact,
    spread_contributions,
    spread_difference_by_sector,
    spread_shock_impact,
)
from fuggers_py.portfolio.contribution import Contribution

from tests.helpers._portfolio_helpers import make_benchmark, make_curve, make_portfolio


def test_return_estimates_match_existing_metrics_and_stress_helpers() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    assumptions = AttributionInput(
        income_horizon_years=Decimal("0.5"),
        rate_change_bps=Decimal("15"),
        spread_change_bps=Decimal("20"),
    )
    metrics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=ref)

    assert estimate_income_returns(portfolio, curve=curve, settlement_date=ref, assumptions=assumptions) == metrics.current_yield * Decimal("0.5")
    assert estimate_rate_returns(portfolio, curve=curve, settlement_date=ref, assumptions=assumptions) == parallel_shift_impact(
        portfolio,
        curve=curve,
        settlement_date=ref,
        bump_bps=Decimal("15"),
    ).actual_change / metrics.dirty_pv
    assert estimate_spread_returns(portfolio, curve=curve, settlement_date=ref, assumptions=assumptions) == spread_shock_impact(
        portfolio,
        curve=curve,
        settlement_date=ref,
        bump_bps=Decimal("20"),
    ) / metrics.dirty_pv


def test_aggregated_attribution_wraps_component_estimates_and_active_decomposition() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    benchmark = make_benchmark(ref)
    curve = make_curve(ref)
    assumptions = AttributionInput(
        income_horizon_years=Decimal("1"),
        rate_change_bps=Decimal("10"),
        spread_change_bps=Decimal("25"),
    )

    aggregated = AggregatedAttribution.from_portfolios(
        portfolio,
        curve=curve,
        settlement_date=ref,
        assumptions=assumptions,
        benchmark=benchmark,
    )
    via_wrapper = PortfolioBenchmark(portfolio, benchmark).aggregated_attribution(
        curve,
        ref,
        assumptions=assumptions,
    )

    assert aggregated == via_wrapper
    assert aggregated.total_return == aggregated.income_return + aggregated.rate_return + aggregated.spread_return
    assert aggregated.benchmark_total_return is not None
    assert aggregated.active_total_return == aggregated.total_return - aggregated.benchmark_total_return
    assert aggregated.duration_by_sector is not None
    assert aggregated.spread_by_sector is not None


def test_sector_difference_helpers_return_typed_bucket_contributions_and_reconcile_to_active_totals() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    benchmark = make_benchmark(ref)
    curve = make_curve(ref)
    comparison = benchmark_comparison(portfolio, benchmark, curve, ref)

    duration = duration_difference_by_sector(portfolio, benchmark, curve=curve, settlement_date=ref)
    spread = spread_difference_by_sector(portfolio, benchmark, curve=curve, settlement_date=ref)

    assert isinstance(duration, SectorAttribution)
    assert isinstance(spread, SectorAttribution)
    assert isinstance(duration["CORPORATE"], BucketContribution)
    assert duration.metric == "duration"
    assert spread.metric == "spread"
    assert float(duration.total_active) == pytest.approx(float(comparison.active_duration))
    assert float(spread.total_active) == pytest.approx(float(comparison.active_z_spread))


def test_spread_contributions_alias_preserves_existing_function_surface() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    contributions = spread_contributions(make_portfolio(ref), curve=make_curve(ref), settlement_date=ref)

    assert isinstance(contributions, SpreadContributions)
    assert SpreadContributions is Cs01Contributions
    assert isinstance(Contribution(make_portfolio(ref)).aggregate(make_curve(ref), ref), AggregatedAttribution)
