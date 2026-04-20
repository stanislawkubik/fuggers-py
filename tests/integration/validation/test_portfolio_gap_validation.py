from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Date
from fuggers_py.portfolio import (
    aggregate_key_rate_profile,
    best_case,
    bucket_by_classifier,
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

from tests.helpers._portfolio_helpers import make_curve, make_portfolio

from ._helpers import D, assert_decimal_close, load_fixture


pytestmark = pytest.mark.validation


def test_per_share_risk_and_liquidity_helpers_match_reference_portfolio_case() -> None:
    fixture = load_fixture("portfolio", "portfolio.json")["benchmark_and_risk_case"]
    reference_date = Date.parse(fixture["reference_date"])
    shares = Decimal("1000")
    portfolio = make_portfolio(reference_date)
    curve = make_curve(reference_date)
    metrics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=reference_date)
    liquidity = estimate_days_to_liquidate(portfolio, curve=curve, settlement_date=reference_date)

    assert dv01_per_share(portfolio, curve=curve, settlement_date=reference_date, shares_outstanding=shares) == metrics.dv01 / shares
    assert cs01_per_share(portfolio, curve=curve, settlement_date=reference_date, shares_outstanding=shares) == metrics.cs01 / shares
    assert_decimal_close(liquidity.days, D(fixture["expected_days_to_liquidate"]), Decimal("1e-24"))
    assert estimate_days_to_liquidate(
        portfolio,
        curve=curve,
        settlement_date=reference_date,
        liquidation_fraction=Decimal("0.5"),
    ).days == liquidity.days / 2


def test_key_rate_profile_and_classifier_buckets_match_existing_reference_breakdowns() -> None:
    fixture = load_fixture("portfolio", "portfolio.json")["benchmark_and_risk_case"]
    reference_date = Date.parse(fixture["reference_date"])
    portfolio = make_portfolio(reference_date)
    curve = make_curve(reference_date)
    partials = aggregate_key_rate_profile(portfolio, curve=curve, settlement_date=reference_date)
    by_sector = bucket_by_classifier(portfolio, "sector")

    assert partials.total_dv01 == sum(partials.values(), Decimal(0))
    assert by_sector["GOVERNMENT"][0].name() == "gov_short"
    assert sorted(by_sector.keys()) == ["CORPORATE", "GOVERNMENT", "INDUSTRIALS"]


def test_stress_summary_helpers_match_manual_extrema_on_reference_portfolio() -> None:
    fixture = load_fixture("portfolio", "portfolio.json")["stress_case"]
    reference_date = Date.parse(fixture["reference_date"])
    portfolio = make_portfolio(reference_date)
    curve = make_curve(reference_date)
    summary = run_stress_scenarios(portfolio, curve=curve, settlement_date=reference_date, scenarios=standard_scenarios())
    summarized = summarize_results(summary.values())
    expected_best = max(summary.values(), key=lambda result: result.actual_change)
    expected_worst = min(summary.values(), key=lambda result: result.actual_change)

    assert parallel_shift_impact(portfolio, curve=curve, settlement_date=reference_date, bump_bps=Decimal("10")) == rate_shock_impact(
        portfolio,
        curve=curve,
        settlement_date=reference_date,
        bump_bps=Decimal("10"),
    )
    assert best_case(summarized) == expected_best
    assert worst_case(summary) == expected_worst
