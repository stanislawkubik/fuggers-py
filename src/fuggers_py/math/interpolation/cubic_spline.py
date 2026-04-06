"""Natural cubic spline interpolation.

The spline uses zero second-derivative boundary conditions at the end knots.
It is a smooth interpolator for finite data where curvature continuity matters.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import InsufficientData
from ..linear_algebra import solve_tridiagonal
from ..utils import assert_finite_array, assert_same_length, assert_strictly_increasing
from .base import _SegmentedInterpolatorMixin


@dataclass(frozen=True, slots=True)
class CubicSpline(_SegmentedInterpolatorMixin):
    """Natural cubic spline interpolator with zero second derivatives at endpoints."""

    _xs: NDArray[np.float64]
    _ys: NDArray[np.float64]
    _m: NDArray[np.float64]
    _allow_extrapolation: bool = False

    @classmethod
    def new(cls, xs: ArrayLike, ys: ArrayLike) -> "CubicSpline":
        """Construct a natural cubic spline from knot and value arrays."""

        return cls(xs=xs, ys=ys)

    def with_extrapolation(self) -> "CubicSpline":
        """Return a copy that allows evaluation outside the knot range."""

        return CubicSpline(self._xs, self._ys, allow_extrapolation=True)

    def __init__(self, xs: ArrayLike, ys: ArrayLike, allow_extrapolation: bool = False) -> None:
        """Validate the knots and precompute the spline second derivatives."""

        x_arr = assert_strictly_increasing(xs, name="xs")
        y_arr = assert_finite_array(ys, name="ys").astype(float, copy=False)
        assert_same_length(x_arr, y_arr, a_name="xs", b_name="ys")
        n = int(x_arr.size)
        if n < 3:
            raise InsufficientData(required=3, actual=n)

        h = np.diff(x_arr)
        diag = 2.0 * (h[:-1] + h[1:])
        rhs = 6.0 * ((np.diff(y_arr[1:]) / h[1:]) - (np.diff(y_arr[:-1]) / h[:-1]))

        if n - 2 == 1:
            m_inner = rhs / diag
        else:
            lower = h[1:-1]
            upper = h[1:-1]
            m_inner = solve_tridiagonal(lower, diag, upper, rhs)

        m = np.zeros(n, dtype=float)
        m[1:-1] = m_inner

        object.__setattr__(self, "_xs", x_arr)
        object.__setattr__(self, "_ys", y_arr)
        object.__setattr__(self, "_m", m)
        object.__setattr__(self, "_allow_extrapolation", bool(allow_extrapolation))

    def interpolate(self, x: float) -> float:
        """Evaluate the spline at ``x``."""

        x = self._validate_x(x)
        i = self._segment_index(x)
        x0 = float(self._xs[i])
        x1 = float(self._xs[i + 1])
        y0 = float(self._ys[i])
        y1 = float(self._ys[i + 1])
        m0 = float(self._m[i])
        m1 = float(self._m[i + 1])
        h = x1 - x0
        a = (x1 - x) / h
        b = (x - x0) / h
        term = ((a**3 - a) * m0 + (b**3 - b) * m1) * (h**2) / 6.0
        return a * y0 + b * y1 + term

    def derivative(self, x: float) -> float:
        """Evaluate the first derivative of the spline at ``x``."""

        x = self._validate_x(x)
        i = self._segment_index(x)
        x0 = float(self._xs[i])
        x1 = float(self._xs[i + 1])
        y0 = float(self._ys[i])
        y1 = float(self._ys[i + 1])
        m0 = float(self._m[i])
        m1 = float(self._m[i + 1])
        h = x1 - x0
        a = (x1 - x) / h
        b = (x - x0) / h
        return (y1 - y0) / h + ((3.0 * b**2 - 1.0) * m1 - (3.0 * a**2 - 1.0) * m0) * h / 6.0
