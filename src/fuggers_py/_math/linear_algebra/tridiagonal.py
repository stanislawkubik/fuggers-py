"""Tridiagonal linear system solver (Thomas algorithm).

The Thomas algorithm is a specialized dense solver for banded systems with one
sub-diagonal, one main diagonal, and one super-diagonal. It is used by the
spline construction code where the coefficient matrix has this structure.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import DivisionByZero, InvalidInput
from ..utils import assert_finite_array


def solve_tridiagonal(
    lower: ArrayLike,
    diag: ArrayLike,
    upper: ArrayLike,
    rhs: ArrayLike,
) -> NDArray[np.float64]:
    """Solve a tridiagonal linear system with the Thomas algorithm.

    Parameters
    ----------
    lower:
        Sub-diagonal entries with length ``n - 1``.
    diag:
        Main diagonal entries with length ``n``.
    upper:
        Super-diagonal entries with length ``n - 1``.
    rhs:
        Right-hand-side vector with length ``n``.

    Returns
    -------
    numpy.ndarray
        Solution vector.

    Raises
    ------
    DivisionByZero
        If a pivot is zero or numerically zero during elimination or back
        substitution.
    InvalidInput
        If the arrays are not finite, not one-dimensional, or have mismatched
        lengths.
    """

    a = assert_finite_array(lower, name="lower").astype(float, copy=False)
    b = assert_finite_array(diag, name="diag").astype(float, copy=False)
    c = assert_finite_array(upper, name="upper").astype(float, copy=False)
    d = assert_finite_array(rhs, name="rhs").astype(float, copy=False)

    if a.ndim != 1 or b.ndim != 1 or c.ndim != 1 or d.ndim != 1:
        raise InvalidInput("All inputs must be 1D arrays.")

    n = int(b.size)
    if d.size != n:
        raise InvalidInput("rhs must have the same length as diag.")
    if a.size != max(0, n - 1) or c.size != max(0, n - 1):
        raise InvalidInput("lower/upper must have length n-1.")
    if n == 0:
        raise InvalidInput("diag must be non-empty.")

    scale = float(np.max(np.abs(b))) if b.size else 0.0
    pivot_tol = np.finfo(float).eps * max(1.0, scale) * n

    cp = c.copy()
    bp = b.copy()
    dp = d.copy()

    for i in range(1, n):
        pivot = float(bp[i - 1])
        if abs(pivot) <= pivot_tol:
            raise DivisionByZero(value=pivot)
        w = float(a[i - 1]) / pivot
        bp[i] = bp[i] - w * cp[i - 1]
        dp[i] = dp[i] - w * dp[i - 1]

    last_pivot = float(bp[-1])
    if abs(last_pivot) <= pivot_tol:
        raise DivisionByZero(value=last_pivot)

    x = np.empty(n, dtype=float)
    x[-1] = dp[-1] / bp[-1]
    for i in range(n - 2, -1, -1):
        pivot = float(bp[i])
        if abs(pivot) <= pivot_tol:
            raise DivisionByZero(value=pivot)
        x[i] = (dp[i] - cp[i] * x[i + 1]) / pivot

    return x
