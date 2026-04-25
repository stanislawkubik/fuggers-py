"""Sector bucketing."""

from __future__ import annotations

from ..portfolio import Portfolio
from ..results import SectorDistribution
from ..types import Position, Sector


def bucket_by_sector(portfolio: Portfolio) -> SectorDistribution:
    """Bucket holdings by sector."""

    buckets: dict[str, list[Position]] = {}
    for position in portfolio.positions:
        if not isinstance(position, Position):
            continue
        sector = None
        if position.sector_info is not None:
            sector = position.sector_info.sector
        elif position.classification is not None:
            sector = position.classification.sector
        key = (sector or Sector.OTHER).value
        buckets.setdefault(key, []).append(position)
    return SectorDistribution(entries=buckets)


__all__ = ["bucket_by_sector"]
