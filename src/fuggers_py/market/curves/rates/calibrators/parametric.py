"""Parametric internal discounting calibrators."""

from __future__ import annotations

import math
from collections.abc import Sequence
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray

from fuggers_py.core.types import Compounding
from fuggers_py.market.quotes import AnyInstrumentQuote
from fuggers_py.math.errors import MathError
from fuggers_py.math.optimization import OptimizationConfig, OptimizationResult, gauss_newton, levenberg_marquardt
from fuggers_py.math.utils import assert_finite_array

from ...conversion import ValueConverter
from ...errors import CurveConstructionError, InvalidCurveInput
from ..enums import ExtrapolationPolicy
from ..kernels import CurveKernel, CurveKernelKind, KernelSpec
from ..kernels.parametric import NelsonSiegelKernel, SvenssonKernel
from ..kernels.spline import ExponentialSplineKernel
from ..reports import CalibrationPoint, CalibrationReport
from ..spec import CurveSpec
from ._quotes import QuoteRow, QuoteValueKind, normalized_quote_rows
from .base import CalibrationObjective, CurveCalibrator

_CONTINUOUS = Compounding.CONTINUOUS
_MIN_TAU = 1e-8
_PARAMETRIC_KINDS = {
    CurveKernelKind.NELSON_SIEGEL,
    CurveKernelKind.SVENSSON,
    CurveKernelKind.EXPONENTIAL_SPLINE,
}
_ALLOWED_KERNEL_PARAMETERS = frozenset({"initial_parameters", "max_t", "decay_factors", "initial_coefficients"})


def _curve_input_error(exc: Exception) -> InvalidCurveInput:
    return InvalidCurveInput(str(exc))


def _allow_extrapolation(spec: CurveSpec) -> bool:
    return spec.extrapolation_policy is not ExtrapolationPolicy.ERROR


def _a(x: float) -> float:
    if abs(x) < 1e-8:
        return 1.0 - x / 2.0 + x * x / 6.0 - x**3 / 24.0
    return (1.0 - math.exp(-x)) / x


def _da_dx(x: float) -> float:
    if abs(x) < 1e-8:
        return -0.5 + x / 3.0 - (x * x) / 8.0 + x**3 / 30.0
    exp_x = math.exp(-x)
    return (exp_x * (x + 1.0) - 1.0) / (x * x)


def _b(x: float) -> float:
    if abs(x) < 1e-8:
        return x / 2.0 - (x * x) / 3.0 + x**3 / 8.0 - x**4 / 30.0
    exp_x = math.exp(-x)
    return (1.0 - exp_x) / x - exp_x


def _db_dx(x: float) -> float:
    if abs(x) < 1e-8:
        return 0.5 - 2.0 * x / 3.0 + 3.0 * x * x / 8.0 - 2.0 * x**3 / 15.0
    return _da_dx(x) + math.exp(-x)


def _resolve_decay_factors(kernel_spec: KernelSpec) -> NDArray[np.float64] | None:
    decay_factors = kernel_spec.parameters.get("decay_factors")
    if decay_factors is None:
        return None
    try:
        resolved = assert_finite_array(decay_factors, name="decay_factors").astype(float, copy=False)
    except MathError as exc:
        raise _curve_input_error(exc) from exc
    if resolved.ndim != 1:
        raise InvalidCurveInput("decay_factors must be a 1D array.")
    if resolved.size == 0:
        raise InvalidCurveInput("decay_factors must be non-empty.")
    if np.any(resolved <= 0.0):
        raise InvalidCurveInput("decay_factors must be > 0.")
    return resolved


def _required_decay_factors(kernel_spec: KernelSpec) -> NDArray[np.float64]:
    decay_factors = _resolve_decay_factors(kernel_spec)
    if decay_factors is None:
        raise InvalidCurveInput("EXPONENTIAL_SPLINE requires kernel_spec.parameters['decay_factors'].")
    return decay_factors


