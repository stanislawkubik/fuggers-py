"""Concrete node-based curve kernels.

These kernels are the first real internal curve representations in the new
rates ontology. They take node inputs such as zero rates or discount factors
and turn them into fitted rate curves that can sit behind ``YieldCurve``.
"""

from __future__ import annotations

from typing import Final

import numpy as np
from numpy.typing import ArrayLike, NDArray

from fuggers_py.core.types import Compounding
from fuggers_py.math.errors import MathError
from fuggers_py.math.interpolation.cubic_spline import CubicSpline
from fuggers_py.math.interpolation.flat_forward import FlatForward
from fuggers_py.math.interpolation.linear import LinearInterpolator
from fuggers_py.math.interpolation.log_linear import LogLinearInterpolator
from fuggers_py.math.interpolation.monotone_convex import MonotoneConvex
from fuggers_py.math.utils import (
    assert_all_positive,
    assert_finite,
    assert_finite_array,
    assert_same_length,
    assert_strictly_increasing,
    bisect_segment,
)

from ...conversion import ValueConverter
from ...errors import InvalidCurveInput, TenorOutOfBounds
from .base import CurveKernel, CurveKernelKind

_CONTINUOUS: Final = Compounding.CONTINUOUS
_ZERO_TOLERANCE: Final = 1e-12


def _curve_input_error(exc: Exception) -> InvalidCurveInput:
    return InvalidCurveInput(str(exc))


def _validate_query_t(tenor: float, *, max_t: float, allow_extrapolation: bool) -> float:
    try:
        checked_tenor = assert_finite(tenor, name="tenor")
    except MathError as exc:
        raise _curve_input_error(exc) from exc
    if checked_tenor < 0.0:
        raise InvalidCurveInput("tenor must be >= 0.")
    if checked_tenor > max_t and not allow_extrapolation:
        raise TenorOutOfBounds(t=checked_tenor, min=0.0, max=max_t)
    return checked_tenor


def _normalize_zero_rate_nodes(tenors: ArrayLike, zero_rates: ArrayLike) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    try:
        t = assert_strictly_increasing(tenors, name="tenors")
        z = assert_finite_array(zero_rates, name="zero_rates").astype(float, copy=False)
        assert_same_length(t, z, a_name="tenors", b_name="zero_rates")
    except MathError as exc:
        raise _curve_input_error(exc) from exc
    if np.any(t < 0.0):
        raise InvalidCurveInput("tenors must be >= 0.")
    if float(t[0]) > 0.0:
        t = np.insert(t, 0, 0.0)
        z = np.insert(z, 0, float(z[0]))
    return t, z


