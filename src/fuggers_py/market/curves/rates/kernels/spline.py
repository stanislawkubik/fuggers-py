"""Spline-based internal curve kernels.

These kernels hold the production spline shapes behind ``YieldCurve``.
`CubicSplineKernel` is the one cubic spline production kernel:

1. natural cubic spline
2. zero-rate space
3. fixed knot grid
4. parameters are the zero rates at those supplied knots
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import ArrayLike, NDArray

from fuggers_py.math.errors import MathError
from fuggers_py.math.utils import assert_finite_array, assert_same_length, assert_strictly_increasing

from ...errors import InvalidCurveInput, TenorOutOfBounds
from .base import CurveKernel, CurveKernelKind


def _curve_input_error(exc: Exception) -> InvalidCurveInput:
    return InvalidCurveInput(str(exc))


def _require_positive(value: float, *, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidCurveInput(f"{name} must be finite.")
    if numeric <= 0.0:
        raise InvalidCurveInput(f"{name} must be > 0.")
    return numeric


def _require_non_negative(value: float, *, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidCurveInput(f"{name} must be finite.")
    if numeric < 0.0:
        raise InvalidCurveInput(f"{name} must be >= 0.")
    return numeric


def _require_1d_finite_array(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    try:
        array = assert_finite_array(values, name=name).astype(float, copy=False)
    except MathError as exc:
        raise _curve_input_error(exc) from exc
    if array.ndim != 1:
        raise InvalidCurveInput(f"{name} must be a 1D array.")
    return array


def _validate_query_t(tenor: float, *, max_t: float, allow_extrapolation: bool) -> float:
    checked_tenor = _require_non_negative(tenor, name="tenor")
    if checked_tenor > max_t and not allow_extrapolation:
        raise TenorOutOfBounds(t=checked_tenor, min=0.0, max=max_t)
    return checked_tenor


def _normalize_exponential_inputs(
    coefficients: ArrayLike,
    decay_factors: ArrayLike,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    normalized_coefficients = _require_1d_finite_array(coefficients, name="coefficients")
    normalized_decay_factors = _require_1d_finite_array(decay_factors, name="decay_factors")
    if normalized_decay_factors.size == 0:
        raise InvalidCurveInput("decay_factors must be non-empty.")
    if np.any(normalized_decay_factors <= 0.0):
        raise InvalidCurveInput("decay_factors must be > 0.")
    if normalized_coefficients.size != normalized_decay_factors.size + 1:
        raise InvalidCurveInput("coefficients must have length len(decay_factors) + 1.")
    return normalized_coefficients, normalized_decay_factors


def _normalize_zero_spline_inputs(
    knot_tenors: ArrayLike,
    zero_rates: ArrayLike,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    try:
        tenors = assert_strictly_increasing(knot_tenors, name="knot_tenors")
        rates = assert_finite_array(zero_rates, name="zero_rates").astype(float, copy=False)
        assert_same_length(tenors, rates, a_name="knot_tenors", b_name="zero_rates")
    except MathError as exc:
        raise _curve_input_error(exc) from exc
    if tenors.size < 3:
        raise InvalidCurveInput("at least three spline knots are required.")
    if np.any(tenors < 0.0):
        raise InvalidCurveInput("knot_tenors must be >= 0.")
    if float(tenors[0]) > 0.0:
        tenors = np.insert(tenors, 0, 0.0)
        rates = np.insert(rates, 0, float(rates[0]))
    front_end_spacing = float(tenors[1] - tenors[0])
    if not math.isfinite(front_end_spacing) or front_end_spacing <= 0.0:
        raise InvalidCurveInput("front-end spline knot spacing must be finite and > 0.")
    return tenors, rates


@dataclass(frozen=True, slots=True)
class _NaturalCubicSplineGeometry:
    """Natural cubic spline geometry for one fixed knot grid.

    The helper precomputes the parts that depend only on knot locations:

    1. interval widths
    2. the natural-spline tridiagonal system structure
    3. a reusable tridiagonal factorization for second-derivative solves
    """

    knot_tenors: NDArray[np.float64]
    interval_widths: NDArray[np.float64]
    system_lower: NDArray[np.float64]
    system_diagonal: NDArray[np.float64]
    system_upper: NDArray[np.float64]
    factorized_diagonal: NDArray[np.float64]
    factorized_upper_ratio: NDArray[np.float64]

    def __init__(self, knot_tenors: ArrayLike) -> None:
        tenors = _require_1d_finite_array(knot_tenors, name="knot_tenors")
        try:
            tenors = assert_strictly_increasing(tenors, name="knot_tenors")
        except MathError as exc:
            raise _curve_input_error(exc) from exc
        if tenors.size < 3:
            raise InvalidCurveInput("at least three spline knots are required.")

        interval_widths = np.diff(tenors).astype(float, copy=False)
        if np.any(interval_widths <= 0.0):
            raise InvalidCurveInput("knot_tenors must be strictly increasing.")

        system_size = int(tenors.size - 2)
        system_lower = interval_widths[1:-1].astype(float, copy=False)
        system_diagonal = (2.0 * (interval_widths[:-1] + interval_widths[1:])).astype(float, copy=False)
        system_upper = interval_widths[1:-1].astype(float, copy=False)
        factorized_diagonal = np.asarray(system_diagonal, dtype=float).copy()
        factorized_upper_ratio = np.empty(max(system_size - 1, 0), dtype=float)
        if system_size > 1:
            factorized_upper_ratio[0] = float(system_upper[0]) / float(factorized_diagonal[0])
            for index in range(1, system_size - 1):
                factorized_diagonal[index] -= float(system_lower[index - 1]) * float(
                    factorized_upper_ratio[index - 1]
                )
                factorized_upper_ratio[index] = float(system_upper[index]) / float(factorized_diagonal[index])
            factorized_diagonal[-1] -= float(system_lower[-1]) * float(factorized_upper_ratio[-1])

        object.__setattr__(self, "knot_tenors", tenors)
        object.__setattr__(self, "interval_widths", interval_widths)
        object.__setattr__(self, "system_lower", system_lower)
        object.__setattr__(self, "system_diagonal", system_diagonal)
        object.__setattr__(self, "system_upper", system_upper)
        object.__setattr__(self, "factorized_diagonal", factorized_diagonal)
        object.__setattr__(self, "factorized_upper_ratio", factorized_upper_ratio)

    def max_t(self) -> float:
        return float(self.knot_tenors[-1])

    def second_derivatives(self, knot_values: ArrayLike) -> NDArray[np.float64]:
        """Solve the natural-spline second derivatives for one value vector."""

        values = _require_1d_finite_array(knot_values, name="knot_values")
        try:
            assert_same_length(self.knot_tenors, values, a_name="knot_tenors", b_name="knot_values")
        except MathError as exc:
            raise _curve_input_error(exc) from exc

        second_derivatives = np.zeros(int(self.knot_tenors.size), dtype=float)
        system_size = int(self.factorized_diagonal.size)

        rhs = 6.0 * (
            (values[2:] - values[1:-1]) / self.interval_widths[1:]
            - (values[1:-1] - values[:-2]) / self.interval_widths[:-1]
        )
        if rhs.shape != (system_size,):
            raise InvalidCurveInput("natural spline rhs must align with the interior knot count.")

        forward_solution = np.empty(system_size, dtype=float)
        forward_solution[0] = float(rhs[0]) / float(self.factorized_diagonal[0])
        for index in range(1, system_size):
            forward_solution[index] = (
                float(rhs[index]) - float(self.system_lower[index - 1]) * float(forward_solution[index - 1])
            ) / float(self.factorized_diagonal[index])

        inner_second_derivatives = np.empty(system_size, dtype=float)
        inner_second_derivatives[-1] = forward_solution[-1]
        for index in range(system_size - 2, -1, -1):
            inner_second_derivatives[index] = forward_solution[index] - float(
                self.factorized_upper_ratio[index]
            ) * float(inner_second_derivatives[index + 1])

        second_derivatives[1:-1] = inner_second_derivatives
        return second_derivatives

    def evaluate(
        self,
        tenor: float,
        knot_values: ArrayLike,
        *,
        second_derivatives: NDArray[np.float64] | None = None,
    ) -> float:
        """Evaluate the spline at one tenor using the fixed-knot geometry."""

        checked_tenor = float(tenor)
        if not math.isfinite(checked_tenor):
            raise InvalidCurveInput("tenor must be finite.")

        values = _require_1d_finite_array(knot_values, name="knot_values")
        try:
            assert_same_length(self.knot_tenors, values, a_name="knot_tenors", b_name="knot_values")
        except MathError as exc:
            raise _curve_input_error(exc) from exc

        curvature = self.second_derivatives(values) if second_derivatives is None else np.asarray(
            second_derivatives,
            dtype=float,
        )
        try:
            assert_same_length(self.knot_tenors, curvature, a_name="knot_tenors", b_name="second_derivatives")
        except MathError as exc:
            raise _curve_input_error(exc) from exc

        interval_index = int(np.searchsorted(self.knot_tenors, checked_tenor, side="right") - 1)
        interval_index = int(np.clip(interval_index, 0, int(self.interval_widths.size) - 1))
        left_tenor = float(self.knot_tenors[interval_index])
        right_tenor = float(self.knot_tenors[interval_index + 1])
        left_value = float(values[interval_index])
        right_value = float(values[interval_index + 1])
        left_curvature = float(curvature[interval_index])
        right_curvature = float(curvature[interval_index + 1])
        width = float(self.interval_widths[interval_index])

        left_weight = (right_tenor - checked_tenor) / width
        right_weight = (checked_tenor - left_tenor) / width
        curvature_term = (
            ((left_weight**3 - left_weight) * left_curvature)
            + ((right_weight**3 - right_weight) * right_curvature)
        ) * (width**2) / 6.0
        return left_weight * left_value + right_weight * right_value + curvature_term


class ExponentialSplineKernel(CurveKernel):
    """Zero-rate kernel built from exponential basis functions."""

    kind: Final[CurveKernelKind] = CurveKernelKind.EXPONENTIAL_SPLINE
    __slots__ = ("_coefficients", "_decay_factors", "_max_t", "_allow_extrapolation")

    def __init__(
        self,
        *,
        coefficients: ArrayLike,
        decay_factors: ArrayLike,
        max_t: float,
        allow_extrapolation: bool = False,
    ) -> None:
        normalized_coefficients, normalized_decay_factors = _normalize_exponential_inputs(
            coefficients,
            decay_factors,
        )
        self._coefficients = normalized_coefficients
        self._decay_factors = normalized_decay_factors
        self._max_t = _require_positive(max_t, name="max_t")
        self._allow_extrapolation = bool(allow_extrapolation)

    def max_t(self) -> float:
        return self._max_t

    def rate_at(self, tenor: float) -> float:
        checked_tenor = _validate_query_t(
            tenor,
            max_t=self._max_t,
            allow_extrapolation=self._allow_extrapolation,
        )
        basis_values = np.exp(-self._decay_factors * checked_tenor)
        return float(self._coefficients[0] + np.dot(self._coefficients[1:], basis_values))


class CubicSplineKernel(CurveKernel):
    """Natural cubic spline in zero-rate space on one fixed knot grid.

    The caller supplies one fixed knot grid with at least three knots and one
    zero-rate value for each knot. The kernel inserts a zero-tenor anchor only
    as an internal helper when the first supplied knot is positive. The fitted
    parameters remain the zero rates at the supplied knots, and the
    natural-spline geometry is built once from the fixed knot grid and then
    reused for evaluation.
    """

    kind: Final[CurveKernelKind] = CurveKernelKind.CUBIC_SPLINE
    __slots__ = ("_geometry", "_zero_rates", "_second_derivatives", "_allow_extrapolation")

    def __init__(
        self,
        knot_tenors: ArrayLike,
        zero_rates: ArrayLike,
        *,
        allow_extrapolation: bool = False,
    ) -> None:
        normalized_tenors, normalized_rates = _normalize_zero_spline_inputs(knot_tenors, zero_rates)
        geometry = _NaturalCubicSplineGeometry(normalized_tenors)
        second_derivatives = geometry.second_derivatives(normalized_rates)
        self._geometry = geometry
        self._zero_rates = normalized_rates
        self._second_derivatives = second_derivatives
        self._allow_extrapolation = bool(allow_extrapolation)

    def max_t(self) -> float:
        return self._geometry.max_t()

    def rate_at(self, tenor: float) -> float:
        checked_tenor = _validate_query_t(
            tenor,
            max_t=self.max_t(),
            allow_extrapolation=self._allow_extrapolation,
        )
        return float(
            self._geometry.evaluate(
                checked_tenor,
                self._zero_rates,
                second_derivatives=self._second_derivatives,
            )
        )


__all__ = [
    "CubicSplineKernel",
    "ExponentialSplineKernel",
]
