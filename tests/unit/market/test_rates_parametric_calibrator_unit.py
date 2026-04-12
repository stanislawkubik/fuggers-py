from __future__ import annotations

from decimal import Decimal
from math import exp

import pytest

from fuggers_py.core.types import Currency, Date, Frequency, Price
from fuggers_py.math.optimization import OptimizationConfig
from fuggers_py.market.curves import CurveSpec, CurveType, ExtrapolationPolicy, YieldCurve
from fuggers_py.market.curves.errors import CurveConstructionError, InvalidCurveInput
from fuggers_py.market.curves.rates.calibrators import (
    CalibrationObjective,
    CurveCalibrator,
    ParametricCalibrator,
    ParametricOptimizerKind,
)
from fuggers_py.market.curves.rates.kernels import (
    CurveKernelKind,
    ExponentialSplineKernel,
    KernelSpec,
    NelsonSiegelKernel,
    SvenssonKernel,
)
from fuggers_py.market.curves.rates.reports import CalibrationReport
from fuggers_py.market.quotes import BondQuote, RepoQuote, SwapQuote
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


def _tenor_text(tenor: float) -> str:
    mapping = {
        0.25: "3M",
        0.5: "6M",
        1.0: "1Y",
        2.0: "2Y",
        3.0: "3Y",
        5.0: "5Y",
        7.0: "7Y",
        10.0: "10Y",
        20.0: "20Y",
    }
    try:
        return mapping[tenor]
    except KeyError as exc:
        raise AssertionError(f"missing test tenor mapping for {tenor}") from exc


def _swap_quote(tenor: float, rate: float, *, instrument_id: str | None = None) -> SwapQuote:
    tenor_text = _tenor_text(tenor)
    return SwapQuote(
        instrument_id=instrument_id or tenor_text,
        tenor=tenor_text,
        rate=rate,
        currency=Currency.USD,
        as_of=Date.parse("2026-04-09"),
    )