def _parameter_count(kind: CurveKernelKind, *, decay_factors: NDArray[np.float64] | None = None) -> int:
    if kind is CurveKernelKind.NELSON_SIEGEL:
        return 4
    if kind is CurveKernelKind.SVENSSON:
        return 6
    if kind is CurveKernelKind.EXPONENTIAL_SPLINE:
        if decay_factors is None:
            raise InvalidCurveInput("EXPONENTIAL_SPLINE requires decay_factors to resolve parameter count.")
        return int(decay_factors.size + 1)
    raise CurveConstructionError(f"parametric calibration does not support kernel kind {kind.name}.")


def _tau_indexes(kind: CurveKernelKind) -> tuple[int, ...]:
    if kind is CurveKernelKind.NELSON_SIEGEL:
        return (3,)
    if kind is CurveKernelKind.SVENSSON:
        return (4, 5)
    if kind is CurveKernelKind.EXPONENTIAL_SPLINE:
        return ()
    raise CurveConstructionError(f"parametric calibration does not support kernel kind {kind.name}.")


def _quote_zero_proxy(quote_row: QuoteRow) -> float:
    if quote_row.value_kind in {QuoteValueKind.ZERO_RATE, QuoteValueKind.BOND_YTM}:
        return ValueConverter.convert_compounding(
            quote_row.value,
            quote_row.compounding,
            _CONTINUOUS,
        )
    return ValueConverter.df_to_zero(quote_row.value, quote_row.tenor, _CONTINUOUS)


def _default_initial_parameters(
    kind: CurveKernelKind,
    quote_rows: Sequence[QuoteRow],
    *,
    decay_factors: NDArray[np.float64] | None = None,
) -> NDArray[np.float64]:
    tenors = np.asarray([quote_row.tenor for quote_row in quote_rows], dtype=float)
    zero_rates = np.asarray([_quote_zero_proxy(quote_row) for quote_row in quote_rows], dtype=float)
    long_rate = float(zero_rates[-1])
    front_rate = float(zero_rates[0])
    slope = front_rate - long_rate
    median_tenor = float(np.median(tenors))
    max_tenor = float(tenors[-1])

    if kind is CurveKernelKind.NELSON_SIEGEL:
        return np.asarray(
            [
                long_rate,
                slope,
                0.0,
                max(median_tenor, 0.25),
            ],
            dtype=float,
        )
    if kind is CurveKernelKind.SVENSSON:
        tau1 = max(median_tenor * 0.5, 0.25)
        tau2 = max(max_tenor * 0.75, tau1 + 0.25)
        return np.asarray(
            [
                long_rate,
                slope,
                0.0,
                0.0,
                tau1,
                tau2,
            ],
            dtype=float,
        )
    if kind is CurveKernelKind.EXPONENTIAL_SPLINE:
        if decay_factors is None:
            raise InvalidCurveInput("EXPONENTIAL_SPLINE requires decay_factors to build default initial parameters.")
        basis = np.column_stack(
            [
                np.ones_like(tenors, dtype=float),
                *[np.exp(-float(decay_factor) * tenors) for decay_factor in decay_factors],
            ]
        )
        coefficients, *_ = np.linalg.lstsq(basis, zero_rates, rcond=None)
        return np.asarray(coefficients, dtype=float)
    raise CurveConstructionError(f"parametric calibration does not support kernel kind {kind.name}.")


