"""Typed portfolio domain objects used by the analytics layer.

The types here carry the portfolio-wide conventions used throughout the
package: clean and dirty values are separated, risk metrics are raw decimals,
and bucket labels and classification fields are preserved for aggregation
surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from fuggers_py.reference.bonds.types import CreditRating, RatingInfo, Sector, SectorInfo, Seniority, SeniorityInfo
from fuggers_py.core.types import Currency

from .cash import CashPosition
from .classification import Classification
from .config import AnalyticsConfig
from .holding import Holding, HoldingAnalytics, HoldingBuilder, Position, PositionAnalytics
from .maturity import MaturityBucket
from .weighting import WeightingMethod


@dataclass(frozen=True, slots=True)
class RatingBucket:
    """A named set of credit ratings used for bucketing."""

    label: str
    ratings: tuple[CreditRating, ...]


@dataclass(frozen=True, slots=True)
class BucketResult:
    """Aggregate metrics for a single portfolio bucket.

    Attributes
    ----------
    label:
        Bucket name.
    clean_pv, dirty_pv:
        Aggregated clean and dirty present values in currency units.
    dv01:
        Bucket DV01 in currency units per 1 bp.
    weight:
        Bucket weight relative to the portfolio total, as a raw decimal.
    market_value:
        Clean market value proxy used by the bucketing helpers.
    average_ytm, average_duration, average_spread:
        Dirty-value-weighted averages, or ``None`` when no metric is available.
    holding_count:
        Number of holdings assigned to the bucket.
    """

    label: str
    clean_pv: Decimal
    dirty_pv: Decimal
    dv01: Decimal
    weight: Decimal = Decimal(0)
    market_value: Decimal = Decimal(0)
    average_ytm: Decimal | None = None
    average_duration: Decimal | None = None
    average_spread: Decimal | None = None
    holding_count: int = 0


@dataclass(frozen=True, slots=True)
class StressResult:
    """Result of a stress scenario against portfolio dirty PV.

    Attributes
    ----------
    base_dirty_pv:
        Unstressed dirty present value.
    stressed_dirty_pv:
        Dirty present value after applying the scenario.
    actual_change:
        Signed PV change, where negative values indicate a loss.
    dv01_approximation:
        First-order approximation of the change, in the same currency units.
    scenario_name:
        Optional label for the scenario.
    breakdown:
        Optional per-position or per-tenor change breakdown.
    """

    base_dirty_pv: Decimal
    stressed_dirty_pv: Decimal
    actual_change: Decimal
    dv01_approximation: Decimal
    scenario_name: str | None = None
    breakdown: dict[str, Decimal] = field(default_factory=dict)

    @property
    def shocked_pv(self) -> Decimal:
        return self.stressed_dirty_pv

    @property
    def pv_change(self) -> Decimal:
        return self.actual_change


@dataclass(frozen=True, slots=True)
class PortfolioMetrics:
    """Portfolio-level weighted metrics and totals.

    All spread and rate values are raw decimals unless a name explicitly says
    ``bps`` or ``pct`` elsewhere in the API. PV and cash fields are currency
    amounts, while the ``weights`` and bucket shares are raw decimals.
    """

    clean_pv: Decimal
    dirty_pv: Decimal
    accrued: Decimal
    duration: Decimal
    convexity: Decimal
    dv01: Decimal
    weights: dict[str, Decimal]
    currency: Currency
    current_yield: Decimal = Decimal(0)
    ytm: Decimal = Decimal(0)
    ytw: Decimal = Decimal(0)
    ytc: Decimal = Decimal(0)
    best_yield: Decimal = Decimal(0)
    z_spread: Decimal = Decimal(0)
    oas: Decimal = Decimal(0)
    g_spread: Decimal | None = None
    i_spread: Decimal | None = None
    asw: Decimal | None = None
    best_spread: Decimal = Decimal(0)
    spread_duration: Decimal = Decimal(0)
    cs01: Decimal = Decimal(0)
    liquidity_score: Decimal = Decimal(0)
    key_rate_profile: dict[str, Decimal] = field(default_factory=dict)
    total_market_value: Decimal = Decimal(0)
    total_dirty_market_value: Decimal = Decimal(0)
    total_accrued_interest: Decimal = Decimal(0)
    cash_value: Decimal = Decimal(0)
    holding_count: int = 0
    priced_count: int = 0
    coverage_count: int = 0
    modified_duration: Decimal = Decimal(0)
    effective_duration: Decimal = Decimal(0)
    macaulay_duration: Decimal = Decimal(0)
    effective_convexity: Decimal = Decimal(0)
    weighted_average_maturity: Decimal = Decimal(0)
    weighted_average_coupon: Decimal = Decimal(0)


__all__ = [
    "AnalyticsConfig",
    "BucketResult",
    "CashPosition",
    "Classification",
    "CreditRating",
    "Holding",
    "HoldingAnalytics",
    "HoldingBuilder",
    "MaturityBucket",
    "PortfolioMetrics",
    "Position",
    "PositionAnalytics",
    "RatingBucket",
    "RatingInfo",
    "Sector",
    "SectorInfo",
    "Seniority",
    "SeniorityInfo",
    "StressResult",
    "WeightingMethod",
]