def _normalize_positive_zero_rate_nodes(
    tenors: ArrayLike,
    zero_rates: ArrayLike,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    t, z = _normalize_zero_rate_nodes(tenors, zero_rates)
    if float(t[0]) == 0.0:
        t = t[1:]
        z = z[1:]
    if t.size < 2:
        raise InvalidCurveInput("at least two positive tenor nodes are required.")
    if np.any(t <= 0.0):
        raise InvalidCurveInput("tenor nodes must be strictly positive.")
    return t, z


def _normalize_discount_factor_nodes(
    tenors: ArrayLike,
    discount_factors: ArrayLike,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    try:
        t = assert_strictly_increasing(tenors, name="tenors")
        df = assert_all_positive(discount_factors, name="discount_factors")
        assert_same_length(t, df, a_name="tenors", b_name="discount_factors")
    except MathError as exc:
        raise _curve_input_error(exc) from exc
    if np.any(t < 0.0):
        raise InvalidCurveInput("tenors must be >= 0.")
    if float(t[0]) == 0.0:
        if abs(float(df[0]) - 1.0) > _ZERO_TOLERANCE:
            raise InvalidCurveInput("discount factor at tenor 0 must equal 1.0.")
        return t, df
    return np.insert(t, 0, 0.0), np.insert(df, 0, 1.0)


class LinearZeroKernel(CurveKernel):
    """Curve kernel built from linear interpolation of zero-rate nodes."""

    kind: Final[CurveKernelKind] = CurveKernelKind.LINEAR_ZERO
    __slots__ = ("_tenors", "_interpolator", "_allow_extrapolation")

    def __init__(self, tenors: ArrayLike, zero_rates: ArrayLike, *, allow_extrapolation: bool = False) -> None:
        normalized_tenors, normalized_rates = _normalize_zero_rate_nodes(tenors, zero_rates)
        try:
            interpolator = LinearInterpolator(
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
        checked_tenor = _validate_query_t(tenor, max_t=self.max_t(), allow_extrapolation=self._allow_extrapolation)
        try:
            return float(self._interpolator.interpolate(checked_tenor))
        except MathError as exc:
            raise _curve_input_error(exc) from exc


class LogLinearDiscountKernel(CurveKernel):
    """Curve kernel built from log-linear interpolation of discount factors."""

    kind: Final[CurveKernelKind] = CurveKernelKind.LOG_LINEAR_DISCOUNT
    __slots__ = ("_tenors", "_interpolator", "_allow_extrapolation")

    def __init__(
        self,
        tenors: ArrayLike,
        discount_factors: ArrayLike,
        *,
        allow_extrapolation: bool = False,
    ) -> None:
        normalized_tenors, normalized_discount_factors = _normalize_discount_factor_nodes(
            tenors,
            discount_factors,
        )
        try:
            interpolator = LogLinearInterpolator(
                normalized_tenors,
                normalized_discount_factors,
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
        checked_tenor = _validate_query_t(tenor, max_t=self.max_t(), allow_extrapolation=self._allow_extrapolation)
        if checked_tenor == 0.0:
            return self.rate_at(_ZERO_TOLERANCE)
        discount_factor = self.discount_factor_at(checked_tenor)
        return ValueConverter.df_to_zero(discount_factor, checked_tenor, _CONTINUOUS)

    def discount_factor_at(self, tenor: float) -> float:
        checked_tenor = _validate_query_t(tenor, max_t=self.max_t(), allow_extrapolation=self._allow_extrapolation)
        if checked_tenor == 0.0:
            return 1.0
        try:
            return float(self._interpolator.interpolate(checked_tenor))
        except MathError as exc:
            raise _curve_input_error(exc) from exc


class PiecewiseConstantZeroKernel(CurveKernel):
    """Curve kernel with left-constant zero rates between tenor knots."""

    kind: Final[CurveKernelKind] = CurveKernelKind.PIECEWISE_CONSTANT
    __slots__ = ("_tenors", "_zero_rates", "_allow_extrapolation")

    def __init__(self, tenors: ArrayLike, zero_rates: ArrayLike, *, allow_extrapolation: bool = False) -> None:
        normalized_tenors, normalized_rates = _normalize_zero_rate_nodes(tenors, zero_rates)
        self._tenors = normalized_tenors
        self._zero_rates = normalized_rates
        self._allow_extrapolation = bool(allow_extrapolation)

    def max_t(self) -> float:
        return float(self._tenors[-1])

    def rate_at(self, tenor: float) -> float:
        checked_tenor = _validate_query_t(tenor, max_t=self.max_t(), allow_extrapolation=self._allow_extrapolation)
        if checked_tenor > float(self._tenors[-1]):
            return float(self._zero_rates[-1])
        index = bisect_segment(self._tenors, checked_tenor)
        return float(self._zero_rates[index])


class PiecewiseFlatForwardKernel(CurveKernel):
    """Curve kernel with piecewise-constant instantaneous forward rates."""

    kind: Final[CurveKernelKind] = CurveKernelKind.PIECEWISE_FLAT_FORWARD
    __slots__ = ("_tenors", "_zero_rates", "_interpolator", "_allow_extrapolation")

    def __init__(self, tenors: ArrayLike, zero_rates: ArrayLike, *, allow_extrapolation: bool = False) -> None:
        positive_tenors, normalized_rates = _normalize_positive_zero_rate_nodes(tenors, zero_rates)
        try:
            interpolator = FlatForward(
                positive_tenors,
                normalized_rates,
                allow_extrapolation=allow_extrapolation,
            )
        except MathError as exc:
            raise _curve_input_error(exc) from exc
        self._tenors = positive_tenors
        self._zero_rates = normalized_rates
        self._interpolator = interpolator
        self._allow_extrapolation = bool(allow_extrapolation)

    def max_t(self) -> float:
        return float(self._tenors[-1])

    def rate_at(self, tenor: float) -> float:
        checked_tenor = _validate_query_t(tenor, max_t=self.max_t(), allow_extrapolation=self._allow_extrapolation)
        if checked_tenor == 0.0:
            return float(self._zero_rates[0])
        try:
            return float(self._interpolator.interpolate(checked_tenor))
        except MathError as exc:
            raise _curve_input_error(exc) from exc


class CubicSplineZeroKernel(CurveKernel):
    """Curve kernel with a natural cubic spline through zero-rate nodes."""

    kind: Final[CurveKernelKind] = CurveKernelKind.CUBIC_SPLINE_ZERO
    __slots__ = ("_tenors", "_interpolator", "_allow_extrapolation")

    def __init__(self, tenors: ArrayLike, zero_rates: ArrayLike, *, allow_extrapolation: bool = False) -> None:
        normalized_tenors, normalized_rates = _normalize_zero_rate_nodes(tenors, zero_rates)
        try:
            interpolator = CubicSpline(
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
        checked_tenor = _validate_query_t(tenor, max_t=self.max_t(), allow_extrapolation=self._allow_extrapolation)
        try:
            return float(self._interpolator.interpolate(checked_tenor))
        except MathError as exc:
            raise _curve_input_error(exc) from exc


class MonotoneConvexKernel(CurveKernel):
    """Curve kernel with a monotone-convex zero-rate shape."""

    kind: Final[CurveKernelKind] = CurveKernelKind.MONOTONE_CONVEX
    __slots__ = ("_tenors", "_zero_rates", "_interpolator", "_allow_extrapolation")

    def __init__(self, tenors: ArrayLike, zero_rates: ArrayLike, *, allow_extrapolation: bool = False) -> None:
        positive_tenors, normalized_rates = _normalize_positive_zero_rate_nodes(tenors, zero_rates)
        try:
            interpolator = MonotoneConvex(
                positive_tenors,
                normalized_rates,
                allow_extrapolation=allow_extrapolation,
            )
        except MathError as exc:
            raise _curve_input_error(exc) from exc
        self._tenors = positive_tenors
        self._zero_rates = normalized_rates
        self._interpolator = interpolator
        self._allow_extrapolation = bool(allow_extrapolation)

    def max_t(self) -> float:
        return float(self._tenors[-1])

    def rate_at(self, tenor: float) -> float:
        checked_tenor = _validate_query_t(tenor, max_t=self.max_t(), allow_extrapolation=self._allow_extrapolation)
        if checked_tenor == 0.0:
            return float(self._zero_rates[0])
        try:
            return float(self._interpolator.interpolate(checked_tenor))
        except MathError as exc:
            raise _curve_input_error(exc) from exc


__all__ = [
    "CubicSplineZeroKernel",
    "LinearZeroKernel",
    "LogLinearDiscountKernel",
    "MonotoneConvexKernel",
    "PiecewiseConstantZeroKernel",
    "PiecewiseFlatForwardKernel",
]
