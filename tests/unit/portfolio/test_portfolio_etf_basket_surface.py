from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py._core import Currency, Date
from fuggers_py.portfolio import (
    BasketAnalysis,
    BasketComponent,
    BasketFlowSummary,
    CashPosition,
    CreationBasket,
    ExpenseMetrics,
    Portfolio,
    PremiumDiscountPoint,
    analyze_etf_basket,
    arbitrage_opportunity,
    build_creation_basket,
    calculate_portfolio_analytics,
    estimate_yield_from_holdings,
)

from tests.helpers._portfolio_helpers import make_curve, make_portfolio


def test_build_creation_basket_and_yield_estimate_are_typed_and_reconcile() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    base = make_portfolio(ref)
    portfolio = Portfolio.new(
        [
            *base.positions,
            CashPosition(amount=Decimal("50"), currency=Currency.USD),
        ],
        currency=base.currency,
    )
    curve = make_curve(ref)
    basket = build_creation_basket(
        portfolio,
        curve=curve,
        settlement_date=ref,
        shares_outstanding=Decimal("1000"),
        creation_unit_shares=Decimal("100"),
        liabilities=Decimal("20"),
    )
    yield_metrics = estimate_yield_from_holdings(
        portfolio,
        curve=curve,
        settlement_date=ref,
        gross_expense_ratio=Decimal("0.0020"),
        fee_waiver_ratio=Decimal("0.0005"),
    )
    analytics = calculate_portfolio_analytics(portfolio, curve=curve, settlement_date=ref)

    assert isinstance(basket, CreationBasket)
    assert isinstance(basket[0], BasketComponent)
    assert isinstance(basket.flow_summary, BasketFlowSummary)
    assert basket.component_count == 3
    assert basket.flow_summary.total_quantity == Decimal("30")
    assert basket.by_name("gov_short") is not None
    assert float(sum((component.weight for component in basket), Decimal(0))) == pytest.approx(1.0)
    assert basket.flow_summary.cash_component == Decimal("5")
    assert basket.flow_summary.liabilities_component == Decimal("2")
    assert basket.flow_summary.total_basket_value == basket.flow_summary.securities_dirty_value + Decimal("3")
    assert basket.basket_per_share == basket.flow_summary.total_basket_value / Decimal("100")

    assert isinstance(yield_metrics, ExpenseMetrics)
    assert yield_metrics.gross_yield == analytics.ytm
    assert yield_metrics.net_expense_ratio == Decimal("0.0015")
    assert yield_metrics.net_yield == analytics.ytm - Decimal("0.0015")
    assert yield_metrics.expense_drag == Decimal("0.0015")
    assert yield_metrics.annual_expense_amount == analytics.dirty_pv * Decimal("0.0015")


def test_arbitrage_opportunity_is_typed_and_directional() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)

    premium = arbitrage_opportunity(
        portfolio,
        curve=curve,
        settlement_date=ref,
        shares_outstanding=Decimal("1000"),
        market_price=Decimal("30"),
    )
    discount = arbitrage_opportunity(
        portfolio,
        curve=curve,
        settlement_date=ref,
        shares_outstanding=Decimal("1000"),
        market_price=Decimal("29.70"),
    )
    too_costly = arbitrage_opportunity(
        portfolio,
        curve=curve,
        settlement_date=ref,
        shares_outstanding=Decimal("1000"),
        market_price=Decimal("29.86"),
        transaction_cost_bps=Decimal("10"),
    )

    assert isinstance(premium, PremiumDiscountPoint)
    assert premium.direction == "create"
    assert premium.is_actionable is True
    assert premium.estimated_edge_per_share == Decimal("0.15")
    assert premium.premium_discount_bps == premium.premium_discount.premium_discount_bps

    assert discount.direction == "redeem"
    assert discount.is_actionable is True
    assert discount.estimated_edge_per_share == Decimal("0.15")

    assert too_costly.direction == "none"
    assert too_costly.is_actionable is False
    assert too_costly.estimated_edge_per_share < Decimal(0)


def test_empty_etf_surface_returns_zero_like_results() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    empty = Portfolio.new([], currency=Currency.USD)
    curve = make_curve(ref)

    analysis = analyze_etf_basket(empty)
    basket = build_creation_basket(
        empty,
        curve=curve,
        settlement_date=ref,
        shares_outstanding=Decimal("1000"),
        creation_unit_shares=Decimal("50000"),
    )
    yield_metrics = estimate_yield_from_holdings(empty, curve=curve, settlement_date=ref)

    assert isinstance(analysis, BasketAnalysis)
    assert analysis.num_positions == 0
    assert isinstance(basket, CreationBasket)
    assert len(basket) == 0
    assert basket.flow_summary.total_basket_value == Decimal(0)
    assert basket.basket_per_share == Decimal(0)
    assert yield_metrics.gross_yield == Decimal(0)
    assert yield_metrics.net_assets == Decimal(0)


def test_creation_basket_and_arbitrage_validate_share_counts_and_prices() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)

    with pytest.raises(ValueError, match="shares_outstanding must be positive"):
        build_creation_basket(
            portfolio,
            curve=make_curve(ref),
            settlement_date=ref,
            shares_outstanding=Decimal(0),
        )

    with pytest.raises(ValueError, match="creation_unit_shares must be positive"):
        build_creation_basket(
            portfolio,
            curve=make_curve(ref),
            settlement_date=ref,
            shares_outstanding=Decimal("1000"),
            creation_unit_shares=Decimal(0),
        )

    with pytest.raises(ValueError, match="shares_outstanding must be positive"):
        arbitrage_opportunity(
            portfolio,
            curve=make_curve(ref),
            settlement_date=ref,
            shares_outstanding=Decimal(0),
            market_price=Decimal("30"),
        )

    missing_price = replace(portfolio.positions[0], clean_price=None, market_value=None)
    missing_portfolio = Portfolio.new([missing_price, *portfolio.positions[1:]], currency=portfolio.currency)

    with pytest.raises(ValueError, match="requires prices or a valuation curve"):
        build_creation_basket(
            missing_portfolio,
            curve=None,
            settlement_date=ref,
            shares_outstanding=Decimal("1000"),
        )


def test_estimate_yield_from_holdings_validates_expense_inputs() -> None:
    ref = Date.from_ymd(2024, 1, 1)
    portfolio = make_portfolio(ref)
    curve = make_curve(ref)

    with pytest.raises(ValueError, match="gross_expense_ratio must be non-negative"):
        estimate_yield_from_holdings(
            portfolio,
            curve=curve,
            settlement_date=ref,
            gross_expense_ratio=Decimal("-0.001"),
        )

    with pytest.raises(ValueError, match="fee_waiver_ratio must be non-negative"):
        estimate_yield_from_holdings(
            portfolio,
            curve=curve,
            settlement_date=ref,
            fee_waiver_ratio=Decimal("-0.001"),
        )
