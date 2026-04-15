from __future__ import annotations

from decimal import Decimal
from math import exp

import pytest

from fuggers_py.core.types import Currency, Date, Frequency, Price
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
    BootstrapSolverKind,
    BondFitTarget,
    CalibrationMode,
    CalibrationObjective,
    CalibrationSpec,
    CurveCalibrator,
)
from fuggers_py.market.curves.rates.kernels import CurveKernelKind, KernelSpec
from fuggers_py.market.curves.rates.reports import CalibrationPoint, CalibrationReport
from fuggers_py.market.quotes import BondQuote, RawQuote, RepoQuote, SwapQuote
from fuggers_py.products.bonds import FixedBondBuilder
from fuggers_py.reference.bonds.types import YieldCalculationRules


def _spec(*, extrapolation_policy: ExtrapolationPolicy = ExtrapolationPolicy.ERROR) -> CurveSpec:
    return CurveSpec(
        name="USD Nominal",
        reference_date=Date.parse("2026-04-09"),
        day_count="ACT_365_FIXED",
        currency=Currency.USD,
        type=CurveType.NOMINAL,
        extrapolation_policy=extrapolation_policy,
    )


def _swap_quote(tenor: str, rate: float, *, instrument_id: str | None = None) -> SwapQuote:
    return SwapQuote(
        instrument_id=instrument_id or tenor,
        tenor=tenor,
        rate=rate,
        currency=Currency.USD,
        as_of=Date.parse("2026-04-09"),
    )


def _repo_quote(term: str, rate: float, *, instrument_id: str | None = None) -> RepoQuote:
    return RepoQuote(
        instrument_id=instrument_id or term,
        term=term,
        rate=rate,
        currency=Currency.USD,
        as_of=Date.parse("2026-04-09"),
    )


def _sample_bond(
    instrument_id: str,
    *,
    maturity_years: int,
    coupon_rate: Decimal,
):
    settlement = Date.parse("2026-04-09")
    return (
        FixedBondBuilder.new()
        .with_issue_date(settlement)
        .with_maturity_date(settlement.add_years(maturity_years))
        .with_coupon_rate(coupon_rate)
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_currency(Currency.USD)
        .with_instrument_id(instrument_id)
        .with_rules(YieldCalculationRules.us_treasury())
        .build()
    )


def _clean_price_from_zero_curve(
    bond,
    *,
    settlement_date: Date,
    zero_rate_fn,
) -> Decimal:
    dirty_price = Decimal(0)
    for cash_flow in bond.cash_flows(settlement_date):
        tenor = float(settlement_date.days_between(cash_flow.date)) / 365.0
        discount_factor = Decimal(str(exp(-zero_rate_fn(tenor) * tenor)))
        dirty_price += cash_flow.factored_amount() * discount_factor
    return dirty_price - bond.accrued_interest(settlement_date)


def _bootstrap_calibration_spec(
    *,
    bond_fit_target: BondFitTarget = BondFitTarget.DIRTY_PRICE,
) -> CalibrationSpec:
    return CalibrationSpec(
        mode=CalibrationMode.BOOTSTRAP,
        objective=CalibrationObjective.EXACT_FIT,
        bond_fit_target=bond_fit_target,
    )


def test_substep_d5_shared_calibrator_contract_is_exported() -> None:
    assert issubclass(BootstrapCalibrator, CurveCalibrator)
    assert CalibrationMode.BOOTSTRAP.name == "BOOTSTRAP"
    assert CalibrationObjective.EXACT_FIT.name == "EXACT_FIT"
    assert _bootstrap_calibration_spec().bond_fit_target is BondFitTarget.DIRTY_PRICE


def test_substep_d5_bootstrap_constructor_validates_calibration_spec() -> None:
    with pytest.raises(
        ValueError,
        match="BootstrapCalibrator requires calibration_spec.mode == CalibrationMode.BOOTSTRAP",
    ):
        BootstrapCalibrator(
            calibration_spec=CalibrationSpec(
                mode=CalibrationMode.GLOBAL_FIT,
                objective=CalibrationObjective.WEIGHTED_L2,
            )
        )

    with pytest.raises(
        ValueError,
        match="BootstrapCalibrator requires calibration_spec.objective == CalibrationObjective.EXACT_FIT",
    ):
        BootstrapCalibrator(
            calibration_spec=CalibrationSpec(
                mode=CalibrationMode.BOOTSTRAP,
                objective=CalibrationObjective.WEIGHTED_L2,
            )
        )

    with pytest.raises(
        ValueError,
        match="BootstrapCalibrator does not accept calibration_spec.regressor_names",
    ):
        BootstrapCalibrator(
            calibration_spec=CalibrationSpec(
                mode=CalibrationMode.BOOTSTRAP,
                objective=CalibrationObjective.EXACT_FIT,
                regressor_names=("level",),
            )
        )


