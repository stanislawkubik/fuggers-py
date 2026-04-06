"""Typed public risk, yield, spread, and credit metrics.

These objects expose portfolio-level metrics with the package's conventions
for raw-decimal yields and spreads, currency-unit PV changes, and sign-aware
credit-migration risk.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict, cast

from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Date
from fuggers_py.reference.bonds.types import CreditRating

from ..analytics.base import PortfolioAnalytics
from ..analytics.credit import (
    calculate_credit_quality as _calculate_credit_quality_dict,
)
from ..portfolio import Portfolio
from ..types import PortfolioMetrics, Position


class _QualityTiersRaw(TypedDict, total=False):
    investment_grade: Decimal
    high_yield: Decimal
    distressed: Decimal
    defaulted: Decimal
    unrated: Decimal


class _MigrationRiskRaw(TypedDict):
    fallen_angel_risk: Decimal
    rising_star_risk: Decimal


class _CreditQualityRaw(TypedDict):
    distribution: dict[str, Decimal]
    sector_distribution: dict[str, Decimal]
    average_score: Decimal
    average_rating: CreditRating
    investment_grade_weight: Decimal
    high_yield_weight: Decimal
    default_weight: Decimal
    unrated_weight: Decimal
    bbb_weight: Decimal
    bb_weight: Decimal
    crossover_weight: Decimal
    quality_tiers: _QualityTiersRaw
    migration_risk: _MigrationRiskRaw


@dataclass(frozen=True, slots=True)
class QualityTiers:
    """Normalized credit-quality tier weights."""

    investment_grade: Decimal
    high_yield: Decimal
    distressed: Decimal
    defaulted: Decimal
    unrated: Decimal


@dataclass(frozen=True, slots=True)
class FallenAngelRisk:
    """Weight and market value at risk from BBB holdings."""

    bbb_weight: Decimal
    market_value_at_risk: Decimal
    holdings_count: int

    @property
    def weight(self) -> Decimal:
        """Return the BBB weight."""

        return self.bbb_weight


@dataclass(frozen=True, slots=True)
class RisingStarRisk:
    """Weight and market value potential from BB holdings."""

    bb_weight: Decimal
    market_value_potential: Decimal
    holdings_count: int

    @property
    def weight(self) -> Decimal:
        """Return the BB weight."""

        return self.bb_weight


@dataclass(frozen=True, slots=True)
class MigrationRisk:
    """Combined fallen-angel and rising-star migration risk."""

    fallen_angel_risk: Decimal
    rising_star_risk: Decimal
    fallen_angel: FallenAngelRisk
    rising_star: RisingStarRisk

    @property
    def crossover_weight(self) -> Decimal:
        """Return the combined BBB and BB crossover weight."""

        return self.fallen_angel_risk + self.rising_star_risk


@dataclass(frozen=True, slots=True)
class CreditQualityMetrics:
    """Portfolio credit-quality distribution and migration risk."""

    distribution: dict[str, Decimal]
    sector_distribution: dict[str, Decimal]
    average_score: Decimal
    average_rating: object
    investment_grade_weight: Decimal
    high_yield_weight: Decimal
    default_weight: Decimal
    unrated_weight: Decimal
    bbb_weight: Decimal
    bb_weight: Decimal
    crossover_weight: Decimal
    quality_tiers: QualityTiers
    migration_risk: MigrationRisk


@dataclass(frozen=True, slots=True)
class YieldMetrics:
    """Portfolio yield metrics expressed as raw decimals."""

    ytm: Decimal
    ytw: Decimal
    ytc: Decimal
    current_yield: Decimal
    best_yield: Decimal


@dataclass(frozen=True, slots=True)
class SpreadMetrics:
    """Portfolio spread metrics expressed as raw decimals."""

    z_spread: Decimal
    oas: Decimal
    g_spread: Decimal | None
    i_spread: Decimal | None
    asw: Decimal | None
    best_spread: Decimal
    spread_duration: Decimal
    cs01: Decimal


@dataclass(frozen=True, slots=True)
class RiskMetrics:
    """Portfolio rate-risk metrics expressed in raw-decimal units."""

    duration: Decimal
    modified_duration: Decimal
    effective_duration: Decimal
    macaulay_duration: Decimal
    best_duration: Decimal
    convexity: Decimal
    effective_convexity: Decimal
    dv01: Decimal
    cs01: Decimal


CurveLike = YieldCurve | None


def _metrics(portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date) -> PortfolioMetrics:
    return PortfolioAnalytics(portfolio).metrics(curve, settlement_date)


def _position_weight(position: Position) -> Decimal:
    if position.market_value is not None:
        return Decimal(position.market_value)
    if position.clean_price is not None:
        return position.market_value_amount
    return position.quantity


def _position_market_value(position: Position) -> Decimal:
    if position.market_value is not None:
        return Decimal(position.market_value)
    return position.market_value_amount


def _position_rating(position: Position) -> CreditRating:
    if position.rating_info is not None:
        return position.rating_info.rating
    if position.classification is not None and position.classification.rating is not None:
        return position.classification.rating
    return CreditRating.NR


def _build_quality_tiers(raw: _CreditQualityRaw) -> QualityTiers:
    tiers = raw["quality_tiers"]
    return QualityTiers(
        investment_grade=tiers.get("investment_grade", Decimal(0)),
        high_yield=tiers.get("high_yield", Decimal(0)),
        distressed=tiers.get("distressed", Decimal(0)),
        defaulted=tiers.get("defaulted", Decimal(0)),
        unrated=tiers.get("unrated", Decimal(0)),
    )


def calculate_migration_risk(portfolio: Portfolio) -> MigrationRisk:
    """Return the BBB and BB crossover risk for the portfolio."""

    total_weight = sum((_position_weight(position) for position in portfolio.investable_holdings()), Decimal(0))
    fallen_positions = [position for position in portfolio.investable_holdings() if _position_rating(position) is CreditRating.BBB]
    rising_positions = [position for position in portfolio.investable_holdings() if _position_rating(position) is CreditRating.BB]

    def _weight_for(positions: tuple[Position, ...] | list[Position]) -> Decimal:
        if total_weight == 0:
            return Decimal(0)
        return sum((_position_weight(position) for position in positions), Decimal(0)) / total_weight

    fallen = FallenAngelRisk(
        bbb_weight=_weight_for(fallen_positions),
        market_value_at_risk=sum((_position_market_value(position) for position in fallen_positions), Decimal(0)),
        holdings_count=len(fallen_positions),
    )
    rising = RisingStarRisk(
        bb_weight=_weight_for(rising_positions),
        market_value_potential=sum((_position_market_value(position) for position in rising_positions), Decimal(0)),
        holdings_count=len(rising_positions),
    )
    return MigrationRisk(
        fallen_angel_risk=fallen.bbb_weight,
        rising_star_risk=rising.bb_weight,
        fallen_angel=fallen,
        rising_star=rising,
    )


def calculate_credit_quality(portfolio: Portfolio) -> CreditQualityMetrics:
    """Return portfolio credit-quality metrics with typed risk fields."""

    raw = cast(_CreditQualityRaw, _calculate_credit_quality_dict(portfolio))
    return CreditQualityMetrics(
        distribution=dict(raw["distribution"]),
        sector_distribution=dict(raw["sector_distribution"]),
        average_score=raw["average_score"],
        average_rating=raw["average_rating"],
        investment_grade_weight=raw["investment_grade_weight"],
        high_yield_weight=raw["high_yield_weight"],
        default_weight=raw["default_weight"],
        unrated_weight=raw["unrated_weight"],
        bbb_weight=raw["bbb_weight"],
        bb_weight=raw["bb_weight"],
        crossover_weight=raw["crossover_weight"],
        quality_tiers=_build_quality_tiers(raw),
        migration_risk=calculate_migration_risk(portfolio),
    )


def calculate_credit_metrics(portfolio: Portfolio) -> CreditQualityMetrics:
    """Compatibility alias for :func:`calculate_credit_quality`."""

    return calculate_credit_quality(portfolio)


def calculate_yield_metrics(
    portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date
) -> YieldMetrics:
    """Return the standard portfolio yield metrics."""

    metrics = _metrics(portfolio, curve=curve, settlement_date=settlement_date)
    return YieldMetrics(
        ytm=metrics.ytm,
        ytw=metrics.ytw,
        ytc=metrics.ytc,
        current_yield=metrics.current_yield,
        best_yield=metrics.best_yield,
    )


def calculate_spread_metrics(
    portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date
) -> SpreadMetrics:
    """Return the standard portfolio spread metrics."""

    metrics = _metrics(portfolio, curve=curve, settlement_date=settlement_date)
    return SpreadMetrics(
        z_spread=metrics.z_spread,
        oas=metrics.oas,
        g_spread=metrics.g_spread,
        i_spread=metrics.i_spread,
        asw=metrics.asw,
        best_spread=metrics.best_spread,
        spread_duration=metrics.spread_duration,
        cs01=metrics.cs01,
    )


def weighted_z_spread(portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date) -> Decimal:
    """Return the portfolio Z-spread as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).z_spread


