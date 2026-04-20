"""Benchmark comparison helpers.

The comparison helpers build active-weight, duration, yield, spread, and risk
views between a portfolio and a benchmark using the portfolio analytics layer.
Active values are signed as portfolio minus benchmark.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core.types import Date
from fuggers_py.curves import DiscountingCurve

from ..analytics import PortfolioAnalytics
from ..portfolio import Portfolio


@dataclass(frozen=True, slots=True)
class ActiveWeight:
    """Active weight for a single holding or bucket."""

    name: str
    portfolio_weight: Decimal
    benchmark_weight: Decimal
    active_weight: Decimal

    @property
    def value(self) -> Decimal:
        """Return the active weight."""

        return self.active_weight

    def as_dict(self) -> dict[str, Decimal | str]:
        """Return a mapping-style representation."""

        return {
            "name": self.name,
            "portfolio_weight": self.portfolio_weight,
            "benchmark_weight": self.benchmark_weight,
            "active_weight": self.active_weight,
        }

    def __getitem__(self, key: str) -> Decimal | str:
        if key == "name":
            return self.name
        if key == "portfolio_weight":
            return self.portfolio_weight
        if key == "benchmark_weight":
            return self.benchmark_weight
        if key in {"active_weight", "value"}:
            return self.active_weight
        raise KeyError(key)


@dataclass(frozen=True, slots=True)
class ActiveWeights(Mapping[str, Decimal]):
    """Collection of active weights keyed by name."""

    entries: tuple[ActiveWeight, ...]
    dimension: str = "holding"

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, key: str) -> Decimal:
        """Return the active weight for ``key``."""

        entry = self.by_name(key)
        if entry is None:
            raise KeyError(key)
        return entry.active_weight

    def keys(self) -> tuple[str, ...]:
        """Return the active-weight names."""

        return tuple(entry.name for entry in self.entries)

    def values(self) -> tuple[Decimal, ...]:
        """Return the active-weight values."""

        return tuple(entry.active_weight for entry in self.entries)

    def items(self) -> tuple[tuple[str, Decimal], ...]:
        """Return ``(name, active_weight)`` pairs."""

        return tuple((entry.name, entry.active_weight) for entry in self.entries)

    def get(self, key: str, default: Decimal | None = None) -> Decimal | None:
        """Return the active weight for ``key`` or ``default``."""

        entry = self.by_name(key)
        return default if entry is None else entry.active_weight

    def by_name(self, name: str) -> ActiveWeight | None:
        """Return the matching entry if present."""

        return next((entry for entry in self.entries if entry.name == name), None)

    @property
    def portfolio_weights(self) -> dict[str, Decimal]:
        """Return portfolio weights by name."""

        return {entry.name: entry.portfolio_weight for entry in self.entries}

    @property
    def benchmark_weights(self) -> dict[str, Decimal]:
        """Return benchmark weights by name."""

        return {entry.name: entry.benchmark_weight for entry in self.entries}

    @property
    def net_active_weight(self) -> Decimal:
        """Return the signed sum of active weights."""

        return sum(self.values(), Decimal(0))

    def to_dict(self) -> dict[str, Decimal]:
        """Return a plain dictionary of active weights."""

        return dict(self.items())


@dataclass(frozen=True, slots=True)
class DurationComparison:
    """Portfolio, benchmark, and active duration values."""

    portfolio_duration: Decimal
    benchmark_duration: Decimal
    active_duration: Decimal


@dataclass(frozen=True, slots=True)
class RiskComparison:
    """Portfolio, benchmark, and active dirty PV and DV01 values."""

    portfolio_dirty_pv: Decimal
    benchmark_dirty_pv: Decimal
    active_dirty_pv: Decimal
    portfolio_dv01: Decimal
    benchmark_dv01: Decimal
    active_dv01: Decimal


@dataclass(frozen=True, slots=True)
class YieldComparison:
    """Portfolio, benchmark, and active yield metrics."""

    portfolio_current_yield: Decimal
    benchmark_current_yield: Decimal
    active_current_yield: Decimal
    portfolio_ytm: Decimal
    benchmark_ytm: Decimal
    active_ytm: Decimal
    portfolio_ytw: Decimal
    benchmark_ytw: Decimal
    active_ytw: Decimal


@dataclass(frozen=True, slots=True)
class SpreadComparison:
    """Portfolio, benchmark, and active spread metrics."""

    portfolio_z_spread: Decimal
    benchmark_z_spread: Decimal
    active_z_spread: Decimal
    portfolio_oas: Decimal
    benchmark_oas: Decimal
    active_oas: Decimal


@dataclass(frozen=True, slots=True)
class SectorComparison:
    """Portfolio, benchmark, and active sector weights."""

    portfolio_weights: dict[str, Decimal]
    benchmark_weights: dict[str, Decimal]
    active_weights: ActiveWeights


@dataclass(frozen=True, slots=True)
class RatingComparison:
    """Portfolio, benchmark, and active rating weights."""

    portfolio_weights: dict[str, Decimal]
    benchmark_weights: dict[str, Decimal]
    active_weights: ActiveWeights


@dataclass(frozen=True, slots=True)
class BenchmarkComparison:
    """Complete portfolio-versus-benchmark comparison output."""

    risk: RiskComparison
    duration: DurationComparison
    yields: YieldComparison
    spread: SpreadComparison
    active_weights: ActiveWeights
    sector: SectorComparison
    rating: RatingComparison

    @property
    def active_dirty_pv(self) -> Decimal:
        """Return the active dirty PV."""

        return self.risk.active_dirty_pv

    @property
    def active_duration(self) -> Decimal:
        """Return the active duration."""

        return self.duration.active_duration

    @property
    def active_dv01(self) -> Decimal:
        """Return the active DV01."""

        return self.risk.active_dv01

    @property
    def active_current_yield(self) -> Decimal:
        """Return the active current yield."""

        return self.yields.active_current_yield

    @property
    def active_z_spread(self) -> Decimal:
        """Return the active Z-spread."""

        return self.spread.active_z_spread

    @property
    def active_ytm(self) -> Decimal:
        """Return the active YTM."""

        return self.yields.active_ytm

    @property
    def active_ytw(self) -> Decimal:
        """Return the active YTW."""

        return self.yields.active_ytw

    @property
    def active_oas(self) -> Decimal:
        """Return the active OAS."""

        return self.spread.active_oas

    @property
    def sector_active_weights(self) -> ActiveWeights:
        """Return the sector active weights."""

        return self.sector.active_weights

    @property
    def rating_active_weights(self) -> ActiveWeights:
        """Return the rating active weights."""

        return self.rating.active_weights


def _active_weights_from_maps(
    portfolio_weights: dict[str, Decimal],
    benchmark_weights: dict[str, Decimal],
    *,
    dimension: str,
) -> ActiveWeights:
    keys = sorted(set(portfolio_weights) | set(benchmark_weights))
    return ActiveWeights(
        entries=tuple(
            ActiveWeight(
                name=key,
                portfolio_weight=portfolio_weights.get(key, Decimal(0)),
                benchmark_weight=benchmark_weights.get(key, Decimal(0)),
                active_weight=portfolio_weights.get(key, Decimal(0)) - benchmark_weights.get(key, Decimal(0)),
            )
            for key in keys
        ),
        dimension=dimension,
    )


def _bucket_weights(
    portfolio: Portfolio,
    curve: DiscountingCurve,
    settlement_date: Date,
    *,
    field_name: str,
) -> dict[str, Decimal]:
    metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    mapping: dict[str, Decimal] = {}
    for position in portfolio.positions:
        if not hasattr(position, "name"):
            continue
        name = position.name()
        weight = metrics.weights.get(name, Decimal(0))
        classification = getattr(position, "classification", None)
        if classification is None:
            key = "UNCLASSIFIED"
        else:
            value = getattr(classification, field_name, None)
            key = "UNCLASSIFIED" if value is None else getattr(value, "value", str(value))
        mapping[key] = mapping.get(key, Decimal(0)) + weight
    return mapping


def active_weights(
    portfolio: Portfolio,
    benchmark: Portfolio,
    curve: DiscountingCurve,
    settlement_date: Date,
) -> ActiveWeights:
    """Return active holding weights for portfolio minus benchmark."""

    portfolio_weights = PortfolioAnalytics(portfolio).metrics(curve, settlement_date).weights
    benchmark_weights = PortfolioAnalytics(benchmark).metrics(curve, settlement_date).weights
    return _active_weights_from_maps(portfolio_weights, benchmark_weights, dimension="holding")


def compare_portfolios(
    portfolio: Portfolio,
    benchmark: Portfolio,
    curve: DiscountingCurve,
    settlement_date: Date,
) -> BenchmarkComparison:
    """Compare a portfolio with a benchmark on risk, yield, and spread."""

    portfolio_metrics = PortfolioAnalytics(portfolio).metrics(curve, settlement_date)
    benchmark_metrics = PortfolioAnalytics(benchmark).metrics(curve, settlement_date)
    holding_weights = active_weights(portfolio, benchmark, curve, settlement_date)
    sector_portfolio = _bucket_weights(portfolio, curve, settlement_date, field_name="sector")
    sector_benchmark = _bucket_weights(benchmark, curve, settlement_date, field_name="sector")
    rating_portfolio = _bucket_weights(portfolio, curve, settlement_date, field_name="rating")
    rating_benchmark = _bucket_weights(benchmark, curve, settlement_date, field_name="rating")
    return BenchmarkComparison(
        risk=RiskComparison(
            portfolio_dirty_pv=portfolio_metrics.dirty_pv,
            benchmark_dirty_pv=benchmark_metrics.dirty_pv,
            active_dirty_pv=portfolio_metrics.dirty_pv - benchmark_metrics.dirty_pv,
            portfolio_dv01=portfolio_metrics.dv01,
            benchmark_dv01=benchmark_metrics.dv01,
            active_dv01=portfolio_metrics.dv01 - benchmark_metrics.dv01,
        ),
        duration=DurationComparison(
            portfolio_duration=portfolio_metrics.duration,
            benchmark_duration=benchmark_metrics.duration,
            active_duration=portfolio_metrics.duration - benchmark_metrics.duration,
        ),
        yields=YieldComparison(
            portfolio_current_yield=portfolio_metrics.current_yield,
            benchmark_current_yield=benchmark_metrics.current_yield,
            active_current_yield=portfolio_metrics.current_yield - benchmark_metrics.current_yield,
            portfolio_ytm=portfolio_metrics.ytm,
            benchmark_ytm=benchmark_metrics.ytm,
            active_ytm=portfolio_metrics.ytm - benchmark_metrics.ytm,
            portfolio_ytw=portfolio_metrics.ytw,
            benchmark_ytw=benchmark_metrics.ytw,
            active_ytw=portfolio_metrics.ytw - benchmark_metrics.ytw,
        ),
        spread=SpreadComparison(
            portfolio_z_spread=portfolio_metrics.z_spread,
            benchmark_z_spread=benchmark_metrics.z_spread,
            active_z_spread=portfolio_metrics.z_spread - benchmark_metrics.z_spread,
            portfolio_oas=portfolio_metrics.oas,
            benchmark_oas=benchmark_metrics.oas,
            active_oas=portfolio_metrics.oas - benchmark_metrics.oas,
        ),
        active_weights=holding_weights,
        sector=SectorComparison(
            portfolio_weights=sector_portfolio,
            benchmark_weights=sector_benchmark,
            active_weights=_active_weights_from_maps(sector_portfolio, sector_benchmark, dimension="sector"),
        ),
        rating=RatingComparison(
            portfolio_weights=rating_portfolio,
            benchmark_weights=rating_benchmark,
            active_weights=_active_weights_from_maps(rating_portfolio, rating_benchmark, dimension="rating"),
        ),
    )


def benchmark_comparison(
    portfolio: Portfolio,
    benchmark: Portfolio,
    curve: DiscountingCurve,
    settlement_date: Date,
) -> BenchmarkComparison:
    """Compatibility alias for :func:`compare_portfolios`."""

    return compare_portfolios(portfolio, benchmark, curve, settlement_date)


@dataclass(frozen=True, slots=True)
class PortfolioBenchmark:
    """Pair a portfolio with its benchmark for repeated comparisons."""

    portfolio: Portfolio
    benchmark: Portfolio

    def compare(self, curve: DiscountingCurve, settlement_date: Date) -> BenchmarkComparison:
        """Return the portfolio-versus-benchmark comparison."""

        return compare_portfolios(self.portfolio, self.benchmark, curve, settlement_date)

    def active_weights(self, curve: DiscountingCurve, settlement_date: Date) -> ActiveWeights:
        """Return active holding weights."""

        return active_weights(self.portfolio, self.benchmark, curve, settlement_date)

    def active_weights_by_holding(self, curve: DiscountingCurve, settlement_date: Date) -> ActiveWeights:
        """Return active holding weights with holding dimension metadata."""

        return self.active_weights(curve, settlement_date)

    def _active_weights_by(self, curve: DiscountingCurve, settlement_date: Date, *, field_name: str) -> ActiveWeights:
        """Return active weights aggregated by a classification field."""

        portfolio_map = _bucket_weights(self.portfolio, curve, settlement_date, field_name=field_name)
        benchmark_map = _bucket_weights(self.benchmark, curve, settlement_date, field_name=field_name)
        return _active_weights_from_maps(portfolio_map, benchmark_map, dimension=field_name)

    def active_weights_by_sector(self, curve: DiscountingCurve, settlement_date: Date) -> ActiveWeights:
        """Return active sector weights."""

        return self._active_weights_by(curve, settlement_date, field_name="sector")

    def active_weights_by_rating(self, curve: DiscountingCurve, settlement_date: Date) -> ActiveWeights:
        """Return active rating weights."""

        return self._active_weights_by(curve, settlement_date, field_name="rating")

    def aggregated_attribution(self, curve: DiscountingCurve, settlement_date: Date, *, assumptions=None):
        """Return aggregated attribution for the paired portfolio and benchmark."""

        from ..contribution import aggregated_attribution

        return aggregated_attribution(
            self.portfolio,
            curve=curve,
            settlement_date=settlement_date,
            benchmark=self.benchmark,
            assumptions=assumptions,
        )

    def duration_difference_by_sector(self, curve: DiscountingCurve, settlement_date: Date):
        """Return sector duration differences."""

        from ..contribution import duration_difference_by_sector

        return duration_difference_by_sector(self.portfolio, self.benchmark, curve=curve, settlement_date=settlement_date)

    def spread_difference_by_sector(self, curve: DiscountingCurve, settlement_date: Date):
        """Return sector spread differences."""

        from ..contribution import spread_difference_by_sector

        return spread_difference_by_sector(self.portfolio, self.benchmark, curve=curve, settlement_date=settlement_date)

    def overweight_underweight_counts(self, curve: DiscountingCurve, settlement_date: Date) -> dict[str, int]:
        """Return overweight and underweight active-weight counts."""

        active = self.active_weights(curve, settlement_date)
        overweight = sum(1 for value in active.values() if value > 0)
        underweight = sum(1 for value in active.values() if value < 0)
        return {"overweight": overweight, "underweight": underweight}

    def largest_active_positions(
        self,
        curve: DiscountingCurve,
        settlement_date: Date,
        *,
        limit: int = 5,
    ) -> list[tuple[str, Decimal]]:
        """Return the largest active positions by absolute active weight."""

        active = self.active_weights(curve, settlement_date)
        return sorted(active.items(), key=lambda item: abs(item[1]), reverse=True)[:limit]

    def tracking_error_estimate(self, curve: DiscountingCurve, settlement_date: Date) -> Decimal:
        """Return the heuristic tracking error estimate."""

        from .tracking import estimate_tracking_error

        return estimate_tracking_error(self, curve, settlement_date)


BenchmarkMetrics = BenchmarkComparison


__all__ = [
    "ActiveWeight",
    "ActiveWeights",
    "BenchmarkComparison",
    "BenchmarkMetrics",
    "DurationComparison",
    "PortfolioBenchmark",
    "RatingComparison",
    "RiskComparison",
    "SectorComparison",
    "SpreadComparison",
    "YieldComparison",
    "active_weights",
    "benchmark_comparison",
    "compare_portfolios",
]
