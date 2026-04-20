from __future__ import annotations

import numpy as np
import pytest

from fuggers_py._math.optimization import OptimizationConfig, gauss_newton, gradient_descent, levenberg_marquardt


def test_gradient_descent_quadratic_converges() -> None:
    def objective(x: np.ndarray) -> float:
        return float(0.5 * np.dot(x - 3.0, x - 3.0))

    def grad(x: np.ndarray) -> np.ndarray:
        return x - 3.0

    res = gradient_descent(objective, grad, [0.0, 0.0])
    assert res.converged is True
    assert res.parameters == pytest.approx(np.array([3.0, 3.0]), abs=1e-8)
    assert res.objective_value == pytest.approx(0.0, abs=1e-12)


def test_lm_lite_fits_simple_line() -> None:
    rng = np.random.default_rng(0)
    t = np.linspace(0.0, 2.0, 25)
    a_true, b_true = 2.0, 1.0
    y = a_true * t + b_true + rng.normal(0.0, 0.01, size=t.shape)

    def residuals(params: np.ndarray) -> np.ndarray:
        a, b = float(params[0]), float(params[1])
        return a * t + b - y

    config = OptimizationConfig(tolerance=1e-10, max_iterations=50, step_size=1e-6)
    res_gn = gauss_newton(residuals, [0.0, 0.0], config=config)
    assert res_gn.converged is True
    assert res_gn.parameters[0] == pytest.approx(a_true, abs=2e-2)
    assert res_gn.parameters[1] == pytest.approx(b_true, abs=2e-2)

    res_lm = levenberg_marquardt(residuals, [0.0, 0.0], config=config)
    assert res_lm.converged is True
    assert res_lm.parameters[0] == pytest.approx(a_true, abs=2e-2)
    assert res_lm.parameters[1] == pytest.approx(b_true, abs=2e-2)

