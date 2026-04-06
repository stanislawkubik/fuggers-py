"""Typed liquidity analytics and compatibility helpers.

The liquidity layer maps holding-level liquidity scores to portfolio-level
weights, spread proxies, and estimated days to liquidate.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, fields
from decimal import Decimal

from ..analytics.base import PortfolioAnalytics
from ..portfolio import Portfolio


class _MetricMapping(Mapping[str, object]):
    def __getitem__(self, key: str) -> object:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self.keys())

    def keys(self) -> tuple[str, ...]:
        return tuple(field.name for field in fields(self))

    def items(self) -> tuple[tuple[str, object], ...]:
        return tuple((key, getattr(self, key)) for key in self.keys())

    def values(self) -> tuple[object, ...]:
        return tuple(getattr(self, key) for key in self.keys())


@dataclass(frozen=True, slots=True)
class LiquidityBucket:
    """A liquidity-score bucket with dirty-PV weight."""

    label: str
    min_score: Decimal
    max_score: Decimal | None
    weight: Decimal
    dirty_pv: Decimal
    holding_count: int


@dataclass(frozen=True, slots=True)
class LiquidityDistribution(Mapping[str, LiquidityBucket]):
    """Ordered liquidity buckets keyed by label."""

    entries: tuple[LiquidityBucket, ...]

    def __getitem__(self, key: str) -> LiquidityBucket:
        for entry in self.entries:
            if entry.label == key:
                return entry
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self.entries)

    def keys(self) -> tuple[str, ...]:
        return tuple(entry.label for entry in self.entries)

    def values(self) -> tuple[LiquidityBucket, ...]:
        return self.entries

    def items(self) -> tuple[tuple[str, LiquidityBucket], ...]:
        return tuple((entry.label, entry) for entry in self.entries)

    @property
    def total_weight(self) -> Decimal:
        """Return the sum of bucket weights."""

        return sum((entry.weight for entry in self.entries), Decimal(0))

    @property
    def total_dirty_pv(self) -> Decimal:
        """Return the sum of bucket dirty PV."""

        return sum((entry.dirty_pv for entry in self.entries), Decimal(0))


@dataclass(frozen=True, slots=True)
class DaysToLiquidate(_MetricMapping):
    """Estimated days to liquidate at a given liquidation fraction."""

    days: Decimal
    liquidity_score: Decimal
    liquidation_fraction: Decimal = Decimal(1)


@dataclass(frozen=True, slots=True)
class LiquidityMetrics(_MetricMapping):
    """Portfolio liquidity summary and bucket distribution."""

    liquidity_score: Decimal
    bid_ask_spread: Decimal
    days_to_liquidate: DaysToLiquidate
    distribution: LiquidityDistribution


_BUCKETS = (
    ("high", Decimal("0.75"), None),
    ("medium", Decimal("0.50"), Decimal("0.75")),
    ("limited", Decimal("0.25"), Decimal("0.50")),
    ("illiquid", Decimal("0.00"), Decimal("0.25")),
)


def _bucket_for(score: Decimal) -> str:
    if score >= Decimal("0.75"):
        return "high"
    if score >= Decimal("0.50"):
        return "medium"
    if score >= Decimal("0.25"):
        return "limited"
    return "illiquid"


def _days_to_liquidate(score: Decimal, liquidation_fraction: Decimal) -> DaysToLiquidate:
    if liquidation_fraction < 0 or liquidation_fraction > 1:
        raise ValueError("liquidation_fraction must be between 0 and 1.")
    base_days = Decimal("1") + (Decimal("1") - score) * Decimal("9")
    return DaysToLiquidate(
        days=base_days * liquidation_fraction,
        liquidity_score=score,
        liquidation_fraction=liquidation_fraction,
    )


def weighted_liquidity_score(portfolio: Portfolio, *, curve, settlement_date) -> Decimal:
    """Return the portfolio liquidity score as a raw decimal."""

    return PortfolioAnalytics(portfolio).metrics(curve, settlement_date).liquidity_score


def weighted_bid_ask_spread(portfolio: Portfolio, *, curve, settlement_date) -> Decimal:
    """Return the dirty-value-weighted bid/ask spread as a raw decimal."""

    positions = PortfolioAnalytics(portfolio).position_metrics(curve, settlement_date)
    total_dirty = sum((item.dirty_value for item in positions), Decimal(0))
    if total_dirty == 0:
        return Decimal(0)
    original_positions = {
        position.name(): position
        for position in portfolio.positions
        if hasattr(position, "name")
    }
    total = Decimal(0)
    for item in positions:
        position = original_positions.get(item.name)
        raw = getattr(position, "bid_ask_spread", None) if position is not None else None
        if raw is None and position is not None:
            custom_fields = getattr(position, "custom_fields", {})
            raw = (
                custom_fields.get("bid_ask_spread")
                or custom_fields.get("bid_ask")
                or custom_fields.get("bidask_spread")
                or Decimal(0)
            )
        spread = raw if isinstance(raw, Decimal) else Decimal(str(raw or 0))
        total += spread * item.dirty_value
    return total / total_dirty


def liquidity_distribution(portfolio: Portfolio, *, curve, settlement_date) -> LiquidityDistribution:
    """Return the liquidity bucket distribution."""

    positions = PortfolioAnalytics(portfolio).position_metrics(curve, settlement_date)
    total_dirty = sum((item.dirty_value for item in positions), Decimal(0))
    grouped: dict[str, list[object]] = {label: [] for label, _, _ in _BUCKETS}
    for item in positions:
        score = item.liquidity_score or Decimal(0)
        grouped[_bucket_for(score)].append(item)
    entries: list[LiquidityBucket] = []
    for label, min_score, max_score in _BUCKETS:
        selected = grouped[label]
        dirty = sum((item.dirty_value for item in selected), Decimal(0))
        weight = Decimal(0) if total_dirty == 0 else dirty / total_dirty
        entries.append(
            LiquidityBucket(
                label=label,
                min_score=min_score,
                max_score=max_score,
                weight=weight,
                dirty_pv=dirty,
                holding_count=len(selected),
            )
        )
    return LiquidityDistribution(entries=tuple(entries))


def estimate_days_to_liquidate(
    portfolio: Portfolio,
    *,
    curve,
    settlement_date,
    liquidation_fraction: Decimal = Decimal(1),
) -> DaysToLiquidate:
    """Estimate days to liquidate for the portfolio."""

    score = weighted_liquidity_score(portfolio, curve=curve, settlement_date=settlement_date)
    return _days_to_liquidate(score, liquidation_fraction)


def calculate_liquidity_metrics(portfolio: Portfolio, *, curve, settlement_date) -> LiquidityMetrics:
    """Return the standard liquidity metrics."""

    score = weighted_liquidity_score(portfolio, curve=curve, settlement_date=settlement_date)
    distribution = liquidity_distribution(portfolio, curve=curve, settlement_date=settlement_date)
    days = _days_to_liquidate(score, Decimal(1))
    return LiquidityMetrics(
        liquidity_score=score,
        bid_ask_spread=weighted_bid_ask_spread(portfolio, curve=curve, settlement_date=settlement_date),
        days_to_liquidate=days,
        distribution=distribution,
    )


__all__ = [
    "DaysToLiquidate",
    "LiquidityBucket",
    "LiquidityDistribution",
    "LiquidityMetrics",
    "calculate_liquidity_metrics",
    "estimate_days_to_liquidate",
    "liquidity_distribution",
    "weighted_bid_ask_spread",
    "weighted_liquidity_score",
]
