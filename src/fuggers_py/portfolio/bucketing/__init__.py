"""Portfolio bucketing helpers.

Bucket helpers group holdings by maturity, sector, rating, or custom
classification fields and summarize the resulting clean and dirty PV totals.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core.types import Date
from fuggers_py.curves import DiscountingCurve

from ..analytics import PortfolioAnalytics
from ..portfolio import Portfolio
from ..results import ClassifierDistribution, CustomDistribution, MaturityDistribution, RatingDistribution, SectorDistribution
from ..types import BucketResult
from .custom import bucket_by_classifier, bucket_by_country, bucket_by_currency, bucket_by_custom_field, bucket_by_issuer, bucket_by_region
from .maturity import DEFAULT_BUCKETS, bucket_by_maturity
from .rating import bucket_by_rating
from .sector import bucket_by_sector


BucketMetrics = BucketResult


@dataclass(frozen=True, slots=True)
class Bucketing:
    """Convenience wrapper for portfolio bucketing helpers."""

    portfolio: Portfolio

    def bucket_dv01(
        self,
        curve: DiscountingCurve,
        settlement_date: Date,
        buckets=DEFAULT_BUCKETS,
    ) -> list[BucketResult]:
        """Return maturity buckets with PV-weighted averages.

        Each bucket is keyed by the supplied maturity definition and includes
        clean PV, dirty PV, DV01, and dirty-value-weighted averages.
        """

        metrics = PortfolioAnalytics(self.portfolio).position_metrics(curve, settlement_date)
        bucketed: list[BucketResult] = []
        assignments = bucket_by_maturity(self.portfolio, settlement_date=settlement_date, buckets=buckets)
        for label, positions in assignments.items():
            clean = Decimal(0)
            dirty = Decimal(0)
            dv01 = Decimal(0)
            ytm_weighted = Decimal(0)
            duration_weighted = Decimal(0)
            spread_weighted = Decimal(0)
            names = {position.name() for position in positions if hasattr(position, "name")}
            for item in metrics:
                if item.name not in names:
                    continue
                clean += item.clean_value
                dirty += item.dirty_value
                dv01 += item.dv01
                ytm_weighted += (item.ytm or Decimal(0)) * item.dirty_value
                duration_weighted += item.duration * item.dirty_value
                spread_weighted += (item.z_spread or Decimal(0)) * item.dirty_value
            divisor = dirty if dirty != 0 else Decimal(1)
            bucketed.append(
                BucketResult(
                    label=label,
                    clean_pv=clean,
                    dirty_pv=dirty,
                    dv01=dv01,
                    weight=Decimal(0),
                    market_value=clean,
                    average_ytm=ytm_weighted / divisor if dirty != 0 else Decimal(0),
                    average_duration=duration_weighted / divisor if dirty != 0 else Decimal(0),
                    average_spread=spread_weighted / divisor if dirty != 0 else Decimal(0),
                    holding_count=len(positions),
                )
            )
        return bucketed


def summarize_bucket_assignments(
    portfolio: Portfolio,
    assignments: Mapping[str, Sequence[object]],
    *,
    curve: DiscountingCurve,
    settlement_date: Date,
) -> dict[str, BucketResult]:
    """Summarize arbitrary bucket assignments into :class:`BucketResult`.

    The summary uses dirty PV as the weight basis for the average metrics and
    bucket weights.
    """

    metrics = PortfolioAnalytics(portfolio).position_metrics(curve, settlement_date)
    total_dirty = sum((item.dirty_value for item in metrics), Decimal(0))
    by_name = {item.name: item for item in metrics}
    results: dict[str, BucketResult] = {}
    for label, positions in assignments.items():
        names = {position.name() for position in positions if hasattr(position, "name")}
        selected = [by_name[name] for name in names if name in by_name]
        clean = sum((item.clean_value for item in selected), Decimal(0))
        dirty = sum((item.dirty_value for item in selected), Decimal(0))
        dv01 = sum((item.dv01 for item in selected), Decimal(0))
        results[label] = BucketResult(
            label=label,
            clean_pv=clean,
            dirty_pv=dirty,
            dv01=dv01,
            weight=Decimal(0) if total_dirty == 0 else dirty / total_dirty,
            market_value=clean,
            average_ytm=(
                sum(((item.ytm or Decimal(0)) * item.dirty_value for item in selected), Decimal(0)) / dirty
                if dirty != 0
                else Decimal(0)
            ),
            average_duration=(
                sum((item.duration * item.dirty_value for item in selected), Decimal(0)) / dirty
                if dirty != 0
                else Decimal(0)
            ),
            average_spread=(
                sum((((item.z_spread or Decimal(0)) * item.dirty_value) for item in selected), Decimal(0)) / dirty
                if dirty != 0
                else Decimal(0)
            ),
            holding_count=len(selected),
        )
    return results


def sector_bucket_metrics(portfolio: Portfolio, *, curve: DiscountingCurve, settlement_date: Date) -> dict[str, BucketResult]:
    """Return bucket metrics grouped by sector."""

    return summarize_bucket_assignments(
        portfolio,
        bucket_by_sector(portfolio),
        curve=curve,
        settlement_date=settlement_date,
    )


def rating_bucket_metrics(portfolio: Portfolio, *, curve: DiscountingCurve, settlement_date: Date) -> dict[str, BucketResult]:
    """Return bucket metrics grouped by rating."""

    return summarize_bucket_assignments(
        portfolio,
        bucket_by_rating(portfolio),
        curve=curve,
        settlement_date=settlement_date,
    )


def maturity_bucket_metrics(
    portfolio: Portfolio,
    *,
    curve: DiscountingCurve,
    settlement_date: Date,
    buckets=DEFAULT_BUCKETS,
) -> dict[str, BucketResult]:
    """Return bucket metrics grouped by maturity."""

    return summarize_bucket_assignments(
        portfolio,
        bucket_by_maturity(portfolio, settlement_date=settlement_date, buckets=buckets),
        curve=curve,
        settlement_date=settlement_date,
    )


__all__ = [
    "BucketMetrics",
    "Bucketing",
    "ClassifierDistribution",
    "CustomDistribution",
    "DEFAULT_BUCKETS",
    "MaturityDistribution",
    "RatingDistribution",
    "SectorDistribution",
    "bucket_by_classifier",
    "bucket_by_country",
    "bucket_by_currency",
    "bucket_by_custom_field",
    "bucket_by_issuer",
    "bucket_by_maturity",
    "bucket_by_rating",
    "bucket_by_region",
    "bucket_by_sector",
    "maturity_bucket_metrics",
    "rating_bucket_metrics",
    "sector_bucket_metrics",
    "summarize_bucket_assignments",
]
