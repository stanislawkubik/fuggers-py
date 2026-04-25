from __future__ import annotations

from decimal import Decimal
from math import exp

import pytest

from fuggers_py._core.types import Currency, Date, Frequency, Price
from fuggers_py._math.solvers.types import SolverConfig
from fuggers_py.curves import CurveSpec, YieldCurve
from fuggers_py.curves.errors import CurveConstructionError, CurvesError, InvalidCurveInput
from fuggers_py.curves.calibrators import CalibrationSpec
from fuggers_py.curves.calibrators.base import CurveCalibrator
from fuggers_py.curves.calibrators.bootstrap import BootstrapCalibrator, BootstrapSolverKind
from fuggers_py.curves.kernels import KernelSpec
from fuggers_py.curves.reports import CalibrationPoint, CalibrationReport
from fuggers_py._runtime.quotes import BondQuote, RawQuote, RepoQuote, SwapQuote
from fuggers_py.bonds import FixedBondBuilder
from fuggers_py._core import YieldCalculationRules


def _spec(*, extrapolation_policy: str = "error") -> CurveSpec:
    return CurveSpec(
        name="USD Nominal",
        reference_date=Date.parse("2026-04-09"),
        day_count="ACT_365_FIXED",
        currency=Currency.USD,
        type="nominal",
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
    currency: Currency = Currency.USD,
):
    settlement = Date.parse("2026-04-09")
    return (
        FixedBondBuilder.new()
        .with_issue_date(settlement)
        .with_maturity_date(settlement.add_years(maturity_years))
        .with_coupon_rate(coupon_rate)
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_currency(currency)
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
    bond_target: str = "dirty_price",
) -> CalibrationSpec:
    return CalibrationSpec(
        method="bootstrap",
        objective="exact_fit",
        bond_target=bond_target,
    )


def test_substep_d5_shared_calibrator_contract_is_exported() -> None:
    assert issubclass(BootstrapCalibrator, CurveCalibrator)
    assert _bootstrap_calibration_spec().method == "bootstrap"
    assert _bootstrap_calibration_spec().objective == "exact_fit"
    assert _bootstrap_calibration_spec().bond_target == "dirty_price"


def test_substep_d5_invalid_calibration_spec_raises_curve_error_subclass() -> None:
    with pytest.raises(CurvesError) as exc_info:
        CalibrationSpec(
            method=object(),  # type: ignore[arg-type]
            objective="exact_fit",
        )

    assert isinstance(exc_info.value, InvalidCurveInput)


def test_substep_d5_bootstrap_constructor_validates_calibration_spec() -> None:
    with pytest.raises(
        InvalidCurveInput,
        match="BootstrapCalibrator requires calibration_spec.method == 'bootstrap'",
    ):
        BootstrapCalibrator(
            calibration_spec=CalibrationSpec(
                method="global_fit",
                objective="weighted_l2",
            )
        )

    with pytest.raises(
        InvalidCurveInput,
        match="CalibrationSpec.method='bootstrap' requires objective='exact_fit'",
    ):
        BootstrapCalibrator(
            calibration_spec=CalibrationSpec(
                method="bootstrap",
                objective="weighted_l2",
            )
        )

    with pytest.raises(
        InvalidCurveInput,
        match="BootstrapCalibrator does not accept calibration_spec.regressors",
    ):
        BootstrapCalibrator(
            calibration_spec=CalibrationSpec(
                method="bootstrap",
                objective="exact_fit",
                regressors=("level",),
            )
        )


def test_substep_d5_quote_validation_rejects_bad_zero_anchor() -> None:
    with pytest.raises(InvalidCurveInput, match="requires at least one quote"):
        BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec()).fit(
            [],
            spec=_spec(),
            kernel_spec=KernelSpec(kind="linear_zero"),
        )

    with pytest.raises(CurveConstructionError, match="RawQuote is too generic"):
        BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec()).fit(
            [
                RawQuote("RAW-1", 0.03, as_of=Date.parse("2026-04-09"), currency=Currency.USD),
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(kind="linear_zero"),
        )


@pytest.mark.parametrize(
    ("quote", "match"),
    [
        (
            SwapQuote("SWAP-1Y", rate=0.03, tenor="1Y", currency=Currency.USD, as_of=Date.parse("2026-04-10")),
            r"SwapQuote\.as_of must equal CurveSpec\.reference_date",
        ),
        (
            SwapQuote("SWAP-1Y", rate=0.03, tenor="1Y", currency=Currency.USD),
            r"SwapQuote\.as_of is required",
        ),
        (
            SwapQuote("SWAP-1Y", rate=0.03, tenor="1Y", currency=Currency.EUR, as_of=Date.parse("2026-04-09")),
            r"SwapQuote\.currency must equal CurveSpec\.currency",
        ),
        (
            RepoQuote("REPO-1Y", rate=0.03, term="1Y", currency=Currency.USD, as_of=Date.parse("2026-04-10")),
            r"RepoQuote\.as_of must equal CurveSpec\.reference_date",
        ),
        (
            RepoQuote("REPO-1Y", rate=0.03, term="1Y", currency=Currency.USD),
            r"RepoQuote\.as_of is required",
        ),
        (
            RepoQuote("REPO-1Y", rate=0.03, term="1Y", currency=Currency.EUR, as_of=Date.parse("2026-04-09")),
            r"RepoQuote\.currency must equal CurveSpec\.currency",
        ),
    ],
)
def test_substep_d5_bootstrap_rejects_swap_and_repo_quote_date_currency_mismatches(
    quote: object,
    match: str,
) -> None:
    with pytest.raises(InvalidCurveInput, match=match):
        BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec()).fit(
            [quote],
            spec=_spec(),
            kernel_spec=KernelSpec(kind="linear_zero"),
        )


