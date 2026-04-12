"""Spline-based internal curve kernels.

These kernels sit beside the node kernels and the parametric kernels. They
wrap spline-style zero-rate shapes behind the shared ``CurveKernel`` contract.
"""

from __future__ import annotations

import math
from typing import Final

import numpy as np
from numpy.typing import ArrayLike, NDArray

from fuggers_py.math.errors import MathError
from fuggers_py.math.interpolation.cubic_spline import CubicSpline as NaturalCubicSpline
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
    if tenors.size < 2:
        raise InvalidCurveInput("at least two spline knots are required.")
    if np.any(tenors < 0.0):
        raise InvalidCurveInput("knot_tenors must be >= 0.")
    if float(tenors[0]) > 0.0:
        tenors = np.insert(tenors, 0, 0.0)
        rates = np.insert(rates, 0, float(rates[0]))
    return tenors, rates


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
    """Natural cubic spline through knot-based zero-rate parameters."""

    kind: Final[CurveKernelKind] = CurveKernelKind.CUBIC_SPLINE
    __slots__ = ("_tenors", "_interpolator", "_allow_extrapolation")

    def __init__(
        self,
        knot_tenors: ArrayLike,
        zero_rates: ArrayLike,
        *,
        allow_extrapolation: bool = False,
    ) -> None:
        normalized_tenors, normalized_rates = _normalize_zero_spline_inputs(knot_tenors, zero_rates)
        try:
            interpolator = NaturalCubicSpline(
                normalized_tenors,
                normalized_rates,
                allow_extrapolation=allow_extrapolation,
            )
        except MathError as exc:
            raise _curve_input_error(exc) from exc
        self._tenors = normalized_tenors
        self._interpolator = interpolator
        self._allow_extrapolation = bool(allow_extrapolation)

    def max_t(self) -> float:
        return float(self._tenors[-1])

    def rate_at(self, tenor: float) -> float:
        checked_tenor = _validate_query_t(
            tenor,
            max_t=self.max_t(),
            allow_extrapolation=self._allow_extrapolation,
        )
        try:
            return float(self._interpolator.interpolate(checked_tenor))
        except MathError as exc:
            raise _curve_input_error(exc) from exc


__all__ = [
    "CubicSplineKernel",
    "ExponentialSplineKernel",
]
