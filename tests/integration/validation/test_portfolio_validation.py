from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Date
from fuggers_py.portfolio import (
    BasketAnalysis,
    BasketComponent,
    CashPosition,
    CreationBasket,
    ExpenseMetrics,
    EtfNavMetrics,
    Portfolio,
    PortfolioBenchmark,
    PremiumDiscountPoint,
    SecYield,
    SecYieldInput,
    active_weights,
    analyze_etf_basket,
    arbitrage_opportunity,
    benchmark_comparison,
    build_creation_basket,
    calculate_etf_nav_metrics,
    calculate_liquidity_metrics,
    calculate_sec_yield,
    duration_contributions,
    dv01_contributions,
    estimate_yield_from_holdings,
    estimate_tracking_error,
    premium_discount_stats,
    run_stress_scenarios,
    spread_contributions,
    standard_scenarios,
)
from fuggers_py.portfolio.contribution.attribution import attribution_summary

from tests.helpers._portfolio_helpers import make_benchmark, make_curve, make_portfolio

from ._helpers import D, assert_decimal_close, load_fixture


pytestmark = pytest.mark.validation


def test_portfolio_benchmark_contribution_and_liquidity_match_reference_fixture() -> None:
    fixture = load_fixture("portfolio", "portfolio.json")["benchmark_and_risk_case"]
    reference_date = Date.parse(fixture["reference_date"])
    portfolio = make_portfolio(reference_date)
    benchmark = make_benchmark(reference_date)
    curve = make_curve(reference_date)

    comparison = benchmark_comparison(portfolio, benchmark, curve, reference_date)
    weights = active_weights(portfolio, benchmark, curve, reference_date)
    liquidity = calculate_liquidity_metrics(portfolio, curve=curve, settlement_date=reference_date)
    benchmark_wrapper = PortfolioBenchmark(portfolio, benchmark)

    assert_decimal_close(comparison.active_duration, D(fixture["expected_active_duration"]), Decimal("1e-24"))
    assert_decimal_close(comparison.active_dv01, D(fixture["expected_active_dv01"]), Decimal("1e-24"))
    assert_decimal_close(weights.net_active_weight, Decimal(fixture["expected_net_active_weight"]), Decimal("1e-24"))
    assert_decimal_close(
        estimate_tracking_error(benchmark_wrapper, curve, reference_date).estimate,
        D(fixture["expected_tracking_error"]),
        Decimal("1e-24"),
    )

    expected_sector = fixture["expected_sector_active_weights"]
    actual_sector = {entry.name: entry.active_weight for entry in comparison.sector.active_weights.entries}
    for sector, expected in expected_sector.items():
        assert_decimal_close(actual_sector[sector], D(expected), Decimal("1e-24"))

    duration_total = duration_contributions(portfolio, curve=curve, settlement_date=reference_date).total
    dv01_total = dv01_contributions(portfolio, curve=curve, settlement_date=reference_date).total
    spread_total = spread_contributions(portfolio, curve=curve, settlement_date=reference_date).total
    attribution = attribution_summary(portfolio, curve=curve, settlement_date=reference_date)

    assert_decimal_close(duration_total, D(fixture["expected_duration_contribution_total"]), Decimal("1e-24"))
    assert_decimal_close(dv01_total, D(fixture["expected_dv01_contribution_total"]), Decimal("1e-24"))
    assert_decimal_close(spread_total, D(fixture["expected_cs01_contribution_total"]), Decimal("1e-18"))
    assert_decimal_close(attribution.total_duration_contribution, D(fixture["expected_attribution_duration_total"]), Decimal("1e-24"))

    assert_decimal_close(liquidity.liquidity_score, D(fixture["expected_liquidity_score"]), Decimal("1e-24"))
    assert_decimal_close(liquidity.days_to_liquidate.days, D(fixture["expected_days_to_liquidate"]), Decimal("1e-24"))
    assert_decimal_close(liquidity.distribution.total_weight, Decimal(1), Decimal("1e-24"))
    expected_distribution = fixture["expected_distribution"]
    for entry in liquidity.distribution.entries:
        expected = expected_distribution[entry.label]
        assert_decimal_close(entry.weight, D(expected["weight"]), Decimal("1e-24"))
        assert_decimal_close(entry.dirty_pv, D(expected["dirty_pv"]), Decimal("1e-24"))
        assert entry.holding_count == int(expected["holding_count"])


