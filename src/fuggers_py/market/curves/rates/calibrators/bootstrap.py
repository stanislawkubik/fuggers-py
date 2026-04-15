"""Bootstrap-style internal calibrators for fitted rate curves."""

from __future__ import annotations

import math
from collections.abc import Sequence
from enum import Enum, auto

from fuggers_py.core.types import Compounding
from fuggers_py.math.errors import ConvergenceFailed, DivisionByZero, InvalidBracket
from fuggers_py.market.quotes import AnyInstrumentQuote
from fuggers_py.math.solvers.brent import brent
from fuggers_py.math.solvers.newton import newton_raphson, newton_raphson_numerical
from fuggers_py.math.solvers.types import SolverConfig, SolverResult

from ...conversion import ValueConverter
from ...errors import CurveConstructionError, InvalidCurveInput
from ..enums import ExtrapolationPolicy
from ..kernels import CurveKernel, CurveKernelKind, KernelSpec
from ..kernels.nodes import (
    LinearZeroKernel,
    LogLinearDiscountKernel,
    MonotoneConvexKernel,
    PiecewiseConstantZeroKernel,
    PiecewiseFlatForwardKernel,
)
from ..reports import CalibrationPoint, CalibrationReport
from ..spec import CurveSpec
from ._quotes import (
    QuoteRow,
    QuoteValueKind,
    model_quote_value,
    normalized_quote_rows,
)
from .base import CalibrationSpec, CurveCalibrator, _require_bootstrap_calibration_spec

_CONTINUOUS = Compounding.CONTINUOUS
_ZERO_NODE_KINDS = {
    CurveKernelKind.LINEAR_ZERO,
    CurveKernelKind.PIECEWISE_CONSTANT,
    CurveKernelKind.PIECEWISE_FLAT_FORWARD,
    CurveKernelKind.MONOTONE_CONVEX,
}
_DISCOUNT_NODE_KINDS = {CurveKernelKind.LOG_LINEAR_DISCOUNT}


class BootstrapSolverKind(Enum):
    """Root solver used when an observation needs cross-space conversion."""

    NEWTON = auto()
    BRENT = auto()


class _BootstrapNodeSpace(Enum):
    ZERO_RATE = auto()
    DISCOUNT_FACTOR = auto()


def _allow_extrapolation(spec: CurveSpec) -> bool:
    return spec.extrapolation_policy is not ExtrapolationPolicy.ERROR


def _node_space_for_kind(kind: CurveKernelKind) -> _BootstrapNodeSpace:
    if kind in _ZERO_NODE_KINDS:
        return _BootstrapNodeSpace.ZERO_RATE
    if kind in _DISCOUNT_NODE_KINDS:
        return _BootstrapNodeSpace.DISCOUNT_FACTOR
    raise CurveConstructionError(
        f"bootstrap calibration does not support kernel kind {kind.name}.",
    )


def _build_kernel(
    *,
    kernel_spec: KernelSpec,
    spec: CurveSpec,
    tenors: Sequence[float],
    node_values: Sequence[float],
) -> CurveKernel:
    allow_extrapolation = _allow_extrapolation(spec)
    kind = kernel_spec.kind
    if kind is CurveKernelKind.LINEAR_ZERO:
        return LinearZeroKernel(tenors, node_values, allow_extrapolation=allow_extrapolation)
    if kind is CurveKernelKind.LOG_LINEAR_DISCOUNT:
        return LogLinearDiscountKernel(tenors, node_values, allow_extrapolation=allow_extrapolation)
    if kind is CurveKernelKind.PIECEWISE_CONSTANT:
        return PiecewiseConstantZeroKernel(tenors, node_values, allow_extrapolation=allow_extrapolation)
    if kind is CurveKernelKind.PIECEWISE_FLAT_FORWARD:
        return PiecewiseFlatForwardKernel(tenors, node_values, allow_extrapolation=allow_extrapolation)
    if kind is CurveKernelKind.MONOTONE_CONVEX:
        return MonotoneConvexKernel(tenors, node_values, allow_extrapolation=allow_extrapolation)
    raise CurveConstructionError(f"bootstrap calibration does not support kernel kind {kind.name}.")


