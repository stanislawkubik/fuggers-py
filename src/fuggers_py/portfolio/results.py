"""Typed public result records for the portfolio package.

These records hold the structured outputs returned by the portfolio analytics
and bucketing helpers. They preserve the package's conventions for clean vs
dirty value, raw-decimal risk metrics, and bucket-level aggregations.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Generic, TypeVar

ValueT = TypeVar("ValueT")


class _EntryMapping(Mapping[str, ValueT], Generic[ValueT]):
    """Dictionary-like base class backed by an ``entries`` attribute."""

    entries: dict[str, ValueT]

    def __iter__(self) -> Iterator[str]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, key: str) -> ValueT:
        return self.entries[key]

    def keys(self) -> tuple[str, ...]:
        return tuple(self.entries.keys())

    def values(self) -> tuple[ValueT, ...]:
        return tuple(self.entries.values())

    def items(self) -> tuple[tuple[str, ValueT], ...]:
        return tuple(self.entries.items())

    def get(self, key: str, default: ValueT | None = None) -> ValueT | None:
        return self.entries.get(key, default)

    def as_dict(self) -> dict[str, ValueT]:
        return dict(self.entries)


@dataclass(frozen=True, slots=True)
class KeyRateProfile(_EntryMapping[Decimal]):
    """Key-rate DV01 profile keyed by tenor string."""

    entries: dict[str, Decimal]

    @property
    def total_dv01(self) -> Decimal:
        """Return the sum of all tenor contributions."""

        return sum(self.entries.values(), Decimal(0))

    def by_tenor(self, tenor: str) -> Decimal | None:
        """Return the contribution for ``tenor`` if present."""

        return self.entries.get(tenor)


@dataclass(frozen=True, slots=True)
class NavBreakdown:
    """Portfolio NAV components in currency units."""

    clean_pv: Decimal
    dirty_pv: Decimal
    accrued: Decimal
    market_value: Decimal
    dirty_market_value: Decimal
    cash_value: Decimal


PositionLikeT = TypeVar("PositionLikeT")


class _DistributionBase(_EntryMapping[list[PositionLikeT]], Generic[PositionLikeT]):
    """Common helpers for bucketed portfolio distributions."""

    @property
    def bucket_count(self) -> int:
        """Return the number of populated buckets."""

        return len(self.entries)

    @property
    def holding_count(self) -> int:
        """Return the number of holdings across all buckets."""

        return sum((len(bucket) for bucket in self.entries.values()), 0)


@dataclass(frozen=True, slots=True)
class CustomDistribution(_DistributionBase[object]):
    """Distribution keyed by a user-defined field name."""

    field_name: str
    entries: dict[str, list[object]]


@dataclass(frozen=True, slots=True)
class ClassifierDistribution(_DistributionBase[object]):
    """Distribution keyed by a named classification dimension."""

    classifier_name: str
    entries: dict[str, list[object]]


@dataclass(frozen=True, slots=True)
class MaturityDistribution(_DistributionBase[object]):
    """Distribution keyed by maturity bucket labels."""

    entries: dict[str, list[object]]
    bucket_definition: tuple[tuple[str, float, float | None], ...]


@dataclass(frozen=True, slots=True)
class RatingDistribution(_DistributionBase[object]):
    """Distribution keyed by credit rating label."""

    entries: dict[str, list[object]]


@dataclass(frozen=True, slots=True)
class SectorDistribution(_DistributionBase[object]):
    """Distribution keyed by sector label."""

    entries: dict[str, list[object]]


@dataclass(frozen=True, slots=True)
class DistributionYield:
    """Distribution yield expressed as raw decimal, percent, and bps."""

    distribution_yield: Decimal
    annual_distribution: Decimal
    market_price: Decimal
    distribution_yield_pct: Decimal
    distribution_yield_bps: Decimal

    @property
    def yield_pct(self) -> Decimal:
        """Return the distribution yield in percentage points."""

        return self.distribution_yield_pct

    def __getattr__(self, name: str) -> Any:
        """Delegate missing numeric operations to the raw decimal value."""

        return getattr(self.distribution_yield, name)

    def __float__(self) -> float:
        return float(self.distribution_yield)

    def __str__(self) -> str:
        return str(self.distribution_yield)

    def __repr__(self) -> str:
        return (
            "DistributionYield("
            f"distribution_yield={self.distribution_yield!r}, "
            f"annual_distribution={self.annual_distribution!r}, "
            f"market_price={self.market_price!r})"
        )

    def _coerce_other(self, other: object) -> Decimal:
        if isinstance(other, DistributionYield):
            return other.distribution_yield
        if isinstance(other, Decimal):
            return other
        return Decimal(str(other))

    def __eq__(self, other: object) -> bool:
        try:
            return self.distribution_yield == self._coerce_other(other)
        except Exception:
            return False

    def __lt__(self, other: object) -> bool:
        return self.distribution_yield < self._coerce_other(other)

    def __le__(self, other: object) -> bool:
        return self.distribution_yield <= self._coerce_other(other)

    def __gt__(self, other: object) -> bool:
        return self.distribution_yield > self._coerce_other(other)

    def __ge__(self, other: object) -> bool:
        return self.distribution_yield >= self._coerce_other(other)

    def __add__(self, other: object) -> Decimal:
        return self.distribution_yield + self._coerce_other(other)

    def __radd__(self, other: object) -> Decimal:
        return self._coerce_other(other) + self.distribution_yield

    def __sub__(self, other: object) -> Decimal:
        return self.distribution_yield - self._coerce_other(other)

    def __rsub__(self, other: object) -> Decimal:
        return self._coerce_other(other) - self.distribution_yield

    def __mul__(self, other: object) -> Decimal:
        return self.distribution_yield * self._coerce_other(other)

    def __rmul__(self, other: object) -> Decimal:
        return self._coerce_other(other) * self.distribution_yield

    def __truediv__(self, other: object) -> Decimal:
        return self.distribution_yield / self._coerce_other(other)

    def __rtruediv__(self, other: object) -> Decimal:
        return self._coerce_other(other) / self.distribution_yield

    def __neg__(self) -> Decimal:
        return -self.distribution_yield

    def __pos__(self) -> Decimal:
        return +self.distribution_yield

    def __abs__(self) -> Decimal:
        return abs(self.distribution_yield)

    def as_decimal(self) -> Decimal:
        """Return the raw decimal distribution yield."""

        return self.distribution_yield


__all__ = [
    "ClassifierDistribution",
    "CustomDistribution",
    "DistributionYield",
    "KeyRateProfile",
    "MaturityDistribution",
    "NavBreakdown",
    "RatingDistribution",
    "SectorDistribution",
]
