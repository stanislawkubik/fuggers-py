from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py._core import Currency, Date
from fuggers_py.portfolio import (
    ClassifierDistribution,
    DaysToLiquidate,
    StressSummary,
    aggregate_key_rate_profile,
    best_case,
    bucket_by_classifier,
    calculate_etf_nav_metrics,
    calculate_liquidity_metrics,
    calculate_portfolio_analytics,
    cs01_per_share,
    dv01_per_share,
    estimate_days_to_liquidate,
    parallel_shift_impact,
    rate_shock_impact,
    run_stress_scenarios,
    standard_scenarios,
    summarize_results,
    worst_case,
)
from fuggers_py.portfolio.portfolio import Portfolio
from fuggers_py.portfolio.types import StressResult

from tests.helpers._portfolio_helpers import make_curve, make_portfolio


def test_per_share_risk_helpers_match_portfolio_metrics_and_etf_surface() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    shares = Decimal("1000")
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    metrics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=ref)
    nav_metrics = calculate_etf_nav_metrics(portfolio, curve=curve, settlement_date=ref, shares_outstanding=shares)

    assert dv01_per_share(portfolio, curve=curve, settlement_date=ref, shares_outstanding=shares) == metrics.dv01 / shares
    assert cs01_per_share(portfolio, curve=curve, settlement_date=ref, shares_outstanding=shares) == metrics.cs01 / shares
    assert nav_metrics.dv01_per_share == metrics.dv01 / shares
    assert nav_metrics.cs01_per_share == metrics.cs01 / shares


def test_per_share_risk_helpers_require_positive_shares() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)

    with pytest.raises(ValueError, match="shares_outstanding must be positive"):
        dv01_per_share(portfolio, curve=curve, settlement_date=ref, shares_outstanding=Decimal(0))

    with pytest.raises(ValueError, match="shares_outstanding must be positive"):
        cs01_per_share(portfolio, curve=curve, settlement_date=ref, shares_outstanding=Decimal("-1"))


def test_estimate_days_to_liquidate_reuses_liquidity_metrics_and_scales_by_fraction() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    full = estimate_days_to_liquidate(portfolio, curve=curve, settlement_date=ref)
    partial = estimate_days_to_liquidate(
        portfolio,
        curve=curve,
        settlement_date=ref,
        liquidation_fraction=Decimal("0.25"),
    )

    assert isinstance(full, DaysToLiquidate)
    assert full == calculate_liquidity_metrics(portfolio, curve=curve, settlement_date=ref).days_to_liquidate
    assert partial.days == full.days * Decimal("0.25")
    assert partial.liquidation_fraction == Decimal("0.25")

    with pytest.raises(ValueError, match="liquidation_fraction must be between 0 and 1"):
        estimate_days_to_liquidate(portfolio, curve=curve, settlement_date=ref, liquidation_fraction=Decimal("1.1"))


def test_aggregate_key_rate_profile_matches_portfolio_metrics_key_rate_profile() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    metrics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=ref)

    profile = aggregate_key_rate_profile(portfolio, curve=curve, settlement_date=ref)

    assert profile.entries == dict(metrics.key_rate_profile)


def test_bucket_by_classifier_supports_metadata_and_custom_field_fallbacks() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    base_portfolio = make_portfolio(ref)
    direct = replace(base_portfolio.positions[0], custom_fields={"desk": "ALPHA"})
    fallback = replace(
        base_portfolio.positions[1],
        classification=replace(base_portfolio.positions[1].classification, custom_fields={"desk": "BETA"}),
    )
    unknown = replace(base_portfolio.positions[2], classification=None, sector_info=None)
    custom_portfolio = Portfolio.new([direct, fallback, unknown], currency=Currency.USD)

    by_country = bucket_by_classifier(base_portfolio, "country")
    by_desk = bucket_by_classifier(custom_portfolio, "desk")

    assert isinstance(by_country, ClassifierDistribution)
    assert by_country.classifier_name == "country"
    assert [position.name() for position in by_country["US"]] == [position.name() for position in base_portfolio.positions]
    assert [position.name() for position in by_desk["ALPHA"]] == ["gov_short"]
    assert [position.name() for position in by_desk["BETA"]] == ["corp_bbb"]
    assert [position.name() for position in by_desk["UNKNOWN"]] == ["corp_bb"]


def test_stress_summary_helpers_select_extrema_and_normalize_names() -> None:
    manual = summarize_results(
        {
            "gain": StressResult(
                base_dirty_pv=Decimal("100"),
                stressed_dirty_pv=Decimal("103"),
                actual_change=Decimal("3"),
                dv01_approximation=Decimal("3"),
            ),
            "loss": StressResult(
                base_dirty_pv=Decimal("100"),
                stressed_dirty_pv=Decimal("96"),
                actual_change=Decimal("-4"),
                dv01_approximation=Decimal("-4"),
            ),
        }
    )

    assert isinstance(manual, StressSummary)
    assert manual["gain"].scenario_name == "gain"
    assert best_case(manual).scenario_name == "gain"
    assert worst_case(manual).scenario_name == "loss"


def test_parallel_shift_impact_and_summary_helpers_reuse_existing_stress_engine() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    scenarios = standard_scenarios()
    summary = run_stress_scenarios(portfolio, curve=curve, settlement_date=ref, scenarios=scenarios)
    summarized = summarize_results(summary.values())
    expected_best = max(summary.values(), key=lambda result: result.actual_change)
    expected_worst = min(summary.values(), key=lambda result: result.actual_change)

    assert parallel_shift_impact(portfolio, curve=curve, settlement_date=ref, bump_bps=Decimal("10")) == rate_shock_impact(
        portfolio,
        curve=curve,
        settlement_date=ref,
        bump_bps=Decimal("10"),
    )
    assert best_case(summarized) == expected_best
    assert worst_case(summary) == expected_worst
