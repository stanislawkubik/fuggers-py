"""Monotone-convex interpolation for zero-rate curves.

This implementation follows the general Hagan-West shape-preserving idea but
keeps the code compact and explicit. It is intended for zero-rate curves where
monotonicity of the implied forwards is more important than exact replication
of a particular market formula.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import ExtrapolationNotAllowed, InsufficientData, InvalidInput
from ..numerical import finite_difference_derivative
from ..utils import assert_finite, assert_finite_array, assert_same_length, assert_strictly_increasing


@dataclass(frozen=True, slots=True)
class MonotoneConvex:
    """Hagan-West-inspired monotone-convex interpolation of zero rates.

    The implementation expects strictly increasing positive times and finite
    zero rates. It preserves non-negative discrete forwards and allows optional
    extrapolation beyond the last pillar.
    """

    _times: NDArray[np.float64]
    _zero_rates: NDArray[np.float64]
    _discrete_forwards: NDArray[np.float64]
    _f_inst: NDArray[np.float64]
    _g: NDArray[np.float64]
    _allow_extrapolation: bool = False

    @classmethod
    def new(cls, times: ArrayLike, zero_rates: ArrayLike) -> "MonotoneConvex":
        """Construct a monotone-convex interpolator from times and zero rates."""

        return cls(times=times, zero_rates=zero_rates)

    def with_extrapolation(self) -> "MonotoneConvex":
        """Return a copy that allows evaluation outside the time range."""

        return MonotoneConvex(self._times, self._zero_rates, allow_extrapolation=True)

    @property
    def allows_extrapolation(self) -> bool:
        return bool(self._allow_extrapolation)

    def times(self) -> NDArray[np.float64]:
        """Return a copy of the knot times."""

        return self._times.copy()

    def zero_rates(self) -> NDArray[np.float64]:
        """Return a copy of the input zero rates."""

        return self._zero_rates.copy()

    def discrete_forwards(self) -> NDArray[np.float64]:
        """Return the cached discrete forward rates."""

        return self._discrete_forwards.copy()

    def min_x(self) -> float:
        return 0.0

    def max_x(self) -> float:
        return float(self._times[-1])

    def in_range(self, t: float) -> bool:
        t = float(t)
        return 0.0 <= t <= self.max_x()

    def __init__(self, times: ArrayLike, zero_rates: ArrayLike, allow_extrapolation: bool = False) -> None:
        """Validate the inputs and precompute the monotonicity adjustment data."""

        t = assert_strictly_increasing(times, name="times")
        z = assert_finite_array(zero_rates, name="zero_rates").astype(float, copy=False)
        assert_same_length(t, z, a_name="times", b_name="zero_rates")
        n = int(t.size)
        if n < 2:
            raise InsufficientData(required=2, actual=n)
        if t[0] <= 0.0:
            raise InvalidInput("first time must be positive (use t=0 extrapolation if needed).")

        # Discrete forwards (first interval assumes flat forward from 0 to t[0])
        f_disc = np.empty(n, dtype=float)
        f_disc[0] = float(z[0])
        for i in range(1, n):
            t_prev = float(t[i - 1])
            t_curr = float(t[i])
            z_prev = float(z[i - 1])
            z_curr = float(z[i])
            f = (z_curr * t_curr - z_prev * t_prev) / (t_curr - t_prev)
            if f < 0.0:
                raise InvalidInput(f"negative forward rate {f} between t={t_prev} and t={t_curr}")
            f_disc[i] = f

        # Instantaneous forward estimates at pillars: weighted average of adjacent forwards.
        f_inst = np.empty(n, dtype=float)
        f_inst[0] = f_disc[0]
        for i in range(1, n - 1):
            dt_left = float(t[i] - t[i - 1])
            dt_right = float(t[i + 1] - t[i])
            f_left = float(f_disc[i])
            f_right = float(f_disc[i + 1])
            f_inst[i] = (dt_right * f_left + dt_left * f_right) / (dt_left + dt_right)
        f_inst[-1] = f_disc[-1]

        # Monotonicity factors.
        g = np.empty(n, dtype=float)
        for i in range(n):
            fd = float(f_disc[min(i, n - 1)])
            fi = float(f_inst[i])
            if fd > 0.0:
                g[i] = float(np.clip(fi / fd, 0.0, 2.0))
            else:
                g[i] = 1.0

        object.__setattr__(self, "_times", t)
        object.__setattr__(self, "_zero_rates", z)
        object.__setattr__(self, "_discrete_forwards", f_disc)
        object.__setattr__(self, "_f_inst", f_inst)
        object.__setattr__(self, "_g", g)
        object.__setattr__(self, "_allow_extrapolation", bool(allow_extrapolation))

    def _find_interval(self, t: float) -> int:
        # Return i+1 for an exact match, otherwise the insertion index.
        idx = int(np.searchsorted(self._times, t, side="left"))
        if idx < self._times.size and float(self._times[idx]) == float(t):
            return idx + 1
        return idx

    def forward_rate(self, t: float) -> float:
        """Return the instantaneous forward rate implied at time ``t``."""

        t = assert_finite(t, name="t")
        if t <= 0.0:
            return float(self._discrete_forwards[0])

        if not self.allows_extrapolation and t > self.max_x():
            raise ExtrapolationNotAllowed(x=t, min=0.0, max=self.max_x())

        i = self._find_interval(t)
        if i == 0:
            t_lo, t_hi = 0.0, float(self._times[0])
            f_lo, f_hi = float(self._discrete_forwards[0]), float(self._f_inst[0])
        elif i >= self._times.size:
            return float(self._f_inst[-1])
        else:
            t_lo, t_hi = float(self._times[i - 1]), float(self._times[i])
            f_lo, f_hi = float(self._f_inst[i - 1]), float(self._f_inst[i])

        x = (t - t_lo) / (t_hi - t_lo)
        f = f_lo + x * (f_hi - f_lo)
        return float(max(f, 0.0))

    def interpolate(self, t: float) -> float:
        """Return the zero rate implied at time ``t``."""

        t = assert_finite(t, name="t")
        if t <= 0.0:
            return float(self._zero_rates[0])

        if not self.allows_extrapolation and t > self.max_x():
            raise ExtrapolationNotAllowed(x=t, min=0.0, max=self.max_x())

        i = self._find_interval(t)
        if i == 0:
            return float(self._zero_rates[0])
        if i >= self._times.size:
            return float(self._zero_rates[-1])

        t_lo = float(self._times[i - 1])
        t_hi = float(self._times[i])
        z_lo = float(self._zero_rates[i - 1])
        z_hi = float(self._zero_rates[i])
        f_discrete = float(self._discrete_forwards[i])

        zt = z_lo * t_lo + f_discrete * (t - t_lo)
        z_forward_preserving = zt / t

        x = (t - t_lo) / (t_hi - t_lo)
        z_linear = z_lo + x * (z_hi - z_lo)
        g_factor = float(self._g[i])
        blend = 0.1 * g_factor
        return float((1.0 - blend) * z_forward_preserving + blend * z_linear)

    def derivative(self, t: float) -> float:
        """Return a finite-difference derivative of the interpolated zero curve."""

        t = assert_finite(t, name="t")
        if t <= 0.0:
            return 0.0
        return float(finite_difference_derivative(self.interpolate, t, h=1e-6, method="central"))
