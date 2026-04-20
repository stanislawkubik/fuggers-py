"""Interpolation interfaces and shared helpers.

The interpolation layer operates on scalar tenor-like axes and keeps the
extrapolation policy explicit so curve objects can state whether values outside
their native knot range are accepted.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..errors import ExtrapolationNotAllowed, InvalidInput
from ..utils import assert_finite, assert_finite_array, bisect_segment


class Interpolator(Protocol):
    """Protocol for one-dimensional interpolators.

    Implementations are expected to accept finite scalar ``x`` values and return
    scalar interpolated values and derivatives. ``allows_extrapolation`` reports
    whether points outside the native knot range are accepted. The axis is
    assumed to be ordered and finite.
    """

    def interpolate(self, x: float) -> float:  # pragma: no cover - protocol
        ...

    def derivative(self, x: float) -> float:  # pragma: no cover - protocol
        ...

    @property
    def allows_extrapolation(self) -> bool:  # pragma: no cover - protocol
        ...

    def min_x(self) -> float:  # pragma: no cover - protocol
        ...

    def max_x(self) -> float:  # pragma: no cover - protocol
        ...

    def in_range(self, x: float) -> bool:  # pragma: no cover - protocol
        ...


class _SegmentedInterpolatorMixin:
    """Shared implementation for interpolators defined on a sorted knot grid."""

    _xs: NDArray[np.float64]
    _ys: NDArray[np.float64]
    _allow_extrapolation: bool

    @property
    def allows_extrapolation(self) -> bool:
        return bool(self._allow_extrapolation)

    def min_x(self) -> float:
        return float(self._xs[0])

    def max_x(self) -> float:
        return float(self._xs[-1])

    def in_range(self, x: float) -> bool:
        x = float(x)
        return self.min_x() <= x <= self.max_x()

    def _validate_x(self, x: float) -> float:
        """Validate a query point and enforce the extrapolation policy.

        Raises
        ------
        ExtrapolationNotAllowed
            If the query point lies outside the knot range and extrapolation is
            disabled.
        InvalidInput
            If the query point is not finite.
        """

        x = assert_finite(x, name="x")
        if not self.allows_extrapolation and not self.in_range(x):
            raise ExtrapolationNotAllowed(x=x, min=self.min_x(), max=self.max_x())
        return x

    def _segment_index(self, x: float) -> int:
        """Return the left-hand segment index containing ``x``."""

        return bisect_segment(self._xs, x)

    def interpolate_vec(self, xs: ArrayLike) -> NDArray[np.float64]:
        """Vectorized interpolation helper for 1D arrays of query points.

        The helper keeps the scalar interpolation rules intact and simply
        applies them point by point.
        """

        arr = assert_finite_array(xs, name="xs").astype(float, copy=False)
        if arr.ndim != 1:
            raise InvalidInput(f"xs must be 1D; got shape {arr.shape}.")
        return np.array([self.interpolate(float(x)) for x in arr], dtype=float)