def _repo_quote(tenor: float, rate: float, *, instrument_id: str | None = None) -> RepoQuote:
    tenor_text = _tenor_text(tenor)
    return RepoQuote(
        instrument_id=instrument_id or tenor_text,
        term=tenor_text,
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


def _ns_zero(t: float, beta0: float, beta1: float, beta2: float, tau: float) -> float:
    if t <= 0.0:
        return beta0 + beta1
    x = t / tau
    factor = (1.0 - exp(-x)) / x
    return beta0 + beta1 * factor + beta2 * (factor - exp(-x))


def _sv_zero(
    t: float,
    beta0: float,
    beta1: float,
    beta2: float,
    beta3: float,
    tau1: float,
    tau2: float,
) -> float:
    if t <= 0.0:
        return beta0 + beta1
    x1 = t / tau1
    x2 = t / tau2
    factor1 = (1.0 - exp(-x1)) / x1
    factor2 = (1.0 - exp(-x2)) / x2
    return beta0 + beta1 * factor1 + beta2 * (factor1 - exp(-x1)) + beta3 * (factor2 - exp(-x2))


def _exp_spline_zero(t: float, coefficients: tuple[float, ...], decay_factors: tuple[float, ...]) -> float:
    return coefficients[0] + sum(
        coefficient * exp(-decay_factor * t)
        for coefficient, decay_factor in zip(coefficients[1:], decay_factors, strict=True)
    )


def test_step9_parametric_calibrator_is_exported() -> None:
    assert issubclass(ParametricCalibrator, CurveCalibrator)
    assert ParametricOptimizerKind.LEVENBERG_MARQUARDT.name == "LEVENBERG_MARQUARDT"


def test_step9_parametric_quote_driven_fit_validates_tenor_and_quote_count() -> None:
    with pytest.raises(InvalidCurveInput, match="tenor must be a tenor string like '3M' or '5Y'"):
        ParametricCalibrator().fit(
            [SwapQuote("0Y", rate=0.03, tenor="0Y", currency=Currency.USD, as_of=Date.parse("2026-04-09"))],
            spec=_spec(),
            kernel_spec=KernelSpec(kind=CurveKernelKind.NELSON_SIEGEL),
        )

    with pytest.raises(InvalidCurveInput, match="requires at least 4 quotes"):
        ParametricCalibrator().fit(
            [
                _swap_quote(1.0, 0.0310),
                _swap_quote(2.0, 0.0320),
                _swap_quote(5.0, 0.0330),
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(kind=CurveKernelKind.NELSON_SIEGEL),
        )


def test_step9_parametric_calibrator_fits_nelson_siegel_zero_observations() -> None:
    true_parameters = (0.035, -0.01, 0.02, 2.5)
    tenors = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)
    calibrator = ParametricCalibrator(
        objective=CalibrationObjective.EXACT_FIT,
        optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
    )
    kernel, report = calibrator.fit(
        [
            _swap_quote(tenor, _ns_zero(tenor, *true_parameters))
            for tenor in tenors
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.NELSON_SIEGEL),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert isinstance(kernel, NelsonSiegelKernel)
    assert isinstance(report, CalibrationReport)
    assert report.converged is True
    assert report.objective == CalibrationObjective.EXACT_FIT.name
    assert report.max_abs_residual == pytest.approx(0.0, abs=1e-10)
    assert curve.rate_at(4.0) == pytest.approx(_ns_zero(4.0, *true_parameters), abs=1e-10)


def test_step9_parametric_calibrator_fits_svensson_with_explicit_initial_parameters() -> None:
    true_parameters = (0.036, -0.012, 0.018, -0.006, 1.7, 4.5)
    tenors = (0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0)
    calibrator = ParametricCalibrator(
        optimization_config=OptimizationConfig(max_iterations=300, tolerance=1e-14),
    )
    kernel, report = calibrator.fit(
        [
            _swap_quote(tenor, _sv_zero(tenor, *true_parameters))
            for tenor in tenors
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(
            kind=CurveKernelKind.SVENSSON,
            parameters={
                "initial_parameters": [0.035, -0.01, 0.017, -0.005, 1.5, 4.0],
            },
        ),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert isinstance(kernel, SvenssonKernel)
    assert report.converged is True
    assert report.objective == CalibrationObjective.WEIGHTED_L2.name
    assert report.max_abs_residual == pytest.approx(0.0, abs=1e-10)
    assert curve.rate_at(4.0) == pytest.approx(_sv_zero(4.0, *true_parameters), abs=1e-10)


def test_step9_parametric_calibrator_accepts_repo_rate_quotes() -> None:
    true_parameters = (0.035, -0.01, 0.02, 2.5)
    tenors = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)
    quotes = [_repo_quote(tenor, _ns_zero(tenor, *true_parameters)) for tenor in tenors]

    calibrator = ParametricCalibrator(
        optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
    )
    kernel, report = calibrator.fit(
        quotes,
        spec=_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.NELSON_SIEGEL),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert report.converged is True
    assert curve.rate_at(4.0) == pytest.approx(_ns_zero(4.0, *true_parameters), abs=1e-10)
    assert report.points[0].observed_kind == "REPO_RATE_CONTINUOUS"


def test_step9_parametric_calibrator_fits_exponential_spline_zero_observations() -> None:
    true_coefficients = (0.031, -0.007, 0.004)
    decay_factors = (0.40, 1.20)
    tenors = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)
    calibrator = ParametricCalibrator(
        objective=CalibrationObjective.EXACT_FIT,
        optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
    )

    kernel, report = calibrator.fit(
        [
            _swap_quote(tenor, _exp_spline_zero(tenor, true_coefficients, decay_factors))
            for tenor in tenors
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(
            kind=CurveKernelKind.EXPONENTIAL_SPLINE,
            parameters={"decay_factors": decay_factors},
        ),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert isinstance(kernel, ExponentialSplineKernel)
    assert report.converged is True
    assert report.max_abs_residual == pytest.approx(0.0, abs=1e-10)
    assert curve.rate_at(4.0) == pytest.approx(
        _exp_spline_zero(4.0, true_coefficients, decay_factors),
        abs=1e-10,
    )


def test_step9_parametric_calibrator_accepts_bond_clean_price_quotes() -> None:
    true_parameters = (0.035, -0.01, 0.02, 2.5)
    settlement = Date.parse("2026-04-09")
    bond_specs = (
        ("UST1Y", 1, Decimal("0.030")),
        ("UST2Y", 2, Decimal("0.032")),
        ("UST3Y", 3, Decimal("0.034")),
        ("UST5Y", 5, Decimal("0.036")),
        ("UST7Y", 7, Decimal("0.038")),
        ("UST10Y", 10, Decimal("0.040")),
    )
    quotes = []
    for instrument_id, maturity_years, coupon_rate in bond_specs:
        bond = _sample_bond(
            instrument_id,
            maturity_years=maturity_years,
            coupon_rate=coupon_rate,
        )
        clean_price = _clean_price_from_zero_curve(
            bond,
            settlement_date=settlement,
            zero_rate_fn=lambda tenor: _ns_zero(tenor, *true_parameters),
        )
        quotes.append(
            BondQuote(
                instrument=bond,
                clean_price=clean_price,
                as_of=settlement,
            )
        )

    calibrator = ParametricCalibrator(
        optimization_config=OptimizationConfig(max_iterations=400, tolerance=1e-14),
    )
    kernel, report = calibrator.fit(
        quotes,
        spec=_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.NELSON_SIEGEL),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert report.converged is True
    assert report.max_abs_residual < 1e-10
    assert curve.rate_at(4.0) == pytest.approx(_ns_zero(4.0, *true_parameters), abs=1e-8)
    assert report.points[0].observed_kind == "BOND_CLEAN_PRICE_TO_YTM_SEMI_ANNUAL"


def test_step9_parametric_calibrator_accepts_bond_quotes_for_exponential_spline() -> None:
    true_coefficients = (0.031, -0.007, 0.004)
    decay_factors = (0.40, 1.20)
    settlement = Date.parse("2026-04-09")
    bond_specs = (
        ("UST1Y", 1, Decimal("0.030")),
        ("UST2Y", 2, Decimal("0.032")),
        ("UST3Y", 3, Decimal("0.034")),
        ("UST5Y", 5, Decimal("0.036")),
        ("UST7Y", 7, Decimal("0.038")),
    )
    quotes = []
    for instrument_id, maturity_years, coupon_rate in bond_specs:
        bond = _sample_bond(
            instrument_id,
            maturity_years=maturity_years,
            coupon_rate=coupon_rate,
        )
        clean_price = _clean_price_from_zero_curve(
            bond,
            settlement_date=settlement,
            zero_rate_fn=lambda tenor: _exp_spline_zero(tenor, true_coefficients, decay_factors),
        )
        quotes.append(
            BondQuote(
                instrument=bond,
                clean_price=clean_price,
                as_of=settlement,
            )
        )

    calibrator = ParametricCalibrator(
        optimization_config=OptimizationConfig(max_iterations=400, tolerance=1e-14),
    )
    kernel, report = calibrator.fit(
        quotes,
        spec=_spec(),
        kernel_spec=KernelSpec(
            kind=CurveKernelKind.EXPONENTIAL_SPLINE,
            parameters={"decay_factors": decay_factors},
        ),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert report.converged is True
    assert report.max_abs_residual < 1e-10
    assert curve.rate_at(4.0) == pytest.approx(
        _exp_spline_zero(4.0, true_coefficients, decay_factors),
        abs=1e-7,
    )
    assert report.points[0].observed_kind == "BOND_CLEAN_PRICE_TO_YTM_SEMI_ANNUAL"


def test_step9_parametric_calibrator_accepts_bond_ytm_quotes() -> None:
    true_parameters = (0.035, -0.01, 0.02, 2.5)
    settlement = Date.parse("2026-04-09")
    bond_specs = (
        ("UST1Y", 1, Decimal("0.030")),
        ("UST2Y", 2, Decimal("0.032")),
        ("UST3Y", 3, Decimal("0.034")),
        ("UST5Y", 5, Decimal("0.036")),
    )
    quotes = []
    for instrument_id, maturity_years, coupon_rate in bond_specs:
        bond = _sample_bond(
            instrument_id,
            maturity_years=maturity_years,
            coupon_rate=coupon_rate,
        )
        clean_price = _clean_price_from_zero_curve(
            bond,
            settlement_date=settlement,
            zero_rate_fn=lambda tenor: _ns_zero(tenor, *true_parameters),
        )
        ytm = bond.yield_from_price(Price.new(clean_price, Currency.USD), settlement).ytm
        quotes.append(
            BondQuote(
                instrument=bond,
                yield_to_maturity=ytm.value(),
                as_of=settlement,
            )
        )

    calibrator = ParametricCalibrator(
        optimization_config=OptimizationConfig(max_iterations=400, tolerance=1e-14),
    )
    kernel, report = calibrator.fit(
        quotes,
        spec=_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.NELSON_SIEGEL),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert report.converged is True
    assert curve.rate_at(4.0) == pytest.approx(_ns_zero(4.0, *true_parameters), abs=1e-8)
    assert report.points[0].observed_kind == "BOND_YTM_SEMI_ANNUAL"


def test_step9_parametric_calibrator_reparameterizes_negative_tau_guess_and_validates_inputs() -> None:
    true_parameters = (0.035, -0.01, 0.02, 2.5)
    tenors = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)
    quotes = [
        _swap_quote(tenor, _ns_zero(tenor, *true_parameters))
        for tenor in tenors
    ]
    calibrator = ParametricCalibrator(
        optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
    )

    kernel, report = calibrator.fit(
        quotes,
        spec=_spec(extrapolation_policy=ExtrapolationPolicy.HOLD_LAST_ZERO_RATE),
        kernel_spec=KernelSpec(
            kind=CurveKernelKind.NELSON_SIEGEL,
            parameters={"initial_parameters": [0.04, -0.01, 0.0, -2.0], "max_t": 15.0},
        ),
    )

    assert report.converged is True
    assert kernel.max_t() == pytest.approx(15.0)
    assert kernel.discount_factor_at(12.0) > 0.0
    assert kernel._model.tau > 0.0  # type: ignore[attr-defined]

    with pytest.raises(CurveConstructionError, match="does not support kernel kind"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(kind=CurveKernelKind.LINEAR_ZERO),
        )

    with pytest.raises(InvalidCurveInput, match="requires kernel_spec.parameters\\['decay_factors'\\]"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(kind=CurveKernelKind.EXPONENTIAL_SPLINE),
        )

    with pytest.raises(InvalidCurveInput, match="length 6"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(
                kind=CurveKernelKind.SVENSSON,
                parameters={"initial_parameters": [0.03, -0.01, 0.01, -0.005]},
            ),
        )

    with pytest.raises(InvalidCurveInput, match="length 3"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(
                kind=CurveKernelKind.EXPONENTIAL_SPLINE,
                parameters={
                    "decay_factors": [0.40, 1.20],
                    "initial_coefficients": [0.03, -0.01],
                },
            ),
        )
