"""Discrete pillar-based curve implementation.

The curve stores sorted tenor/value pillars and exposes interpolation and
extrapolation rules over raw decimal ordinates. The economic meaning of those
ordinates is carried by
:class:`~fuggers_py.market.curves.value_type.ValueType`, not by the container.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from numpy.typing import ArrayLike, NDArray

from fuggers_py.core.types import Date
from fuggers_py.math import CubicSpline, FlatForward, LinearInterpolator, LogLinearInterpolator, MonotoneConvex

from .errors import InvalidCurveInput
from .term_structure import TermStructure
from .value_type import ValueType


class InterpolationMethod(str, Enum):
    """Interpolation families supported by :class:`DiscreteCurve`.

    The method controls how values are inferred between adjacent pillars.
    """

    LINEAR = "LINEAR"
    LOG_LINEAR = "LOG_LINEAR"
    CUBIC_SPLINE = "CUBIC_SPLINE"
    MONOTONE_CONVEX = "MONOTONE_CONVEX"
    FLAT_FORWARD = "FLAT_FORWARD"
    NELSON_SIEGEL = "NELSON_SIEGEL"
    SVENSSON = "SVENSSON"
    PIECEWISE_CONSTANT = "PIECEWISE_CONSTANT"


class ExtrapolationMethod(str, Enum):
    """Extrapolation behavior for tenors outside the pillar range."""

    NONE = "NONE"
    FLAT = "FLAT"
    LINEAR = "LINEAR"
    FLAT_FORWARD = "FLAT_FORWARD"


@dataclass(frozen=True, slots=True)
class _PiecewiseConstantInterpolator:
    _xs: NDArray[np.float64]
    _ys: NDArray[np.float64]

    def min_x(self) -> float:
        return float(self._xs[0])

    def max_x(self) -> float:
        return float(self._xs[-1])

    def interpolate(self, x: float) -> float:
        xv = float(x)
        if xv <= self.min_x():
            return float(self._ys[0])
        if xv >= self.max_x():
            return float(self._ys[-1])
        i = int(np.searchsorted(self._xs, xv, side="right") - 1)
        i = int(np.clip(i, 0, self._xs.size - 1))
        return float(self._ys[i])

    def derivative(self, x: float) -> float:
        return 0.0


def _as_1d_float_array(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise InvalidCurveInput(f"{name} must be 1D; got shape {arr.shape}.")
    if arr.size == 0:
        raise InvalidCurveInput(f"{name} must be non-empty.")
    if not np.all(np.isfinite(arr)):
        raise InvalidCurveInput(f"{name} must be finite.")
    return arr.astype(float, copy=False)


@dataclass(frozen=True, slots=True)
class DiscreteCurve(TermStructure):
    """Curve backed by sorted tenor/value pillars.

    Parameters
    ----------
    reference_date:
        Curve reference date.
    tenors:
        Pillar tenors measured in year fractions from ``reference_date``.
    values:
        Raw decimal curve ordinates associated with each tenor.
    value_type:
        Semantic description of the ordinates, such as discount factors or
        zero rates.
    interpolation_method:
        Interpolation scheme used between pillars.
    extrapolation_method:
        Behavior to use outside the pillar range.
    """

    _reference_date: Date
    _tenors: NDArray[np.float64]
    _values: NDArray[np.float64]
    _value_type: ValueType
    _interpolation_method: InterpolationMethod
    _extrapolation_method: ExtrapolationMethod
    _interpolator: object

    def __init__(
        self,
        reference_date: Date,
        tenors: ArrayLike,
        values: ArrayLike,
        *,
        value_type: ValueType,
        interpolation_method: InterpolationMethod = InterpolationMethod.LOG_LINEAR,
        extrapolation_method: ExtrapolationMethod = ExtrapolationMethod.FLAT,
    ) -> None:
        """Construct a discrete curve from tenor/value pillars.

        The curve keeps the provided ordinates as raw decimals and sorts the
        pillars by tenor before building the interpolator.
        """
        t_arr = _as_1d_float_array(tenors, name="tenors")
        v_arr = _as_1d_float_array(values, name="values")
        if t_arr.size != v_arr.size:
            raise InvalidCurveInput(f"tenors and values must have the same length; got {t_arr.size} and {v_arr.size}.")
        if t_arr.size < 2:
            raise InvalidCurveInput(f"DiscreteCurve requires at least 2 pillars; got {t_arr.size}.")
        if np.any(t_arr < 0.0):
            raise InvalidCurveInput("tenors must be non-negative.")

        order = np.argsort(t_arr)
        t_arr = t_arr[order]
        v_arr = v_arr[order]
        if not np.all(np.diff(t_arr) > 0.0):
            raise InvalidCurveInput("tenors must be strictly increasing (after sorting).")

        method = InterpolationMethod(interpolation_method)
        if method in {InterpolationMethod.FLAT_FORWARD, InterpolationMethod.MONOTONE_CONVEX}:
            mask = t_arr > 0.0
            t_arr = t_arr[mask]
            v_arr = v_arr[mask]
            if t_arr.size < 2:
                raise InvalidCurveInput(
                    f"{method.value} interpolation requires at least 2 strictly positive tenors."
                )

        if method is InterpolationMethod.CUBIC_SPLINE and t_arr.size < 3:
            raise InvalidCurveInput("CUBIC_SPLINE interpolation requires at least 3 pillars.")
        if method is InterpolationMethod.LOG_LINEAR and np.any(v_arr <= 0.0):
            raise InvalidCurveInput("LOG_LINEAR interpolation requires strictly positive values.")

        interpolator = self._create_interpolator(method, t_arr, v_arr)

        object.__setattr__(self, "_reference_date", reference_date)
        object.__setattr__(self, "_tenors", t_arr.astype(float, copy=False))
        object.__setattr__(self, "_values", v_arr.astype(float, copy=False))
        object.__setattr__(self, "_value_type", value_type)
        object.__setattr__(self, "_interpolation_method", method)
        object.__setattr__(self, "_extrapolation_method", ExtrapolationMethod(extrapolation_method))
        object.__setattr__(self, "_interpolator", interpolator)

    @staticmethod
    def _create_interpolator(
        method: InterpolationMethod, tenors: NDArray[np.float64], values: NDArray[np.float64]
    ) -> object:
        match method:
            case InterpolationMethod.LINEAR:
                return LinearInterpolator(tenors, values, allow_extrapolation=False)
            case InterpolationMethod.LOG_LINEAR:
                return LogLinearInterpolator(tenors, values, allow_extrapolation=False)
            case InterpolationMethod.CUBIC_SPLINE:
                return CubicSpline(tenors, values, allow_extrapolation=False)
            case InterpolationMethod.MONOTONE_CONVEX:
                return MonotoneConvex(tenors, values, allow_extrapolation=False)
            case InterpolationMethod.FLAT_FORWARD:
                return FlatForward(tenors, values, allow_extrapolation=False)
            case InterpolationMethod.PIECEWISE_CONSTANT:
                return _PiecewiseConstantInterpolator(tenors, values)
            case InterpolationMethod.NELSON_SIEGEL | InterpolationMethod.SVENSSON:
                raise InvalidCurveInput("Parametric models require calibration, not direct construction")

    def date(self) -> Date:
        """Return the date from which pillar tenors are measured."""
        return self._reference_date

    def interpolation_method(self) -> InterpolationMethod:
        """Return the interpolation method used between pillars."""
        return self._interpolation_method

    def extrapolation_method(self) -> ExtrapolationMethod:
        """Return the extrapolation method used outside the pillar range."""
        return self._extrapolation_method

    def tenors(self) -> NDArray[np.float64]:
        """Return a copy of the sorted pillar tenors in year fractions."""
        return self._tenors.copy()

    def values(self) -> NDArray[np.float64]:
        """Return a copy of the pillar ordinates as raw decimals."""
        return self._values.copy()

    def _extrapolate(self, t: float) -> float:
        """Extrapolate a value outside the pillar range when configured."""

        tau = float(t)
        lo = float(self._tenors[0])
        hi = float(self._tenors[-1])
        if self._extrapolation_method is ExtrapolationMethod.NONE:
            return float("nan")
        if self._extrapolation_method in {ExtrapolationMethod.FLAT, ExtrapolationMethod.FLAT_FORWARD}:
            return float(self._values[0] if tau < lo else self._values[-1])
        if self._extrapolation_method is ExtrapolationMethod.LINEAR:
            if tau < lo:
                x0 = float(self._tenors[0])
                x1 = float(self._tenors[1])
                y0 = float(self._values[0])
                y1 = float(self._values[1])
                slope = (y1 - y0) / (x1 - x0)
                return float(y0 + slope * (tau - x0))
            x0 = float(self._tenors[-2])
            x1 = float(self._tenors[-1])
            y0 = float(self._values[-2])
            y1 = float(self._values[-1])
            slope = (y1 - y0) / (x1 - x0)
            return float(y1 + slope * (tau - x1))
        return float("nan")

    def value_at_tenor(self, t: float) -> float:
        """Return the interpolated or extrapolated curve value at tenor ``t``."""
        tau = float(t)
        lo = float(self._tenors[0])
        hi = float(self._tenors[-1])
        if tau < lo or tau > hi:
            return self._extrapolate(tau)
        return float(self._interpolator.interpolate(tau))

    def derivative_at_tenor(self, t: float) -> float | None:
        """Return the tenor derivative when the interpolator provides one."""
        tau = float(t)
        lo = float(self._tenors[0])
        hi = float(self._tenors[-1])
        if tau < lo or tau > hi:
            return None
        return float(self._interpolator.derivative(tau))
