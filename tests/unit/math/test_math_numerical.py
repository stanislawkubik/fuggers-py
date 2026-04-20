from __future__ import annotations

import math

import numpy as np
import pytest

from fuggers_py._math.errors import InvalidInput
from fuggers_py._math.numerical import (
    finite_difference_derivative,
    finite_difference_gradient,
    finite_difference_jacobian,
)


@pytest.mark.parametrize("method", ["central", "forward", "backward"])
def test_finite_difference_derivative_matches_known_quadratic(method: str) -> None:
    result = finite_difference_derivative(lambda x: x * x + 2.0 * x, 1.5, h=1e-6, method=method)
    assert result == pytest.approx(5.0, abs=1e-5)


def test_finite_difference_derivative_rejects_invalid_steps_methods_and_non_finite_values() -> None:
    with pytest.raises(InvalidInput, match="h must be positive"):
        finite_difference_derivative(lambda x: x, 1.0, h=0.0)

    with pytest.raises(InvalidInput, match="Unknown finite-difference method"):
        finite_difference_derivative(lambda x: x, 1.0, method="secant")  # type: ignore[arg-type]

    with pytest.raises(InvalidInput, match="f\\(x\\)"):
        finite_difference_derivative(lambda _x: math.inf, 1.0)


def test_finite_difference_gradient_matches_known_function() -> None:
    point = np.array([1.5, -2.0], dtype=float)
    gradient = finite_difference_gradient(lambda x: x[0] ** 2 + 3.0 * x[1], point)
    assert gradient == pytest.approx(np.array([3.0, 3.0]), abs=1e-6)


def test_finite_difference_gradient_rejects_bad_inputs() -> None:
    with pytest.raises(InvalidInput, match="x must be 1D"):
        finite_difference_gradient(lambda x: float(np.sum(x)), np.array([[1.0, 2.0]]))

    with pytest.raises(InvalidInput, match="h must be positive"):
        finite_difference_gradient(lambda x: float(np.sum(x)), np.array([1.0, 2.0]), h=-1.0)

    with pytest.raises(InvalidInput, match="f\\(x\\+h\\)"):
        finite_difference_gradient(lambda _x: math.nan, np.array([1.0, 2.0]))


def test_finite_difference_jacobian_matches_known_residual_system() -> None:
    jacobian = finite_difference_jacobian(
        lambda x: np.array([x[0] + x[1], x[0] * x[1]], dtype=float),
        np.array([2.0, 3.0], dtype=float),
    )

    assert jacobian == pytest.approx(np.array([[1.0, 1.0], [3.0, 2.0]]), abs=1e-6)


def test_finite_difference_jacobian_rejects_bad_inputs_and_shapes() -> None:
    with pytest.raises(InvalidInput, match="x must be 1D"):
        finite_difference_jacobian(lambda x: np.array([float(np.sum(x))]), np.array([[1.0, 2.0]]))

    with pytest.raises(InvalidInput, match="residuals_fn must return 1D"):
        finite_difference_jacobian(lambda _x: np.array([[1.0, 2.0]]), np.array([1.0, 2.0]))

    with pytest.raises(InvalidInput, match="inconsistent shapes"):
        finite_difference_jacobian(
            lambda x: np.array([1.0, 2.0]) if x[0] >= 0 else np.array([1.0]),
            np.array([0.0, 1.0]),
        )

    with pytest.raises(InvalidInput, match="residuals\\(x\\+h\\)"):
        finite_difference_jacobian(
            lambda x: np.array([math.inf]) if x[0] > 0 else np.array([0.0]),
            np.array([0.0]),
        )
