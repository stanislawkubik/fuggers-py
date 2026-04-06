"""LU decomposition with partial pivoting.

The routines in this module are small, dense-matrix helpers used by the math
layer. They operate on finite floating-point arrays and raise structured
exceptions when the matrix is singular or the inputs do not form a square
system.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import InvalidInput, SingularMatrix
from ..utils import assert_finite_array


def lu_decomposition(
    a: ArrayLike,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Compute the LU decomposition with partial pivoting.

    Parameters
    ----------
    a:
        Square matrix to factorize.

    Returns
    -------
    tuple of numpy.ndarray
        ``(P, L, U)`` such that ``P @ A = L @ U`` where ``P`` is a permutation
        matrix, ``L`` is unit lower triangular, and ``U`` is upper triangular.

    Raises
    ------
    InvalidInput
        If ``a`` is not a finite square matrix.
    SingularMatrix
        If the pivot tolerance indicates that the matrix is numerically singular.
    """

    a_arr = assert_finite_array(a, name="a").astype(float, copy=False)
    if a_arr.ndim != 2:
        raise InvalidInput(f"a must be 2D; got shape {a_arr.shape}.")
    n, m = a_arr.shape
    if n != m:
        raise InvalidInput(f"a must be square; got shape {a_arr.shape}.")

    u = a_arr.copy()
    l = np.zeros((n, n), dtype=float)
    p = np.eye(n, dtype=float)

    scale = float(np.max(np.abs(u))) if u.size else 0.0
    pivot_tol = np.finfo(float).eps * max(1.0, scale) * n

    for k in range(n):
        pivot_row = int(k + np.argmax(np.abs(u[k:, k])))
        pivot = float(u[pivot_row, k])
        if abs(pivot) <= pivot_tol:
            raise SingularMatrix()

        if pivot_row != k:
            u[[k, pivot_row], :] = u[[pivot_row, k], :]
            p[[k, pivot_row], :] = p[[pivot_row, k], :]
            if k > 0:
                l[[k, pivot_row], :k] = l[[pivot_row, k], :k]

        for i in range(k + 1, n):
            l[i, k] = u[i, k] / u[k, k]
            u[i, k:] = u[i, k:] - l[i, k] * u[k, k:]
            u[i, k] = 0.0

    np.fill_diagonal(l, 1.0)
    return p, l, u
