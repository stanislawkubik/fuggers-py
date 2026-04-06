"""Risk contribution helpers.

The helpers in this module allocate portfolio risk back to individual holdings
or classification buckets using the portfolio analytics layer as the source of
truth for PV, duration, DV01, and CS01 values.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from ..analytics.base import PortfolioAnalytics
from ..portfolio import Portfolio
from .types import Cs01Contributions, DurationContributions, Dv01Contributions, HoldingContribution, SpreadContributions


def _position_groups(portfolio: Portfolio, *, field_name: str) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for position in portfolio.positions:
        if not hasattr(position, "name"):
            continue
        classification = getattr(position, "classification", None)
        if classification is None:
            key = "UNCLASSIFIED"
        else:
            value = getattr(classification, field_name, None)
            key = "UNCLASSIFIED" if value is None else getattr(value, "value", str(value))
        groups.setdefault(key, []).append(position.name())
    return groups


def duration_contributions(portfolio: Portfolio, *, curve, settlement_date) -> DurationContributions:
    """Return duration contributions weighted by dirty PV.

    Each holding contribution is its duration multiplied by its dirty-value
    weight in the portfolio.
    """

    metrics = PortfolioAnalytics(portfolio).position_metrics(curve, settlement_date)
    total_dirty = sum((item.dirty_value for item in metrics), Decimal(0))
    results: list[HoldingContribution] = []
    for item in metrics:
        weight = Decimal(0) if total_dirty == 0 else item.dirty_value / total_dirty
        results.append(
            HoldingContribution(
                name=item.name,
                amount=item.duration * weight,
                metric="duration",
                value_key="duration_contribution",
                weight=weight,
            )
        )
    return DurationContributions(
        entries=tuple(results),
        total=sum((entry.amount for entry in results), Decimal(0)),
    )


def dv01_contributions(portfolio: Portfolio, *, curve, settlement_date) -> Dv01Contributions:
    """Return holding DV01 contributions.

    The contribution amount is the holding-level DV01 returned by the
    analytics layer.
    """

    metrics = PortfolioAnalytics(portfolio).position_metrics(curve, settlement_date)
    results = tuple(
        HoldingContribution(
            name=item.name,
            amount=item.dv01,
            metric="dv01",
            value_key="dv01_contribution",
        )
        for item in metrics
    )
    return Dv01Contributions(entries=results, total=sum((entry.amount for entry in results), Decimal(0)))


def spread_contributions(portfolio: Portfolio, *, curve, settlement_date) -> SpreadContributions:
    """Return holding CS01 contributions.

    The contribution amount is the holding-level CS01 returned by the
    analytics layer.
    """

    metrics = PortfolioAnalytics(portfolio).position_metrics(curve, settlement_date)
    results = tuple(
        HoldingContribution(
            name=item.name,
            amount=item.cs01 or Decimal(0),
            metric="cs01",
            value_key="spread_contribution",
        )
        for item in metrics
    )
    return SpreadContributions(entries=results, total=sum((entry.amount for entry in results), Decimal(0)))


def cs01_contributions(portfolio: Portfolio, *, curve, settlement_date) -> SpreadContributions:
    """Compatibility alias for :func:`spread_contributions`."""

    return spread_contributions(portfolio, curve=curve, settlement_date=settlement_date)


def contribution_by_sector(portfolio: Portfolio, *, curve, settlement_date, metric: str = "dv01") -> dict[str, Decimal]:
    """Aggregate a contribution metric by sector.

    Parameters
    ----------
    metric:
        One of ``"dv01"``, ``"duration"``, or ``"spread"``. ``"spread"``
        uses CS01.
    """

    metrics = PortfolioAnalytics(portfolio).position_metrics(curve, settlement_date)
    metric_key = {"dv01": "dv01", "duration": "duration", "spread": "cs01"}[metric]
    groups = _position_groups(portfolio, field_name="sector")
    values = {item.name: getattr(item, metric_key) or Decimal(0) for item in metrics}
    return {key: sum((values.get(name, Decimal(0)) for name in names), Decimal(0)) for key, names in groups.items()}


def contribution_by_rating(portfolio: Portfolio, *, curve, settlement_date, metric: str = "dv01") -> dict[str, Decimal]:
    """Aggregate a contribution metric by rating.

    Parameters
    ----------
    metric:
        One of ``"dv01"``, ``"duration"``, or ``"spread"``. ``"spread"``
        uses CS01.
    """

    metrics = PortfolioAnalytics(portfolio).position_metrics(curve, settlement_date)
    metric_key = {"dv01": "dv01", "duration": "duration", "spread": "cs01"}[metric]
    groups = _position_groups(portfolio, field_name="rating")
    values = {item.name: getattr(item, metric_key) or Decimal(0) for item in metrics}
    return {key: sum((values.get(name, Decimal(0)) for name in names), Decimal(0)) for key, names in groups.items()}


def top_contributors(
    contributions: Sequence[HoldingContribution] | Sequence[Mapping[str, Decimal | str]],
    *,
    value_key: str,
    limit: int = 5,
    absolute: bool = False,
) -> list[HoldingContribution | Mapping[str, Decimal | str]]:
    """Return the largest contributors ordered by the requested value key."""

    return sorted(
        contributions,
        key=lambda item: abs(Decimal(item[value_key])) if absolute else Decimal(item[value_key]),
        reverse=True,
    )[:limit]


__all__ = [
    "Cs01Contributions",
    "DurationContributions",
    "Dv01Contributions",
    "HoldingContribution",
    "SpreadContributions",
    "contribution_by_rating",
    "contribution_by_sector",
    "cs01_contributions",
    "duration_contributions",
    "dv01_contributions",
    "spread_contributions",
    "top_contributors",
]
