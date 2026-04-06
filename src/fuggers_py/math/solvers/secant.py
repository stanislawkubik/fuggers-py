"""Secant root solver."""

from __future__ import annotations

from collections.abc import Callable

from ..errors import ConvergenceFailed, DivisionByZero, InvalidInput
from ..utils import assert_finite
from .types import SolverConfig, SolverResult


def secant(
    f: Callable[[float], float],
    x0: float,
    x1: float,
    config: SolverConfig = SolverConfig(),
) -> SolverResult:
    """Find a scalar root with the secant method.

    The solver uses two starting points and updates the pair by the standard
    secant recurrence. The residual in the result is the absolute function
    value at the final iterate. A bracket is not required, but the method can
    fail if consecutive function values become equal.
    """

    x0 = assert_finite(x0, name="x0")
    x1 = assert_finite(x1, name="x1")
    if config.max_iterations <= 0:
        raise InvalidInput("max_iterations must be positive.")
    if config.tolerance <= 0:
        raise InvalidInput("tolerance must be positive.")

    f0 = assert_finite(f(x0), name="f(x0)")
    f1 = assert_finite(f(x1), name="f(x1)")
    if abs(f0) <= config.tolerance:
        return SolverResult(root=x0, iterations=0, residual=abs(f0), converged=True)
    if abs(f1) <= config.tolerance:
        return SolverResult(root=x1, iterations=0, residual=abs(f1), converged=True)

    for it in range(1, config.max_iterations + 1):
        denom = f1 - f0
        if denom == 0.0:
            raise DivisionByZero(value=denom)
        x2 = x1 - f1 * (x1 - x0) / denom
        f2 = assert_finite(f(x2), name="f(x2)")
        residual = abs(f2)
        if residual <= config.tolerance:
            return SolverResult(root=x2, iterations=it, residual=residual, converged=True)
        x0, f0, x1, f1 = x1, f1, x2, f2

    residual = abs(assert_finite(f(x1), name="f(last)"))
    raise ConvergenceFailed(iterations=config.max_iterations, residual=residual)


class SecantSolver:
    """Callable wrapper around :func:`secant` with a stored configuration."""

    def __init__(self, *, config: SolverConfig = SolverConfig()) -> None:
        self._config = config

    def find_root(self, f: Callable[[float], float], x0: float, x1: float) -> SolverResult:
        """Dispatch to :func:`secant` using the stored configuration."""

        return secant(f, x0, x1, config=self._config)
