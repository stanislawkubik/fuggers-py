"""Portfolio analytics package.

This namespace re-exports the main portfolio summary, risk, spread, yield,
liquidity, credit, key-rate, and quote-output aggregation helpers used
throughout the public surface.
"""

from __future__ import annotations

from decimal import Decimal

from ..liquidity import (
    DaysToLiquidate,
    LiquidityBucket,
    LiquidityDistribution,
    LiquidityMetrics,
    calculate_liquidity_metrics,
    estimate_days_to_liquidate,
    liquidity_distribution,
    weighted_bid_ask_spread,
    weighted_liquidity_score,
)
from ..portfolio import Portfolio
from ..results import KeyRateProfile, NavBreakdown
from ..risk import (
    calculate_risk_metrics,
    calculate_spread_metrics,
    calculate_yield_metrics,
    weighted_asw,
    weighted_oas,
    weighted_spread_duration,
)
from .base import PortfolioAnalytics
from .credit import calculate_credit_quality
from .quote_outputs import PortfolioAnalyzer, PortfolioPosition
from .summary import calculate_portfolio_analytics


def _metrics(portfolio: Portfolio, *, curve, settlement_date):
    return PortfolioAnalytics(portfolio).metrics(curve, settlement_date)


def aggregate_key_rate_profile(portfolio: Portfolio, *, curve, settlement_date) -> KeyRateProfile:
    """Return the portfolio key-rate DV01 profile."""

    return KeyRateProfile(entries=dict(_metrics(portfolio, curve=curve, settlement_date=settlement_date).key_rate_profile))


def partial_dv01s(portfolio: Portfolio, *, curve, settlement_date) -> KeyRateProfile:
    """Compatibility alias for :func:`aggregate_key_rate_profile`."""

    return aggregate_key_rate_profile(portfolio, curve=curve, settlement_date=settlement_date)


def calculate_nav_breakdown(portfolio: Portfolio, *, curve, settlement_date) -> NavBreakdown:
    """Return the portfolio NAV split into clean, dirty, and cash components."""

    metrics = _metrics(portfolio, curve=curve, settlement_date=settlement_date)
    return NavBreakdown(
        clean_pv=metrics.clean_pv,
        dirty_pv=metrics.dirty_pv,
        accrued=metrics.accrued,
        market_value=metrics.total_market_value,
        dirty_market_value=metrics.total_dirty_market_value,
        cash_value=metrics.cash_value,
    )


def weighted_duration(portfolio: Portfolio, *, curve, settlement_date) -> Decimal:
    """Return portfolio duration as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).duration


def weighted_convexity(portfolio: Portfolio, *, curve, settlement_date) -> Decimal:
    """Return portfolio convexity as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).convexity


def total_dv01(portfolio: Portfolio, *, curve, settlement_date) -> Decimal:
    """Return portfolio DV01 in currency units per 1 bp."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).dv01


def total_cs01(portfolio: Portfolio, *, curve, settlement_date) -> Decimal:
    """Return portfolio CS01 in currency units per 1 bp."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).cs01


def weighted_spreads(portfolio: Portfolio, *, curve, settlement_date) -> Decimal:
    """Return the portfolio Z-spread as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).z_spread


def weighted_ytm(portfolio: Portfolio, *, curve, settlement_date) -> Decimal:
    """Return the portfolio yield to maturity as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).ytm


def weighted_ytw(portfolio: Portfolio, *, curve, settlement_date) -> Decimal:
    """Return the portfolio yield to worst as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).ytw


def weighted_ytc(portfolio: Portfolio, *, curve, settlement_date) -> Decimal:
    """Return the portfolio yield to call as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).ytc


def weighted_current_yield(portfolio: Portfolio, *, curve, settlement_date) -> Decimal:
    """Return the portfolio current yield as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).current_yield


__all__ = [
    "DaysToLiquidate",
    "KeyRateProfile",
    "LiquidityBucket",
    "LiquidityDistribution",
    "LiquidityMetrics",
    "NavBreakdown",
    "PortfolioAnalytics",
    "PortfolioAnalyzer",
    "PortfolioPosition",
    "aggregate_key_rate_profile",
    "calculate_credit_quality",
    "calculate_liquidity_metrics",
    "calculate_nav_breakdown",
    "calculate_portfolio_analytics",
    "calculate_risk_metrics",
    "calculate_spread_metrics",
    "calculate_yield_metrics",
    "estimate_days_to_liquidate",
    "liquidity_distribution",
    "partial_dv01s",
    "total_cs01",
    "total_dv01",
    "weighted_asw",
    "weighted_bid_ask_spread",
    "weighted_convexity",
    "weighted_current_yield",
    "weighted_duration",
    "weighted_liquidity_score",
    "weighted_oas",
    "weighted_spread_duration",
    "weighted_spreads",
    "weighted_ytc",
    "weighted_ytm",
    "weighted_ytw",
]
