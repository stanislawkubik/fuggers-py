"""Street-convention yield (`fuggers_py.bonds._yields.street`).

The returned yield is a raw decimal rate, matching the bond solver's internal
representation rather than a quoted percentage.
"""

from __future__ import annotations

from fuggers_py.bonds.types import YieldConvention

from .solver import YieldSolver


def street_convention_yield(
    dirty_price: float,
    cashflows: list[float],
    times: list[float],
    *,
    frequency: int,
    initial_guess: float | None = None,
) -> float:
    """Return the street-convention yield as a raw decimal rate.

    The result follows the bond solver's raw-decimal convention rather than a
    quoted percentage display format.
    """

    solver = YieldSolver()
    result = solver.solve(
        dirty_price=float(dirty_price),
        cashflows=[float(cf) for cf in cashflows],
        times=[float(t) for t in times],
        frequency=int(frequency),
        convention=YieldConvention.STREET_CONVENTION,
        initial_guess=initial_guess,
    )
    return float(result.yield_value)


__all__ = ["street_convention_yield"]