@pytest.mark.parametrize(
    ("quote", "match"),
    [
        (
            BondQuote(
                instrument=_sample_bond("UST2Y-DATE", maturity_years=2, coupon_rate=Decimal("0.04")),
                clean_price=Decimal("100.0"),
                as_of=Date.parse("2026-04-10"),
            ),
            r"BondQuote\.as_of must equal CurveSpec\.reference_date",
        ),
        (
            BondQuote(
                instrument=_sample_bond("UST2Y-MISSING-DATE", maturity_years=2, coupon_rate=Decimal("0.04")),
                clean_price=Decimal("100.0"),
            ),
            r"BondQuote\.as_of is required",
        ),
        (
            BondQuote(
                instrument=_sample_bond(
                    "BUND2Y",
                    maturity_years=2,
                    coupon_rate=Decimal("0.04"),
                    currency=Currency.EUR,
                ),
                clean_price=Decimal("100.0"),
                as_of=Date.parse("2026-04-09"),
            ),
            r"BondQuote\.currency must equal CurveSpec\.currency",
        ),
    ],
)
def test_substep_d5_bootstrap_rejects_bond_quote_date_currency_mismatches(
    quote: BondQuote,
    match: str,
) -> None:
    with pytest.raises(InvalidCurveInput, match=match):
        BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec()).fit(
            [quote],
            spec=_spec(),
            kernel_spec=KernelSpec(kind="linear_zero"),
        )


def test_substep_d5_bootstrap_builds_linear_zero_kernel_and_report() -> None:
    calibrator = BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec())
    kernel, report = calibrator.fit(
        [
            _swap_quote("5Y", 0.04),
            _swap_quote("1Y", 0.03),
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(kind="linear_zero"),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert curve.rate_at(1.0) == pytest.approx(0.03)
    assert curve.rate_at(5.0) == pytest.approx(0.04)
    assert curve.rate_at(3.0) == pytest.approx(0.035)
    assert isinstance(report, CalibrationReport)
    assert report.converged is True
    assert report.objective == "exact_fit"
    assert report.max_abs_residual == pytest.approx(0.0)
    assert tuple(point.instrument_id for point in report.points) == ("1Y", "5Y")
    assert tuple(point.observed_kind for point in report.points) == ("SWAP_ZERO_RATE", "SWAP_ZERO_RATE")


def test_bootstrap_swap_quote_report_marks_zero_rate_observation() -> None:
    reference_date = Date.parse("2026-04-09")
    quote = SwapQuote(
        instrument_id="SWAP-5Y",
        rate=0.04,
        tenor="5Y",
        currency=Currency.USD,
        as_of=reference_date,
    )
    kernel, report = BootstrapCalibrator(calibration_spec=_bootstrap_calibration_spec()).fit(
        [quote],
        spec=_spec(),
        kernel_spec=KernelSpec(kind="linear_zero"),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert curve.zero_rate_at(5.0) == pytest.approx(0.04)
    assert report.points[0].observed_kind == "SWAP_ZERO_RATE"
    assert report.points[0].observed_value == pytest.approx(0.04)
    assert report.points[0].fitted_value == pytest.approx(0.04)
    assert report.points[0].residual == pytest.approx(0.0)


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
        kernel_spec=KernelSpec(kind="linear_zero"),
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
        kernel_spec=KernelSpec(kind="log_linear_discount"),
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
        calibration_spec=_bootstrap_calibration_spec(bond_target="clean_price"),
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
        kernel_spec=KernelSpec(kind="linear_zero"),
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
        kernel_spec=KernelSpec(kind="piecewise_flat_forward"),
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
        spec=_spec(extrapolation_policy="hold_last_zero_rate"),
        kernel_spec=KernelSpec(kind="linear_zero"),
    )
    curve = YieldCurve(
        spec=_spec(extrapolation_policy="hold_last_zero_rate"),
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
            kernel_spec=KernelSpec(kind="nelson_siegel"),
        )

    with pytest.raises(CurveConstructionError, match="does not support kernel kind"):
        calibrator.fit(
            [
                _swap_quote("1Y", 0.03),
                _swap_quote("2Y", 0.035),
                _swap_quote("5Y", 0.04),
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(kind="cubic_spline"),
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
            kernel_spec=KernelSpec(kind="linear_zero"),
        )
