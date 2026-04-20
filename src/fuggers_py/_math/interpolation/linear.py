"""Piecewise-linear interpolation on strictly increasing knots.

This interpolator is the simplest segmented curve model in the package. It is
used when the caller wants local linear behavior between finite knot points and
an explicit choice about whether endpoint extrapolation is allowed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import InsufficientData
from ..utils import assert_finite_array, assert_same_length, assert_strictly_increasing
from .base import _SegmentedInterpolatorMixin


@dataclass(frozen=True, slots=True)
class LinearInterpolator(_SegmentedInterpolatorMixin):
    """Piecewise-linear interpolator for finite 1D data.

    The interpolator requires strictly increasing ``xs`` and finite ``ys``. By
    default it refuses extrapolation outside the knot range; use
    :meth:`with_extrapolation` to opt in to endpoint extrapolation.
    """

    _xs: NDArray[np.float64]
    _ys: NDArray[np.float64]
    _allow_extrapolation: bool = False

    @classmethod
    def new(cls, xs: ArrayLike, ys: ArrayLike) -> "LinearInterpolator":
        """Construct a linear interpolator from knot and value arrays."""

        return cls(xs=xs, ys=ys)

    def with_extrapolation(self) -> "LinearInterpolator":
        """Return a copy that allows evaluation outside the knot range."""

        return LinearInterpolator(self._xs, self._ys, allow_extrapolation=True)

    def __init__(self, xs: ArrayLike, ys: ArrayLike, allow_extrapolation: bool = False) -> None:
        """Validate knots and cache the piecewise-linear segments."""

        x_arr = assert_strictly_increasing(xs, name="xs")
        y_arr = assert_finite_array(ys, name="ys").astype(float, copy=False)
        assert_same_length(x_arr, y_arr, a_name="xs", b_name="ys")
        if x_arr.size < 2:
            raise InsufficientData(required=2, actual=int(x_arr.size))
        object.__setattr__(self, "_xs", x_arr)
        object.__setattr__(self, "_ys", y_arr)
        object.__setattr__(self, "_allow_extrapolation", bool(allow_extrapolation))

    def interpolate(self, x: float) -> float:
        """Interpolate the value at ``x`` with piecewise linear segments."""

        x = self._validate_x(x)
        i = self._segment_index(x)
        x0 = float(self._xs[i])
        x1 = float(self._xs[i + 1])
        y0 = float(self._ys[i])
        y1 = float(self._ys[i + 1])
        t = (x - x0) / (x1 - x0)
        return y0 + t * (y1 - y0)

    def derivative(self, x: float) -> float:
        """Return the slope of the active linear segment at ``x``."""

        x = self._validate_x(x)
        i = self._segment_index(x)
        x0 = float(self._xs[i])
        x1 = float(self._xs[i + 1])
        y0 = float(self._ys[i])
        y1 = float(self._ys[i + 1])
        return (y1 - y0) / (x1 - x0)
