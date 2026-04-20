"""Parametric internal discounting kernels.

These kernels wrap low-dimensional zero-rate families behind the shared
``CurveKernel`` contract. They sit at the same internal layer as the node
kernels in ``nodes.py``: they define the fitted rate curve shape, while the
public ``YieldCurve`` stays unchanged.
"""

from __future__ import annotations

import math
from typing import Final

from fuggers_py._math.errors import InvalidInput
from fuggers_py._math.interpolation.parametric import NelsonSiegel, Svensson

from ..errors import InvalidCurveInput, TenorOutOfBounds
from .base import CurveKernel, CurveKernelKind


def _require_finite(value: float, *, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidCurveInput(f"{name} must be finite.")
    return numeric


def _require_positive(value: float, *, name: str) -> float:
    numeric = _require_finite(value, name=name)
    if numeric <= 0.0:
        raise InvalidCurveInput(f"{name} must be > 0.")
    return numeric


def _require_non_negative(value: float, *, name: str) -> float:
    numeric = _require_finite(value, name=name)
    if numeric < 0.0:
        raise InvalidCurveInput(f"{name} must be >= 0.")
    return numeric


def _validate_query_t(tenor: float, *, max_t: float, allow_extrapolation: bool) -> float:
    checked_tenor = _require_non_negative(tenor, name="tenor")
    if checked_tenor > max_t and not allow_extrapolation:
        raise TenorOutOfBounds(t=checked_tenor, min=0.0, max=max_t)
    return checked_tenor


class NelsonSiegelKernel(CurveKernel):
    """Nelson-Siegel zero-rate kernel on a finite tenor domain."""

    kind: Final[CurveKernelKind] = CurveKernelKind.NELSON_SIEGEL
    __slots__ = ("_model", "_max_t", "_allow_extrapolation")

    def __init__(
        self,
        *,
        beta0: float,
        beta1: float,
        beta2: float,
        tau: float,
        max_t: float,
        allow_extrapolation: bool = False,
    ) -> None:
        self._model = NelsonSiegel.new(
            beta0=_require_finite(beta0, name="beta0"),
            beta1=_require_finite(beta1, name="beta1"),
            beta2=_require_finite(beta2, name="beta2"),
            tau=_require_positive(tau, name="tau"),
        )
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
        try:
            return float(self._model.interpolate(checked_tenor))
        except InvalidInput as exc:
            raise InvalidCurveInput(str(exc)) from exc


class SvenssonKernel(CurveKernel):
    """Svensson zero-rate kernel on a finite tenor domain."""

    kind: Final[CurveKernelKind] = CurveKernelKind.SVENSSON
    __slots__ = ("_model", "_max_t", "_allow_extrapolation")

    def __init__(
        self,
        *,
        beta0: float,
        beta1: float,
        beta2: float,
        beta3: float,
        tau1: float,
        tau2: float,
        max_t: float,
        allow_extrapolation: bool = False,
    ) -> None:
        self._model = Svensson.new(
            beta0=_require_finite(beta0, name="beta0"),
            beta1=_require_finite(beta1, name="beta1"),
            beta2=_require_finite(beta2, name="beta2"),
            beta3=_require_finite(beta3, name="beta3"),
            tau1=_require_positive(tau1, name="tau1"),
            tau2=_require_positive(tau2, name="tau2"),
        )
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
        try:
            return float(self._model.interpolate(checked_tenor))
        except InvalidInput as exc:
            raise InvalidCurveInput(str(exc)) from exc


__all__ = [
    "NelsonSiegelKernel",
    "SvenssonKernel",
]