def test_portfolio_stress_summary_matches_reference_fixture() -> None:
    fixture = load_fixture("portfolio", "portfolio.json")["stress_case"]
    reference_date = Date.parse(fixture["reference_date"])
    portfolio = make_portfolio(reference_date)
    curve = make_curve(reference_date)
    summary = run_stress_scenarios(portfolio, curve=curve, settlement_date=reference_date, scenarios=standard_scenarios())

    assert_decimal_close(summary.aggregate_change, D(fixture["expected_aggregate_change"]), Decimal("1e-24"))
    assert_decimal_close(summary.worst_loss, D(fixture["expected_worst_loss"]), Decimal("1e-24"))
    assert_decimal_close(summary.best_gain, D(fixture["expected_best_gain"]), Decimal("1e-24"))
    for scenario_name, expected in fixture["expected_scenarios"].items():
        result = summary[scenario_name]
        assert_decimal_close(result.actual_change, D(expected["actual_change"]), Decimal("1e-24"))
        assert_decimal_close(result.stressed_dirty_pv, D(expected["stressed_dirty_pv"]), Decimal("1e-18"))


def test_etf_nav_premium_discount_sec_yield_and_basket_analysis_match_reference_fixture() -> None:
    fixture = load_fixture("portfolio", "etf.json")["simple_etf_case"]
    reference_date = Date.parse(fixture["reference_date"])
    portfolio = make_portfolio(reference_date)
    curve = make_curve(reference_date)
    shares_outstanding = D(fixture["shares_outstanding"])
    nav_metrics = calculate_etf_nav_metrics(
        portfolio,
        curve=curve,
        settlement_date=reference_date,
        shares_outstanding=shares_outstanding,
        market_price=D(fixture["market_price"]),
    )
    premium_discount = premium_discount_stats(nav_metrics.nav_per_share, D(fixture["market_price"]))
    basket = analyze_etf_basket(portfolio)
    sec_yield = calculate_sec_yield(
        SecYieldInput(
            net_investment_income=D(fixture["net_investment_income"]),
            average_shares_outstanding=D(fixture["average_shares_outstanding"]),
            max_offering_price=D(fixture["max_offering_price"]),
            gross_expenses=D(fixture["gross_expenses"]),
            fee_waivers=D(fixture["fee_waivers"]),
            as_of_date=reference_date,
        )
    )

    assert isinstance(nav_metrics, EtfNavMetrics)
    assert isinstance(basket, BasketAnalysis)
    assert isinstance(sec_yield, SecYield)
    assert sec_yield.unsubsidized_yield is not None
    assert_decimal_close(nav_metrics.nav_per_share, D(fixture["expected_nav"]), Decimal("1e-24"))
    assert_decimal_close(premium_discount.premium_discount_bps, D(fixture["expected_premium_discount_bps"]), Decimal("1e-24"))
    assert_decimal_close(sec_yield.sec_30_day_yield, D(fixture["expected_sec_30_day_yield"]), Decimal("1e-24"))
    assert_decimal_close(sec_yield.unsubsidized_yield, D(fixture["expected_unsubsidized_yield"]), Decimal("1e-24"))
    assert basket.num_positions == fixture["expected_basket"]["num_positions"]
    assert basket.sector_counts == fixture["expected_basket"]["sector_counts"]
    assert basket.total_quantity == D(fixture["expected_basket"]["total_quantity"])


