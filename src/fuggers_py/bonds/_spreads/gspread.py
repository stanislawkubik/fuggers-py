"""G-spread helpers.

Unsuffixed helpers return raw decimal spreads. Use the explicit ``*_bps``
wrappers for display/reporting values quoted in basis points.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core import Tenor
from fuggers_py.bonds.traits import Bond
from fuggers_py._core.types import Date

from .benchmark import BenchmarkSpec, BenchmarkKind, _to_decimal
from .government_curve import GovernmentCurve


def g_spread(bond_yield: object, benchmark_yield: object) -> Decimal:
    """Return the g-spread as a raw decimal.

    Positive values mean the bond yield is above the benchmark yield.
    """
    by = _to_decimal(bond_yield)
    gy = _to_decimal(benchmark_yield)
    return by - gy


def g_spread_bps(bond_yield: object, benchmark_yield: object) -> Decimal:
    """Return the g-spread in basis points."""

    return g_spread(bond_yield, benchmark_yield) * Decimal(10_000)


def g_spread_with_benchmark(
    bond_yield: object,
    curve: GovernmentCurve,
    maturity: Tenor | Date,
    *,
    benchmark: BenchmarkSpec | None = None,
) -> Decimal:
    """Return the g-spread as a raw decimal against a curve benchmark."""
    if benchmark is None:
        benchmark = BenchmarkSpec.interpolated()
    if benchmark.kind is BenchmarkKind.EXPLICIT and benchmark.explicit_yield is not None:
        bench_yield = benchmark.explicit_yield
    else:
        if isinstance(maturity, Tenor):
            bench_yield = curve.yield_for_tenor(maturity, spec=benchmark)
        else:
            bench_yield = curve.yield_for_date(maturity, spec=benchmark)
    return g_spread(bond_yield, bench_yield)


def g_spread_with_benchmark_bps(
    bond_yield: object,
    curve: GovernmentCurve,
    maturity: Tenor | Date,
    *,
    benchmark: BenchmarkSpec | None = None,
) -> Decimal:
    """Return the g-spread in basis points against a curve benchmark."""

    return g_spread_with_benchmark(
        bond_yield,
        curve,
        maturity,
        benchmark=benchmark,
    ) * Decimal(10_000)


@dataclass(frozen=True, slots=True)
class GSpreadCalculator:
    """Curve-backed g-spread calculator with decimal and bps outputs.

    Parameters
    ----------
    curve:
        Government curve used to locate the benchmark yield.
    """

    curve: GovernmentCurve

    def spread_decimal(
        self,
        bond: Bond,
        bond_yield: object,
        *,
        benchmark: BenchmarkSpec | None = None,
    ) -> Decimal:
        """Return the g-spread as a raw decimal for ``bond``."""
        maturity = bond.maturity_date()
        return g_spread_with_benchmark(bond_yield, self.curve, maturity, benchmark=benchmark)

    def spread_bps(
        self,
        bond: Bond,
        bond_yield: object,
        *,
        benchmark: BenchmarkSpec | None = None,
    ) -> Decimal:
        """Return the g-spread in basis points for ``bond``."""

        return self.spread_decimal(bond, bond_yield, benchmark=benchmark) * Decimal(10_000)

__all__ = [
    "GSpreadCalculator",
    "g_spread",
    "g_spread_bps",
    "g_spread_with_benchmark",
    "g_spread_with_benchmark_bps",
]
