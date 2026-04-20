"""Rating bucketing."""

from __future__ import annotations

from fuggers_py.bonds import CreditRating

from ..portfolio import Portfolio
from ..results import RatingDistribution
from ..types import Position


def bucket_by_rating(portfolio: Portfolio) -> RatingDistribution:
    """Bucket holdings by credit rating."""

    buckets: dict[str, list[Position]] = {}
    for position in portfolio.positions:
        if not isinstance(position, Position):
            continue
        rating = None
        if position.rating_info is not None:
            rating = position.rating_info.rating
        elif position.classification is not None:
            rating = position.classification.rating
        key = (rating or CreditRating.NR).value
        buckets.setdefault(key, []).append(position)
    return RatingDistribution(entries=buckets)


__all__ = ["bucket_by_rating"]
