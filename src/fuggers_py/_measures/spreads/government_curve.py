"""Government-curve helpers for spread analytics.

Benchmarks are stored as raw decimal yields and interpolated linearly by
maturity. Nearest-benchmark ties resolve to the shorter tenor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from fuggers_py._core import Tenor
from fuggers_py._core.types import Date

from .benchmark import BenchmarkSpec, BenchmarkKind
from .sovereign import Sovereign
from .benchmark import _to_decimal


@dataclass(frozen=True, slots=True)
class GovernmentBenchmark:
    """Single government benchmark point on the curve.

    Parameters
    ----------
    tenor:
        Benchmark tenor.
    yield_rate:
        Benchmark yield as a raw decimal.
    """

    tenor: Tenor
    yield_rate: Decimal


@dataclass(slots=True)
class GovernmentCurve:
    """Sparse government curve with interpolation and tenor lookup helpers.

    Parameters
    ----------
    sovereign:
        Sovereign issuer tag for the curve.
    reference_date:
        Date from which date-based maturities are measured.
    """

    sovereign: Sovereign
    reference_date: Date
    _benchmarks: dict[Tenor, GovernmentBenchmark] = field(default_factory=dict)

    def add_benchmark(self, tenor: Tenor, yield_rate: object) -> "GovernmentCurve":
        """Add or replace a benchmark yield on the curve."""
        self._benchmarks[tenor] = GovernmentBenchmark(tenor=tenor, yield_rate=_to_decimal(yield_rate))
        return self

    def benchmark_for_tenor(self, tenor: Tenor) -> GovernmentBenchmark | None:
        """Return the stored benchmark for `tenor`, if any."""
        return self._benchmarks.get(tenor)

    def nearest_benchmark(self, years: float) -> GovernmentBenchmark:
        """Return the benchmark tenor closest to `years`."""
        if not self._benchmarks:
            raise ValueError("No benchmarks available.")
        target = float(years)
        best: GovernmentBenchmark | None = None
        best_dist: float | None = None
        best_years: float | None = None
        eps = 1e-12

        for tenor, bench in self._benchmarks.items():
            tenor_years = float(tenor.to_years_approx())
            dist = abs(tenor_years - target)
            if best is None or best_dist is None or best_years is None:
                best = bench
                best_dist = dist
                best_years = tenor_years
                continue
            if dist < best_dist - eps:
                best = bench
                best_dist = dist
                best_years = tenor_years
                continue
            if abs(dist - best_dist) <= eps and tenor_years < best_years:
                best = bench
                best_dist = dist
                best_years = tenor_years

        if best is None:  # pragma: no cover - defensive
            raise ValueError("No benchmarks available.")
        return best

    def interpolated_yield(self, years: float) -> Decimal:
        """Interpolate a raw-decimal yield across the stored benchmarks."""
        if not self._benchmarks:
            raise ValueError("No benchmarks available.")
        points = sorted((tenor.to_years_approx(), bench.yield_rate) for tenor, bench in self._benchmarks.items())
        x = float(years)
        if x <= points[0][0]:
            return points[0][1]
        if x >= points[-1][0]:
            return points[-1][1]
        for (x0, y0), (x1, y1) in zip(points, points[1:], strict=True):
            if x0 <= x <= x1:
                if x1 == x0:
                    return y0
                w = (x - x0) / (x1 - x0)
                return _to_decimal(y0 + (y1 - y0) * Decimal(str(w)))
        return points[-1][1]

    def yield_for_tenor(self, tenor: Tenor, *, spec: BenchmarkSpec | None = None) -> Decimal:
        """Resolve a benchmark yield for the supplied tenor.

        When ``spec`` is omitted or interpolated, the return value is a raw
        decimal yield. Explicit benchmark overrides are also interpreted as raw
        decimal yields.
        """
        if spec is None or spec.kind is BenchmarkKind.INTERPOLATED:
            return self.interpolated_yield(tenor.to_years_approx())
        if spec.kind is BenchmarkKind.NEAREST:
            return self.nearest_benchmark(tenor.to_years_approx()).yield_rate
        if spec.kind is BenchmarkKind.TENOR:
            if spec.tenor is None:
                raise ValueError("BenchmarkSpec.tenor missing.")
            bench = self.benchmark_for_tenor(spec.tenor)
            if bench is None:
                return self.interpolated_yield(spec.tenor.to_years_approx())
            return bench.yield_rate
        if spec.kind is BenchmarkKind.EXPLICIT and spec.explicit_yield is not None:
            return spec.explicit_yield
        return self.interpolated_yield(tenor.to_years_approx())

    def yield_for_date(self, maturity_date: Date, *, spec: BenchmarkSpec | None = None) -> Decimal:
        """Resolve a benchmark yield for a maturity date."""
        years = float(self.reference_date.days_between(maturity_date)) / 365.0
        if spec is None or spec.kind is BenchmarkKind.INTERPOLATED:
            return self.interpolated_yield(years)
        if spec.kind is BenchmarkKind.NEAREST:
            return self.nearest_benchmark(years).yield_rate
        if spec.kind is BenchmarkKind.TENOR:
            if spec.tenor is None:
                raise ValueError("BenchmarkSpec.tenor missing.")
            bench = self.benchmark_for_tenor(spec.tenor)
            if bench is None:
                return self.interpolated_yield(spec.tenor.to_years_approx())
            return bench.yield_rate
        if spec.kind is BenchmarkKind.EXPLICIT and spec.explicit_yield is not None:
            return spec.explicit_yield
        return self.interpolated_yield(years)

    @classmethod
    def us_treasury(cls, reference_date: Date) -> "GovernmentCurve":
        """Build a curve tagged as U.S. Treasury."""
        return cls(sovereign=Sovereign.us_treasury(), reference_date=reference_date)

    @classmethod
    def uk_gilt(cls, reference_date: Date) -> "GovernmentCurve":
        """Build a curve tagged as U.K. gilt."""
        return cls(sovereign=Sovereign.uk_gilt(), reference_date=reference_date)


__all__ = ["GovernmentBenchmark", "GovernmentCurve"]