def _solve_zero_rate_from_discount_factor(
    *,
    tenor: float,
    target_discount_factor: float,
    solver_kind: BootstrapSolverKind,
    solver_config: SolverConfig,
) -> SolverResult:
    analytic_guess = ValueConverter.df_to_zero(target_discount_factor, tenor, _CONTINUOUS)

    def residual(zero_rate: float) -> float:
        return ValueConverter.zero_to_df(zero_rate, tenor, _CONTINUOUS) - target_discount_factor

    if solver_kind is BootstrapSolverKind.NEWTON:
        def derivative(zero_rate: float) -> float:
            return -tenor * math.exp(-zero_rate * tenor)

        return newton_raphson(residual, derivative, analytic_guess, config=solver_config)

    if abs(residual(analytic_guess)) <= solver_config.tolerance:
        return SolverResult(root=analytic_guess, iterations=0, residual=0.0, converged=True)

    width = 0.25
    lower = analytic_guess - width
    upper = analytic_guess + width
    for _ in range(32):
        f_lower = residual(lower)
        f_upper = residual(upper)
        if f_lower == 0.0:
            return SolverResult(root=lower, iterations=0, residual=0.0, converged=True)
        if f_upper == 0.0:
            return SolverResult(root=upper, iterations=0, residual=0.0, converged=True)
        if f_lower * f_upper < 0.0:
            return brent(residual, lower, upper, config=solver_config)
        width *= 2.0
        lower = analytic_guess - width
        upper = analytic_guess + width
    raise CurveConstructionError("could not bracket zero-rate bootstrap solve.")


def _solve_discount_factor_from_zero_rate(
    *,
    tenor: float,
    target_zero_rate: float,
    solver_kind: BootstrapSolverKind,
    solver_config: SolverConfig,
) -> SolverResult:
    analytic_guess = ValueConverter.zero_to_df(target_zero_rate, tenor, _CONTINUOUS)

    def residual(discount_factor: float) -> float:
        return ValueConverter.df_to_zero(discount_factor, tenor, _CONTINUOUS) - target_zero_rate

    if solver_kind is BootstrapSolverKind.NEWTON:
        def derivative(discount_factor: float) -> float:
            return -1.0 / (discount_factor * tenor)

        return newton_raphson(residual, derivative, analytic_guess, config=solver_config)

    if abs(residual(analytic_guess)) <= solver_config.tolerance:
        return SolverResult(root=analytic_guess, iterations=0, residual=0.0, converged=True)

    lower = max(1e-12, analytic_guess * 0.5)
    upper = max(analytic_guess * 1.5, lower * 2.0)
    for _ in range(32):
        f_lower = residual(lower)
        f_upper = residual(upper)
        if f_lower == 0.0:
            return SolverResult(root=lower, iterations=0, residual=0.0, converged=True)
        if f_upper == 0.0:
            return SolverResult(root=upper, iterations=0, residual=0.0, converged=True)
        if f_lower * f_upper < 0.0:
            return brent(residual, lower, upper, config=solver_config)
        lower = max(1e-12, lower * 0.5)
        upper = upper * 2.0
    raise CurveConstructionError("could not bracket discount-factor bootstrap solve.")


def _initial_node_guess(quote_row: QuoteRow, *, node_space: _BootstrapNodeSpace) -> float:
    if quote_row.value_kind is QuoteValueKind.BOND_YTM:
        zero_guess = ValueConverter.convert_compounding(
            quote_row.value,
            quote_row.compounding,
            _CONTINUOUS,
        )
        if node_space is _BootstrapNodeSpace.ZERO_RATE:
            return zero_guess
        return ValueConverter.zero_to_df(zero_guess, quote_row.tenor, _CONTINUOUS)
    if quote_row.value_kind in {QuoteValueKind.BOND_CLEAN_PRICE, QuoteValueKind.BOND_DIRTY_PRICE}:
        raise CurveConstructionError("BootstrapCalibrator only accepts bond rows in BOND_YTM space.")
    if node_space is _BootstrapNodeSpace.ZERO_RATE:
        if quote_row.value_kind is QuoteValueKind.DISCOUNT_FACTOR:
            return ValueConverter.df_to_zero(quote_row.value, quote_row.tenor, _CONTINUOUS)
        return quote_row.value
    if quote_row.value_kind is QuoteValueKind.DISCOUNT_FACTOR:
        return quote_row.value
    return ValueConverter.zero_to_df(quote_row.value, quote_row.tenor, _CONTINUOUS)


