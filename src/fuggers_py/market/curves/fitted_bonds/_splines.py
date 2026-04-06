"""Internal spline helpers for fitted bond curves."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from numpy.typing import NDArray

from fuggers_py.math.utils import assert_same_length, assert_strictly_increasing, bisect_segment


@dataclass(frozen=True, slots=True)
class NaturalCubicSplineGrid:
    """Cached natural cubic spline algebra for one fixed knot grid."""

    support_knots: NDArray[np.float64]
    segment_widths: NDArray[np.float64]
    second_derivative_operator: NDArray[np.float64]

    def __init__(self, support_knots: tuple[float, ...]) -> None:
        knot_array = assert_strictly_increasing(support_knots, name="support_knots")
        if knot_array.size < 3:
            raise ValueError("NaturalCubicSplineGrid requires at least three support knots.")

        widths = np.diff(knot_array)
        interior_count = int(knot_array.size - 2)
        rhs_matrix = np.zeros((interior_count, knot_array.size), dtype=float)
        for row in range(interior_count):
            left_width = float(widths[row])
            right_width = float(widths[row + 1])
            rhs_matrix[row, row] = 6.0 / left_width
            rhs_matrix[row, row + 1] = -6.0 * ((1.0 / left_width) + (1.0 / right_width))
            rhs_matrix[row, row + 2] = 6.0 / right_width

        system = np.zeros((interior_count, interior_count), dtype=float)
        if interior_count:
            np.fill_diagonal(system, 2.0 * (widths[:-1] + widths[1:]))
        if interior_count > 1:
            offsets = np.arange(interior_count - 1)
            system[offsets + 1, offsets] = widths[1:-1]
            system[offsets, offsets + 1] = widths[1:-1]

        operator = np.zeros((knot_array.size, knot_array.size), dtype=float)
        if interior_count:
            solved = np.linalg.solve(system, rhs_matrix)
            operator[1:-1, :] = np.asarray(solved, dtype=float)

        object.__setattr__(self, "support_knots", knot_array)
        object.__setattr__(self, "segment_widths", widths.astype(float, copy=False))
        object.__setattr__(self, "second_derivative_operator", operator)

    def second_derivatives(self, node_values: NDArray[np.float64]) -> NDArray[np.float64]:
        """Return natural-spline second derivatives for the supplied node values."""

        assert_same_length(self.support_knots, node_values, a_name="support_knots", b_name="node_values")
        return np.asarray(self.second_derivative_operator @ node_values, dtype=float)

    def evaluate(
        self,
        node_values: NDArray[np.float64],
        second_derivatives: NDArray[np.float64],
        x: float,
    ) -> float:
        """Evaluate the spline at ``x`` using cached grid algebra."""

        assert_same_length(self.support_knots, node_values, a_name="support_knots", b_name="node_values")
        assert_same_length(
            self.support_knots,
            second_derivatives,
            a_name="support_knots",
            b_name="second_derivatives",
        )
        index = bisect_segment(self.support_knots, x)
        x0 = float(self.support_knots[index])
        x1 = float(self.support_knots[index + 1])
        y0 = float(node_values[index])
        y1 = float(node_values[index + 1])
        m0 = float(second_derivatives[index])
        m1 = float(second_derivatives[index + 1])
        width = x1 - x0
        left_weight = (x1 - x) / width
        right_weight = (x - x0) / width
        curvature = (
            ((left_weight**3 - left_weight) * m0)
            + ((right_weight**3 - right_weight) * m1)
        ) * (width**2) / 6.0
        return float((left_weight * y0) + (right_weight * y1) + curvature)

    def derivative(
        self,
        node_values: NDArray[np.float64],
        second_derivatives: NDArray[np.float64],
        x: float,
    ) -> float:
        """Evaluate the spline first derivative at ``x``."""

        assert_same_length(self.support_knots, node_values, a_name="support_knots", b_name="node_values")
        assert_same_length(
            self.support_knots,
            second_derivatives,
            a_name="support_knots",
            b_name="second_derivatives",
        )
        index = bisect_segment(self.support_knots, x)
        x0 = float(self.support_knots[index])
        x1 = float(self.support_knots[index + 1])
        y0 = float(node_values[index])
        y1 = float(node_values[index + 1])
        m0 = float(second_derivatives[index])
        m1 = float(second_derivatives[index + 1])
        width = x1 - x0
        left_weight = (x1 - x) / width
        right_weight = (x - x0) / width
        slope = (y1 - y0) / width
        curvature = (((3.0 * right_weight**2) - 1.0) * m1 - ((3.0 * left_weight**2) - 1.0) * m0) * width / 6.0
        return float(slope + curvature)


@lru_cache(maxsize=None)
def cached_natural_cubic_spline_grid(support_knots: tuple[float, ...]) -> NaturalCubicSplineGrid:
    """Return the cached natural cubic spline helper for ``support_knots``."""

    normalized = tuple(float(knot) for knot in support_knots)
    return NaturalCubicSplineGrid(normalized)


__all__ = ["NaturalCubicSplineGrid", "cached_natural_cubic_spline_grid"]
