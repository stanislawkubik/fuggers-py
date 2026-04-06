from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date
from fuggers_py.portfolio import calculate_portfolio_analytics, parallel_shift_impact, rate_shock_impact
from fuggers_py.portfolio.analytics import (
    calculate_liquidity_metrics,
    calculate_nav_breakdown,
    total_cs01,
    total_dv01,
    weighted_convexity,
    weighted_duration,
    weighted_spread_duration,
    weighted_asw,
    weighted_current_yield,
    weighted_oas,
    weighted_spreads,
    weighted_ytc,
    weighted_ytm,
    weighted_ytw,
)
from fuggers_py.portfolio.risk import calculate_risk_metrics, calculate_spread_metrics, calculate_yield_metrics
from fuggers_py.portfolio.portfolio import Portfolio
from fuggers_py.portfolio.types import CashPosition, HoldingBuilder

from tests.helpers._portfolio_helpers import make_curve, make_holding, make_portfolio


def test_portfolio_analytics_wrappers_match_aggregated_metrics() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    metrics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=ref)

    risk = calculate_risk_metrics(portfolio, curve=curve, settlement_date=ref)
    yields = calculate_yield_metrics(portfolio, curve=curve, settlement_date=ref)
    spreads = calculate_spread_metrics(portfolio, curve=curve, settlement_date=ref)
    nav = calculate_nav_breakdown(portfolio, curve=curve, settlement_date=ref)
    liquidity = calculate_liquidity_metrics(portfolio, curve=curve, settlement_date=ref)

    assert weighted_duration(portfolio, curve=curve, settlement_date=ref) == metrics.duration
    assert weighted_convexity(portfolio, curve=curve, settlement_date=ref) == metrics.convexity
    assert total_dv01(portfolio, curve=curve, settlement_date=ref) == metrics.dv01
    assert total_cs01(portfolio, curve=curve, settlement_date=ref) == metrics.cs01
    assert weighted_ytm(portfolio, curve=curve, settlement_date=ref) == metrics.ytm
    assert weighted_ytw(portfolio, curve=curve, settlement_date=ref) == metrics.ytw
    assert weighted_ytc(portfolio, curve=curve, settlement_date=ref) == metrics.ytc
    assert weighted_current_yield(portfolio, curve=curve, settlement_date=ref) == metrics.current_yield
    assert weighted_spreads(portfolio, curve=curve, settlement_date=ref) == metrics.z_spread
    assert weighted_oas(portfolio, curve=curve, settlement_date=ref) == metrics.oas
    assert weighted_asw(portfolio, curve=curve, settlement_date=ref) == metrics.asw
    assert weighted_spread_duration(portfolio, curve=curve, settlement_date=ref) == metrics.spread_duration
    assert risk.effective_duration == metrics.effective_duration
    assert yields.best_yield == metrics.best_yield
    assert spreads.spread_duration == metrics.spread_duration
    assert nav.dirty_market_value == metrics.total_dirty_market_value
    assert liquidity["liquidity_score"] == metrics.liquidity_score


def test_parallel_rate_impact_matches_stress_helper() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)
    bump = Decimal("15")

    assert parallel_shift_impact(portfolio, curve=curve, settlement_date=ref, bump_bps=bump) == rate_shock_impact(
        portfolio,
        curve=curve,
        settlement_date=ref,
        bump_bps=bump,
    )


def test_holding_builder_and_portfolio_container_cover_market_value_helpers() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    base = make_holding(
        ref,
        years=4,
        coupon="0.0425",
        label="builder",
        sector=make_portfolio(ref).positions[0].classification.sector,
        rating=make_portfolio(ref).positions[0].classification.rating,
        quantity="150",
        price="99.25",
    )
    holding = (
        HoldingBuilder()
        .with_instrument(base.instrument)
        .with_quantity("150")
        .with_market_price(Decimal("99.25"))
        .with_label("builder")
        .with_id("builder-id")
        .with_classification(base.classification)
        .with_rating_info(base.rating_info)
        .with_sector_info(base.sector_info)
        .with_liquidity_score("0.82")
        .with_fx_rate("1.10")
        .build()
    )
    portfolio = Portfolio.new(
        [
            holding,
            CashPosition(amount=Decimal("25"), currency=Currency.USD, fx_rate=Decimal("1.10")),
        ],
        currency=Currency.USD,
    )

    assert holding.market_value_amount == Decimal("14887.50")
    assert holding.weight_in_portfolio(Decimal("15000")) == pytest.approx(Decimal("0.9925"))
    assert holding.base_currency_value == Decimal("16376.250")
    assert portfolio.total_quantity() == Decimal("150")
    assert len(portfolio.investable_holdings()) == 1
    assert len(portfolio.cash_positions()) == 1
    assert portfolio.total_market_value() == Decimal("14912.50")