def _resolve_initial_parameters(
    kind: CurveKernelKind,
    quote_rows: Sequence[QuoteRow],
    kernel_spec: KernelSpec,
    *,
    decay_factors: NDArray[np.float64] | None = None,
) -> NDArray[np.float64]:
    unexpected = set(kernel_spec.parameters) - _ALLOWED_KERNEL_PARAMETERS
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise InvalidCurveInput(f"unsupported parametric kernel_spec parameters: {names}.")

    if kind is CurveKernelKind.EXPONENTIAL_SPLINE:
        initial_parameters = kernel_spec.parameters.get("initial_coefficients", kernel_spec.parameters.get("initial_parameters"))
    else:
        initial_parameters = kernel_spec.parameters.get("initial_parameters")
    if initial_parameters is None:
        return _default_initial_parameters(kind, quote_rows, decay_factors=decay_factors)

    try:
        resolved = assert_finite_array(initial_parameters, name="initial_parameters").astype(float, copy=False)
    except MathError as exc:
        raise _curve_input_error(exc) from exc
    if resolved.ndim != 1:
        raise InvalidCurveInput("initial_parameters must be a 1D array.")
    expected_length = _parameter_count(kind, decay_factors=decay_factors)
    if int(resolved.size) != expected_length:
        raise InvalidCurveInput(
            f"initial_parameters must have length {expected_length} for kernel kind {kind.name}."
        )
    return resolved


def _encode_parameters(kind: CurveKernelKind, raw_parameters: NDArray[np.float64]) -> NDArray[np.float64]:
    encoded = np.asarray(raw_parameters, dtype=float).copy()
    for index in _tau_indexes(kind):
        encoded[index] = math.log(max(abs(float(encoded[index])), _MIN_TAU))
    return encoded


def _decode_parameters(kind: CurveKernelKind, encoded_parameters: NDArray[np.float64]) -> NDArray[np.float64]:
    raw = np.asarray(encoded_parameters, dtype=float).copy()
    for index in _tau_indexes(kind):
        raw[index] = math.exp(float(raw[index]))
    return raw


def _rate_and_jacobian(
    kind: CurveKernelKind,
    tenor: float,
    encoded_parameters: NDArray[np.float64],
    *,
    decay_factors: NDArray[np.float64] | None = None,
) -> tuple[float, NDArray[np.float64]]:
    parameters = _decode_parameters(kind, encoded_parameters)

    if kind is CurveKernelKind.NELSON_SIEGEL:
        beta0, beta1, beta2, tau = (float(value) for value in parameters)
        x = tenor / tau
        a = _a(x)
        b = _b(x)
        da = _da_dx(x)
        db = _db_dx(x)
        rate = beta0 + beta1 * a + beta2 * b
        jacobian = np.asarray(
            [
                1.0,
                a,
                b,
                -x * (beta1 * da + beta2 * db),
            ],
            dtype=float,
        )
        return float(rate), jacobian

    if kind is CurveKernelKind.SVENSSON:
        beta0, beta1, beta2, beta3, tau1, tau2 = (float(value) for value in parameters)
        x1 = tenor / tau1
        x2 = tenor / tau2
        a1 = _a(x1)
        b1 = _b(x1)
        b2 = _b(x2)
        da1 = _da_dx(x1)
        db1 = _db_dx(x1)
        db2 = _db_dx(x2)
        rate = beta0 + beta1 * a1 + beta2 * b1 + beta3 * b2
        jacobian = np.asarray(
            [
                1.0,
                a1,
                b1,
                b2,
                -x1 * (beta1 * da1 + beta2 * db1),
                -x2 * (beta3 * db2),
            ],
            dtype=float,
        )
        return float(rate), jacobian

    if kind is CurveKernelKind.EXPONENTIAL_SPLINE:
        if decay_factors is None:
            raise InvalidCurveInput("EXPONENTIAL_SPLINE requires decay_factors during evaluation.")
        basis_values = np.asarray(
            [
                1.0,
                *[math.exp(-float(decay_factor) * tenor) for decay_factor in decay_factors],
            ],
            dtype=float,
        )
        rate = float(np.dot(parameters, basis_values))
        return rate, basis_values

    raise CurveConstructionError(f"parametric calibration does not support kernel kind {kind.name}.")


