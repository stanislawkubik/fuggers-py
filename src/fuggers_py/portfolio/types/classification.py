"""Classification metadata attached to holdings for aggregation.

The fields are intentionally lightweight and optional so portfolio analytics
can bucket holdings by sector, rating, seniority, geography, currency, issuer,
or user-defined custom fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fuggers_py.bonds import CreditRating, RatingInfo, Sector, SectorInfo, Seniority, SeniorityInfo
from fuggers_py._core.types import Currency


@dataclass(frozen=True, slots=True)
class Classification:
    """Optional cross-sectional classification data for a holding.

    The fields are used for bucketing, active-weight analysis, and custom
    portfolio aggregation. A field may be left unset when the information is
    not available at holding creation time.
    """

    sector: Sector | None = None
    rating: CreditRating | None = None
    seniority: Seniority | None = None
    country: str | None = None
    currency: Currency | None = None
    issuer: str | None = None
    region: str | None = None
    custom_fields: dict[str, str] = field(default_factory=dict)


__all__ = [
    "Classification",
    "CreditRating",
    "RatingInfo",
    "Sector",
    "SectorInfo",
    "Seniority",
    "SeniorityInfo",
]
