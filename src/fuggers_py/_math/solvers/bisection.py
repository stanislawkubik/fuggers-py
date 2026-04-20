"""Bisection root solver."""

from __future__ import annotations

from collections.abc import Callable

from ..errors import ConvergenceFailed, InvalidBracket, InvalidInput
from ..utils import assert_finite
from .types import SolverConfig, SolverResult


def bisection(
    f: Callable[[float], float],
    a: float,
    b: float,
    config: SolverConfig = SolverConfig(),
) -> SolverResult:
    """Find a scalar root with the bisection method.

    The method requires a sign-changing bracket and repeatedly halves the
    interval until either the residual or the interval width falls below
    ``config.tolerance``.

    Parameters
    ----------
    f:
        Scalar function whose root is sought.
    a, b:
        Bracketing endpoints. They must be finite, distinct, and either bracket
        a sign change or hit a root exactly.
    config:
        Iteration cap and absolute residual tolerance.

    Returns
    -------
    SolverResult
        Root estimate, iteration count, residual ``|f(root)|``, and convergence
        flag.

    Raises
    ------
    InvalidBracket
        If ``f(a)`` and ``f(b)`` do not have opposite signs.
    ConvergenceFailed
        If the tolerance is not met within ``config.max_iterations``.
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

    for it in range(1, config.max_iterations + 1):
        mid = 0.5 * (lo + hi)
        fmid = assert_finite(f(mid), name="f(mid)")
        residual = abs(fmid)
        if residual <= config.tolerance or abs(hi - lo) <= config.tolerance:
            return SolverResult(root=mid, iterations=it, residual=residual, converged=True)
        if flo * fmid <= 0.0:
            hi, fhi = mid, fmid
        else:
            lo, flo = mid, fmid

    last_mid = 0.5 * (lo + hi)
    residual = abs(assert_finite(f(last_mid), name="f(last_mid)"))
    raise ConvergenceFailed(iterations=config.max_iterations, residual=residual)


class BisectionSolver:
    """Callable wrapper around :func:`bisection` with a stored configuration."""

    def __init__(self, *, config: SolverConfig = SolverConfig()) -> None:
        self._config = config

    def find_root(self, f: Callable[[float], float], a: float, b: float) -> SolverResult:
        """Dispatch to :func:`bisection` using the stored configuration."""

        return bisection(f, a, b, config=self._config)
