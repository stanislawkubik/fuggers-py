"""Dense linear system helpers built on LU factorization.

These helpers solve full dense systems by factoring the coefficient matrix once
and then applying forward and backward substitution. They are intended for
small to medium dense systems in the numerical subpackages.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import DimensionMismatch, InvalidInput, SingularMatrix
from ..utils import assert_finite_array
from .lu import lu_decomposition


def _forward_substitution(l: NDArray[np.float64], b: NDArray[np.float64]) -> NDArray[np.float64]:
    """Solve a unit-lower-triangular system by forward substitution."""

    n = int(l.shape[0])
    y = np.empty(n, dtype=float)
    for i in range(n):
        y[i] = b[i] - float(np.dot(l[i, :i], y[:i]))
    return y


def _back_substitution(u: NDArray[np.float64], y: NDArray[np.float64]) -> NDArray[np.float64]:
    """Solve an upper-triangular system by backward substitution."""

    n = int(u.shape[0])
    x = np.empty(n, dtype=float)
    scale = float(np.max(np.abs(u))) if u.size else 0.0
    pivot_tol = np.finfo(float).eps * max(1.0, scale) * n
    for i in range(n - 1, -1, -1):
        pivot = float(u[i, i])
        if abs(pivot) <= pivot_tol:
            raise SingularMatrix()
        x[i] = (y[i] - float(np.dot(u[i, i + 1 :], x[i + 1 :]))) / pivot
    return x


def solve_linear_system(a: ArrayLike, b: ArrayLike) -> NDArray[np.float64]:
    """Solve ``A x = b`` using LU decomposition with partial pivoting.

    Parameters
    ----------
    a:
        Square coefficient matrix.
    b:
        Right-hand-side vector.

    Returns
    -------
    numpy.ndarray
        Solution vector ``x``.

    Raises
    ------
    DimensionMismatch
        If ``b`` does not have the same length as ``a`` has rows.
    InvalidInput
        If the inputs are not finite or have incompatible shapes.
    SingularMatrix
        If the matrix is singular or numerically singular.
    """

    a_arr = assert_finite_array(a, name="a").astype(float, copy=False)
    b_arr = assert_finite_array(b, name="b").astype(float, copy=False)

    if a_arr.ndim != 2:
        raise InvalidInput(f"a must be 2D; got shape {a_arr.shape}.")
    if b_arr.ndim != 1:
        raise InvalidInput(f"b must be 1D; got shape {b_arr.shape}.")

    n, m = a_arr.shape
    if n != m:
        raise InvalidInput(f"a must be square; got shape {a_arr.shape}.")
    if b_arr.shape[0] != n:
        raise DimensionMismatch(rows1=n, cols1=m, rows2=int(b_arr.shape[0]), cols2=1)

    p, l, u = lu_decomposition(a_arr)
    pb = p @ b_arr
    y = _forward_substitution(l, pb)
    return _back_substitution(u, y)
