"""Typed contribution and attribution results.

These records keep contribution amounts in the same sign convention as the
underlying portfolio analytics: positive values represent positive PV, DV01,
or spread contribution unless a specific helper documents otherwise.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class HoldingContribution:
    """Contribution for a single holding."""

    name: str
    amount: Decimal
    metric: str
    value_key: str
    weight: Decimal = Decimal(0)

    @property
    def contribution(self) -> Decimal:
        """Return the raw contribution amount."""

        return self.amount

    @property
    def duration_contribution(self) -> Decimal:
        """Return the duration contribution when this metric is duration."""

        return self.amount if self.metric == "duration" else Decimal(0)

    @property
    def dv01_contribution(self) -> Decimal:
        """Return the DV01 contribution when this metric is DV01."""

        return self.amount if self.metric == "dv01" else Decimal(0)

    @property
    def spread_contribution(self) -> Decimal:
        """Return the spread contribution when this metric is CS01."""

        return self.amount if self.metric == "cs01" else Decimal(0)

    @property
    def cs01_contribution(self) -> Decimal:
        """Return the CS01 contribution alias."""

        return self.spread_contribution

    def as_dict(self) -> dict[str, Decimal | str]:
        """Return a mapping-style representation."""

        return {
            "name": self.name,
            "metric": self.metric,
            "weight": self.weight,
            "contribution": self.amount,
            self.value_key: self.amount,
        }

    def __getitem__(self, key: str) -> Decimal | str:
        if key == "name":
            return self.name
        if key == "metric":
            return self.metric
        if key == "weight":
            return self.weight
        if key in {"contribution", self.value_key}:
            return self.amount
        if self.metric == "cs01" and key == "cs01_contribution":
            return self.amount
        raise KeyError(key)


class _ContributionCollection(Sequence[HoldingContribution]):
    """Sequence-like base class for holding contribution collections."""

    entries: tuple[HoldingContribution, ...]

    def __iter__(self) -> Iterator[HoldingContribution]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, index: int | slice) -> HoldingContribution | tuple[HoldingContribution, ...]:
        return self.entries[index]

    def values(self) -> tuple[Decimal, ...]:
        """Return the contribution amounts."""

        return tuple(entry.amount for entry in self.entries)

    def by_name(self, name: str) -> HoldingContribution | None:
        """Return the named contribution if present."""

        return next((entry for entry in self.entries if entry.name == name), None)


@dataclass(frozen=True, slots=True)
class DurationContributions(_ContributionCollection):
    """Holding duration contributions."""

    entries: tuple[HoldingContribution, ...]
    total: Decimal = Decimal(0)


@dataclass(frozen=True, slots=True)
class Dv01Contributions(_ContributionCollection):
    """Holding DV01 contributions."""

    entries: tuple[HoldingContribution, ...]
    total: Decimal = Decimal(0)


@dataclass(frozen=True, slots=True)
class Cs01Contributions(_ContributionCollection):
    """Holding CS01 contributions."""

    entries: tuple[HoldingContribution, ...]
    total: Decimal = Decimal(0)


SpreadContributions = Cs01Contributions


@dataclass(frozen=True, slots=True)
class HoldingAttribution:
    """Holding-level PV and DV01 attribution."""

    name: str
    pv_pct: Decimal
    dv01_pct: Decimal
    duration_contribution: Decimal

    def as_dict(self) -> dict[str, Decimal | str]:
        """Return a mapping-style representation."""

        return {
            "name": self.name,
            "pv_pct": self.pv_pct,
            "dv01_pct": self.dv01_pct,
            "duration_contribution": self.duration_contribution,
        }

    def __getitem__(self, key: str) -> Decimal | str:
        if key == "name":
            return self.name
        if key == "pv_pct":
            return self.pv_pct
        if key == "dv01_pct":
            return self.dv01_pct
        if key == "duration_contribution":
            return self.duration_contribution
        raise KeyError(key)


@dataclass(frozen=True, slots=True)
class PortfolioAttribution(Sequence[HoldingAttribution]):
    """Sequence of holding-level attribution records."""

    entries: tuple[HoldingAttribution, ...]
    total_pv_pct: Decimal = Decimal(0)
    total_dv01_pct: Decimal = Decimal(0)
    total_duration_contribution: Decimal = Decimal(0)

    def __iter__(self) -> Iterator[HoldingAttribution]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, index: int | slice) -> HoldingAttribution | tuple[HoldingAttribution, ...]:
        return self.entries[index]

    def by_name(self, name: str) -> HoldingAttribution | None:
        """Return the named holding attribution if present."""

        return next((entry for entry in self.entries if entry.name == name), None)


@dataclass(frozen=True, slots=True)
class AttributionInput:
    """Assumptions used to scale attribution return estimates."""

    income_horizon_years: Decimal = Decimal(1)
    rate_change_bps: Decimal = Decimal(0)
    spread_change_bps: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        """Normalize assumption values and validate the horizon."""

        object.__setattr__(self, "income_horizon_years", Decimal(str(self.income_horizon_years)))
        object.__setattr__(self, "rate_change_bps", Decimal(str(self.rate_change_bps)))
        object.__setattr__(self, "spread_change_bps", Decimal(str(self.spread_change_bps)))
        if self.income_horizon_years < 0:
            raise ValueError("income_horizon_years must be non-negative.")

    def aggregate(
        self,
        portfolio: "Portfolio",
        *,
        curve,
        settlement_date,
        benchmark: "Portfolio | None" = None,
    ) -> "AggregatedAttribution":
        """Aggregate attribution using these assumptions."""

        return AggregatedAttribution.from_portfolios(
            portfolio,
            curve=curve,
            settlement_date=settlement_date,
            benchmark=benchmark,
            assumptions=self,
        )


@dataclass(frozen=True, slots=True)
class BucketContribution:
    """Portfolio-versus-benchmark contribution for a bucket."""

    name: str
    portfolio_value: Decimal
    benchmark_value: Decimal
    active_value: Decimal
    portfolio_weight: Decimal = Decimal(0)
    benchmark_weight: Decimal = Decimal(0)
    active_weight: Decimal = Decimal(0)

    @property
    def value(self) -> Decimal:
        """Return the active value."""

        return self.active_value


@dataclass(frozen=True, slots=True)
class SectorAttribution(Mapping[str, BucketContribution]):
    """Bucketed attribution results keyed by sector."""

    entries: tuple[BucketContribution, ...]
    metric: str
    portfolio_total: Decimal
    benchmark_total: Decimal
    active_total: Decimal

    def __getitem__(self, key: str) -> BucketContribution:
        entry = self.by_name(key)
        if entry is None:
            raise KeyError(key)
        return entry

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self.entries)

    def keys(self) -> tuple[str, ...]:
        return tuple(entry.name for entry in self.entries)

    def values(self) -> tuple[BucketContribution, ...]:
        return self.entries

    def items(self) -> tuple[tuple[str, BucketContribution], ...]:
        return tuple((entry.name, entry) for entry in self.entries)

    def by_name(self, name: str) -> BucketContribution | None:
        return next((entry for entry in self.entries if entry.name == name), None)

    @property
    def total_active(self) -> Decimal:
        """Return the total active contribution."""

        return self.active_total


@dataclass(frozen=True, slots=True)
class AggregatedAttribution:
    """Aggregated income, rate, and spread attribution outputs."""

    assumptions: AttributionInput
    income_return: Decimal
    rate_return: Decimal
    spread_return: Decimal
    total_return: Decimal
    benchmark_income_return: Decimal | None = None
    benchmark_rate_return: Decimal | None = None
    benchmark_spread_return: Decimal | None = None
    benchmark_total_return: Decimal | None = None
    active_income_return: Decimal | None = None
    active_rate_return: Decimal | None = None
    active_spread_return: Decimal | None = None
    active_total_return: Decimal | None = None
    duration_by_sector: SectorAttribution | None = None
    spread_by_sector: SectorAttribution | None = None

    @classmethod
    def from_portfolios(
        cls,
        portfolio: "Portfolio",
        *,
        curve,
        settlement_date,
        assumptions: AttributionInput | None = None,
        benchmark: "Portfolio | None" = None,
    ) -> "AggregatedAttribution":
        """Build aggregated attribution from one or two portfolios."""

        from .attribution import aggregated_attribution

        return aggregated_attribution(
            portfolio,
            curve=curve,
            settlement_date=settlement_date,
            assumptions=assumptions,
            benchmark=benchmark,
        )


__all__ = [
    "AggregatedAttribution",
    "AttributionInput",
    "BucketContribution",
    "Cs01Contributions",
    "DurationContributions",
    "Dv01Contributions",
    "HoldingAttribution",
    "HoldingContribution",
    "PortfolioAttribution",
    "SectorAttribution",
    "SpreadContributions",
]