def _resolve_max_t(quote_rows: Sequence[QuoteRow], kernel_spec: KernelSpec) -> float:
    observation_max_t = max(quote_row.tenor for quote_row in quote_rows)
    configured_max_t = kernel_spec.parameters.get("max_t")
    if configured_max_t is None:
        return observation_max_t
    max_t = float(configured_max_t)
    if not math.isfinite(max_t) or max_t <= 0.0:
        raise InvalidCurveInput("kernel_spec.parameters['max_t'] must be finite and > 0.")
    if max_t < observation_max_t:
        raise InvalidCurveInput("kernel_spec.parameters['max_t'] must be >= the last observation tenor.")
    return max_t


def _build_kernel(
    kind: CurveKernelKind,
    raw_parameters: NDArray[np.float64],
    *,
    max_t: float,
    allow_extrapolation: bool,
    decay_factors: NDArray[np.float64] | None = None,
) -> CurveKernel:
    if kind is CurveKernelKind.NELSON_SIEGEL:
        return NelsonSiegelKernel(
            beta0=float(raw_parameters[0]),
            beta1=float(raw_parameters[1]),
            beta2=float(raw_parameters[2]),
            tau=float(raw_parameters[3]),
            max_t=max_t,
            allow_extrapolation=allow_extrapolation,
        )
    if kind is CurveKernelKind.SVENSSON:
        return SvenssonKernel(
            beta0=float(raw_parameters[0]),
            beta1=float(raw_parameters[1]),
            beta2=float(raw_parameters[2]),
            beta3=float(raw_parameters[3]),
            tau1=float(raw_parameters[4]),
            tau2=float(raw_parameters[5]),
            max_t=max_t,
            allow_extrapolation=allow_extrapolation,
        )
    if kind is CurveKernelKind.EXPONENTIAL_SPLINE:
        if decay_factors is None:
            raise InvalidCurveInput("EXPONENTIAL_SPLINE requires decay_factors to build the kernel.")
        return ExponentialSplineKernel(
            coefficients=raw_parameters,
            decay_factors=decay_factors,
            max_t=max_t,
            allow_extrapolation=allow_extrapolation,
        )
    raise CurveConstructionError(f"parametric calibration does not support kernel kind {kind.name}.")


def _observed_kind_label(quote_row: QuoteRow) -> str:
    if quote_row.value_kind in {QuoteValueKind.ZERO_RATE, QuoteValueKind.BOND_YTM}:
        return f"{quote_row.observed_kind}_{quote_row.compounding.name}"
    return quote_row.observed_kind


def _native_fitted_value(kernel: CurveKernel, quote_row: QuoteRow, *, spec: CurveSpec) -> float:
    from ._quotes import model_quote_value

    return model_quote_value(kernel, quote_row, spec=spec)


