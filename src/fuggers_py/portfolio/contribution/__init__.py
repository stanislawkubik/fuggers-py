"""Contribution analytics.

The contribution surface provides holding-level and bucket-level attribution
for duration, DV01, spread, and return decomposition. Metrics use the same
portfolio weights as the main analytics layer.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..portfolio import Portfolio
from .attribution import (
    AggregatedAttribution,
    AttributionInput,
    BucketContribution,
    HoldingAttribution,
    PortfolioAttribution,
    SectorAttribution,
    aggregated_attribution,
    attribution_summary,
    calculate_attribution,
    duration_difference_by_sector,
    estimate_income_returns,
    estimate_rate_returns,
    estimate_spread_returns,
    spread_difference_by_sector,
    top_contributors,
    weights_sum_check,
)
from .risk import (
    Cs01Contributions,
    DurationContributions,
    Dv01Contributions,
    HoldingContribution,
    SpreadContributions,
    contribution_by_rating,
    contribution_by_sector,
    cs01_contributions,
    duration_contributions,
    dv01_contributions,
    spread_contributions,
)


@dataclass(frozen=True, slots=True)
class Contribution:
    """Convenience wrapper for portfolio contribution helpers."""

    portfolio: Portfolio

    def by_position(self, curve, settlement_date):
        """Return holding-level attribution for the portfolio."""

        return attribution_summary(self.portfolio, curve=curve, settlement_date=settlement_date)

    def aggregate(self, curve, settlement_date, *, assumptions: AttributionInput | None = None):
        """Return aggregated contribution and return decomposition."""

        return aggregated_attribution(
            self.portfolio,
            curve=curve,
            settlement_date=settlement_date,
            assumptions=assumptions,
        )


__all__ = [
    "AggregatedAttribution",
    "AttributionInput",
    "BucketContribution",
    "Cs01Contributions",
    "Contribution",
    "DurationContributions",
    "Dv01Contributions",
    "HoldingAttribution",
    "HoldingContribution",
    "PortfolioAttribution",
    "SectorAttribution",
    "SpreadContributions",
    "aggregated_attribution",
    "attribution_summary",
    "calculate_attribution",
    "contribution_by_rating",
    "contribution_by_sector",
    "cs01_contributions",
    "duration_difference_by_sector",
    "duration_contributions",
    "dv01_contributions",
    "estimate_income_returns",
    "estimate_rate_returns",
    "estimate_spread_returns",
    "spread_contributions",
    "spread_difference_by_sector",
    "top_contributors",
    "weights_sum_check",
]