def _bootstrap_quote_residual(
    candidate_node_value: float,
    *,
    quote_row: QuoteRow,
    spec: CurveSpec,
    kernel_spec: KernelSpec,
    solved_tenors: Sequence[float],
    solved_values: Sequence[float],
) -> float:
    kernel = _build_kernel(
        kernel_spec=kernel_spec,
        spec=spec,
        tenors=(*solved_tenors, quote_row.tenor),
        node_values=(*solved_values, candidate_node_value),
    )
    return model_quote_value(kernel, quote_row, spec=spec) - quote_row.value


def _solve_node_from_quote(
    *,
    quote_row: QuoteRow,
    spec: CurveSpec,
    kernel_spec: KernelSpec,
    node_space: _BootstrapNodeSpace,
    solved_tenors: Sequence[float],
    solved_values: Sequence[float],
    solver_kind: BootstrapSolverKind,
    solver_config: SolverConfig,
) -> SolverResult:
    guess = _initial_node_guess(quote_row, node_space=node_space)

    def residual(candidate_node_value: float) -> float:
        return _bootstrap_quote_residual(
            candidate_node_value,
            quote_row=quote_row,
            spec=spec,
            kernel_spec=kernel_spec,
            solved_tenors=solved_tenors,
            solved_values=solved_values,
        )

    if node_space is _BootstrapNodeSpace.ZERO_RATE and solver_kind is BootstrapSolverKind.NEWTON:
        try:
            return newton_raphson_numerical(residual, guess, config=solver_config)
        except (ConvergenceFailed, DivisionByZero, InvalidCurveInput, CurveConstructionError):
            pass

    if node_space is _BootstrapNodeSpace.ZERO_RATE:
        width = max(0.25, abs(guess) * 0.25 + 0.25)
        lower = guess - width
        upper = guess + width
        for _ in range(32):
            f_lower = residual(lower)
            f_upper = residual(upper)
            if f_lower == 0.0:
                return SolverResult(root=lower, iterations=0, residual=0.0, converged=True)
            if f_upper == 0.0:
                return SolverResult(root=upper, iterations=0, residual=0.0, converged=True)
            if f_lower * f_upper < 0.0:
                return brent(residual, lower, upper, config=solver_config)
            width *= 2.0
            lower = guess - width
            upper = guess + width
        raise CurveConstructionError("could not bracket bootstrap solve for quote-driven bond fit.")

    lower = max(1e-12, guess * 0.5)
    upper = max(guess * 1.5, lower * 2.0)
    for _ in range(32):
        f_lower = residual(lower)
        f_upper = residual(upper)
        if f_lower == 0.0:
            return SolverResult(root=lower, iterations=0, residual=0.0, converged=True)
        if f_upper == 0.0:
            return SolverResult(root=upper, iterations=0, residual=0.0, converged=True)
        if f_lower * f_upper < 0.0:
            return brent(residual, lower, upper, config=solver_config)
        lower = max(1e-12, lower * 0.5)
        upper = upper * 2.0
    raise CurveConstructionError("could not bracket bootstrap solve for quote-driven bond fit.")


