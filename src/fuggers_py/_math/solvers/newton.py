"""Newton-Raphson root solvers."""

from __future__ import annotations

from collections.abc import Callable

from ..errors import ConvergenceFailed, DivisionByZero, InvalidInput
from ..numerical import finite_difference_derivative
from ..utils import assert_finite
from .types import SolverConfig, SolverResult


def newton_raphson(
    f: Callable[[float], float],
    df: Callable[[float], float],
    x0: float,
    config: SolverConfig = SolverConfig(),
) -> SolverResult:
    """Find a scalar root with Newton-Raphson iteration.

    The method applies the analytic derivative at each iterate and stops when
    ``|f(x)|`` is within ``config.tolerance``. It requires a non-zero
    derivative at every evaluated iterate.

    Parameters
    ----------
    f:
        Scalar function whose root is sought.
    df:
        Analytic derivative of ``f``.
    x0:
        Initial guess.
    config:
        Absolute residual tolerance and iteration cap.

    Raises
    ------
    DivisionByZero
        If the derivative evaluates to zero at an iterate.
    ConvergenceFailed
        If the solver exhausts the iteration budget before meeting tolerance.
    """

    x = assert_finite(x0, name="x0")
    if config.max_iterations <= 0:
        raise InvalidInput("max_iterations must be positive.")
    if config.tolerance <= 0:
        raise InvalidInput("tolerance must be positive.")

    for it in range(1, config.max_iterations + 1):
        fx = assert_finite(f(x), name="f(x)")
        residual = abs(fx)
        if residual <= config.tolerance:
            return SolverResult(root=x, iterations=it - 1, residual=residual, converged=True)
        dfx = assert_finite(df(x), name="df(x)")
        if dfx == 0.0:
            raise DivisionByZero(value=dfx)
        x = x - fx / dfx

    residual = abs(assert_finite(f(x), name="f(last)"))
    raise ConvergenceFailed(iterations=config.max_iterations, residual=residual)


def newton_raphson_numerical(
    f: Callable[[float], float],
    x0: float,
    config: SolverConfig = SolverConfig(),
    *,
    h: float = 1e-6,
) -> SolverResult:
    """Find a scalar root with Newton-Raphson using finite-difference slopes.

    The derivative is approximated with a central finite difference using the
    supplied step size ``h``.
    """

    return newton_raphson(
        f,
        lambda t: finite_difference_derivative(f, t, h=h, method="central"),
        x0,
        config=config,
    )


class NewtonSolver:
    """Callable wrapper around the Newton solvers with an optional derivative."""

    def __init__(
        self,
        *,
        config: SolverConfig = SolverConfig(),
        df: Callable[[float], float] | None = None,
        h: float = 1e-6,
    ) -> None:
        self._config = config
        self._df = df
        self._h = float(h)

    def find_root(self, f: Callable[[float], float], x0: float) -> SolverResult:
        """Dispatch to the analytic or numerical Newton solver."""

        if self._df is None:
            return newton_raphson_numerical(f, x0, config=self._config, h=self._h)
        return newton_raphson(f, self._df, x0, config=self._config)