class _ParametricResiduals:
    def __init__(
        self,
        kind: CurveKernelKind,
        quote_rows: Sequence[QuoteRow],
        *,
        spec: CurveSpec,
        max_t: float,
        allow_extrapolation: bool,
        decay_factors: NDArray[np.float64] | None = None,
    ) -> None:
        self._kind = kind
        self._quote_rows = tuple(quote_rows)
        self._spec = spec
        self._max_t = float(max_t)
        self._allow_extrapolation = bool(allow_extrapolation)
        self._decay_factors = None if decay_factors is None else np.asarray(decay_factors, dtype=float)

    def _kernel(self, encoded_parameters: NDArray[np.float64]) -> CurveKernel:
        return _build_kernel(
            self._kind,
            _decode_parameters(self._kind, encoded_parameters),
            max_t=self._max_t,
            allow_extrapolation=self._allow_extrapolation,
            decay_factors=self._decay_factors,
        )

    def _bond_row_value(self, quote_row: QuoteRow, encoded_parameters: NDArray[np.float64]) -> float:
        from ._quotes import model_quote_value

        return model_quote_value(self._kernel(encoded_parameters), quote_row, spec=self._spec)

    def __call__(self, encoded_parameters: NDArray[np.float64]) -> NDArray[np.float64]:
        residuals = np.empty(len(self._quote_rows), dtype=float)
        kernel: CurveKernel | None = None
        for index, quote_row in enumerate(self._quote_rows):
            weight_scale = math.sqrt(quote_row.weight)
            if quote_row.value_kind is QuoteValueKind.ZERO_RATE:
                zero_rate, _ = _rate_and_jacobian(
                    self._kind,
                    quote_row.tenor,
                    encoded_parameters,
                    decay_factors=self._decay_factors,
                )
                target = _quote_zero_proxy(quote_row)
                residuals[index] = weight_scale * (zero_rate - target)
                continue
            if quote_row.value_kind is QuoteValueKind.DISCOUNT_FACTOR:
                zero_rate, _ = _rate_and_jacobian(
                    self._kind,
                    quote_row.tenor,
                    encoded_parameters,
                    decay_factors=self._decay_factors,
                )
                fitted_discount_factor = ValueConverter.zero_to_df(zero_rate, quote_row.tenor, _CONTINUOUS)
                residuals[index] = weight_scale * (fitted_discount_factor - quote_row.value)
                continue
            if kernel is None:
                kernel = self._kernel(encoded_parameters)
            from ._quotes import model_quote_value

            fitted_value = model_quote_value(kernel, quote_row, spec=self._spec)
            residuals[index] = weight_scale * (fitted_value - quote_row.value)
        return residuals

    def jacobian(self, encoded_parameters: NDArray[np.float64]) -> NDArray[np.float64]:
        jacobian = np.empty((len(self._quote_rows), encoded_parameters.size), dtype=float)
        for row_index, quote_row in enumerate(self._quote_rows):
            weight_scale = math.sqrt(quote_row.weight)
            if quote_row.value_kind is QuoteValueKind.ZERO_RATE:
                zero_rate, zero_jacobian = _rate_and_jacobian(
                    self._kind,
                    quote_row.tenor,
                    encoded_parameters,
                    decay_factors=self._decay_factors,
                )
                jacobian[row_index, :] = weight_scale * zero_jacobian
                continue
            if quote_row.value_kind is QuoteValueKind.DISCOUNT_FACTOR:
                zero_rate, zero_jacobian = _rate_and_jacobian(
                    self._kind,
                    quote_row.tenor,
                    encoded_parameters,
                    decay_factors=self._decay_factors,
                )
                fitted_discount_factor = ValueConverter.zero_to_df(zero_rate, quote_row.tenor, _CONTINUOUS)
                jacobian[row_index, :] = weight_scale * (-quote_row.tenor * fitted_discount_factor) * zero_jacobian
                continue
            for column_index in range(encoded_parameters.size):
                step = 1e-6 * max(1.0, abs(float(encoded_parameters[column_index])))
                bumped_up = encoded_parameters.copy()
                bumped_down = encoded_parameters.copy()
                bumped_up[column_index] += step
                bumped_down[column_index] -= step
                up_value = self._bond_row_value(quote_row, bumped_up)
                down_value = self._bond_row_value(quote_row, bumped_down)
                jacobian[row_index, column_index] = weight_scale * (up_value - down_value) / (2.0 * step)
        return jacobian


class ParametricOptimizerKind(Enum):
    """Least-squares routine used by the parametric calibrator."""

    LEVENBERG_MARQUARDT = auto()
    GAUSS_NEWTON = auto()


