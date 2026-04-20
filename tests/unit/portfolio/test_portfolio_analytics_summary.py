from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Currency, Date
from fuggers_py.portfolio import AnalyticsConfig, CashPosition, Portfolio, PortfolioBuilder, calculate_portfolio_analytics
from fuggers_py.portfolio.analytics import PortfolioAnalytics

from tests.helpers._portfolio_helpers import make_curve, make_portfolio


def test_portfolio_summary_empty() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = Portfolio.new([], currency=Currency.USD)
    metrics = calculate_portfolio_analytics(portfolio, curve=make_curve(ref), settlement_date=ref)
    assert metrics.dirty_pv == Decimal("0")
    assert metrics.holding_count == 0


def test_portfolio_summary_basic_aggregation() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    metrics = calculate_portfolio_analytics(portfolio, curve=make_curve(ref), settlement_date=ref.add_days(30))
    assert metrics.total_dirty_market_value >= metrics.total_market_value
    assert metrics.holding_count == 3


def test_weighted_yields_are_market_value_weighted() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = make_curve(ref)
    portfolio = make_portfolio(ref)
    analytics = PortfolioAnalytics(portfolio)
    positions = analytics.position_metrics(curve, ref)
    metrics = analytics.metrics(curve, ref, config=AnalyticsConfig(settlement_date=ref))
    total_dirty = sum((item.dirty_value for item in positions), Decimal(0))
    manual = sum(((item.ytm or Decimal(0)) * item.dirty_value for item in positions), Decimal(0)) / total_dirty
    assert float(metrics.ytm) == pytest.approx(float(manual))


def test_weighted_risk_is_market_value_weighted() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = make_curve(ref)
    portfolio = make_portfolio(ref)
    analytics = PortfolioAnalytics(portfolio)
    positions = analytics.position_metrics(curve, ref)
    metrics = analytics.metrics(curve, ref)
    total_dirty = sum((item.dirty_value for item in positions), Decimal(0))
    manual = sum((item.duration * item.dirty_value for item in positions), Decimal(0)) / total_dirty
    assert float(metrics.duration) == pytest.approx(float(manual))


def test_weighted_spreads_are_market_value_weighted_where_available() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    curve = make_curve(ref)
    portfolio = make_portfolio(ref)
    analytics = PortfolioAnalytics(portfolio)
    positions = analytics.position_metrics(curve, ref)
    metrics = analytics.metrics(curve, ref)
    total_dirty = sum((item.dirty_value for item in positions), Decimal(0))
    manual = sum(((item.z_spread or Decimal(0)) * item.dirty_value for item in positions), Decimal(0)) / total_dirty
    assert float(metrics.z_spread) == pytest.approx(float(manual))


def test_coverage_counts_ignore_missing_analytics() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = PortfolioBuilder().with_currency(Currency.USD).add_positions(list(make_portfolio(ref).positions)).add_position(
        CashPosition(amount=Decimal("10"), currency=Currency.USD)
    ).build()
    metrics = calculate_portfolio_analytics(portfolio, curve=make_curve(ref), settlement_date=ref)
    assert metrics.coverage_count == 3
