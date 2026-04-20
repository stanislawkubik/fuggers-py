"""Finite-difference helpers built on ``float`` and ``numpy`` arrays.

The functions in this module are intentionally small and explicit so they can
be used for derivative estimation in the solver and optimization layers without
pulling in symbolic or automatic differentiation dependencies. They assume the
caller can evaluate the target function at nearby points and that the resulting
values are finite.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .errors import InvalidInput
from .utils import assert_finite, assert_finite_array

FiniteDifferenceMethod = Literal["central", "forward", "backward"]


def finite_difference_derivative(
    f: Callable[[float], float],
    x: float,
    *,
    h: float = 1e-6,
    method: FiniteDifferenceMethod = "central",
) -> float:
    """Estimate the derivative of a scalar function by finite differences.

    Parameters
    ----------
    f:
        Scalar function of one scalar variable.
    x:
        Evaluation point.
    h:
        Positive finite-difference step size.
    method:
        Finite-difference stencil to use. ``"central"`` is the default and is
        the most accurate of the supported first-order stencils.

    Returns
    -------
    float
        Numerical derivative estimate at ``x``.

    Raises
    ------
    InvalidInput
        If ``h`` is not positive, the method name is unknown, or any sampled
        value is non-finite.
    """

    x = assert_finite(x, name="x")
    h = assert_finite(h, name="h")
    if h <= 0.0:
        raise InvalidInput("h must be positive.")

    fx = assert_finite(f(x), name="f(x)")
    if method == "central":
        fx_plus = assert_finite(f(x + h), name="f(x+h)")
        fx_minus = assert_finite(f(x - h), name="f(x-h)")
        return (fx_plus - fx_minus) / (2.0 * h)
    if method == "forward":
        fx_plus = assert_finite(f(x + h), name="f(x+h)")
        return (fx_plus - fx) / h
    if method == "backward":
        fx_minus = assert_finite(f(x - h), name="f(x-h)")
        return (fx - fx_minus) / h
    raise InvalidInput(f"Unknown finite-difference method: {method!r}.")


def finite_difference_gradient(
    f: Callable[[NDArray[np.float64]], float],
    x: NDArray[np.float64] | ArrayLike,
    *,
    h: float = 1e-6,
) -> NDArray[np.float64]:
    """Estimate the gradient of a scalar objective on a 1D parameter vector.

    Parameters
    ----------
    f:
        Scalar objective function.
    x:
        One-dimensional parameter vector.
    h:
        Positive central-difference step size applied coordinate-wise.

    Returns
    -------
    numpy.ndarray
        Gradient vector with the same shape as ``x``.

    Raises
    ------
    InvalidInput
        If ``x`` is not one-dimensional or ``h`` is not positive.
    """

    x_arr = assert_finite_array(x, name="x").astype(float, copy=False)
    if x_arr.ndim != 1:
        raise InvalidInput(f"x must be 1D; got shape {x_arr.shape}.")
    h = assert_finite(h, name="h")
    if h <= 0.0:
        raise InvalidInput("h must be positive.")

    grad = np.empty_like(x_arr, dtype=float)
    for i in range(x_arr.size):
        step = np.zeros_like(x_arr)
        step[i] = h
        f_plus = assert_finite(float(f(x_arr + step)), name="f(x+h)")
        f_minus = assert_finite(float(f(x_arr - step)), name="f(x-h)")
        grad[i] = (f_plus - f_minus) / (2.0 * h)
    return grad


def finite_difference_jacobian(
    residuals_fn: Callable[[NDArray[np.float64]], NDArray[np.float64] | ArrayLike],
    x: NDArray[np.float64] | ArrayLike,
    *,
    h: float = 1e-6,
) -> NDArray[np.float64]:
    """Estimate the Jacobian of a vector residual function.

    Parameters
    ----------
    residuals_fn:
        Function returning a one-dimensional residual vector.
    x:
        One-dimensional parameter vector.
    h:
        Positive central-difference step size applied coordinate-wise.

    Returns
    -------
    numpy.ndarray
        Jacobian matrix with shape ``(m, n)`` for ``m`` residuals and ``n``
        parameters.

    Raises
    ------
    InvalidInput
        If the parameter vector is not one-dimensional, ``h`` is not positive,
        or the residual function returns inconsistent shapes.
    """

    x_arr = assert_finite_array(x, name="x").astype(float, copy=False)
    if x_arr.ndim != 1:
        raise InvalidInput(f"x must be 1D; got shape {x_arr.shape}.")
    h = assert_finite(h, name="h")
    if h <= 0.0:
        raise InvalidInput("h must be positive.")

    r0 = assert_finite_array(residuals_fn(x_arr), name="residuals(x)")
    if r0.ndim != 1:
        raise InvalidInput(f"residuals_fn must return 1D; got shape {r0.shape}.")
    m = int(r0.size)
    n = int(x_arr.size)
    jac = np.empty((m, n), dtype=float)

    for j in range(n):
        step = np.zeros_like(x_arr)
        step[j] = h
        r_plus = assert_finite_array(residuals_fn(x_arr + step), name="residuals(x+h)")
        r_minus = assert_finite_array(residuals_fn(x_arr - step), name="residuals(x-h)")
        if r_plus.shape != r0.shape or r_minus.shape != r0.shape:
            raise InvalidInput("residuals_fn returned inconsistent shapes.")
        jac[:, j] = (r_plus - r_minus) / (2.0 * h)
    if not np.all(np.isfinite(jac)):
        raise InvalidInput("Jacobian contains non-finite values.")
    return jac
