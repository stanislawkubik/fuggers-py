"""Flat-forward interpolation for zero rates with piecewise-constant forwards.

The curve stores zero rates on a strictly increasing tenor grid, then derives a
piecewise-constant instantaneous forward curve. Between pillars the zero curve
is backed out from those forwards. This is a common convention for discount
curve work.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import ExtrapolationNotAllowed, InsufficientData, InvalidInput
from ..utils import assert_finite, assert_finite_array, assert_same_length, assert_strictly_increasing, bisect_segment


@dataclass(frozen=True, slots=True)
class FlatForward:
    """Interpolate zero rates while keeping forward rates constant by segment.

    The input curve is interpreted as zero rates at strictly increasing positive
    tenors. Between pillars the implied instantaneous forward rate is held
    constant; extrapolation beyond the last tenor reuses the last forward rate
    when enabled.
    """

    _tenors: NDArray[np.float64]
    _zero_rates: NDArray[np.float64]
    _forwards: NDArray[np.float64]
    _allow_extrapolation: bool = False

    def __init__(self, tenors: ArrayLike, zero_rates: ArrayLike, allow_extrapolation: bool = False) -> None:
        """Validate the tenor grid and precompute piecewise-constant forwards."""

        t = assert_strictly_increasing(tenors, name="tenors")
        r = assert_finite_array(zero_rates, name="zero_rates").astype(float, copy=False)
        assert_same_length(t, r, a_name="tenors", b_name="zero_rates")
        if t.size < 2:
            raise InsufficientData(required=2, actual=int(t.size))
        if np.any(t <= 0.0):
            raise InvalidInput("tenors must be strictly positive.")

        forwards = np.empty(int(t.size - 1), dtype=float)
        for i in range(forwards.size):
            t0 = float(t[i])
            t1 = float(t[i + 1])
            r0 = float(r[i])
            r1 = float(r[i + 1])
            forwards[i] = (r1 * t1 - r0 * t0) / (t1 - t0)

        object.__setattr__(self, "_tenors", t)
        object.__setattr__(self, "_zero_rates", r)
        object.__setattr__(self, "_forwards", forwards)
        object.__setattr__(self, "_allow_extrapolation", bool(allow_extrapolation))

    @classmethod
    def new(cls, tenors: ArrayLike, zero_rates: ArrayLike) -> "FlatForward":
        """Construct a flat-forward interpolator from tenors and zero rates."""

        return cls(tenors, zero_rates)

    @property
    def allows_extrapolation(self) -> bool:
        return bool(self._allow_extrapolation)

    def with_extrapolation(self) -> "FlatForward":
        """Return a copy that allows evaluation outside the tenor range."""

        return FlatForward(self._tenors, self._zero_rates, allow_extrapolation=True)

    def tenors(self) -> NDArray[np.float64]:
        """Return a copy of the tenor grid."""

        return self._tenors.copy()

    def zero_rates(self) -> NDArray[np.float64]:
        """Return a copy of the input zero rates."""

        return self._zero_rates.copy()

    def forward_rates_vec(self) -> NDArray[np.float64]:
        """Return the cached piecewise-constant forward rates."""

        return self._forwards.copy()

    def min_x(self) -> float:
        return float(self._tenors[0])

    def max_x(self) -> float:
        return float(self._tenors[-1])

    def in_range(self, x: float) -> bool:
        x = float(x)
        return self.min_x() <= x <= self.max_x()

    def _validate_t(self, t: float) -> float:
        t = assert_finite(t, name="t")
        if t <= 0.0:
            raise InvalidInput("t must be positive.")
        if not self.allows_extrapolation and not self.in_range(t):
            raise ExtrapolationNotAllowed(x=t, min=self.min_x(), max=self.max_x())
        return t

    def forward_rate(self, t: float) -> float:
        """Return the instantaneous forward rate implied at tenor ``t``."""

        t = self._validate_t(t)
        if t < self._tenors[0]:
            return float(self._zero_rates[0])
        if t > self._tenors[-1]:
            return float(self._forwards[-1])
        i = bisect_segment(self._tenors, t)
        return float(self._forwards[i])

    def interpolate(self, t: float) -> float:
        """Return the zero rate implied at tenor ``t``."""

        t = self._validate_t(t)
        if t <= self._tenors[0]:
            return float(self._zero_rates[0])
        if t >= self._tenors[-1]:
            if t == self._tenors[-1]:
                return float(self._zero_rates[-1])
            f_last = float(self._forwards[-1])
            r_last = float(self._zero_rates[-1])
            t_last = float(self._tenors[-1])
            return (r_last * t_last + f_last * (t - t_last)) / t

        i = bisect_segment(self._tenors, t)
        t0 = float(self._tenors[i])
        r0 = float(self._zero_rates[i])
        f = float(self._forwards[i])
        return (r0 * t0 + f * (t - t0)) / t

    def derivative(self, t: float) -> float:
        """Return the derivative of the zero-rate curve at tenor ``t``."""

        t = self._validate_t(t)
        if t <= self._tenors[0]:
            return 0.0

        if t >= self._tenors[-1]:
            if t == self._tenors[-1]:
                i = int(self._tenors.size - 2)
            else:
                i = int(self._tenors.size - 2)
        else:
            i = bisect_segment(self._tenors, t)

        t0 = float(self._tenors[i])
        r0 = float(self._zero_rates[i])
        f = float(self._forwards[i])
        return -(t0 * (r0 - f)) / (t**2)
