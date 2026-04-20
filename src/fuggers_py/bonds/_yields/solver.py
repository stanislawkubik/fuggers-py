"""Yield solver (`fuggers_py._measures.yields.solver`).

This wrapper keeps the bond yield solver behavior intact while translating
bond-layer failures into analytics-layer errors.
"""

from __future__ import annotations

from fuggers_py.bonds._yields.bond import YieldResult
from fuggers_py.bonds._yields.bond import YieldSolver as _BondYieldSolver
from fuggers_py.bonds.errors import BondPricingError, YieldConvergenceFailed
from fuggers_py.bonds.types import YieldConvention

from ..analytics_errors import AnalyticsError


class YieldSolver(_BondYieldSolver):
    """Yield solver with analytics error translation.

    The solver delegates to the bond-layer implementation and converts
    bond-layer pricing errors into analytics-layer exceptions.
    """

    def solve(
        self,
        *,
        dirty_price: float,
        cashflows: list[float],
        times: list[float],
        frequency: int,
        convention: YieldConvention = YieldConvention.STREET_CONVENTION,
        initial_guess: float | None = None,
    ) -> YieldResult:
        """Solve for yield using the parent bond solver and normalize errors.

        Returns
        -------
        YieldResult
            Solved yield and convergence metadata.
        """

        try:
            return super().solve(
                dirty_price=dirty_price,
                cashflows=cashflows,
                times=times,
                frequency=frequency,
                convention=convention,
                initial_guess=initial_guess,
            )
        except BondPricingError as exc:
            raise AnalyticsError.invalid_input(exc.reason) from exc
        except YieldConvergenceFailed as exc:
            raise AnalyticsError.yield_solver_failed(str(exc)) from exc


__all__ = ["YieldResult", "YieldSolver"]
