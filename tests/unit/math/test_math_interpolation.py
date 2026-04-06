from __future__ import annotations

import numpy as np
import pytest

from fuggers_py.math.errors import ExtrapolationNotAllowed
from fuggers_py.math.interpolation import (
    CubicSpline,
    FlatForward,
    LinearInterpolator,
    LogLinearInterpolator,
    MonotoneConvex,
    NelsonSiegel,
    Svensson,
)


def _central_diff(fn, x: float, h: float = 1e-6) -> float:
    return float((fn(x + h) - fn(x - h)) / (2.0 * h))


def test_linear_interpolator_passes_through_points() -> None:
    xs = [0.0, 1.0, 2.0]
    ys = [0.0, 1.0, 4.0]
    itp = LinearInterpolator(xs, ys)
    for x, y in zip(xs, ys, strict=True):
        assert itp.interpolate(x) == pytest.approx(y)
    assert itp.derivative(0.5) == pytest.approx(1.0)
    assert itp.derivative(1.5) == pytest.approx(3.0)

    with pytest.raises(ExtrapolationNotAllowed):
        _ = itp.interpolate(-0.1)


def test_log_linear_interpolator_is_exact_for_exponential() -> None:
    r = 0.05
    xs = np.array([0.0, 1.0, 2.0])
    ys = np.exp(-r * xs)
    itp = LogLinearInterpolator(xs, ys)
    x = 0.3
    assert itp.interpolate(x) == pytest.approx(float(np.exp(-r * x)), rel=0, abs=1e-12)
    assert itp.derivative(x) == pytest.approx(float(-r * np.exp(-r * x)), rel=0, abs=1e-10)


def test_cubic_spline_derivative_matches_central_diff() -> None:
    xs = np.array([0.0, 1.0, 2.0, 3.0])
    ys = np.sin(xs)
    sp = CubicSpline(xs, ys, allow_extrapolation=True)
    for x, y in zip(xs, ys, strict=True):
        assert sp.interpolate(float(x)) == pytest.approx(float(y))
    x = 1.3
    assert sp.derivative(x) == pytest.approx(_central_diff(sp.interpolate, x), abs=1e-6)


def test_flat_forward_passes_through_pillars() -> None:
    tenors = np.array([1.0, 2.0, 3.0])
    zeros = np.array([0.02, 0.025, 0.03])
    ff = FlatForward(tenors, zeros, allow_extrapolation=True)
    for t, r in zip(tenors, zeros, strict=True):
        assert ff.interpolate(float(t)) == pytest.approx(float(r))

    t = 1.5
    expected_f = (0.025 * 2.0 - 0.02 * 1.0) / (2.0 - 1.0)
    expected_r = (0.02 * 1.0 + expected_f * (t - 1.0)) / t
    assert ff.interpolate(t) == pytest.approx(expected_r)
    assert ff.derivative(t) == pytest.approx(_central_diff(ff.interpolate, t), abs=1e-6)


def test_monotone_convex_forward_non_negative() -> None:
    times = np.array([1.0, 2.0, 5.0, 10.0])
    zeros = np.array([0.01, 0.015, 0.02, 0.02])
    mc = MonotoneConvex(times, zeros, allow_extrapolation=False)
    for t, r in zip(times, zeros, strict=True):
        assert mc.interpolate(float(t)) == pytest.approx(float(r))

    grid = np.linspace(0.0, float(times[-1]), 101)
    forwards = np.array([mc.forward_rate(float(t)) for t in grid])
    assert np.all(forwards >= -1e-12)


def test_parametric_derivatives_match_central_diff() -> None:
    ns = NelsonSiegel.new(beta0=0.02, beta1=-0.01, beta2=0.03, tau=2.0)
    sv = Svensson.new(beta0=0.02, beta1=-0.01, beta2=0.03, beta3=-0.005, tau1=2.0, tau2=5.0)

    for model in (ns, sv):
        t = 3.7
        assert model.derivative(t) == pytest.approx(_central_diff(model.interpolate, t), abs=1e-6)