def weighted_oas(portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date) -> Decimal:
    """Return the portfolio OAS as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).oas


def weighted_g_spread(portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date) -> Decimal | None:
    """Return the portfolio G-spread as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).g_spread


def weighted_i_spread(portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date) -> Decimal | None:
    """Return the portfolio I-spread as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).i_spread


def weighted_asw(portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date) -> Decimal | None:
    """Return the portfolio asset-swap spread as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).asw


def weighted_best_spread(
    portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date
) -> Decimal:
    """Return the portfolio best spread as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).best_spread


def weighted_spread_duration(
    portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date
) -> Decimal:
    """Return the portfolio spread duration as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).spread_duration


def calculate_risk_metrics(
    portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date
) -> RiskMetrics:
    """Return the standard portfolio rate-risk metrics."""

    metrics = _metrics(portfolio, curve=curve, settlement_date=settlement_date)
    return RiskMetrics(
        duration=metrics.duration,
        modified_duration=metrics.modified_duration,
        effective_duration=metrics.effective_duration,
        macaulay_duration=metrics.macaulay_duration,
        best_duration=weighted_best_duration(portfolio, curve=curve, settlement_date=settlement_date),
        convexity=metrics.convexity,
        effective_convexity=metrics.effective_convexity,
        dv01=metrics.dv01,
        cs01=metrics.cs01,
    )


