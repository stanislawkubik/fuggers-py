from __future__ import annotations

import numpy as np
import pytest

from fuggers_py.math.errors import DivisionByZero, SingularMatrix
from fuggers_py.math.linear_algebra import lu_decomposition, solve_linear_system, solve_tridiagonal


def test_lu_decomposition_reconstructs() -> None:
    a = np.array([[4.0, 3.0], [6.0, 3.0]])
    p, l, u = lu_decomposition(a)
    assert np.allclose(p @ a, l @ u)


def test_solve_linear_system() -> None:
    a = np.array([[3.0, 2.0], [1.0, 2.0]])
    b = np.array([5.0, 5.0])
    x = solve_linear_system(a, b)
    assert x == pytest.approx(np.array([0.0, 2.5]))


def test_singular_matrix_raises() -> None:
    a = np.array([[1.0, 2.0], [2.0, 4.0]])
    b = np.array([1.0, 1.0])
    with pytest.raises(SingularMatrix):
        _ = solve_linear_system(a, b)


def test_solve_tridiagonal_matches_known_solution() -> None:
    lower = np.array([1.0, 1.0])
    diag = np.array([4.0, 4.0, 4.0])
    upper = np.array([1.0, 1.0])
    rhs = np.array([6.0, 6.0, 6.0])
    x = solve_tridiagonal(lower, diag, upper, rhs)
    expected = np.array([1.2857142857142858, 0.8571428571428571, 1.2857142857142858])
    assert x == pytest.approx(expected)


def test_tridiagonal_division_by_zero_raises() -> None:
    with pytest.raises(DivisionByZero):
        _ = solve_tridiagonal([0.0], [0.0, 1.0], [0.0], [1.0, 1.0])

