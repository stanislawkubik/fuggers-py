"""Shared global-fit calibrator for the imperfect-fit rate-curve kernels."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray

from fuggers_py.core.types import Compounding
from fuggers_py.market.quotes import AnyInstrumentQuote, BondQuote
from fuggers_py.math.errors import MathError
from fuggers_py.math.optimization import OptimizationConfig, OptimizationResult, gauss_newton, levenberg_marquardt
from fuggers_py.math.solvers.brent import brent
from fuggers_py.math.solvers.types import SolverConfig
from fuggers_py.math.utils import assert_finite_array, assert_strictly_increasing
from fuggers_py.reference.bonds.errors import BondError

from ...conversion import ValueConverter
from ...errors import CurveConstructionError, InvalidCurveInput
from ..enums import ExtrapolationPolicy
from ..kernels import CurveKernel, CurveKernelKind, KernelSpec
from ..kernels.parametric import NelsonSiegelKernel, SvenssonKernel
from ..kernels.spline import CubicSplineKernel, ExponentialSplineKernel
from ..reports import CalibrationReport, GlobalFitPoint, GlobalFitReport
from ..spec import CurveSpec
from ._quotes import (
    QuoteRow,
    QuoteValueKind,
    TargetSpaceCategory,
    _bond_clean_price_from_curve,
    _bond_clean_price_from_quote,
    _resolved_bond_settlement_date,
    model_quote_value,
    normalized_quote_rows,
    quote_value_target_space,
)
from .base import CalibrationSpec, CurveCalibrator, _require_global_fit_calibration_spec

_CONTINUOUS = Compounding.CONTINUOUS
_MIN_TAU = 1e-8
_PROXY_SOLVER_CONFIG = SolverConfig(tolerance=1e-12, max_iterations=100)
_GLOBAL_FIT_KINDS = {
    CurveKernelKind.CUBIC_SPLINE,
    CurveKernelKind.NELSON_SIEGEL,
    CurveKernelKind.SVENSSON,
    CurveKernelKind.EXPONENTIAL_SPLINE,
}
_ALLOWED_KERNEL_PARAMETERS_BY_KIND = {
    CurveKernelKind.CUBIC_SPLINE: frozenset({"knots", "initial_parameters"}),
    CurveKernelKind.NELSON_SIEGEL: frozenset({"initial_parameters", "max_t"}),
    CurveKernelKind.SVENSSON: frozenset({"initial_parameters", "max_t"}),
    CurveKernelKind.EXPONENTIAL_SPLINE: frozenset({"decay_factors", "initial_parameters", "initial_coefficients", "max_t"}),
}


def _curve_input_error(exc: Exception) -> InvalidCurveInput:
    return InvalidCurveInput(str(exc))


def _allow_extrapolation(spec: CurveSpec) -> bool:
    return spec.extrapolation_policy is not ExtrapolationPolicy.ERROR


def _validate_kernel_parameters(kind: CurveKernelKind, kernel_spec: KernelSpec) -> None:
    allowed = _ALLOWED_KERNEL_PARAMETERS_BY_KIND[kind]
    unexpected = set(kernel_spec.parameters) - allowed
    if unexpected:
        names = ", ".join(sorted(unexpected))
        allowed_names = ", ".join(sorted(allowed))
        raise InvalidCurveInput(
            f"{kind.name} does not accept kernel_spec parameters: {names}. "
            f"Allowed parameters are: {allowed_names}."
        )
    if kind is CurveKernelKind.EXPONENTIAL_SPLINE:
        has_initial_parameters = "initial_parameters" in kernel_spec.parameters
        has_initial_coefficients = "initial_coefficients" in kernel_spec.parameters
        if has_initial_parameters and has_initial_coefficients:
            raise InvalidCurveInput(
                "EXPONENTIAL_SPLINE accepts only one of kernel_spec.parameters['initial_parameters'] "
                "or kernel_spec.parameters['initial_coefficients']."
            )


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


def _front_end_knot_spacing(knots: NDArray[np.float64]) -> float:
    if knots.size < 2:
        raise InvalidCurveInput("knots must contain at least two values to define front-end spacing.")
    if float(knots[0]) > 0.0:
        return float(knots[0])
    return float(knots[1] - knots[0])


def _resolve_knots(kernel_spec: KernelSpec) -> NDArray[np.float64] | None:
    knots = kernel_spec.parameters.get("knots")
    if knots is None:
        return None
    try:
        resolved = assert_strictly_increasing(knots, name="knots").astype(float, copy=False)
    except MathError as exc:
        raise _curve_input_error(exc) from exc
    if resolved.ndim != 1:
        raise InvalidCurveInput("knots must be a 1D array.")
    if resolved.size < 3:
        raise InvalidCurveInput("knots must contain at least three knots.")
    if np.any(resolved < 0.0):
        raise InvalidCurveInput("knots must be >= 0.")
    if not math.isfinite(_front_end_knot_spacing(resolved)) or _front_end_knot_spacing(resolved) <= 0.0:
        raise InvalidCurveInput("front-end knot spacing must be finite and > 0.")
    return resolved


def _required_knots(kernel_spec: KernelSpec) -> NDArray[np.float64]:
    knots = _resolve_knots(kernel_spec)
    if knots is None:
        raise InvalidCurveInput("CUBIC_SPLINE requires kernel_spec.parameters['knots'].")
    return knots


def _kernel_parameter_count(
    kind: CurveKernelKind,
    *,
    decay_factors: NDArray[np.float64] | None = None,
    knots: NDArray[np.float64] | None = None,
) -> int:
    if kind is CurveKernelKind.CUBIC_SPLINE:
        if knots is None:
            raise InvalidCurveInput("CUBIC_SPLINE requires knots to resolve parameter count.")
        return int(knots.size)
    if kind is CurveKernelKind.NELSON_SIEGEL:
        return 4
    if kind is CurveKernelKind.SVENSSON:
        return 6
    if kind is CurveKernelKind.EXPONENTIAL_SPLINE:
        if decay_factors is None:
            raise InvalidCurveInput("EXPONENTIAL_SPLINE requires decay_factors to resolve parameter count.")
        return int(decay_factors.size + 1)
    raise CurveConstructionError(f"global-fit calibration does not support kernel kind {kind.name}.")


def _parameter_count(
    kind: CurveKernelKind,
    *,
    decay_factors: NDArray[np.float64] | None = None,
    knots: NDArray[np.float64] | None = None,
) -> int:
    return _kernel_parameter_count(
        kind,
        decay_factors=decay_factors,
        knots=knots,
    )


def _tau_indexes(kind: CurveKernelKind) -> tuple[int, ...]:
    if kind is CurveKernelKind.CUBIC_SPLINE:
        return ()
    if kind is CurveKernelKind.NELSON_SIEGEL:
        return (3,)
    if kind is CurveKernelKind.SVENSSON:
        return (4, 5)
    if kind is CurveKernelKind.EXPONENTIAL_SPLINE:
        return ()
    raise CurveConstructionError(f"global-fit calibration does not support kernel kind {kind.name}.")


class _FlatZeroProxyKernel(CurveKernel):
    def __init__(self, *, zero_rate: float, max_t: float) -> None:
        self._zero_rate = float(zero_rate)
        self._max_t = float(max_t)

    def max_t(self) -> float:
        return self._max_t

    def rate_at(self, tenor: float) -> float:
        return self._zero_rate


def _bond_price_zero_proxy(quote_row: QuoteRow, *, spec: CurveSpec) -> float:
    def residual(zero_rate: float) -> float:
        kernel = _FlatZeroProxyKernel(zero_rate=zero_rate, max_t=max(quote_row.tenor, 1.0))
        return model_quote_value(kernel, quote_row, spec=spec) - quote_row.value

    guess = 0.03
    lower = guess - 0.25
    upper = guess + 0.25
    for _ in range(32):
        f_lower = residual(lower)
        f_upper = residual(upper)
        if f_lower == 0.0:
            return lower
        if f_upper == 0.0:
            return upper
        if f_lower * f_upper < 0.0:
            return float(brent(residual, lower, upper, config=_PROXY_SOLVER_CONFIG).root)
        lower -= 0.25
        upper += 0.25
    raise CurveConstructionError("could not derive a flat zero-rate proxy from the bond price quote.")


def _quote_zero_proxy(quote_row: QuoteRow, *, spec: CurveSpec) -> float:
    if quote_row.value_kind in {QuoteValueKind.ZERO_RATE, QuoteValueKind.BOND_YTM}:
        return ValueConverter.convert_compounding(
            quote_row.value,
            quote_row.compounding,
            _CONTINUOUS,
        )
    if quote_row.value_kind in {QuoteValueKind.BOND_CLEAN_PRICE, QuoteValueKind.BOND_DIRTY_PRICE}:
        return _bond_price_zero_proxy(quote_row, spec=spec)
    return ValueConverter.df_to_zero(quote_row.value, quote_row.tenor, _CONTINUOUS)


def _default_initial_parameters(
    kind: CurveKernelKind,
    quote_rows: Sequence[QuoteRow],
    *,
    spec: CurveSpec,
    decay_factors: NDArray[np.float64] | None = None,
    knots: NDArray[np.float64] | None = None,
) -> NDArray[np.float64]:
    tenors = np.asarray([quote_row.tenor for quote_row in quote_rows], dtype=float)
    zero_rates = np.asarray([_quote_zero_proxy(quote_row, spec=spec) for quote_row in quote_rows], dtype=float)
    long_rate = float(zero_rates[-1])
    front_rate = float(zero_rates[0])
    slope = front_rate - long_rate
    median_tenor = float(np.median(tenors))
    max_tenor = float(tenors[-1])

    if kind is CurveKernelKind.CUBIC_SPLINE:
        if knots is None:
            raise InvalidCurveInput("CUBIC_SPLINE requires knots to build default initial parameters.")
        return np.interp(knots, tenors, zero_rates).astype(float, copy=False)
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
    raise CurveConstructionError(f"global-fit calibration does not support kernel kind {kind.name}.")


def _resolve_initial_parameters(
    kind: CurveKernelKind,
    quote_rows: Sequence[QuoteRow],
    kernel_spec: KernelSpec,
    *,
    spec: CurveSpec,
    decay_factors: NDArray[np.float64] | None = None,
    knots: NDArray[np.float64] | None = None,
) -> NDArray[np.float64]:
    if kind is CurveKernelKind.EXPONENTIAL_SPLINE:
        initial_parameters = kernel_spec.parameters.get("initial_coefficients", kernel_spec.parameters.get("initial_parameters"))
    else:
        initial_parameters = kernel_spec.parameters.get("initial_parameters")
    if initial_parameters is None:
        return _default_initial_parameters(
            kind,
            quote_rows,
            spec=spec,
            decay_factors=decay_factors,
            knots=knots,
        )

    try:
        resolved = assert_finite_array(initial_parameters, name="initial_parameters").astype(float, copy=False)
    except MathError as exc:
        raise _curve_input_error(exc) from exc
    if resolved.ndim != 1:
        raise InvalidCurveInput("initial_parameters must be a 1D array.")
    kernel_parameter_count = _kernel_parameter_count(
        kind,
        decay_factors=decay_factors,
        knots=knots,
    )
    if int(resolved.size) != kernel_parameter_count:
        raise InvalidCurveInput(
            f"initial_parameters must have length {kernel_parameter_count} for kernel kind {kind.name}."
        )
    return resolved


def _encode_parameters(
    kind: CurveKernelKind,
    raw_parameters: NDArray[np.float64],
    *,
    decay_factors: NDArray[np.float64] | None = None,
    knots: NDArray[np.float64] | None = None,
) -> NDArray[np.float64]:
    encoded = np.asarray(raw_parameters, dtype=float).copy()
    kernel_parameter_count = _kernel_parameter_count(
        kind,
        decay_factors=decay_factors,
        knots=knots,
    )
    if encoded.size != kernel_parameter_count:
        raise InvalidCurveInput("encoded parameter vector must match the kernel parameter count.")
    for index in _tau_indexes(kind):
        encoded[index] = math.log(max(abs(float(encoded[index])), _MIN_TAU))
    return encoded


def _decode_parameters(
    kind: CurveKernelKind,
    encoded_parameters: NDArray[np.float64],
    *,
    decay_factors: NDArray[np.float64] | None = None,
    knots: NDArray[np.float64] | None = None,
) -> NDArray[np.float64]:
    raw = np.asarray(encoded_parameters, dtype=float).copy()
    kernel_parameter_count = _kernel_parameter_count(
        kind,
        decay_factors=decay_factors,
        knots=knots,
    )
    if raw.size != kernel_parameter_count:
        raise InvalidCurveInput("encoded parameter vector must match the kernel parameter count.")
    for index in _tau_indexes(kind):
        raw[index] = math.exp(float(raw[index]))
    return raw


def _resolve_max_t(
    kind: CurveKernelKind,
    quote_rows: Sequence[QuoteRow],
    kernel_spec: KernelSpec,
    *,
    knots: NDArray[np.float64] | None = None,
) -> float:
    observation_max_t = max(quote_row.tenor for quote_row in quote_rows)
    if kind is CurveKernelKind.CUBIC_SPLINE:
        if knots is None:
            raise InvalidCurveInput("CUBIC_SPLINE requires knots to resolve max_t.")
        if kernel_spec.parameters.get("max_t") is not None:
            raise InvalidCurveInput("CUBIC_SPLINE uses the last knot as max_t. Do not pass max_t.")
        max_t = float(knots[-1])
        if max_t < observation_max_t:
            raise InvalidCurveInput("kernel_spec.parameters['knots'] must reach the last observation tenor.")
        return max_t
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
    knots: NDArray[np.float64] | None = None,
) -> CurveKernel:
    if kind is CurveKernelKind.CUBIC_SPLINE:
        if knots is None:
            raise InvalidCurveInput("CUBIC_SPLINE requires knots to build the kernel.")
        return CubicSplineKernel(
            knot_tenors=knots,
            zero_rates=raw_parameters,
            allow_extrapolation=allow_extrapolation,
        )
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
    raise CurveConstructionError(f"global-fit calibration does not support kernel kind {kind.name}.")


def _observed_kind_label(quote_row: QuoteRow) -> str:
    if quote_row.value_kind in {QuoteValueKind.ZERO_RATE, QuoteValueKind.BOND_YTM}:
        return f"{quote_row.observed_kind}_{quote_row.compounding.name}"
    return quote_row.observed_kind


def _require_single_target_space(quote_rows: Sequence[QuoteRow]) -> TargetSpaceCategory | None:
    target_space_kinds: dict[TargetSpaceCategory, set[QuoteValueKind]] = {}
    for quote_row in quote_rows:
        target_space = quote_value_target_space(quote_row.value_kind)
        target_space_kinds.setdefault(target_space, set()).add(quote_row.value_kind)
    if len(target_space_kinds) <= 1:
        return next(iter(target_space_kinds), None)

    details = ", ".join(
        f"{target_space.name}=[{', '.join(kind.name for kind in sorted(kinds, key=lambda value: value.name))}]"
        for target_space, kinds in sorted(target_space_kinds.items(), key=lambda item: item[0].name)
    )
    raise InvalidCurveInput(
        "GlobalFitCalibrator requires all normalized rows to share one target-space category. "
        f"Got mixed target spaces: {details}."
    )


def _curve_only_values(
    kernel: CurveKernel,
    quote_rows: Sequence[QuoteRow],
    *,
    spec: CurveSpec,
) -> NDArray[np.float64]:
    values = np.asarray(
        [model_quote_value(kernel, quote_row, spec=spec) for quote_row in quote_rows],
        dtype=float,
    )
    if values.shape != (len(quote_rows),):
        raise CurveConstructionError("curve-only modeled values must align one-to-one with quote rows.")
    if not np.all(np.isfinite(values)):
        raise CurveConstructionError("curve-only modeled values must be finite.")
    return values


def _quote_targets(quote_rows: Sequence[QuoteRow]) -> NDArray[np.float64]:
    targets = np.asarray([quote_row.value for quote_row in quote_rows], dtype=float)
    if targets.shape != (len(quote_rows),):
        raise CurveConstructionError("quote targets must align one-to-one with quote rows.")
    if not np.all(np.isfinite(targets)):
        raise CurveConstructionError("quote targets must be finite.")
    return targets


def _quote_sqrt_weights(quote_rows: Sequence[QuoteRow]) -> NDArray[np.float64]:
    weights = np.asarray([quote_row.weight for quote_row in quote_rows], dtype=float)
    if weights.shape != (len(quote_rows),):
        raise CurveConstructionError("quote weights must align one-to-one with quote rows.")
    if not np.all(np.isfinite(weights)):
        raise InvalidCurveInput("QuoteRow.weight must be finite for global-fit weighted least squares.")
    if np.any(weights < 0.0):
        raise InvalidCurveInput("QuoteRow.weight must be >= 0 for global-fit weighted least squares.")
    return np.sqrt(weights)


def _regressor_matrix(
    quote_rows: Sequence[QuoteRow],
    *,
    regressor_count: int,
) -> NDArray[np.float64] | None:
    if regressor_count < 0:
        raise InvalidCurveInput("regressor_count must be >= 0.")
    if regressor_count == 0:
        return None

    matrix = np.empty((len(quote_rows), regressor_count), dtype=float)
    for row_index, quote_row in enumerate(quote_rows):
        if len(quote_row.regressor_values) != regressor_count:
            raise InvalidCurveInput(
                "each QuoteRow.regressor_values entry must align with CalibrationSpec.regressor_names."
            )
        matrix[row_index, :] = np.asarray(quote_row.regressor_values, dtype=float)
    if matrix.shape != (len(quote_rows), regressor_count):
        raise CurveConstructionError("regressor matrix shape must be (number of rows, number of regressors).")
    if not np.all(np.isfinite(matrix)):
        raise CurveConstructionError("regressor matrix values must be finite.")
    return matrix


def _profiled_regressor_coefficients(
    regressor_matrix: NDArray[np.float64] | None,
    *,
    target_minus_curve: NDArray[np.float64],
    sqrt_weights: NDArray[np.float64],
) -> NDArray[np.float64]:
    if target_minus_curve.ndim != 1:
        raise CurveConstructionError("target_minus_curve must be a 1D array.")
    if sqrt_weights.shape != target_minus_curve.shape:
        raise CurveConstructionError("sqrt_weights must align with target_minus_curve.")
    if regressor_matrix is None:
        return np.empty(0, dtype=float)
    if regressor_matrix.ndim != 2:
        raise CurveConstructionError("regressor matrix must be a 2D array.")
    if regressor_matrix.shape[0] != target_minus_curve.size:
        raise CurveConstructionError("regressor matrix row count must match the quote row count.")

    weighted_regressor_matrix = sqrt_weights[:, np.newaxis] * regressor_matrix
    weighted_target = sqrt_weights * target_minus_curve
    coefficients, *_ = np.linalg.lstsq(weighted_regressor_matrix, weighted_target, rcond=None)
    beta = np.asarray(coefficients, dtype=float)
    if beta.shape != (regressor_matrix.shape[1],):
        raise CurveConstructionError("profiled regressor coefficient vector must match regressor_names.")
    if not np.all(np.isfinite(beta)):
        raise CurveConstructionError("profiled regressor coefficient vector must be finite.")
    return beta


def _fitted_values(
    curve_only_values: NDArray[np.float64],
    *,
    regressor_matrix: NDArray[np.float64] | None,
    regressor_coefficients: NDArray[np.float64],
) -> NDArray[np.float64]:
    if curve_only_values.ndim != 1:
        raise CurveConstructionError("curve_only_values must be a 1D array.")
    if regressor_matrix is None:
        if regressor_coefficients.size != 0:
            raise CurveConstructionError("pure curve-only fitting must not return regressor coefficients.")
        return curve_only_values.copy()
    if regressor_matrix.shape[0] != curve_only_values.size:
        raise CurveConstructionError("regressor matrix row count must match curve_only_values.")
    if regressor_coefficients.shape != (regressor_matrix.shape[1],):
        raise CurveConstructionError("regressor coefficient vector must match the regressor matrix width.")

    fitted_values = curve_only_values + regressor_matrix @ regressor_coefficients
    if fitted_values.shape != curve_only_values.shape:
        raise CurveConstructionError("fitted values must align one-to-one with quote rows.")
    if not np.all(np.isfinite(fitted_values)):
        raise CurveConstructionError("fitted values must be finite.")
    return fitted_values


@dataclass(frozen=True, slots=True)
class _ProfiledFitState:
    kernel: CurveKernel
    curve_only_values: NDArray[np.float64]
    regressor_coefficients: NDArray[np.float64]
    fitted_values: NDArray[np.float64]
    weighted_residuals: NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class _BondPriceDiagnostics:
    price_residual: float | None = None
    observed_ytm: float | None = None
    modeled_ytm: float | None = None
    ytm_residual: float | None = None
    ytm_bp_residual: float | None = None


def _profiled_fit_state(
    kernel: CurveKernel,
    quote_rows: Sequence[QuoteRow],
    *,
    spec: CurveSpec,
    regressor_matrix: NDArray[np.float64] | None,
    targets: NDArray[np.float64],
    sqrt_weights: NDArray[np.float64],
) -> _ProfiledFitState:
    curve_only_values = _curve_only_values(kernel, quote_rows, spec=spec)
    regressor_coefficients = _profiled_regressor_coefficients(
        regressor_matrix,
        target_minus_curve=targets - curve_only_values,
        sqrt_weights=sqrt_weights,
    )
    fitted_values = _fitted_values(
        curve_only_values,
        regressor_matrix=regressor_matrix,
        regressor_coefficients=regressor_coefficients,
    )
    weighted_residuals = sqrt_weights * (fitted_values - targets)
    if weighted_residuals.shape != targets.shape:
        raise CurveConstructionError("weighted residuals must align one-to-one with quote rows.")
    if not np.all(np.isfinite(weighted_residuals)):
        raise CurveConstructionError("weighted residuals must be finite.")
    return _ProfiledFitState(
        kernel=kernel,
        curve_only_values=curve_only_values,
        regressor_coefficients=regressor_coefficients,
        fitted_values=fitted_values,
        weighted_residuals=weighted_residuals,
    )


def _final_objective_value(weighted_residuals: NDArray[np.float64]) -> float:
    return 0.5 * float(np.dot(weighted_residuals, weighted_residuals))


def _bond_price_diagnostics(
    quote_row: QuoteRow,
    *,
    kernel: CurveKernel,
    spec: CurveSpec,
    fitted_value: float,
) -> _BondPriceDiagnostics:
    if quote_row.value_kind not in {QuoteValueKind.BOND_CLEAN_PRICE, QuoteValueKind.BOND_DIRTY_PRICE}:
        return _BondPriceDiagnostics()

    source_quote = quote_row.source_quote
    if not isinstance(source_quote, BondQuote):
        raise CurveConstructionError("Bond price quote rows must keep their source BondQuote.")

    price_residual = fitted_value - quote_row.value
    settlement_date = _resolved_bond_settlement_date(source_quote)
    try:
        observed_clean_price = _bond_clean_price_from_quote(source_quote, settlement_date)
        modeled_clean_price = _bond_clean_price_from_curve(source_quote, kernel=kernel, spec=spec)
        observed_ytm = float(source_quote.instrument.yield_from_price(observed_clean_price, settlement_date).ytm.value())
        modeled_ytm = float(source_quote.instrument.yield_from_price(modeled_clean_price, settlement_date).ytm.value())
    except (InvalidCurveInput, BondError):
        return _BondPriceDiagnostics(price_residual=price_residual)

    ytm_residual = modeled_ytm - observed_ytm
    return _BondPriceDiagnostics(
        price_residual=price_residual,
        observed_ytm=observed_ytm,
        modeled_ytm=modeled_ytm,
        ytm_residual=ytm_residual,
        ytm_bp_residual=ytm_residual * 10000.0,
    )


def _global_fit_point(
    quote_row: QuoteRow,
    *,
    index: int,
    final_state: _ProfiledFitState,
    spec: CurveSpec,
    solver_iterations: int,
) -> GlobalFitPoint:
    curve_only_value = float(final_state.curve_only_values[index])
    fitted_value = float(final_state.fitted_values[index])
    diagnostics = _bond_price_diagnostics(
        quote_row,
        kernel=final_state.kernel,
        spec=spec,
        fitted_value=fitted_value,
    )
    return GlobalFitPoint(
        instrument_id=quote_row.instrument_id,
        tenor=quote_row.tenor,
        observed_value=quote_row.value,
        fitted_value=fitted_value,
        residual=fitted_value - quote_row.value,
        observed_kind=_observed_kind_label(quote_row),
        weight=quote_row.weight,
        solver_iterations=solver_iterations,
        curve_only_value=curve_only_value,
        regressor_values=quote_row.regressor_values,
        regressor_contribution=fitted_value - curve_only_value,
        price_residual=diagnostics.price_residual,
        observed_ytm=diagnostics.observed_ytm,
        modeled_ytm=diagnostics.modeled_ytm,
        ytm_residual=diagnostics.ytm_residual,
        ytm_bp_residual=diagnostics.ytm_bp_residual,
    )


def _global_fit_report(
    *,
    kind: CurveKernelKind,
    quote_rows: Sequence[QuoteRow],
    final_state: _ProfiledFitState,
    optimization_result: OptimizationResult,
    calibration_spec: CalibrationSpec,
    spec: CurveSpec,
    optimizer_kind: GlobalFitOptimizerKind,
    decay_factors: NDArray[np.float64] | None = None,
    knots: NDArray[np.float64] | None = None,
) -> GlobalFitReport:
    residuals = tuple(
        _global_fit_point(
            quote_row,
            index=index,
            final_state=final_state,
            spec=spec,
            solver_iterations=optimization_result.iterations,
        )
        for index, quote_row in enumerate(quote_rows)
    )
    max_abs_residual = max((abs(point.residual) for point in residuals), default=0.0)
    raw_parameters = _decode_parameters(
        kind,
        optimization_result.parameters,
        decay_factors=decay_factors,
        knots=knots,
    )
    return GlobalFitReport(
        converged=optimization_result.converged,
        objective=calibration_spec.objective.name,
        iterations=optimization_result.iterations,
        max_abs_residual=max_abs_residual,
        points=residuals,
        solver=optimizer_kind.name,
        regressor_names=calibration_spec.regressor_names,
        regressor_coefficients=tuple(float(value) for value in final_state.regressor_coefficients),
        kernel_kind=kind.name,
        fitted_kernel_parameters=tuple(float(value) for value in raw_parameters),
        objective_value=_final_objective_value(final_state.weighted_residuals),
        residuals=residuals,
    )


class _GlobalFitResiduals:
    def __init__(
        self,
        kind: CurveKernelKind,
        quote_rows: Sequence[QuoteRow],
        *,
        spec: CurveSpec,
        max_t: float,
        allow_extrapolation: bool,
        regressor_count: int,
        decay_factors: NDArray[np.float64] | None = None,
        knots: NDArray[np.float64] | None = None,
    ) -> None:
        self._kind = kind
        self._quote_rows = tuple(quote_rows)
        self._spec = spec
        self._max_t = float(max_t)
        self._allow_extrapolation = bool(allow_extrapolation)
        self._regressor_count = int(regressor_count)
        self._decay_factors = None if decay_factors is None else np.asarray(decay_factors, dtype=float)
        self._knots = None if knots is None else np.asarray(knots, dtype=float)
        self._kernel_parameter_count = _kernel_parameter_count(
            kind,
            decay_factors=self._decay_factors,
            knots=self._knots,
        )
        if self._regressor_count < 0:
            raise InvalidCurveInput("regressor_count must be >= 0.")
        self._targets = _quote_targets(self._quote_rows)
        self._sqrt_weights = _quote_sqrt_weights(self._quote_rows)
        self._regressor_matrix = _regressor_matrix(
            self._quote_rows,
            regressor_count=self._regressor_count,
        )

    def _kernel(self, encoded_parameters: NDArray[np.float64]) -> CurveKernel:
        if np.asarray(encoded_parameters, dtype=float).shape != (self._kernel_parameter_count,):
            raise InvalidCurveInput("encoded parameter vector must match the kernel parameter count.")
        raw_parameters = _decode_parameters(
            self._kind,
            encoded_parameters,
            decay_factors=self._decay_factors,
            knots=self._knots,
        )
        return _build_kernel(
            self._kind,
            raw_parameters,
            max_t=self._max_t,
            allow_extrapolation=self._allow_extrapolation,
            decay_factors=self._decay_factors,
            knots=self._knots,
        )

    def evaluate(self, encoded_parameters: NDArray[np.float64]) -> _ProfiledFitState:
        kernel = self._kernel(encoded_parameters)
        return _profiled_fit_state(
            kernel,
            self._quote_rows,
            spec=self._spec,
            regressor_matrix=self._regressor_matrix,
            targets=self._targets,
            sqrt_weights=self._sqrt_weights,
        )

    def __call__(self, encoded_parameters: NDArray[np.float64]) -> NDArray[np.float64]:
        return self.evaluate(encoded_parameters).weighted_residuals

    def jacobian(self, encoded_parameters: NDArray[np.float64]) -> NDArray[np.float64]:
        jacobian = np.empty((len(self._quote_rows), encoded_parameters.size), dtype=float)
        for column_index in range(encoded_parameters.size):
            step = 1e-6 * max(1.0, abs(float(encoded_parameters[column_index])))
            bumped_up = encoded_parameters.copy()
            bumped_down = encoded_parameters.copy()
            bumped_up[column_index] += step
            bumped_down[column_index] -= step
            up_residuals = self(bumped_up)
            down_residuals = self(bumped_down)
            jacobian[:, column_index] = (up_residuals - down_residuals) / (2.0 * step)
        return jacobian


class GlobalFitOptimizerKind(Enum):
    """Least-squares routine used by the global-fit calibrator."""

    LEVENBERG_MARQUARDT = auto()
    GAUSS_NEWTON = auto()


class GlobalFitCalibrator(CurveCalibrator):
    """Shared imperfect-fit calibrator for the global rate-curve kernels.

    One algorithm covers all supported kernel kinds:
    ``NELSON_SIEGEL``, ``SVENSSON``, ``EXPONENTIAL_SPLINE``, and
    ``CUBIC_SPLINE``. For the cubic-spline case, the spline meaning is fixed:
    natural cubic spline, zero-rate space, fixed knot grid from
    ``KernelSpec.parameters['knots']``, and knot zero values as fitted
    parameters.

    When ``CalibrationSpec.regressor_names`` is non-empty, this calibrator
    profiles the linear regressor coefficients by weighted least squares
    inside each curve-parameter evaluation instead of adding those
    coefficients to the nonlinear optimizer state.

    Quote-level regressors come from ``BondQuote.regressors`` and are meant
    for time-varying external variables such as ``issue_size_bn``,
    ``issue_age_years``, ``deliverable_bpv``, or ``repo_specialness_bp``.
    Quote-level weights come from ``BondQuote.fit_weight`` and feed directly
    into the weighted-L2 objective. The fitted regressor coefficients are
    reported back in the same target space as the fitted quote rows, so each
    coefficient is the additive change in that target per one unit of the
    matching regressor. Duplicate tenors are allowed here; this route does not
    require the bootstrap-style strictly increasing tenor sequence.

    The constructor owns the route-level ``CalibrationSpec``. This calibrator
    only accepts ``mode=GLOBAL_FIT`` and currently only supports
    ``objective=WEIGHTED_L2``.
    """

    def __init__(
        self,
        *,
        calibration_spec: CalibrationSpec,
        optimizer_kind: GlobalFitOptimizerKind = GlobalFitOptimizerKind.LEVENBERG_MARQUARDT,
        optimization_config: OptimizationConfig = OptimizationConfig(),
    ) -> None:
        self._calibration_spec = _require_global_fit_calibration_spec(calibration_spec)
        if not isinstance(optimizer_kind, GlobalFitOptimizerKind):
            raise InvalidCurveInput("optimizer_kind must be a GlobalFitOptimizerKind.")
        if not isinstance(optimization_config, OptimizationConfig):
            raise InvalidCurveInput("optimization_config must be an OptimizationConfig.")
        self._optimizer_kind = optimizer_kind
        self._optimization_config = optimization_config

    def _optimize(
        self,
        residuals: _GlobalFitResiduals,
        initial_parameters: NDArray[np.float64],
    ) -> OptimizationResult:
        if self._optimizer_kind is GlobalFitOptimizerKind.GAUSS_NEWTON:
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
        calibration_spec = self._calibration_spec
        if kernel_spec.kind not in _GLOBAL_FIT_KINDS:
            raise CurveConstructionError(
                f"global-fit calibration does not support kernel kind {kernel_spec.kind.name}.",
            )
        _validate_kernel_parameters(kernel_spec.kind, kernel_spec)

        quote_rows = normalized_quote_rows(
            quotes,
            spec=spec,
            calibration_spec=calibration_spec,
            require_strictly_positive_tenor=True,
        )
        _require_single_target_space(quote_rows)
        decay_factors = _required_decay_factors(kernel_spec) if kernel_spec.kind is CurveKernelKind.EXPONENTIAL_SPLINE else None
        knots = _required_knots(kernel_spec) if kernel_spec.kind is CurveKernelKind.CUBIC_SPLINE else None
        regressor_count = len(calibration_spec.regressor_names)
        required_count = _parameter_count(
            kernel_spec.kind,
            decay_factors=decay_factors,
            knots=knots,
        )
        if len(quote_rows) < required_count:
            raise InvalidCurveInput(
                f"global-fit calibration of {kernel_spec.kind.name} requires at least {required_count} quotes."
            )

        raw_initial_parameters = _resolve_initial_parameters(
            kernel_spec.kind,
            quote_rows,
            kernel_spec,
            spec=spec,
            decay_factors=decay_factors,
            knots=knots,
        )
        encoded_initial_parameters = _encode_parameters(
            kernel_spec.kind,
            raw_initial_parameters,
            decay_factors=decay_factors,
            knots=knots,
        )
        max_t = _resolve_max_t(kernel_spec.kind, quote_rows, kernel_spec, knots=knots)
        residuals = _GlobalFitResiduals(
            kernel_spec.kind,
            quote_rows,
            spec=spec,
            max_t=max_t,
            allow_extrapolation=_allow_extrapolation(spec),
            regressor_count=regressor_count,
            decay_factors=decay_factors,
            knots=knots,
        )

        try:
            optimization_result = self._optimize(residuals, encoded_initial_parameters)
        except MathError as exc:
            raise CurveConstructionError(f"global-fit calibration failed: {exc}") from exc

        final_state = residuals.evaluate(optimization_result.parameters)
        kernel = final_state.kernel

        report = _global_fit_report(
            kind=kernel_spec.kind,
            quote_rows=quote_rows,
            final_state=final_state,
            optimization_result=optimization_result,
            calibration_spec=calibration_spec,
            spec=spec,
            optimizer_kind=self._optimizer_kind,
            decay_factors=decay_factors,
            knots=knots,
        )
        return kernel, report


__all__ = [
    "GlobalFitCalibrator",
    "GlobalFitOptimizerKind",
]
