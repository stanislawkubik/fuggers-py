"""Log-linear interpolation on strictly positive values.

This interpolator is appropriate for positive curve objects such as discount
factors and survival probabilities, where the logarithm should vary linearly
between knots.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import InsufficientData
from ..utils import assert_all_positive, assert_same_length, assert_strictly_increasing
from .base import _SegmentedInterpolatorMixin


@dataclass(frozen=True, slots=True)
class LogLinearInterpolator(_SegmentedInterpolatorMixin):
    """Interpolate ``y`` values in log space to preserve positivity.

    The inputs must be strictly increasing in ``x`` and strictly positive in
    ``y``. Extrapolation is opt-in and follows the same log-linear rule.
    """

    _xs: NDArray[np.float64]
    _log_ys: NDArray[np.float64]
    _ys: NDArray[np.float64]
    _allow_extrapolation: bool = False

    @classmethod
    def new(cls, xs: ArrayLike, ys: ArrayLike) -> "LogLinearInterpolator":
        """Construct a log-linear interpolator from knot and value arrays."""

        return cls(xs=xs, ys=ys)

    def with_extrapolation(self) -> "LogLinearInterpolator":
        """Return a copy that allows evaluation outside the knot range."""

        return LogLinearInterpolator(self._xs, self._ys, allow_extrapolation=True)

    def __init__(self, xs: ArrayLike, ys: ArrayLike, allow_extrapolation: bool = False) -> None:
        """Validate knots, require positive values, and cache the log values."""

        x_arr = assert_strictly_increasing(xs, name="xs")
        y_arr = assert_all_positive(ys, name="ys")
        assert_same_length(x_arr, y_arr, a_name="xs", b_name="ys")
        if x_arr.size < 2:
            raise InsufficientData(required=2, actual=int(x_arr.size))
        log_y = np.log(y_arr)
        object.__setattr__(self, "_xs", x_arr)
        object.__setattr__(self, "_ys", y_arr)
        object.__setattr__(self, "_log_ys", log_y)
        object.__setattr__(self, "_allow_extrapolation", bool(allow_extrapolation))

    def y_values(self) -> NDArray[np.float64]:
        """Return a copy of the original positive values."""

        return self._ys.copy()

    def interpolate(self, x: float) -> float:
        """Interpolate the value at ``x`` by linearly interpolating ``log(y)``."""

        x = self._validate_x(x)
        i = self._segment_index(x)
        x0 = float(self._xs[i])
        x1 = float(self._xs[i + 1])
        ly0 = float(self._log_ys[i])
        ly1 = float(self._log_ys[i + 1])
        t = (x - x0) / (x1 - x0)
        return float(np.exp(ly0 + t * (ly1 - ly0)))

    def derivative(self, x: float) -> float:
        """Return the derivative implied by the log-linear interpolant."""

        x = self._validate_x(x)
        i = self._segment_index(x)
        x0 = float(self._xs[i])
        x1 = float(self._xs[i + 1])
        ly0 = float(self._log_ys[i])
        ly1 = float(self._log_ys[i + 1])
        slope = (ly1 - ly0) / (x1 - x0)
        y = self.interpolate(x)
        return float(y * slope)
