"""Brent's method root solver with bracketing safeguards."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from ..errors import ConvergenceFailed, InvalidBracket, InvalidInput
from ..utils import assert_finite
from .types import SolverConfig, SolverResult


def brent(
    f: Callable[[float], float],
    a: float,
    b: float,
    config: SolverConfig = SolverConfig(),
) -> SolverResult:
    """Find a scalar root with Brent's bracketed hybrid method.

    The implementation combines inverse quadratic interpolation, secant steps,
    and bisection fallback. The returned residual is the absolute function
    value at the final iterate. A sign-changing bracket is required.
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

    tol = float(config.tolerance)
    if abs(fa) < abs(fb):
        a, b = b, a
        fa, fb = fb, fa

    c = a
    fc = fa
    d = c
    mflag = True

    for it in range(1, config.max_iterations + 1):
        if abs(fb) <= tol:
            return SolverResult(root=b, iterations=it - 1, residual=abs(fb), converged=True)
        if abs(b - a) <= tol:
            return SolverResult(root=b, iterations=it - 1, residual=abs(fb), converged=True)

        # Inverse quadratic interpolation or secant step.
        if fa != fc and fb != fc:
            s = (
                a * fb * fc / ((fa - fb) * (fa - fc))
                + b * fa * fc / ((fb - fa) * (fb - fc))
                + c * fa * fb / ((fc - fa) * (fc - fb))
            )
        else:
            denom = fb - fa
            if denom == 0.0:
                s = 0.5 * (a + b)
            else:
                s = b - fb * (b - a) / denom

        if b > a:
            cond1 = not ((3.0 * a + b) / 4.0 < s < b)
        else:
            cond1 = not (b < s < (3.0 * a + b) / 4.0)

        cond2 = mflag and abs(s - b) >= abs(b - c) / 2.0
        cond3 = (not mflag) and abs(s - b) >= abs(c - d) / 2.0
        cond4 = mflag and abs(b - c) < tol
        cond5 = (not mflag) and abs(c - d) < tol

        if cond1 or cond2 or cond3 or cond4 or cond5:
            s = 0.5 * (a + b)
            mflag = True
        else:
            mflag = False

        fs = assert_finite(f(float(s)), name="f(s)")

        d = c
        c = b
        fc = fb

        if fa * fs < 0.0:
            b = float(s)
            fb = fs
        else:
            a = float(s)
            fa = fs

        if abs(fa) < abs(fb):
            a, b = b, a
            fa, fb = fb, fa

    residual = abs(assert_finite(f(float(b)), name="f(last)"))
    raise ConvergenceFailed(iterations=config.max_iterations, residual=residual)


class BrentSolver:
    """Callable wrapper around :func:`brent` with a stored configuration."""

    def __init__(self, *, config: SolverConfig = SolverConfig()) -> None:
        self._config = config

    def find_root(self, f: Callable[[float], float], a: float, b: float) -> SolverResult:
        """Dispatch to :func:`brent` using the stored configuration."""

        return brent(f, a, b, config=self._config)
