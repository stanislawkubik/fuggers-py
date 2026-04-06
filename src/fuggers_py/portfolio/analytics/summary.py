"""High-level portfolio summary helpers.

This module exposes the public convenience wrapper used by the generated
docs and by callers that only need the full portfolio summary in one step.
"""

from __future__ import annotations

from ..portfolio import Portfolio
from ..types import AnalyticsConfig
from .base import PortfolioAnalytics


def calculate_portfolio_analytics(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    config: AnalyticsConfig | None = None,
):
    """Return the full portfolio analytics summary.

    The returned object includes the portfolio-level metrics computed by
    :class:`~fuggers_py.portfolio.analytics.base.PortfolioAnalytics`.
    """

    return PortfolioAnalytics(portfolio).metrics(curve, settlement_date, config=config)


__all__ = ["calculate_portfolio_analytics"]