def weighted_modified_duration(
    portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date
) -> Decimal:
    """Return the portfolio modified duration as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).modified_duration


def weighted_effective_duration(
    portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date
) -> Decimal:
    """Return the portfolio effective duration as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).effective_duration


def weighted_macaulay_duration(
    portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date
) -> Decimal:
    """Return the portfolio Macaulay duration as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).macaulay_duration


def weighted_effective_convexity(
    portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date
) -> Decimal:
    """Return the portfolio effective convexity as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).effective_convexity


def weighted_best_yield(portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date) -> Decimal:
    """Return the portfolio best yield as a raw decimal."""

    return _metrics(portfolio, curve=curve, settlement_date=settlement_date).best_yield


def weighted_best_duration(
    portfolio: Portfolio, *, curve: CurveLike, settlement_date: Date
) -> Decimal:
    """Return the dirty-value-weighted best duration."""

    positions = PortfolioAnalytics(portfolio).position_metrics(curve, settlement_date)
    total_dirty = sum((item.dirty_value for item in positions), Decimal(0))
    if total_dirty == 0:
        return Decimal(0)
    weighted_sum = Decimal(0)
    for item in positions:
        best_duration = item.duration
        if item.effective_duration is not None and item.effective_duration != Decimal(0):
            best_duration = item.effective_duration
        elif item.modified_duration is not None:
            best_duration = item.modified_duration
        weighted_sum += best_duration * item.dirty_value
    return weighted_sum / total_dirty


CreditMetrics = CreditQualityMetrics


__all__ = [
    "CreditMetrics",
    "CreditQualityMetrics",
    "FallenAngelRisk",
    "MigrationRisk",
    "QualityTiers",
    "RiskMetrics",
    "RisingStarRisk",
    "SpreadMetrics",
    "YieldMetrics",
    "calculate_credit_metrics",
    "calculate_credit_quality",
    "calculate_migration_risk",
    "calculate_risk_metrics",
    "calculate_spread_metrics",
    "calculate_yield_metrics",
    "weighted_asw",
    "weighted_best_duration",
    "weighted_best_spread",
    "weighted_best_yield",
    "weighted_effective_convexity",
    "weighted_effective_duration",
    "weighted_g_spread",
    "weighted_i_spread",
    "weighted_macaulay_duration",
    "weighted_modified_duration",
    "weighted_oas",
    "weighted_spread_duration",
    "weighted_z_spread",
]
