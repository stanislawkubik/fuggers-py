"""Yield engine (`fuggers_py.bonds._yields.engine`).

This module wraps the lower-level bond yield engine and exposes analytics
results with explicit decimal-versus-percentage helpers. The engine result
stores raw decimal yields, while the helper methods convert to quoted
percentage points when needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from fuggers_py._core import YieldCalculationRules
from fuggers_py.bonds._pricing_yield_engine import StandardYieldEngine as _BondYieldEngine
from fuggers_py.bonds.traits import BondCashFlow
from fuggers_py.bonds.types import YieldConvention
from fuggers_py._core.types import Date

from ..errors import AnalyticsError
from .current import current_yield_simple as _current_yield_simple
from .money_market import bond_equivalent_yield, discount_yield


@dataclass(frozen=True, slots=True)
class YieldEngineResult:
    """Container for a solved yield and its convergence metadata.

    Attributes
    ----------
    yield_value : float
        Raw decimal yield returned by the solver.
    iterations : int
        Number of solver iterations performed.
    converged : bool
        Whether the solver converged within the configured tolerance.
    residual : float
        Final pricing residual.
    method : str
        Solver method name reported by the bond engine.
    convention : YieldConvention
        Yield convention used for the solution.
    """

    yield_value: float
    iterations: int
    converged: bool
    residual: float
    method: str
    convention: YieldConvention

    def yield_percent(self) -> float:
        """Return the solved yield in quoted percentage points."""

        return float(self.yield_value) * 100.0

    def yield_decimal(self) -> float:
        """Return the solved yield as a raw decimal rate."""

        return float(self.yield_value)


class YieldEngine(Protocol):
    """Protocol for yield engine implementations used by analytics wrappers."""

    def yield_from_price(
        self,
        cashflows: list[BondCashFlow],
        *,
        clean_price: Decimal,
        accrued: Decimal,
        settlement_date: Date,
        rules: YieldCalculationRules,
    ) -> YieldEngineResult:
        ...

    def dirty_price_from_yield(
        self,
        cashflows: list[BondCashFlow],
        *,
        yield_rate: float,
        settlement_date: Date,
        rules: YieldCalculationRules,
    ) -> float:
        ...

    def clean_price_from_yield(
        self,
        cashflows: list[BondCashFlow],
        *,
        yield_rate: float,
        accrued: Decimal,
        settlement_date: Date,
        rules: YieldCalculationRules,
    ) -> float:
        ...


@dataclass(frozen=True, slots=True)
class StandardYieldEngine:
    """Analytics wrapper around the bond pricing yield engine.

    The wrapper preserves the underlying solver behavior while converting the
    result into ``YieldEngineResult``.
    """

    tolerance: float = 1e-10
    max_iterations: int = 100

    def _engine(self) -> _BondYieldEngine:
        return _BondYieldEngine(tolerance=self.tolerance, max_iterations=self.max_iterations)

    def yield_from_price(
        self,
        cashflows: list[BondCashFlow],
        *,
        clean_price: Decimal,
        accrued: Decimal,
        settlement_date: Date,
        rules: YieldCalculationRules,
    ) -> YieldEngineResult:
        engine = self._engine()
        result = engine.yield_from_price(
            cashflows,
            clean_price=clean_price,
            accrued=accrued,
            settlement_date=settlement_date,
            rules=rules,
        )
        return YieldEngineResult(
            yield_value=float(result.yield_rate),
            iterations=int(result.iterations),
            converged=bool(result.converged),
            residual=float(result.residual),
            method=str(result.method),
            convention=result.convention,
        )

    def dirty_price_from_yield(
        self,
        cashflows: list[BondCashFlow],
        *,
        yield_rate: float,
        settlement_date: Date,
        rules: YieldCalculationRules,
    ) -> float:
        engine = self._engine()
        return float(
            engine.dirty_price_from_yield(
                cashflows,
                yield_rate=float(yield_rate),
                settlement_date=settlement_date,
                rules=rules,
            )
        )

    def clean_price_from_yield(
        self,
        cashflows: list[BondCashFlow],
        *,
        yield_rate: float,
        accrued: Decimal,
        settlement_date: Date,
        rules: YieldCalculationRules,
    ) -> float:
        dirty = self.dirty_price_from_yield(
            cashflows,
            yield_rate=yield_rate,
            settlement_date=settlement_date,
            rules=rules,
        )
        return dirty - float(accrued)


def discount_yield_simple(face_value: float, price: float, days_to_maturity: float) -> float:
    """Return discount yield as a float quoted percentage."""

    return float(discount_yield(face_value, price, days_to_maturity))


def bond_equivalent_yield_simple(face_value: float, price: float, days_to_maturity: float) -> float:
    """Return bond-equivalent yield as a float quoted percentage."""

    return float(bond_equivalent_yield(face_value, price, days_to_maturity))


def current_yield_simple(coupon_rate: float, clean_price: float) -> float:
    """Return current yield as a raw decimal float."""

    return float(_current_yield_simple(coupon_rate, clean_price))


__all__ = [
    "YieldEngine",
    "YieldEngineResult",
    "StandardYieldEngine",
    "discount_yield_simple",
    "bond_equivalent_yield_simple",
    "current_yield_simple",
]