def test_etf_creation_basket_arbitrage_and_holdings_yield_match_reference_fixture() -> None:
    fixture = load_fixture("portfolio", "etf.json")["creation_basket_case"]
    reference_date = Date.parse(fixture["reference_date"])
    base_portfolio = make_portfolio(reference_date)
    portfolio = Portfolio.new(
        [
            *base_portfolio.positions,
            CashPosition(amount=D(fixture["cash_amount"]), currency=base_portfolio.currency),
        ],
        currency=base_portfolio.currency,
    )
    curve = make_curve(reference_date)
    basket = build_creation_basket(
        portfolio,
        curve=curve,
        settlement_date=reference_date,
        shares_outstanding=D(fixture["shares_outstanding"]),
        creation_unit_shares=D(fixture["creation_unit_shares"]),
        liabilities=D(fixture["liabilities"]),
    )
    opportunity = arbitrage_opportunity(
        portfolio,
        curve=curve,
        settlement_date=reference_date,
        shares_outstanding=D(fixture["shares_outstanding"]),
        liabilities=D(fixture["liabilities"]),
        market_price=D(fixture["market_price"]),
    )
    holdings_yield = estimate_yield_from_holdings(
        portfolio,
        curve=curve,
        settlement_date=reference_date,
        gross_expense_ratio=D(fixture["gross_expense_ratio"]),
        fee_waiver_ratio=D(fixture["fee_waiver_ratio"]),
    )

    assert isinstance(basket, CreationBasket)
    assert isinstance(basket[0], BasketComponent)
    assert isinstance(opportunity, PremiumDiscountPoint)
    assert isinstance(holdings_yield, ExpenseMetrics)

    summary_fixture = fixture["expected_basket_summary"]
    assert basket.flow_summary.component_count == summary_fixture["component_count"]
    assert_decimal_close(basket.flow_summary.total_quantity, D(summary_fixture["total_quantity"]), Decimal("1e-24"))
    assert_decimal_close(
        basket.flow_summary.securities_market_value,
        D(summary_fixture["securities_market_value"]),
        Decimal("1e-24"),
    )
    assert_decimal_close(
        basket.flow_summary.total_basket_value,
        D(summary_fixture["total_basket_value"]),
        Decimal("1e-24"),
    )
    assert_decimal_close(
        basket.flow_summary.basket_per_share,
        D(summary_fixture["basket_per_share"]),
        Decimal("1e-24"),
    )

    first_component = basket.by_name("gov_short")
    assert first_component is not None
    component_fixture = fixture["expected_first_component"]
    assert first_component.sector == component_fixture["sector"]
    assert_decimal_close(first_component.quantity, D(component_fixture["quantity"]), Decimal("1e-24"))
    assert_decimal_close(first_component.weight, D(component_fixture["weight"]), Decimal("1e-24"))

    arbitrage_fixture = fixture["expected_arbitrage"]
    assert opportunity.direction == arbitrage_fixture["direction"]
    assert opportunity.is_actionable is arbitrage_fixture["is_actionable"]
    assert_decimal_close(opportunity.nav_per_share, D(arbitrage_fixture["nav_per_share"]), Decimal("1e-24"))
    assert_decimal_close(
        opportunity.estimated_edge_per_share,
        D(arbitrage_fixture["estimated_edge_per_share"]),
        Decimal("1e-24"),
    )
    assert_decimal_close(opportunity.premium_discount_bps, D(arbitrage_fixture["premium_discount_bps"]), Decimal("1e-24"))

    yield_fixture = fixture["expected_yield"]
    assert_decimal_close(holdings_yield.gross_yield, D(yield_fixture["gross_yield"]), Decimal("1e-24"))
    assert_decimal_close(holdings_yield.net_yield, D(yield_fixture["net_yield"]), Decimal("1e-24"))
    assert_decimal_close(
        holdings_yield.annual_income_estimate,
        D(yield_fixture["annual_income_estimate"]),
        Decimal("1e-18"),
    )
    assert_decimal_close(
        holdings_yield.annual_expense_amount,
        D(yield_fixture["annual_expense_amount"]),
        Decimal("1e-24"),
    )
