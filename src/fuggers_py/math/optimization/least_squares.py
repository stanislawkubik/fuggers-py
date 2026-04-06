"""Least-squares routines (Gauss-Newton and a small Levenberg-Marquardt)."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import InvalidInput
from ..linear_algebra import solve_linear_system
from ..numerical import finite_difference_jacobian
from ..utils import assert_finite, assert_finite_array
from .types import OptimizationConfig, OptimizationResult


def _residuals_and_jacobian(
    residuals_fn: Callable[[NDArray[np.float64]], NDArray[np.float64] | ArrayLike],
    x: NDArray[np.float64],
    *,
    fd_step: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return residuals and a Jacobian, using finite differences as fallback.

    The residual function may expose a ``jacobian`` attribute. When present, it
    is treated as an analytic Jacobian and must return a two-dimensional array
    with shape ``(m, n)`` matching the residual vector and parameter vector.
    """

    r = assert_finite_array(residuals_fn(x), name="residuals(x)").astype(float, copy=False)
    if r.ndim != 1:
        raise InvalidInput(f"residuals_fn must return 1D; got shape {r.shape}.")

    jac_fn = getattr(residuals_fn, "jacobian", None)
    if callable(jac_fn):
        j = assert_finite_array(jac_fn(x), name="jacobian(x)").astype(float, copy=False)
        if j.ndim != 2:
            raise InvalidInput(f"jacobian must be 2D; got shape {j.shape}.")
        if j.shape[0] != r.size or j.shape[1] != x.size:
            raise InvalidInput("jacobian has incompatible shape.")
        return r, j

    j = finite_difference_jacobian(residuals_fn, x, h=fd_step)
    return r, j


def gauss_newton(
    residuals_fn: Callable[[NDArray[np.float64]], NDArray[np.float64] | ArrayLike],
    x0: ArrayLike,
    config: OptimizationConfig = OptimizationConfig(),
) -> OptimizationResult:
    """Solve a nonlinear least-squares problem with Gauss-Newton iteration.

    The objective optimized is one half of the squared 2-norm of the residual
    vector. Residuals and Jacobians are evaluated on 1D parameter vectors. The
    solver uses the normal equations and falls back to finite-difference
    Jacobians when no analytic Jacobian is provided.

    Returns
    -------
    OptimizationResult
        Best parameter vector, objective value, iteration count, and
        convergence flag. If the iteration budget is exhausted, the final state
        is returned with ``converged=False``.

    Raises
    ------
    InvalidInput
        If the parameter vector is not one-dimensional or the configuration
        contains invalid values.
    """

    x = assert_finite_array(x0, name="x0").astype(float, copy=False)
    if x.ndim != 1:
        raise InvalidInput(f"x0 must be 1D; got shape {x.shape}.")
    if config.max_iterations <= 0:
        raise InvalidInput("max_iterations must be positive.")
    if config.tolerance <= 0:
        raise InvalidInput("tolerance must be positive.")
    fd_step = assert_finite(config.step_size, name="step_size")
    if fd_step <= 0:
        raise InvalidInput("step_size must be positive.")

    r, j = _residuals_and_jacobian(residuals_fn, x, fd_step=fd_step)
    obj = 0.5 * float(np.dot(r, r))

    for it in range(1, config.max_iterations + 1):
        jt = j.T
        g = jt @ r
        if float(np.linalg.norm(g)) <= config.tolerance:
            return OptimizationResult(parameters=x, objective_value=obj, iterations=it - 1, converged=True)

        a = jt @ j
        delta = solve_linear_system(a, -g)
        x_new = x + delta

        r_new, j_new = _residuals_and_jacobian(residuals_fn, x_new, fd_step=fd_step)
        obj_new = 0.5 * float(np.dot(r_new, r_new))

        if abs(obj - obj_new) <= config.tolerance:
            return OptimizationResult(parameters=x_new, objective_value=obj_new, iterations=it, converged=True)

        x, r, j, obj = x_new, r_new, j_new, obj_new

    return OptimizationResult(parameters=x, objective_value=obj, iterations=config.max_iterations, converged=False)


def levenberg_marquardt(
    residuals_fn: Callable[[NDArray[np.float64]], NDArray[np.float64] | ArrayLike],
    x0: ArrayLike,
    config: OptimizationConfig = OptimizationConfig(),
) -> OptimizationResult:
    """Solve a nonlinear least-squares problem with a damped Gauss-Newton step.

    The damping parameter is adapted multiplicatively: rejected steps increase
    damping, while accepted steps reduce it. Residuals and Jacobians are
    evaluated on 1D parameter vectors. This variant is more forgiving than
    plain Gauss-Newton on poorly scaled problems because the diagonal damping
    term keeps the linear solve well conditioned.

    Returns
    -------
    OptimizationResult
        Best parameter vector, objective value, iteration count, and
        convergence flag. If the iteration budget is exhausted, the final state
        is returned with ``converged=False``.

    Raises
    ------
    InvalidInput
        If the parameter vector is not one-dimensional or any damping-related
        configuration value is invalid.
    """

    x = assert_finite_array(x0, name="x0").astype(float, copy=False)
    if x.ndim != 1:
        raise InvalidInput(f"x0 must be 1D; got shape {x.shape}.")
    if config.max_iterations <= 0:
        raise InvalidInput("max_iterations must be positive.")
    if config.tolerance <= 0:
        raise InvalidInput("tolerance must be positive.")
    fd_step = assert_finite(config.step_size, name="step_size")
    if fd_step <= 0:
        raise InvalidInput("step_size must be positive.")

    r, j = _residuals_and_jacobian(residuals_fn, x, fd_step=fd_step)
    obj = 0.5 * float(np.dot(r, r))

    lam = float(config.lm_initial_damping)
    if not np.isfinite(lam) or lam <= 0:
        raise InvalidInput("lm_initial_damping must be positive and finite.")

    for it in range(1, config.max_iterations + 1):
        jt = j.T
        a = jt @ j
        g = jt @ r

        if float(np.linalg.norm(g)) <= config.tolerance:
            return OptimizationResult(parameters=x, objective_value=obj, iterations=it - 1, converged=True)

        n = int(x.size)
        a_damped = a + lam * np.eye(n)
        delta = solve_linear_system(a_damped, -g)
        x_candidate = x + delta

        r_candidate, j_candidate = _residuals_and_jacobian(residuals_fn, x_candidate, fd_step=fd_step)
        obj_candidate = 0.5 * float(np.dot(r_candidate, r_candidate))

        if obj_candidate < obj:
            x, r, j, obj = x_candidate, r_candidate, j_candidate, obj_candidate
            lam = max(lam * float(config.lm_damping_decrease), 1e-15)
            if float(np.linalg.norm(delta)) <= config.tolerance:
                return OptimizationResult(parameters=x, objective_value=obj, iterations=it, converged=True)
        else:
            lam = lam * float(config.lm_damping_increase)

    return OptimizationResult(parameters=x, objective_value=obj, iterations=config.max_iterations, converged=False)
