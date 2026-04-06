"""Maturity bucketing.

The maturity buckets use time to maturity in years as of the supplied
settlement date. Cash positions are grouped separately under ``Cash``.
"""

from __future__ import annotations

from ..portfolio import Portfolio
from ..results import MaturityDistribution
from ..types import CashPosition, MaturityBucket, Position


DEFAULT_BUCKETS: tuple[tuple[str, float, float | None], ...] = (
    ("0-2Y", 0.0, 2.0),
    ("2-5Y", 2.0, 5.0),
    ("5-10Y", 5.0, 10.0),
    ("10Y+", 10.0, None),
)


def bucket_by_maturity(portfolio: Portfolio, *, settlement_date, buckets=DEFAULT_BUCKETS) -> MaturityDistribution:
    """Bucket holdings by time to maturity in years."""

    results = {label: [] for label, _, _ in buckets}
    for position in portfolio.positions:
        if isinstance(position, CashPosition):
            results.setdefault("Cash", []).append(position)
            continue
        maturity_years = float(settlement_date.days_between(position.instrument.maturity_date())) / 365.0
        for label, start, end in buckets:
            if maturity_years < start:
                continue
            if end is not None and maturity_years >= end:
                continue
            results[label].append(position)
            break
    return MaturityDistribution(entries=results, bucket_definition=tuple(buckets))


__all__ = ["DEFAULT_BUCKETS", "bucket_by_maturity"]
