"""Gradient descent with Armijo backtracking line search."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import InvalidInput
from ..utils import assert_finite, assert_finite_array
from .types import OptimizationConfig, OptimizationResult


def gradient_descent(
    objective: Callable[[NDArray[np.float64]], float],
    gradient: Callable[[NDArray[np.float64]], NDArray[np.float64]],
    initial_params: ArrayLike,
    config: OptimizationConfig = OptimizationConfig(),
) -> OptimizationResult:
    """Minimize a scalar objective with gradient descent.

    The routine uses a steepest-descent step direction and Armijo backtracking
    to keep each accepted update monotone in the objective value. It stops when
    the gradient norm falls below ``config.tolerance``, or when backtracking
    can no longer find an acceptable step.

    Parameters
    ----------
    objective:
        Scalar objective function of the parameter vector.
    gradient:
        Gradient of ``objective`` with the same shape as the parameters.
    initial_params:
        One-dimensional starting point.
    config:
        Absolute tolerance, iteration cap, and backtracking parameters.

    Returns
    -------
    OptimizationResult
        Best parameter vector found, objective value at that point, iteration
        count, and convergence flag. If backtracking fails, the result is
        returned with ``converged=False`` instead of raising.

    Raises
    ------
    InvalidInput
        If the parameters are not one-dimensional or the configuration values
        are not positive where required.
    """

    x = assert_finite_array(initial_params, name="initial_params").astype(float, copy=False)
    if x.ndim != 1:
        raise InvalidInput(f"initial_params must be 1D; got shape {x.shape}.")
    if config.max_iterations <= 0:
        raise InvalidInput("max_iterations must be positive.")
    if config.tolerance <= 0:
        raise InvalidInput("tolerance must be positive.")

    f_x = assert_finite(float(objective(x)), name="objective(x)")

    for it in range(1, config.max_iterations + 1):
        g = assert_finite_array(gradient(x), name="gradient(x)").astype(float, copy=False)
        if g.shape != x.shape:
            raise InvalidInput("gradient must have the same shape as parameters.")

        g_norm = float(np.linalg.norm(g))
        if g_norm <= config.tolerance:
            return OptimizationResult(parameters=x, objective_value=f_x, iterations=it - 1, converged=True)

        step = 1.0
        descent = float(np.dot(g, g))
        while step >= config.min_step:
            x_new = x - step * g
            f_new = assert_finite(float(objective(x_new)), name="objective(x_new)")
            if f_new <= f_x - config.armijo_c * step * descent:
                x, f_x = x_new, f_new
                break
            step *= config.backtracking_beta

        if step < config.min_step:
            return OptimizationResult(parameters=x, objective_value=f_x, iterations=it, converged=False)

    return OptimizationResult(parameters=x, objective_value=f_x, iterations=config.max_iterations, converged=False)
