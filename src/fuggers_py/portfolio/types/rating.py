"""Credit rating types used by portfolio classification and bucketing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CreditRating(str, Enum):
    """Issuer credit rating buckets."""

    AAA = "AAA"
    AA = "AA"
    A = "A"
    BBB = "BBB"
    BB = "BB"
    B = "B"
    CCC = "CCC"
    CC = "CC"
    C = "C"
    D = "D"
    NR = "NR"

    def score(self) -> int:
        """Return an ordinal score where lower numbers indicate stronger credit."""
        scores = {
            CreditRating.AAA: 1,
            CreditRating.AA: 2,
            CreditRating.A: 3,
            CreditRating.BBB: 4,
            CreditRating.BB: 5,
            CreditRating.B: 6,
            CreditRating.CCC: 7,
            CreditRating.CC: 8,
            CreditRating.C: 9,
            CreditRating.D: 10,
            CreditRating.NR: 99,
        }
        return scores[self]


@dataclass(frozen=True, slots=True)
class RatingInfo:
    """Rating metadata from an agency or internal source."""

    rating: CreditRating
    agency: str | None = None
    outlook: str | None = None


__all__ = ["CreditRating", "RatingInfo"]