def test_substep_d5_quote_validation_rejects_bad_zero_anchor() -> None:
    with pytest.raises(InvalidCurveInput, match="requires at least one quote"):
        BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec()).fit(
            [],
            spec=_spec(),
            kernel_spec=KernelSpec(kind=CurveKernelKind.LINEAR_ZERO),
        )

    with pytest.raises(CurveConstructionError, match="RawQuote is too generic"):
        BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec()).fit(
            [
                RawQuote("RAW-1", 0.03, as_of=Date.parse("2026-04-09"), currency=Currency.USD),
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(kind=CurveKernelKind.LINEAR_ZERO),
        )


def test_substep_d5_bootstrap_builds_linear_zero_kernel_and_report() -> None:
    calibrator = BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec())
    kernel, report = calibrator.fit(
        [
            _swap_quote("5Y", 0.04),
            _swap_quote("1Y", 0.03),
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


def test_substep_d5_bootstrap_can_fit_repo_rate_quotes_into_zero_kernel() -> None:
    calibrator = BootstrapCalibrator(
        calibration_spec=_bootstrap_calibration_spec(),
        solver_kind=BootstrapSolverKind.NEWTON,
        solver_config=SolverConfig(tolerance=1e-12, max_iterations=25),
    )
    kernel, report = calibrator.fit(
        [
            _repo_quote("2Y", 0.04),
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.LINEAR_ZERO),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert curve.zero_rate_at(2.0) == pytest.approx(0.04)
    assert report.points[0].observed_kind == "REPO_RATE"
    assert report.points[0].solver_iterations == 0


def test_substep_d5_bootstrap_can_fit_swap_rate_quotes_into_discount_kernel() -> None:
    calibrator = BootstrapCalibrator(
        calibration_spec=_bootstrap_calibration_spec(),
        solver_kind=BootstrapSolverKind.NEWTON,
        solver_config=SolverConfig(tolerance=1e-12, max_iterations=25),
    )
    kernel, report = calibrator.fit(
        [
            _swap_quote("3Y", 0.05),
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.LOG_LINEAR_DISCOUNT),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert curve.zero_rate_at(3.0) == pytest.approx(0.05)
    assert curve.discount_factor_at(3.0) == pytest.approx(exp(-0.05 * 3.0))


def test_substep_d5_bootstrap_can_fit_bond_clean_price_quotes_into_zero_kernel() -> None:
    settlement = Date.parse("2026-04-09")
    bond = _sample_bond(
        "UST2Y",
        maturity_years=2,
        coupon_rate=Decimal("0.04"),
    )
    zero_rate = 0.03
    clean_price = _clean_price_from_zero_curve(
        bond,
        settlement_date=settlement,
        zero_rate_fn=lambda _: zero_rate,
    )

    kernel, report = BootstrapCalibrator(
        calibration_spec=_bootstrap_calibration_spec(bond_fit_target=BondFitTarget.CLEAN_PRICE),
        solver_kind=BootstrapSolverKind.BRENT,
        solver_config=SolverConfig(tolerance=1e-12, max_iterations=100),
    ).fit(
        [
            BondQuote(
                instrument=bond,
                clean_price=clean_price,
                as_of=settlement,
            ),
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.LINEAR_ZERO),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)
    expected_ytm = bond.yield_from_price(Price.new(clean_price, Currency.USD), settlement).ytm.value()

    assert curve.discount_factor_at(2.0) > 0.0
    assert report.points[0].observed_kind == "BOND_YTM"
    assert report.points[0].observed_value == pytest.approx(float(expected_ytm), abs=1e-10)
    assert report.points[0].fitted_value == pytest.approx(float(expected_ytm), abs=1e-10)
    assert report.points[0].residual == pytest.approx(0.0, abs=1e-10)


def test_substep_d5_bootstrap_report_contains_point_rows() -> None:
    calibrator = BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec())
    _, report = calibrator.fit(
        [
            _swap_quote("1Y", 0.03),
            _swap_quote("2Y", 0.035),
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.PIECEWISE_FLAT_FORWARD),
    )

    assert all(isinstance(point, CalibrationPoint) for point in report.points)
    assert report.points[0].residual == pytest.approx(0.0)
    assert report.points[1].residual == pytest.approx(0.0)


def test_substep_d5_bootstrap_uses_spec_extrapolation_policy_when_building_kernel() -> None:
    calibrator = BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec())
    kernel, report = calibrator.fit(
        [
            _swap_quote("1Y", 0.03),
            _swap_quote("5Y", 0.04),
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
    calibrator = BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec())

    with pytest.raises(CurveConstructionError, match="does not support kernel kind"):
        calibrator.fit(
            [
                _swap_quote("5Y", 0.04),
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(kind=CurveKernelKind.NELSON_SIEGEL),
        )

    with pytest.raises(CurveConstructionError, match="does not support kernel kind"):
        calibrator.fit(
            [
                _swap_quote("1Y", 0.03),
                _swap_quote("2Y", 0.035),
                _swap_quote("5Y", 0.04),
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(kind=CurveKernelKind.CUBIC_SPLINE),
        )


def test_substep_d5_bootstrap_rejects_non_increasing_observation_tenors() -> None:
    calibrator = BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec())

    with pytest.raises(InvalidCurveInput, match="strictly increasing tenors"):
        calibrator.fit(
            [
                _swap_quote("5Y", 0.04, instrument_id="5Y-a"),
                _swap_quote("5Y", 0.041, instrument_id="5Y-b"),
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(kind=CurveKernelKind.LINEAR_ZERO),
        )
