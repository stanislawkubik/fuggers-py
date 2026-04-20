from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py._core import Currency, Date
from fuggers_py.portfolio import Portfolio, PortfolioBenchmark, PortfolioBuilder, estimate_tracking_error
from fuggers_py.portfolio.analytics import PortfolioAnalytics
from fuggers_py.portfolio.contribution import (
    attribution_summary,
    contribution_by_rating,
    contribution_by_sector,
    dv01_contributions,
    spread_contributions,
)

from tests.helpers._portfolio_helpers import make_benchmark, make_curve, make_portfolio


def test_grouped_contributions_reconcile_to_portfolio_totals_across_metrics() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    positions = PortfolioAnalytics(portfolio).position_metrics(curve, ref)

    duration_total = sum((item.duration for item in positions), Decimal(0))
    dv01_total = dv01_contributions(portfolio, curve=curve, settlement_date=ref).total
    spread_total = spread_contributions(portfolio, curve=curve, settlement_date=ref).total

    assert float(
        sum(contribution_by_sector(portfolio, curve=curve, settlement_date=ref, metric="duration").values(), Decimal(0))
    ) == pytest.approx(float(duration_total))
    assert float(
        sum(contribution_by_rating(portfolio, curve=curve, settlement_date=ref, metric="dv01").values(), Decimal(0))
    ) == pytest.approx(float(dv01_total))
    assert float(
        sum(contribution_by_sector(portfolio, curve=curve, settlement_date=ref, metric="spread").values(), Decimal(0))
    ) == pytest.approx(float(spread_total))


def test_grouped_contributions_bucket_unclassified_positions() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    base = make_portfolio(ref)
    positions = list(base.positions)
    positions[0] = replace(positions[0], classification=None)
    portfolio = Portfolio.new(positions, currency=base.currency)
    curve = make_curve(ref)

    sector = contribution_by_sector(portfolio, curve=curve, settlement_date=ref)
    rating = contribution_by_rating(portfolio, curve=curve, settlement_date=ref)

    assert "UNCLASSIFIED" in sector
    assert "UNCLASSIFIED" in rating
    assert sector["UNCLASSIFIED"] != Decimal(0)
    assert rating["UNCLASSIFIED"] != Decimal(0)


def test_attribution_summary_is_stable_for_empty_portfolios() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = PortfolioBuilder().with_currency(Currency.USD).build()
    attribution = attribution_summary(portfolio, curve=make_curve(ref), settlement_date=ref)

    assert len(attribution) == 0
    assert attribution.total_pv_pct == Decimal(0)
    assert attribution.total_dv01_pct == Decimal(0)
    assert attribution.total_duration_contribution == Decimal(0)


def test_tracking_error_estimate_components_sum_and_compare_like_decimals() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = make_curve(ref)
    benchmark = PortfolioBenchmark(make_portfolio(ref), make_benchmark(ref))
    comparison = benchmark.compare(curve, ref)
    weights = benchmark.active_weights(curve, ref)
    estimate = estimate_tracking_error(benchmark, curve, ref)
    expected = (
        abs(comparison.active_duration) * Decimal("0.01")
        + abs(comparison.active_z_spread) * Decimal("0.001")
        + sum((abs(value) for value in weights.values()), Decimal(0)) * Decimal("0.005")
    )

    assert estimate.estimate == expected
    assert estimate.duration_component + estimate.spread_component + estimate.dispersion_component == expected
    assert estimate == expected
    assert estimate > Decimal(0)
    assert float(estimate) == pytest.approx(float(expected), abs=1e-12)
