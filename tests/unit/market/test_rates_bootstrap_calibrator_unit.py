from __future__ import annotations

from math import exp

import pytest

from fuggers_py.core.types import Currency, Date
from fuggers_py.math.solvers.types import SolverConfig
from fuggers_py.market.curves import (
    CurveSpec,
    CurveType,
    ExtrapolationPolicy,
    YieldCurve,
)
from fuggers_py.market.curves.errors import CurveConstructionError, InvalidCurveInput
from fuggers_py.market.curves.rates.calibrators import (
    BootstrapCalibrator,
    BootstrapObservation,
    BootstrapObservationKind,
    BootstrapSolverKind,
    CalibrationObjective,
    CurveCalibrator,
)
from fuggers_py.market.curves.rates.kernels import CurveKernelKind, KernelSpec
from fuggers_py.market.curves.rates.reports import CalibrationPoint, CalibrationReport


def _spec(*, extrapolation_policy: ExtrapolationPolicy = ExtrapolationPolicy.ERROR) -> CurveSpec:
    return CurveSpec(
        name="USD Nominal",
        reference_date=Date.parse("2026-04-09"),
        day_count="ACT_365_FIXED",
        currency=Currency.USD,
        type=CurveType.NOMINAL,
        extrapolation_policy=extrapolation_policy,
    )


def test_substep_d5_shared_calibrator_contract_is_exported() -> None:
    assert issubclass(BootstrapCalibrator, CurveCalibrator)
    assert CalibrationObjective.EXACT_FIT.name == "EXACT_FIT"


def test_substep_d5_observation_validation_rejects_bad_zero_anchor() -> None:
    with pytest.raises(InvalidCurveInput, match="discount factor at tenor 0 must equal 1.0"):
        BootstrapObservation(
            instrument_id="df0",
            tenor=0.0,
            value=0.99,
            kind=BootstrapObservationKind.DISCOUNT_FACTOR,
        )


def test_substep_d5_bootstrap_builds_linear_zero_kernel_and_report() -> None:
    calibrator = BootstrapCalibrator()
    kernel, report = calibrator.fit(
        [
            BootstrapObservation("5Y", 5.0, 0.04, BootstrapObservationKind.ZERO_RATE),
            BootstrapObservation("1Y", 1.0, 0.03, BootstrapObservationKind.ZERO_RATE),
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.LINEAR_ZERO),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert curve.rate_at(1.0) == pytest.approx(0.03)
    assert curve.rate_at(5.0) == pytest.approx(0.04)
    assert curve.rate_at(3.0) == pytest.approx(0.035)
    assert isinstance(report, CalibrationReport)
    assert report.converged is True
    assert report.objective == CalibrationObjective.EXACT_FIT.name
    assert report.max_abs_residual == pytest.approx(0.0)
    assert tuple(point.instrument_id for point in report.points) == ("1Y", "5Y")


def test_substep_d5_bootstrap_can_fit_discount_factor_observations_into_zero_kernel() -> None:
    calibrator = BootstrapCalibrator(
        solver_kind=BootstrapSolverKind.NEWTON,
        solver_config=SolverConfig(tolerance=1e-12, max_iterations=25),
    )
    discount_factor = exp(-0.04 * 2.0)
    kernel, report = calibrator.fit(
        [
            BootstrapObservation("2Y", 2.0, discount_factor, BootstrapObservationKind.DISCOUNT_FACTOR),
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.LINEAR_ZERO),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert curve.zero_rate_at(2.0) == pytest.approx(0.04)
    assert report.points[0].observed_kind == BootstrapObservationKind.DISCOUNT_FACTOR.name
    assert report.points[0].solver_iterations >= 0


def test_substep_d5_bootstrap_can_fit_zero_rate_observations_into_discount_kernel() -> None:
    calibrator = BootstrapCalibrator(
        solver_kind=BootstrapSolverKind.NEWTON,
        solver_config=SolverConfig(tolerance=1e-12, max_iterations=25),
    )
    kernel, report = calibrator.fit(
        [
            BootstrapObservation("3Y", 3.0, 0.05, BootstrapObservationKind.ZERO_RATE),
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.LOG_LINEAR_DISCOUNT),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert curve.zero_rate_at(3.0) == pytest.approx(0.05)
    assert curve.discount_factor_at(3.0) == pytest.approx(exp(-0.05 * 3.0))


def test_substep_d5_bootstrap_report_contains_point_rows() -> None:
    calibrator = BootstrapCalibrator()
    _, report = calibrator.fit(
        [
            BootstrapObservation("1Y", 1.0, 0.03, BootstrapObservationKind.ZERO_RATE),
            BootstrapObservation("2Y", 2.0, 0.035, BootstrapObservationKind.ZERO_RATE),
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.PIECEWISE_FLAT_FORWARD),
    )

    assert all(isinstance(point, CalibrationPoint) for point in report.points)
    assert report.points[0].residual == pytest.approx(0.0)
    assert report.points[1].residual == pytest.approx(0.0)


def test_substep_d5_bootstrap_uses_spec_extrapolation_policy_when_building_kernel() -> None:
    calibrator = BootstrapCalibrator()
    kernel, report = calibrator.fit(
        [
            BootstrapObservation("1Y", 1.0, 0.03, BootstrapObservationKind.ZERO_RATE),
            BootstrapObservation("5Y", 5.0, 0.04, BootstrapObservationKind.ZERO_RATE),
        ],
        spec=_spec(extrapolation_policy=ExtrapolationPolicy.HOLD_LAST_ZERO_RATE),
        kernel_spec=KernelSpec(kind=CurveKernelKind.LINEAR_ZERO),
    )
    curve = YieldCurve(
        spec=_spec(extrapolation_policy=ExtrapolationPolicy.HOLD_LAST_ZERO_RATE),
        kernel=kernel,
        calibration_report=report,
    )

    assert curve.discount_factor_at(6.0) > 0.0


def test_substep_d5_bootstrap_rejects_unsupported_kernel_kind() -> None:
    calibrator = BootstrapCalibrator()

    with pytest.raises(CurveConstructionError, match="does not support kernel kind"):
        calibrator.fit(
            [
                BootstrapObservation("5Y", 5.0, 0.04, BootstrapObservationKind.ZERO_RATE),
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(kind=CurveKernelKind.NELSON_SIEGEL),
        )


def test_substep_d5_bootstrap_rejects_non_increasing_observation_tenors() -> None:
    calibrator = BootstrapCalibrator()

    with pytest.raises(InvalidCurveInput, match="strictly increasing tenors"):
        calibrator.fit(
            [
                BootstrapObservation("5Y-a", 5.0, 0.04, BootstrapObservationKind.ZERO_RATE),
                BootstrapObservation("5Y-b", 5.0, 0.041, BootstrapObservationKind.ZERO_RATE),
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(kind=CurveKernelKind.LINEAR_ZERO),
        )