class BootstrapCalibrator(CurveCalibrator):
    """Sequential exact-fit calibrator for the local node-based curve families.

    The constructor owns the route-level ``CalibrationSpec``. This calibrator
    only accepts ``mode=BOOTSTRAP`` and ``objective=EXACT_FIT``. It does not
    accept regressors, it requires one strictly increasing tenor sequence, and
    it does not support ``CUBIC_SPLINE``.
    """

    def __init__(
        self,
        *,
        calibration_spec: CalibrationSpec,
        solver_kind: BootstrapSolverKind = BootstrapSolverKind.NEWTON,
        solver_config: SolverConfig = SolverConfig(),
    ) -> None:
        self._calibration_spec = _require_bootstrap_calibration_spec(calibration_spec)
        if not isinstance(solver_kind, BootstrapSolverKind):
            raise InvalidCurveInput("solver_kind must be a BootstrapSolverKind.")
        if not isinstance(solver_config, SolverConfig):
            raise InvalidCurveInput("solver_config must be a SolverConfig.")
        self._solver_kind = solver_kind
        self._solver_config = solver_config

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
        quote_rows = normalized_quote_rows(
            quotes,
            spec=spec,
            calibration_spec=calibration_spec,
            require_strictly_positive_tenor=True,
        )
        tenors = [quote_row.tenor for quote_row in quote_rows]
        for left, right in zip(tenors, tenors[1:], strict=False):
            if right <= left:
                raise InvalidCurveInput("curve-fit quotes must have strictly increasing tenors.")
        node_space = _node_space_for_kind(kernel_spec.kind)

        solved_tenors: list[float] = []
        solved_values: list[float] = []
        per_quote_iterations: list[int] = []
        total_iterations = 0

        for quote_row in quote_rows:
            if node_space is _BootstrapNodeSpace.ZERO_RATE:
                if quote_row.value_kind is QuoteValueKind.ZERO_RATE:
                    node_value = quote_row.value
                    iterations = 0
                elif quote_row.value_kind is QuoteValueKind.BOND_YTM:
                    result = _solve_node_from_quote(
                        quote_row=quote_row,
                        spec=spec,
                        kernel_spec=kernel_spec,
                        node_space=node_space,
                        solved_tenors=solved_tenors,
                        solved_values=solved_values,
                        solver_kind=self._solver_kind,
                        solver_config=self._solver_config,
                    )
                    node_value = result.root
                    iterations = result.iterations
                else:
                    result = _solve_zero_rate_from_discount_factor(
                        tenor=quote_row.tenor,
                        target_discount_factor=quote_row.value,
                        solver_kind=self._solver_kind,
                        solver_config=self._solver_config,
                    )
                    node_value = result.root
                    iterations = result.iterations
            else:
                if quote_row.value_kind is QuoteValueKind.DISCOUNT_FACTOR:
                    node_value = quote_row.value
                    iterations = 0
                elif quote_row.value_kind is QuoteValueKind.BOND_YTM:
                    result = _solve_node_from_quote(
                        quote_row=quote_row,
                        spec=spec,
                        kernel_spec=kernel_spec,
                        node_space=node_space,
                        solved_tenors=solved_tenors,
                        solved_values=solved_values,
                        solver_kind=self._solver_kind,
                        solver_config=self._solver_config,
                    )
                    node_value = result.root
                    iterations = result.iterations
                else:
                    result = _solve_discount_factor_from_zero_rate(
                        tenor=quote_row.tenor,
                        target_zero_rate=quote_row.value,
                        solver_kind=self._solver_kind,
                        solver_config=self._solver_config,
                    )
                    node_value = result.root
                    iterations = result.iterations

            solved_tenors.append(quote_row.tenor)
            solved_values.append(node_value)
            per_quote_iterations.append(iterations)
            total_iterations += iterations

        kernel = _build_kernel(
            kernel_spec=kernel_spec,
            spec=spec,
            tenors=solved_tenors,
            node_values=solved_values,
        )

        points = tuple(
            CalibrationPoint(
                instrument_id=quote_row.instrument_id,
                tenor=quote_row.tenor,
                observed_value=quote_row.value,
                fitted_value=(fitted_value := model_quote_value(kernel, quote_row, spec=spec)),
                residual=fitted_value - quote_row.value,
                observed_kind=quote_row.observed_kind,
                weight=quote_row.weight,
                solver_iterations=iterations,
            )
            for quote_row, iterations in zip(quote_rows, per_quote_iterations, strict=True)
        )
        max_abs_residual = max(abs(point.residual) for point in points) if points else 0.0

        report = CalibrationReport(
            converged=True,
            objective=calibration_spec.objective.name,
            iterations=total_iterations,
            max_abs_residual=max_abs_residual,
            points=points,
            solver=self._solver_kind.name,
        )
        return kernel, report


__all__ = [
    "BootstrapCalibrator",
    "BootstrapSolverKind",
]