class ParametricCalibrator(CurveCalibrator):
    """Least-squares calibrator for global coefficient-based curve kernels."""

    def __init__(
        self,
        *,
        objective: CalibrationObjective = CalibrationObjective.WEIGHTED_L2,
        optimizer_kind: ParametricOptimizerKind = ParametricOptimizerKind.LEVENBERG_MARQUARDT,
        optimization_config: OptimizationConfig = OptimizationConfig(),
    ) -> None:
        if not isinstance(objective, CalibrationObjective):
            raise InvalidCurveInput("objective must be a CalibrationObjective.")
        if not isinstance(optimizer_kind, ParametricOptimizerKind):
            raise InvalidCurveInput("optimizer_kind must be a ParametricOptimizerKind.")
        if not isinstance(optimization_config, OptimizationConfig):
            raise InvalidCurveInput("optimization_config must be an OptimizationConfig.")
        self._objective = objective
        self._optimizer_kind = optimizer_kind
        self._optimization_config = optimization_config

    def _optimize(
        self,
        residuals: _ParametricResiduals,
        initial_parameters: NDArray[np.float64],
    ) -> OptimizationResult:
        if self._optimizer_kind is ParametricOptimizerKind.GAUSS_NEWTON:
            return gauss_newton(residuals, initial_parameters, config=self._optimization_config)
        return levenberg_marquardt(residuals, initial_parameters, config=self._optimization_config)

    def fit(
        self,
        quotes: Sequence[AnyInstrumentQuote],
        *,
        spec: CurveSpec,
        kernel_spec: KernelSpec,
    ) -> tuple[CurveKernel, CalibrationReport]:
        if not isinstance(spec, CurveSpec):
            raise InvalidCurveInput("spec must be a CurveSpec.")
        if not isinstance(kernel_spec, KernelSpec):
            raise InvalidCurveInput("kernel_spec must be a KernelSpec.")
        if kernel_spec.kind not in _PARAMETRIC_KINDS:
            raise CurveConstructionError(
                f"parametric calibration does not support kernel kind {kernel_spec.kind.name}.",
            )

        quote_rows = normalized_quote_rows(
            quotes,
            spec=spec,
            require_strictly_positive_tenor=True,
        )
        decay_factors = _required_decay_factors(kernel_spec) if kernel_spec.kind is CurveKernelKind.EXPONENTIAL_SPLINE else None
        required_count = _parameter_count(kernel_spec.kind, decay_factors=decay_factors)
        if len(quote_rows) < required_count:
            raise InvalidCurveInput(
                f"parametric calibration of {kernel_spec.kind.name} requires at least {required_count} quotes."
            )

        raw_initial_parameters = _resolve_initial_parameters(
            kernel_spec.kind,
            quote_rows,
            kernel_spec,
            decay_factors=decay_factors,
        )
        encoded_initial_parameters = _encode_parameters(kernel_spec.kind, raw_initial_parameters)
        max_t = _resolve_max_t(quote_rows, kernel_spec)
        residuals = _ParametricResiduals(
            kernel_spec.kind,
            quote_rows,
            spec=spec,
            max_t=max_t,
            allow_extrapolation=_allow_extrapolation(spec),
            decay_factors=decay_factors,
        )

        try:
            optimization_result = self._optimize(residuals, encoded_initial_parameters)
        except MathError as exc:
            raise CurveConstructionError(f"parametric calibration failed: {exc}") from exc

        raw_parameters = _decode_parameters(kernel_spec.kind, optimization_result.parameters)
        kernel = _build_kernel(
            kernel_spec.kind,
            raw_parameters,
            max_t=max_t,
            allow_extrapolation=_allow_extrapolation(spec),
            decay_factors=decay_factors,
        )

        points = tuple(
            CalibrationPoint(
                instrument_id=quote_row.instrument_id,
                tenor=quote_row.tenor,
                observed_value=quote_row.value,
                fitted_value=(fitted_value := _native_fitted_value(kernel, quote_row, spec=spec)),
                residual=fitted_value - quote_row.value,
                observed_kind=_observed_kind_label(quote_row),
                weight=quote_row.weight,
                solver_iterations=optimization_result.iterations,
            )
            for quote_row in quote_rows
        )
        max_abs_residual = max((abs(point.residual) for point in points), default=0.0)
        converged = optimization_result.converged
        if self._objective is CalibrationObjective.EXACT_FIT and max_abs_residual > self._optimization_config.tolerance:
            converged = False

        report = CalibrationReport(
            converged=converged,
            objective=self._objective.name,
            iterations=optimization_result.iterations,
            max_abs_residual=max_abs_residual,
            points=points,
            solver=self._optimizer_kind.name,
        )
        return kernel, report


__all__ = [
    "ParametricCalibrator",
    "ParametricOptimizerKind",
]
