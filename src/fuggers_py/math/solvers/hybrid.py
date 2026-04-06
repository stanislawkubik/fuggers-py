"""Bracketed hybrid root solvers combining Newton and bisection steps."""

from __future__ import annotations

from collections.abc import Callable

from ..errors import ConvergenceFailed, DivisionByZero, InvalidBracket, InvalidInput
from ..numerical import finite_difference_derivative
from ..utils import assert_finite
from .types import SolverConfig, SolverResult


def hybrid(
    f: Callable[[float], float],
    df: Callable[[float], float],
    a: float,
    b: float,
    x0: float,
    config: SolverConfig = SolverConfig(),
) -> SolverResult:
    """Find a scalar root with safeguarded Newton iteration inside a bracket.

    The method keeps a valid sign-changing bracket and falls back to bisection
    whenever a Newton step would leave the bracket. The residual is the
    absolute scalar function value at the returned iterate. A valid bracket is
    required, and the starting guess is projected into the bracket when needed.
    """

    a = assert_finite(a, name="a")
    b = assert_finite(b, name="b")
    if a == b:
        raise InvalidInput("a and b must be distinct.")
    if config.max_iterations <= 0:
        raise InvalidInput("max_iterations must be positive.")
    if config.tolerance <= 0:
        raise InvalidInput("tolerance must be positive.")

    fa = assert_finite(f(a), name="f(a)")
    fb = assert_finite(f(b), name="f(b)")
    if fa == 0.0:
        return SolverResult(root=a, iterations=0, residual=0.0, converged=True)
    if fb == 0.0:
        return SolverResult(root=b, iterations=0, residual=0.0, converged=True)
    if fa * fb > 0.0:
        raise InvalidBracket(a=a, b=b, fa=fa, fb=fb)

    lo, hi = (a, b) if a < b else (b, a)
    flo = fa if a < b else fb
    fhi = fb if a < b else fa

    x = assert_finite(x0, name="x0")
    if x <= lo or x >= hi:
        x = 0.5 * (lo + hi)

    for it in range(1, config.max_iterations + 1):
        fx = assert_finite(f(x), name="f(x)")
        residual = abs(fx)
        if residual <= config.tolerance:
            return SolverResult(root=x, iterations=it - 1, residual=residual, converged=True)

        # Maintain the bracket using the current point.
        if flo * fx <= 0.0:
            hi, fhi = x, fx
        else:
            lo, flo = x, fx

        dfx = assert_finite(df(x), name="df(x)")
        x_new: float
        if dfx != 0.0:
            x_new = x - fx / dfx
        else:
            raise DivisionByZero(value=dfx)

        # Safeguard: if Newton step leaves bracket, fall back to bisection.
        if not (lo < x_new < hi):
            x_new = 0.5 * (lo + hi)
        x = x_new

    residual = abs(assert_finite(f(x), name="f(last)"))
    raise ConvergenceFailed(iterations=config.max_iterations, residual=residual)


def hybrid_numerical(
    f: Callable[[float], float],
    a: float,
    b: float,
    x0: float,
    config: SolverConfig = SolverConfig(),
    *,
    h: float = 1e-6,
) -> SolverResult:
    """Find a scalar root with safeguarded Newton iteration and numerical slopes.

    The derivative is approximated with a central finite difference using the
    supplied step size ``h``.
    """

    return hybrid(
        f,
        lambda t: finite_difference_derivative(f, t, h=h, method="central"),
        a,
        b,
        x0,
        config=config,
    )


class HybridSolver:
    """Callable wrapper around the safeguarded Newton root solvers."""

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

    def find_root(self, f: Callable[[float], float], a: float, b: float, x0: float) -> SolverResult:
        """Dispatch to :func:`hybrid` or :func:`hybrid_numerical`."""

        if self._df is None:
            return hybrid_numerical(f, a, b, x0, config=self._config, h=self._h)
        return hybrid(f, self._df, a, b, x0, config=self._config)
