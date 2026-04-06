"""Base portfolio analytics class.

The base analytics object evaluates a portfolio at a settlement date using an
optional curve and spread-curve context, then returns typed per-holding and
portfolio-level metrics.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.measures.spreads import OASCalculator
from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Date

from .._analytics_utils import aggregate_metrics, position_analytics
from ..portfolio import Portfolio
from ..types import AnalyticsConfig, PortfolioMetrics, PositionAnalytics


@dataclass(frozen=True, slots=True)
class PortfolioAnalytics:
    """Evaluate portfolio holdings into typed analytics outputs.

    The object is a thin wrapper around the portfolio plus the analytics
    helpers that derive per-position and portfolio-level metrics.
    """

    portfolio: Portfolio

    def position_metrics(
        self,
        curve: YieldCurve | None,
        settlement_date: Date,
        *,
        config: AnalyticsConfig | None = None,
        spread_curve: YieldCurve | None = None,
        oas_calculator: OASCalculator | None = None,
    ) -> list[PositionAnalytics]:
        """Return per-position analytics for the portfolio.

        Parameters
        ----------
        curve:
            Valuation curve used for discounting and risk calculations.
        settlement_date:
            Settlement or valuation date that anchors accrued interest and
            year-fraction conventions.
        config:
            Optional analytics configuration. When omitted, the portfolio
            currency and settlement date are used to build a default config.
        spread_curve:
            Optional curve used for spread calculations when it differs from
            the valuation curve.
        oas_calculator:
            Optional spread calculator override.

        Returns
        -------
        list[PositionAnalytics]
            One analytics record per position in portfolio order.
        """

        active_config = config or AnalyticsConfig(settlement_date=settlement_date, default_currency=self.portfolio.currency)
        return [
            position_analytics(
                position,
                curve=curve,
                settlement_date=settlement_date,
                config=active_config,
                spread_curve=spread_curve,
                oas_calculator=oas_calculator,
            )
            for position in self.portfolio.positions
        ]

    def metrics(
        self,
        curve: YieldCurve | None,
        settlement_date: Date,
        *,
        config: AnalyticsConfig | None = None,
        spread_curve: YieldCurve | None = None,
        oas_calculator: OASCalculator | None = None,
    ) -> PortfolioMetrics:
        """Return portfolio-level aggregated analytics.

        The totals and weighted averages are reported in the portfolio's base
        currency and raw-decimal risk units. The weighting basis follows the
        active analytics configuration.
        """

        active_config = config or AnalyticsConfig(settlement_date=settlement_date, default_currency=self.portfolio.currency)
        analytics_list = self.position_metrics(
            curve,
            settlement_date,
            config=active_config,
            spread_curve=spread_curve,
            oas_calculator=oas_calculator,
        )
        return aggregate_metrics(
            analytics_list,
            currency=self.portfolio.currency,
            weighting_method=active_config.weighting_method,
        )


__all__ = ["PortfolioAnalytics"]
