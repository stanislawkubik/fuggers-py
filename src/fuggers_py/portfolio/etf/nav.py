"""ETF NAV helpers.

NAV helpers report per-share portfolio value, risk per share, and premium or
discount metrics using raw decimals unless a field name explicitly says
``_bps`` or ``_pct``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..analytics import PortfolioAnalytics
from ..portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class PremiumDiscountStats:
    """Portfolio premium or discount relative to NAV."""

    premium_discount: Decimal
    premium_discount_bps: Decimal
    premium_discount_pct: Decimal

    @property
    def premium_discount_dollars(self) -> Decimal:
        """Return the per-share premium or discount in currency units."""

        return self.premium_discount

    @property
    def is_premium(self) -> bool:
        """Return ``True`` when the market price is above NAV."""

        return self.premium_discount > 0

    @property
    def is_discount(self) -> bool:
        """Return ``True`` when the market price is below NAV."""

        return self.premium_discount < 0


@dataclass(frozen=True, slots=True)
class PremiumDiscountPoint:
    """Premium/discount evaluation point with actionable edge data."""

    nav_per_share: Decimal
    market_price: Decimal
    shares_outstanding: Decimal
    premium_discount: PremiumDiscountStats
    premium_discount_dollars: Decimal
    estimated_edge_per_share: Decimal
    estimated_edge_bps: Decimal
    direction: str
    is_actionable: bool

    @property
    def premium_discount_pct(self) -> Decimal:
        """Return the premium or discount in percent."""

        return self.premium_discount.premium_discount_pct

    @property
    def premium_discount_bps(self) -> Decimal:
        """Return the premium or discount in basis points."""

        return self.premium_discount.premium_discount_bps


@dataclass(frozen=True, slots=True)
class EtfNavMetrics:
    """ETF NAV, iNAV, and per-share risk metrics."""

    total_nav: Decimal
    shares_outstanding: Decimal
    nav_per_share: Decimal
    dv01_per_share: Decimal
    cs01_per_share: Decimal
    securities_value: Decimal
    cash_value: Decimal
    accrued_interest: Decimal
    liabilities: Decimal
    inav: Decimal | None = None
    market_price: Decimal | None = None
    premium_discount: PremiumDiscountStats | None = None
    premium_discount_dollars: Decimal | None = None

    @property
    def premium_discount_pct(self) -> Decimal | None:
        """Return the premium or discount in percent."""

        return None if self.premium_discount is None else self.premium_discount.premium_discount_pct

    @property
    def premium_discount_bps(self) -> Decimal | None:
        """Return the premium or discount in basis points."""

        return None if self.premium_discount is None else self.premium_discount.premium_discount_bps

    def is_premium(self) -> bool:
        """Return ``True`` when a premium/discount value is available and positive."""

        return self.premium_discount is not None and self.premium_discount.is_premium

    def is_discount(self) -> bool:
        """Return ``True`` when a premium/discount value is available and negative."""

        return self.premium_discount is not None and self.premium_discount.is_discount

    def abs_premium_discount(self) -> Decimal | None:
        """Return the absolute premium or discount in percent."""

        return None if self.premium_discount is None else abs(self.premium_discount.premium_discount_pct)


def _validate_shares_outstanding(shares_outstanding: Decimal) -> None:
    if shares_outstanding <= 0:
        raise ValueError("shares_outstanding must be positive.")


def _per_share_risk(metric_value: Decimal, shares_outstanding: Decimal) -> Decimal:
    _validate_shares_outstanding(shares_outstanding)
    return metric_value / shares_outstanding


def calculate_etf_nav(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    shares_outstanding: Decimal = Decimal(1),
    liabilities: Decimal = Decimal(0),
) -> Decimal:
    """Return ETF NAV per share."""

    return calculate_etf_nav_metrics(
        portfolio,
        curve=curve,
        settlement_date=settlement_date,
        shares_outstanding=shares_outstanding,
        liabilities=liabilities,
    ).nav_per_share


def calculate_inav(portfolio: Portfolio, *, curve, settlement_date, shares_outstanding: Decimal = Decimal(1)) -> Decimal:
    """Return ETF indicative NAV per share."""

    return calculate_etf_nav_metrics(
        portfolio,
        curve=curve,
        settlement_date=settlement_date,
        shares_outstanding=shares_outstanding,
    ).inav or Decimal(0)


def dv01_per_share(portfolio: Portfolio, *, curve, settlement_date, shares_outstanding: Decimal = Decimal(1)) -> Decimal:
    """Return ETF DV01 per share in currency units per 1 bp."""

    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    return _per_share_risk(metrics.dv01, shares_outstanding)


def cs01_per_share(portfolio: Portfolio, *, curve, settlement_date, shares_outstanding: Decimal = Decimal(1)) -> Decimal:
    """Return ETF CS01 per share in currency units per 1 bp."""

    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    return _per_share_risk(metrics.cs01, shares_outstanding)


def premium_discount_stats(nav: Decimal, market_price: Decimal) -> PremiumDiscountStats:
    """Return ETF premium or discount statistics."""

    if nav <= 0:
        raise ValueError("nav must be positive for premium/discount calculations.")
    premium_discount = (market_price - nav) / nav
    return PremiumDiscountStats(
        premium_discount=premium_discount,
        premium_discount_bps=premium_discount * Decimal(10_000),
        premium_discount_pct=premium_discount * Decimal(100),
    )


def premium_discount(nav: Decimal, market_price: Decimal) -> PremiumDiscountStats:
    """Compatibility alias for :func:`premium_discount_stats`."""

    return premium_discount_stats(nav, market_price)


def arbitrage_opportunity(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    shares_outstanding: Decimal,
    market_price: Decimal,
    liabilities: Decimal = Decimal(0),
    transaction_cost_bps: Decimal = Decimal(0),
) -> PremiumDiscountPoint:
    """Evaluate ETF creation or redemption arbitrage against NAV.

    The result compares market price to NAV after estimated transaction costs
    and flags whether create or redeem is the better direction.
    """

    costs_bps = Decimal(str(transaction_cost_bps))
    if costs_bps < 0:
        raise ValueError("transaction_cost_bps must be non-negative.")
    nav_metrics = calculate_etf_nav_metrics(
        portfolio,
        curve=curve,
        settlement_date=settlement_date,
        shares_outstanding=shares_outstanding,
        liabilities=liabilities,
        market_price=market_price,
    )
    if nav_metrics.premium_discount is None or nav_metrics.premium_discount_dollars is None:
        raise ValueError("market_price is required to evaluate an arbitrage opportunity.")
    gross_edge = abs(nav_metrics.premium_discount_dollars)
    cost_per_share = nav_metrics.nav_per_share * costs_bps / Decimal(10_000)
    net_edge = gross_edge - cost_per_share
    actionable = net_edge > 0
    if actionable and nav_metrics.premium_discount.is_premium:
        direction = "create"
    elif actionable and nav_metrics.premium_discount.is_discount:
        direction = "redeem"
    else:
        direction = "none"
    return PremiumDiscountPoint(
        nav_per_share=nav_metrics.nav_per_share,
        market_price=market_price,
        shares_outstanding=shares_outstanding,
        premium_discount=nav_metrics.premium_discount,
        premium_discount_dollars=nav_metrics.premium_discount_dollars,
        estimated_edge_per_share=net_edge,
        estimated_edge_bps=Decimal(0) if nav_metrics.nav_per_share == 0 else net_edge / nav_metrics.nav_per_share * Decimal(10_000),
        direction=direction,
        is_actionable=actionable,
    )


def calculate_etf_nav_metrics(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    shares_outstanding: Decimal = Decimal(1),
    liabilities: Decimal = Decimal(0),
    market_price: Decimal | None = None,
) -> EtfNavMetrics:
    """Return the full ETF NAV and per-share risk summary.

    The output includes total NAV, NAV per share, indicative NAV, per-share
    DV01 and CS01, and optional premium/discount data when a market price is
    supplied.
    """

    _validate_shares_outstanding(shares_outstanding)
    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    total_nav = metrics.dirty_pv - liabilities
    nav_per_share = total_nav / shares_outstanding
    indicative_nav = metrics.dirty_pv / shares_outstanding
    premium_discount = None if market_price is None else premium_discount_stats(nav_per_share, market_price)
    premium_discount_dollars = None if market_price is None else market_price - nav_per_share
    return EtfNavMetrics(
        total_nav=total_nav,
        shares_outstanding=shares_outstanding,
        nav_per_share=nav_per_share,
        dv01_per_share=_per_share_risk(metrics.dv01, shares_outstanding),
        cs01_per_share=_per_share_risk(metrics.cs01, shares_outstanding),
        securities_value=metrics.total_market_value,
        cash_value=metrics.cash_value,
        accrued_interest=metrics.total_accrued_interest,
        liabilities=liabilities,
        inav=indicative_nav,
        market_price=market_price,
        premium_discount=premium_discount,
        premium_discount_dollars=premium_discount_dollars,
    )


__all__ = [
    "EtfNavMetrics",
    "PremiumDiscountPoint",
    "PremiumDiscountStats",
    "arbitrage_opportunity",
    "calculate_etf_nav",
    "calculate_etf_nav_metrics",
    "calculate_inav",
    "cs01_per_share",
    "dv01_per_share",
    "premium_discount",
    "premium_discount_stats",
]
