"""Credit-quality aggregation.

The credit-quality helper re-expresses portfolio holdings into a normalized
rating distribution, sector distribution, and migration-risk view.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py.bonds import CreditRating

from ..portfolio import Portfolio
from ..types import Holding, Position


_SCORE_TO_RATING = {rating.score(): rating for rating in CreditRating}


def _holding_weight(position: Position) -> Decimal:
    if position.market_value is not None:
        return Decimal(position.market_value)
    if position.clean_price is not None:
        return position.market_value_amount
    return position.quantity


def _rating_for(position: Position) -> CreditRating:
    if position.rating_info is not None:
        return position.rating_info.rating
    if position.classification is not None and position.classification.rating is not None:
        return position.classification.rating
    return CreditRating.NR


def _sector_for(position: Position) -> str:
    if position.sector_info is not None:
        return position.sector_info.sector.value
    if position.classification is not None and position.classification.sector is not None:
        return position.classification.sector.value
    return "OTHER"


def _nearest_rating(score: Decimal) -> CreditRating:
    eligible = {value: rating for value, rating in _SCORE_TO_RATING.items() if rating is not CreditRating.NR}
    closest = min(eligible, key=lambda value: abs(Decimal(value) - score))
    return eligible[closest]


def calculate_credit_quality(portfolio: Portfolio) -> dict[str, object]:
    """Return normalized credit-quality metrics for the portfolio.

    The weights are returned as raw decimals summing to one where possible.
    The output includes the rating distribution, sector distribution, average
    rating score, quality tiers, and a simple migration-risk split.
    """

    distribution: dict[str, Decimal] = {}
    sector_distribution: dict[str, Decimal] = {}
    weighted_score = Decimal(0)
    total_weight = Decimal(0)
    for position in portfolio.positions:
        if not isinstance(position, Position):
            continue
        rating = _rating_for(position)
        weight = _holding_weight(position)
        distribution[rating.value] = distribution.get(rating.value, Decimal(0)) + weight
        sector = _sector_for(position)
        sector_distribution[sector] = sector_distribution.get(sector, Decimal(0)) + weight
        weighted_score += Decimal(rating.score()) * weight
        total_weight += weight
    average_score = Decimal(0) if total_weight == 0 else weighted_score / total_weight
    if total_weight == 0:
        return {
            "distribution": {},
            "sector_distribution": {},
            "average_score": Decimal(0),
            "average_rating": CreditRating.NR,
            "investment_grade_weight": Decimal(0),
            "high_yield_weight": Decimal(0),
            "default_weight": Decimal(0),
            "unrated_weight": Decimal(0),
            "bbb_weight": Decimal(0),
            "bb_weight": Decimal(0),
            "crossover_weight": Decimal(0),
            "quality_tiers": {},
            "migration_risk": {"fallen_angel_risk": Decimal(0), "rising_star_risk": Decimal(0)},
        }

    normalized_distribution = {key: value / total_weight for key, value in distribution.items()}
    normalized_sector_distribution = {key: value / total_weight for key, value in sector_distribution.items()}
    ig_ratings = {CreditRating.AAA, CreditRating.AA, CreditRating.A, CreditRating.BBB}
    hy_ratings = {CreditRating.BB, CreditRating.B, CreditRating.CCC, CreditRating.CC, CreditRating.C}
    investment_grade_weight = sum(
        (normalized_distribution.get(rating.value, Decimal(0)) for rating in ig_ratings),
        Decimal(0),
    )
    high_yield_weight = sum((normalized_distribution.get(rating.value, Decimal(0)) for rating in hy_ratings), Decimal(0))
    default_weight = normalized_distribution.get(CreditRating.D.value, Decimal(0))
    unrated_weight = normalized_distribution.get(CreditRating.NR.value, Decimal(0))
    bbb_weight = normalized_distribution.get(CreditRating.BBB.value, Decimal(0))
    bb_weight = normalized_distribution.get(CreditRating.BB.value, Decimal(0))
    quality_tiers = {
        "investment_grade": investment_grade_weight,
        "high_yield": high_yield_weight,
        "distressed": sum(
            (
                normalized_distribution.get(CreditRating.CCC.value, Decimal(0)),
                normalized_distribution.get(CreditRating.CC.value, Decimal(0)),
                normalized_distribution.get(CreditRating.C.value, Decimal(0)),
            ),
            Decimal(0),
        ),
        "defaulted": default_weight,
        "unrated": unrated_weight,
    }
    return {
        "distribution": normalized_distribution,
        "sector_distribution": normalized_sector_distribution,
        "average_score": average_score,
        "average_rating": _nearest_rating(average_score),
        "investment_grade_weight": investment_grade_weight,
        "high_yield_weight": high_yield_weight,
        "default_weight": default_weight,
        "unrated_weight": unrated_weight,
        "bbb_weight": bbb_weight,
        "bb_weight": bb_weight,
        "crossover_weight": bbb_weight + bb_weight,
        "quality_tiers": quality_tiers,
        "migration_risk": {
            "fallen_angel_risk": bbb_weight,
            "rising_star_risk": bb_weight,
        },
    }


__all__ = ["calculate_credit_quality"]
