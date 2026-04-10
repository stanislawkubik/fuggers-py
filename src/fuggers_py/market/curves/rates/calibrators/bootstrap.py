"""Bootstrap-style internal calibrators for fitted rate curves."""

from __future__ import annotations

import math
from collections.abc import Sequence
from enum import Enum, auto

from fuggers_py.core.types import Compounding
from fuggers_py.math.solvers.brent import brent
from fuggers_py.math.solvers.newton import newton_raphson
from fuggers_py.math.solvers.types import SolverConfig, SolverResult

from ...conversion import ValueConverter
from ...errors import CurveConstructionError, InvalidCurveInput
from ..enums import ExtrapolationPolicy
from ..kernels import CurveKernel, CurveKernelKind, KernelSpec
from ..kernels.nodes import (
    CubicSplineZeroKernel,
    LinearZeroKernel,
    LogLinearDiscountKernel,
    MonotoneConvexKernel,
    PiecewiseConstantZeroKernel,
    PiecewiseFlatForwardKernel,
)
from ..reports import CalibrationPoint, CalibrationReport
from ..spec import CurveSpec
from .base import CalibrationObjective, CurveCalibrator
from .observations import BootstrapObservation, BootstrapObservationKind

_CONTINUOUS = Compounding.CONTINUOUS
_ZERO_NODE_KINDS = {
    CurveKernelKind.LINEAR_ZERO,
    CurveKernelKind.PIECEWISE_CONSTANT,
    CurveKernelKind.PIECEWISE_FLAT_FORWARD,
    CurveKernelKind.CUBIC_SPLINE_ZERO,
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


def _sorted_observations(observations: Sequence[BootstrapObservation]) -> tuple[BootstrapObservation, ...]:
    if not observations:
        raise InvalidCurveInput("bootstrap calibration requires at least one observation.")
    if not all(isinstance(observation, BootstrapObservation) for observation in observations):
        raise InvalidCurveInput("all observations must be BootstrapObservation objects.")
    sorted_observations = tuple(sorted(observations, key=lambda observation: observation.tenor))
    tenors = [observation.tenor for observation in sorted_observations]
    for left, right in zip(tenors, tenors[1:], strict=False):
        if right <= left:
            raise InvalidCurveInput("bootstrap observations must have strictly increasing tenors.")
    return sorted_observations


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
    if kind is CurveKernelKind.CUBIC_SPLINE_ZERO:
        return CubicSplineZeroKernel(tenors, node_values, allow_extrapolation=allow_extrapolation)
    if kind is CurveKernelKind.MONOTONE_CONVEX:
        return MonotoneConvexKernel(tenors, node_values, allow_extrapolation=allow_extrapolation)
    raise CurveConstructionError(f"bootstrap calibration does not support kernel kind {kind.name}.")


def _fitted_value(kernel: CurveKernel, observation: BootstrapObservation) -> float:
    if observation.kind is BootstrapObservationKind.DISCOUNT_FACTOR:
        return kernel.discount_factor_at(observation.tenor)
    if observation.tenor == 0.0:
        return 0.0
    return kernel.rate_at(observation.tenor)


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


class BootstrapCalibrator(CurveCalibrator):
    """Sequential bootstrap calibrator for node-based discount curves."""

    def __init__(
        self,
        *,
        objective: CalibrationObjective = CalibrationObjective.EXACT_FIT,
        solver_kind: BootstrapSolverKind = BootstrapSolverKind.NEWTON,
        solver_config: SolverConfig = SolverConfig(),
    ) -> None:
        if not isinstance(objective, CalibrationObjective):
            raise InvalidCurveInput("objective must be a CalibrationObjective.")
        if not isinstance(solver_kind, BootstrapSolverKind):
            raise InvalidCurveInput("solver_kind must be a BootstrapSolverKind.")
        if not isinstance(solver_config, SolverConfig):
            raise InvalidCurveInput("solver_config must be a SolverConfig.")
        self._objective = objective
        self._solver_kind = solver_kind
        self._solver_config = solver_config

    def fit(
        self,
        observations: Sequence[BootstrapObservation],
        *,
        spec: CurveSpec,
        kernel_spec: KernelSpec,
    ) -> tuple[CurveKernel, CalibrationReport]:
        if not isinstance(spec, CurveSpec):
            raise InvalidCurveInput("spec must be a CurveSpec.")
        if not isinstance(kernel_spec, KernelSpec):
            raise InvalidCurveInput("kernel_spec must be a KernelSpec.")
        if self._objective is not CalibrationObjective.EXACT_FIT:
            raise CurveConstructionError("BootstrapCalibrator currently supports EXACT_FIT only.")

        sorted_observations = _sorted_observations(observations)
        node_space = _node_space_for_kind(kernel_spec.kind)

        solved_tenors: list[float] = []
        solved_values: list[float] = []
        per_observation_iterations: list[int] = []
        total_iterations = 0

        for observation in sorted_observations:
            if node_space is _BootstrapNodeSpace.ZERO_RATE:
                if observation.kind is BootstrapObservationKind.ZERO_RATE:
                    node_value = observation.value
                    iterations = 0
                elif observation.tenor == 0.0:
                    node_value = 0.0
                    iterations = 0
                else:
                    result = _solve_zero_rate_from_discount_factor(
                        tenor=observation.tenor,
                        target_discount_factor=observation.value,
                        solver_kind=self._solver_kind,
                        solver_config=self._solver_config,
                    )
                    node_value = result.root
                    iterations = result.iterations
            else:
                if observation.kind is BootstrapObservationKind.DISCOUNT_FACTOR:
                    node_value = observation.value
                    iterations = 0
                elif observation.tenor == 0.0:
                    node_value = 1.0
                    iterations = 0
                else:
                    result = _solve_discount_factor_from_zero_rate(
                        tenor=observation.tenor,
                        target_zero_rate=observation.value,
                        solver_kind=self._solver_kind,
                        solver_config=self._solver_config,
                    )
                    node_value = result.root
                    iterations = result.iterations

            solved_tenors.append(observation.tenor)
            solved_values.append(node_value)
            per_observation_iterations.append(iterations)
            total_iterations += iterations

        kernel = _build_kernel(
            kernel_spec=kernel_spec,
            spec=spec,
            tenors=solved_tenors,
            node_values=solved_values,
        )

        points = tuple(
            CalibrationPoint(
                instrument_id=observation.instrument_id,
                tenor=observation.tenor,
                observed_value=observation.value,
                fitted_value=(fitted_value := _fitted_value(kernel, observation)),
                residual=fitted_value - observation.value,
                observed_kind=observation.kind.name,
                weight=observation.weight,
                solver_iterations=iterations,
            )
            for observation, iterations in zip(sorted_observations, per_observation_iterations, strict=True)
        )
        max_abs_residual = max(abs(point.residual) for point in points) if points else 0.0

        report = CalibrationReport(
            converged=True,
            objective=self._objective.name,
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
