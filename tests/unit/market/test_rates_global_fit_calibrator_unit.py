from __future__ import annotations

from decimal import Decimal
from math import exp

import pytest

from fuggers_py._core.types import Currency, Date, Frequency, Price
from fuggers_py._math.optimization import OptimizationConfig
from fuggers_py.curves import CurveSpec, YieldCurve
from fuggers_py.curves.errors import CurveConstructionError, InvalidCurveInput
from fuggers_py.curves.calibrators import CalibrationSpec
from fuggers_py.curves.calibrators.base import CurveCalibrator
from fuggers_py.curves.calibrators.global_fit import GlobalFitCalibrator
from fuggers_py.curves.kernels import KernelSpec
from fuggers_py.curves.kernels.parametric import NelsonSiegelKernel, SvenssonKernel
from fuggers_py.curves.kernels.spline import CubicSplineKernel, ExponentialSplineKernel
from fuggers_py.curves.reports import CalibrationReport
from fuggers_py._runtime.quotes import BondQuote, RepoQuote, SwapQuote
from fuggers_py.bonds import FixedBondBuilder
from fuggers_py.bonds.errors import BondPricingError
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


def _global_fit_calibration_spec(
    *,
    objective: str = "weighted_l2",
    bond_target: str = "dirty_price",
    regressors: tuple[str, ...] = (),
) -> CalibrationSpec:
    return CalibrationSpec(
        method="global_fit",
        objective=objective,
        regressors=regressors,
        bond_target=bond_target,
    )


def _bond_quotes_with_liquidity_shift(
    *,
    settlement_date: Date,
    zero_rate_fn,
    bond_specs: tuple[tuple[str, int, Decimal, float], ...],
    liquidity_shift: Decimal,
) -> list[BondQuote]:
    quotes: list[BondQuote] = []
    for instrument_id, maturity_years, coupon_rate, liquidity in bond_specs:
        bond = _sample_bond(
            instrument_id,
            maturity_years=maturity_years,
            coupon_rate=coupon_rate,
        )
        clean_price = _clean_price_from_zero_curve(
            bond,
            settlement_date=settlement_date,
            zero_rate_fn=zero_rate_fn,
        )
        quotes.append(
            BondQuote(
                instrument=bond,
                clean_price=clean_price + (liquidity_shift * Decimal(str(liquidity))),
                as_of=settlement_date,
                regressors={"liquidity": liquidity},
            )
        )
    return quotes


def test_step9_global_fit_calibrator_is_exported() -> None:
    assert issubclass(GlobalFitCalibrator, CurveCalibrator)
    assert _global_fit_calibration_spec().method == "global_fit"
    assert _global_fit_calibration_spec().objective == "weighted_l2"


def test_step9_global_fit_constructor_validates_calibration_spec() -> None:
    with pytest.raises(
        InvalidCurveInput,
        match="GlobalFitCalibrator requires calibration_spec.method == 'global_fit'",
    ):
        GlobalFitCalibrator(
            calibration_spec=CalibrationSpec(
                method="bootstrap",
                objective="exact_fit",
            )
        )

    with pytest.raises(
        InvalidCurveInput,
        match="CalibrationSpec.method='global_fit' requires objective='weighted_l2'",
    ):
        GlobalFitCalibrator(
            calibration_spec=_global_fit_calibration_spec(objective="exact_fit"),
        )


def test_step9_global_fit_quote_driven_fit_validates_tenor_and_quote_count() -> None:
    with pytest.raises(InvalidCurveInput, match="tenor must be a tenor string like '3M' or '5Y'"):
        GlobalFitCalibrator(calibration_spec=_global_fit_calibration_spec()).fit(
            [SwapQuote("0Y", rate=0.03, tenor="0Y", currency=Currency.USD, as_of=Date.parse("2026-04-09"))],
            spec=_spec(),
            kernel_spec=KernelSpec(kind="nelson_siegel"),
        )

    with pytest.raises(InvalidCurveInput, match="requires at least 4 quotes"):
        GlobalFitCalibrator(calibration_spec=_global_fit_calibration_spec()).fit(
            [
                _swap_quote(1.0, 0.0310),
                _swap_quote(2.0, 0.0320),
                _swap_quote(5.0, 0.0330),
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(kind="nelson_siegel"),
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
def test_step9_global_fit_rejects_swap_and_repo_quote_date_currency_mismatches(
    quote: object,
    match: str,
) -> None:
    with pytest.raises(InvalidCurveInput, match=match):
        GlobalFitCalibrator(calibration_spec=_global_fit_calibration_spec()).fit(
            [quote],
            spec=_spec(),
            kernel_spec=KernelSpec(kind="nelson_siegel"),
        )


def test_step9_global_fit_allows_duplicate_tenors() -> None:
    true_parameters = (0.035, -0.01, 0.02, 2.5)
    quotes = [
        _swap_quote(1.0, _ns_zero(1.0, *true_parameters), instrument_id="1Y"),
        _swap_quote(2.0, _ns_zero(2.0, *true_parameters), instrument_id="2Y-a"),
        _swap_quote(2.0, _ns_zero(2.0, *true_parameters), instrument_id="2Y-b"),
        _swap_quote(5.0, _ns_zero(5.0, *true_parameters), instrument_id="5Y"),
        _swap_quote(7.0, _ns_zero(7.0, *true_parameters), instrument_id="7Y"),
        _swap_quote(10.0, _ns_zero(10.0, *true_parameters), instrument_id="10Y"),
    ]
    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(),
        optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
    )

    kernel, report = calibrator.fit(
        quotes,
        spec=_spec(),
        kernel_spec=KernelSpec(kind="nelson_siegel"),
    )

    assert isinstance(kernel, NelsonSiegelKernel)
    assert report.converged is True
    assert report.max_abs_residual == pytest.approx(0.0, abs=1e-10)
    assert report.regressors == ()
    assert report.regressor_coefficients == ()
    assert isinstance(report, CalibrationReport)
    assert report.kernel == "nelson_siegel"
    assert len(report.kernel_parameters) == 4
    assert report.objective_value == pytest.approx(0.0, abs=1e-12)
    assert report.points == report.points
    assert report.points[0].curve_only_value == pytest.approx(report.points[0].fitted_value, abs=1e-12)
    assert report.points[0].price_residual is None


def test_step9_global_fit_rejects_mixed_target_spaces_before_optimization() -> None:
    settlement = Date.parse("2026-04-09")
    bond = _sample_bond("UST2Y", maturity_years=2, coupon_rate=Decimal("0.04"))
    clean_price = _clean_price_from_zero_curve(
        bond,
        settlement_date=settlement,
        zero_rate_fn=lambda tenor: _ns_zero(tenor, 0.035, -0.01, 0.02, 2.5),
    )

    with pytest.raises(InvalidCurveInput, match="mixed target spaces") as exc_info:
        GlobalFitCalibrator(calibration_spec=_global_fit_calibration_spec(bond_target="clean_price")).fit(
            [
                _swap_quote(1.0, 0.0310, instrument_id="1Y"),
                _swap_quote(2.0, 0.0320, instrument_id="2Y"),
                _swap_quote(5.0, 0.0330, instrument_id="5Y"),
                BondQuote(
                    instrument=bond,
                    clean_price=clean_price,
                    as_of=settlement,
                ),
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(kind="nelson_siegel"),
        )

    message = str(exc_info.value)
    assert "RATE=[ZERO_RATE]" in message
    assert "BOND_PRICE=[BOND_CLEAN_PRICE]" in message


@pytest.mark.parametrize(
    ("kernel_spec", "zero_rate_fn", "bond_specs", "expected_kernel_type", "expected_shift"),
    [
        (
            KernelSpec(kind="svensson"),
            lambda tenor: _sv_zero(tenor, 0.036, -0.012, 0.018, -0.006, 1.7, 4.5),
            (
                ("UST2Y-A", 2, Decimal("0.040"), 0.0),
                ("UST2Y-B", 2, Decimal("0.040"), 1.0),
                ("UST3Y", 3, Decimal("0.0425"), 0.0),
                ("UST5Y", 5, Decimal("0.045"), 0.0),
                ("UST7Y", 7, Decimal("0.047"), 0.0),
                ("UST10Y", 10, Decimal("0.048"), 0.0),
            ),
            SvenssonKernel,
            0.40,
        ),
        (
            KernelSpec(
                kind="exponential_spline",
                parameters={"decay_factors": (0.40, 1.20)},
            ),
            lambda tenor: _exp_spline_zero(tenor, (0.031, -0.007, 0.004), (0.40, 1.20)),
            (
                ("UST2Y-A", 2, Decimal("0.040"), 0.0),
                ("UST2Y-B", 2, Decimal("0.040"), 1.0),
                ("UST3Y", 3, Decimal("0.0425"), 0.0),
                ("UST5Y", 5, Decimal("0.045"), 0.0),
            ),
            ExponentialSplineKernel,
            0.30,
        ),
        (
            KernelSpec(
                kind="cubic_spline",
                parameters={"knots": (2.1, 3.1, 5.1)},
            ),
            lambda tenor: 0.03,
            (
                ("UST2Y-A", 2, Decimal("0.040"), 0.0),
                ("UST2Y-B", 2, Decimal("0.040"), 1.0),
                ("UST3Y", 3, Decimal("0.0425"), 0.0),
                ("UST5Y", 5, Decimal("0.045"), 0.0),
            ),
            CubicSplineKernel,
            0.50,
        ),
    ],
)
def test_step9_global_fit_supports_supported_global_fit_kernels_with_bond_regressors(
    kernel_spec: KernelSpec,
    zero_rate_fn,
    bond_specs: tuple[tuple[str, int, Decimal, float], ...],
    expected_kernel_type: type,
    expected_shift: float,
) -> None:
    settlement = Date.parse("2026-04-09")
    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(
            bond_target="clean_price",
            regressors=("liquidity",),
        ),
        optimization_config=OptimizationConfig(max_iterations=400, tolerance=1e-14),
    )

    kernel, report = calibrator.fit(
        _bond_quotes_with_liquidity_shift(
            settlement_date=settlement,
            zero_rate_fn=zero_rate_fn,
            bond_specs=bond_specs,
            liquidity_shift=Decimal(str(expected_shift)),
        ),
        spec=_spec(),
        kernel_spec=kernel_spec,
    )

    assert isinstance(kernel, expected_kernel_type)
    assert report.converged is True
    assert report.max_abs_residual == pytest.approx(0.0, abs=1e-7)
    assert report.regressors == ("liquidity",)
    assert report.regressor_coefficients == pytest.approx((expected_shift,), abs=1e-7)
    assert report.points[0].observed_kind == "BOND_CLEAN_PRICE"


def test_step9_global_fit_does_not_count_profiled_regressors_as_extra_curve_parameters() -> None:
    true_parameters = (0.035, -0.01, 0.02, 2.5)
    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(regressors=("liquidity",)),
        optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
    )

    kernel, report = calibrator.fit(
        [
            _swap_quote(0.5, _ns_zero(0.5, *true_parameters), instrument_id="6M"),
            _swap_quote(2.0, _ns_zero(2.0, *true_parameters), instrument_id="2Y"),
            _swap_quote(5.0, _ns_zero(5.0, *true_parameters), instrument_id="5Y"),
            _swap_quote(10.0, _ns_zero(10.0, *true_parameters), instrument_id="10Y"),
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(kind="nelson_siegel"),
    )

    assert isinstance(kernel, NelsonSiegelKernel)
    assert report.converged is True
    assert report.regressors == ("liquidity",)
    assert report.regressor_coefficients == pytest.approx((0.0,), abs=1e-12)


def test_step9_global_fit_cubic_spline_requires_knots_at_calibrator_entry() -> None:
    with pytest.raises(InvalidCurveInput, match="cubic_spline requires kernel_spec.parameters\\['knots'\\]"):
        GlobalFitCalibrator(calibration_spec=_global_fit_calibration_spec()).fit(
            [
                _swap_quote(1.0, 0.03),
                _swap_quote(2.0, 0.031),
                _swap_quote(5.0, 0.033),
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(kind="cubic_spline"),
        )


def test_step9_global_fit_uses_quote_row_regressor_values_in_one_shared_residual_engine() -> None:
    settlement = Date.parse("2026-04-09")
    zero_rate = 0.03
    liquidity_adjustment = Decimal("0.50")
    bond_2y_a = _sample_bond("UST2Y-A", maturity_years=2, coupon_rate=Decimal("0.04"))
    bond_2y_b = _sample_bond("UST2Y-B", maturity_years=2, coupon_rate=Decimal("0.04"))
    bond_3y = _sample_bond("UST3Y", maturity_years=3, coupon_rate=Decimal("0.0425"))
    bond_5y = _sample_bond("UST5Y", maturity_years=5, coupon_rate=Decimal("0.045"))
    clean_2y = _clean_price_from_zero_curve(
        bond_2y_a,
        settlement_date=settlement,
        zero_rate_fn=lambda _: zero_rate,
    )
    clean_3y = _clean_price_from_zero_curve(
        bond_3y,
        settlement_date=settlement,
        zero_rate_fn=lambda _: zero_rate,
    )
    clean_5y = _clean_price_from_zero_curve(
        bond_5y,
        settlement_date=settlement,
        zero_rate_fn=lambda _: zero_rate,
    )
    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(
            bond_target="clean_price",
            regressors=("liquidity",),
        ),
        optimization_config=OptimizationConfig(max_iterations=300, tolerance=1e-14),
    )

    kernel, report = calibrator.fit(
        [
            BondQuote(
                instrument=bond_2y_a,
                clean_price=clean_2y,
                as_of=settlement,
                regressors={"liquidity": 0.0},
            ),
            BondQuote(
                instrument=bond_2y_b,
                clean_price=clean_2y + liquidity_adjustment,
                as_of=settlement,
                regressors={"liquidity": 1.0},
            ),
            BondQuote(
                instrument=bond_3y,
                clean_price=clean_3y,
                as_of=settlement,
                regressors={"liquidity": 0.0},
            ),
            BondQuote(
                instrument=bond_5y,
                clean_price=clean_5y,
                as_of=settlement,
                regressors={"liquidity": 0.0},
            ),
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(
            kind="cubic_spline",
            parameters={"knots": (2.1, 3.1, 7.1)},
        ),
    )

    assert isinstance(kernel, CubicSplineKernel)
    assert report.converged is True
    assert report.max_abs_residual == pytest.approx(0.0, abs=1e-9)
    assert isinstance(report, CalibrationReport)
    assert tuple(point.observed_kind for point in report.points) == (
        "BOND_CLEAN_PRICE",
        "BOND_CLEAN_PRICE",
        "BOND_CLEAN_PRICE",
        "BOND_CLEAN_PRICE",
    )
    assert report.regressors == ("liquidity",)
    assert report.regressor_coefficients == pytest.approx((0.5,), abs=1e-9)
    assert report.kernel == "cubic_spline"
    assert report.kernel_parameters == pytest.approx((zero_rate, zero_rate, zero_rate), abs=1e-7)
    assert report.objective_value == pytest.approx(0.0, abs=1e-12)
    assert len(report.points) == 4
    assert report.points == report.points
    assert report.points[0].price_residual == pytest.approx(0.0, abs=1e-9)
    assert report.points[0].modeled_ytm is not None
    assert report.points[0].observed_ytm is not None
    assert report.points[0].ytm_residual == pytest.approx(0.0, abs=1e-9)
    assert report.points[0].ytm_bp_residual == pytest.approx(0.0, abs=1e-5)
    assert report.points[1].regressor_values == (1.0,)
    assert report.points[1].regressor_contribution == pytest.approx(0.5, abs=1e-9)


def test_step9_global_fit_calibrator_fits_nelson_siegel_zero_observations() -> None:
    true_parameters = (0.035, -0.01, 0.02, 2.5)
    tenors = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)
    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(),
        optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
    )
    kernel, report = calibrator.fit(
        [
            _swap_quote(tenor, _ns_zero(tenor, *true_parameters))
            for tenor in tenors
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(kind="nelson_siegel"),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert isinstance(kernel, NelsonSiegelKernel)
    assert isinstance(report, CalibrationReport)
    assert isinstance(report, CalibrationReport)
    assert report.converged is True
    assert report.objective == "weighted_l2"
    assert report.max_abs_residual == pytest.approx(0.0, abs=1e-10)
    assert report.regressors == ()
    assert report.regressor_coefficients == ()
    assert report.objective_value == pytest.approx(0.0, abs=1e-12)
    assert report.points[0].observed_kind == "SWAP_ZERO_RATE_CONTINUOUS"
    assert curve.rate_at(4.0) == pytest.approx(_ns_zero(4.0, *true_parameters), abs=1e-10)


def test_step9_global_fit_suppresses_optional_bond_ytm_diagnostics_only_for_expected_bond_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settlement = Date.parse("2026-04-09")
    zero_rate = 0.03
    bonds = [
        _sample_bond("UST2Y", maturity_years=2, coupon_rate=Decimal("0.040")),
        _sample_bond("UST3Y", maturity_years=3, coupon_rate=Decimal("0.0425")),
        _sample_bond("UST5Y", maturity_years=5, coupon_rate=Decimal("0.045")),
        _sample_bond("UST7Y", maturity_years=7, coupon_rate=Decimal("0.047")),
    ]

    def _raise_bond_pricing_error(self, clean_price: Price, settlement_date: Date):
        raise BondPricingError(reason="diagnostic ytm unavailable")

    monkeypatch.setattr(bonds[0].__class__, "yield_from_price", _raise_bond_pricing_error)

    _, report = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(bond_target="clean_price"),
        optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
    ).fit(
        [
            BondQuote(
                instrument=bond,
                clean_price=_clean_price_from_zero_curve(
                    bond,
                    settlement_date=settlement,
                    zero_rate_fn=lambda tenor: zero_rate,
                ),
                as_of=settlement,
            )
            for bond in bonds
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(
            kind="cubic_spline",
            parameters={"knots": (2.1, 3.1, 7.1)},
        ),
    )

    assert isinstance(report, CalibrationReport)
    assert report.points[0].price_residual == pytest.approx(0.0, abs=1e-9)
    assert report.points[0].observed_ytm is None
    assert report.points[0].modeled_ytm is None
    assert report.points[0].ytm_residual is None
    assert report.points[0].ytm_bp_residual is None


def test_step9_global_fit_does_not_hide_unexpected_bond_diagnostic_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settlement = Date.parse("2026-04-09")
    zero_rate = 0.03
    bonds = [
        _sample_bond("UST2Y", maturity_years=2, coupon_rate=Decimal("0.040")),
        _sample_bond("UST3Y", maturity_years=3, coupon_rate=Decimal("0.0425")),
        _sample_bond("UST5Y", maturity_years=5, coupon_rate=Decimal("0.045")),
        _sample_bond("UST7Y", maturity_years=7, coupon_rate=Decimal("0.047")),
    ]

    def _raise_runtime_error(self, clean_price: Price, settlement_date: Date):
        raise RuntimeError("unexpected diagnostic failure")

    monkeypatch.setattr(bonds[0].__class__, "yield_from_price", _raise_runtime_error)

    with pytest.raises(RuntimeError, match="unexpected diagnostic failure"):
        GlobalFitCalibrator(
            calibration_spec=_global_fit_calibration_spec(bond_target="clean_price"),
            optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
        ).fit(
            [
                BondQuote(
                    instrument=bond,
                    clean_price=_clean_price_from_zero_curve(
                        bond,
                        settlement_date=settlement,
                        zero_rate_fn=lambda tenor: zero_rate,
                    ),
                    as_of=settlement,
                )
                for bond in bonds
            ],
            spec=_spec(),
            kernel_spec=KernelSpec(
                kind="cubic_spline",
                parameters={"knots": (2.1, 3.1, 7.1)},
            ),
        )


def test_step9_global_fit_calibrator_fits_svensson_with_explicit_initial_parameters() -> None:
    true_parameters = (0.036, -0.012, 0.018, -0.006, 1.7, 4.5)
    tenors = (0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0)
    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(),
        optimization_config=OptimizationConfig(max_iterations=300, tolerance=1e-14),
    )
    kernel, report = calibrator.fit(
        [
            _swap_quote(tenor, _sv_zero(tenor, *true_parameters))
            for tenor in tenors
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(
            kind="svensson",
            parameters={
                "initial_parameters": [0.035, -0.01, 0.017, -0.005, 1.5, 4.0],
            },
        ),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert isinstance(kernel, SvenssonKernel)
    assert report.converged is True
    assert report.objective == "weighted_l2"
    assert report.max_abs_residual == pytest.approx(0.0, abs=1e-10)
    assert curve.rate_at(4.0) == pytest.approx(_sv_zero(4.0, *true_parameters), abs=1e-10)


def test_step9_global_fit_calibrator_accepts_repo_rate_quotes() -> None:
    true_parameters = (0.035, -0.01, 0.02, 2.5)
    tenors = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)
    quotes = [_repo_quote(tenor, _ns_zero(tenor, *true_parameters)) for tenor in tenors]

    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(),
        optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
    )
    kernel, report = calibrator.fit(
        quotes,
        spec=_spec(),
        kernel_spec=KernelSpec(kind="nelson_siegel"),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert report.converged is True
    assert curve.rate_at(4.0) == pytest.approx(_ns_zero(4.0, *true_parameters), abs=1e-10)
    assert report.points[0].observed_kind == "REPO_RATE_CONTINUOUS"


def test_step9_global_fit_calibrator_fits_exponential_spline_zero_observations() -> None:
    true_coefficients = (0.031, -0.007, 0.004)
    decay_factors = (0.40, 1.20)
    tenors = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)
    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(),
        optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
    )

    kernel, report = calibrator.fit(
        [
            _swap_quote(tenor, _exp_spline_zero(tenor, true_coefficients, decay_factors))
            for tenor in tenors
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(
            kind="exponential_spline",
            parameters={
                "decay_factors": decay_factors,
                "initial_parameters": true_coefficients,
            },
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


def test_step9_global_fit_calibrator_fits_cubic_spline_on_fixed_knot_grid() -> None:
    knots = (1.0, 2.0, 5.0, 7.0)
    knot_zero_rates = (0.024, 0.028, 0.033, 0.036)
    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(),
        optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
    )

    kernel, report = calibrator.fit(
        [
            _swap_quote(tenor, zero_rate)
            for tenor, zero_rate in zip(knots, knot_zero_rates, strict=True)
        ],
        spec=_spec(),
        kernel_spec=KernelSpec(
            kind="cubic_spline",
            parameters={"knots": knots},
        ),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert isinstance(kernel, CubicSplineKernel)
    assert report.converged is True
    assert report.max_abs_residual == pytest.approx(0.0, abs=1e-10)
    assert kernel.max_t() == pytest.approx(7.0)
    assert curve.rate_at(1.0) == pytest.approx(0.024)
    assert curve.rate_at(5.0) == pytest.approx(0.033)
    assert curve.discount_factor_at(3.0) > 0.0


def test_step9_global_fit_calibrator_accepts_bond_clean_price_quotes() -> None:
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

    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(bond_target="clean_price"),
        optimization_config=OptimizationConfig(max_iterations=400, tolerance=1e-14),
    )
    kernel, report = calibrator.fit(
        quotes,
        spec=_spec(),
        kernel_spec=KernelSpec(kind="nelson_siegel"),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert report.converged is True
    assert report.max_abs_residual < 1e-10
    assert curve.rate_at(4.0) == pytest.approx(_ns_zero(4.0, *true_parameters), abs=1e-8)
    assert report.points[0].observed_kind == "BOND_CLEAN_PRICE"


def test_step9_global_fit_calibrator_accepts_bond_quotes_for_exponential_spline() -> None:
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

    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(),
        optimization_config=OptimizationConfig(max_iterations=400, tolerance=1e-14),
    )
    kernel, report = calibrator.fit(
        quotes,
        spec=_spec(),
        kernel_spec=KernelSpec(
            kind="exponential_spline",
            parameters={
                "decay_factors": decay_factors,
                "initial_parameters": true_coefficients,
            },
        ),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert report.converged is True
    assert report.max_abs_residual < 1e-10
    assert curve.rate_at(4.0) == pytest.approx(
        _exp_spline_zero(4.0, true_coefficients, decay_factors),
        abs=1e-7,
    )
    assert report.points[0].observed_kind == "BOND_DIRTY_PRICE"


def test_step9_global_fit_calibrator_accepts_bond_ytm_quotes() -> None:
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

    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(),
        optimization_config=OptimizationConfig(max_iterations=400, tolerance=1e-14),
    )
    kernel, report = calibrator.fit(
        quotes,
        spec=_spec(),
        kernel_spec=KernelSpec(kind="nelson_siegel"),
    )
    curve = YieldCurve(spec=_spec(), kernel=kernel, calibration_report=report)

    assert report.converged is True
    assert curve.rate_at(4.0) == pytest.approx(_ns_zero(4.0, *true_parameters), abs=1e-8)
    assert report.points[0].observed_kind == "BOND_YTM_SEMI_ANNUAL"


def test_step9_global_fit_calibrator_reparameterizes_negative_tau_guess_and_validates_inputs() -> None:
    true_parameters = (0.035, -0.01, 0.02, 2.5)
    tenors = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)
    quotes = [
        _swap_quote(tenor, _ns_zero(tenor, *true_parameters))
        for tenor in tenors
    ]
    calibrator = GlobalFitCalibrator(
        calibration_spec=_global_fit_calibration_spec(),
        optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
    )

    kernel, report = calibrator.fit(
        quotes,
        spec=_spec(extrapolation_policy="hold_last_zero_rate"),
        kernel_spec=KernelSpec(
            kind="nelson_siegel",
            parameters={"initial_parameters": [0.04, -0.01, 0.0, -2.0], "max_t": 15.0},
        ),
    )

    assert report.converged is True
    assert kernel.max_t() == pytest.approx(15.0)
    assert kernel.discount_factor_at(12.0) > 0.0
    assert kernel._model.tau > 0.0  # type: ignore[attr-defined]

    with pytest.raises(CurveConstructionError, match="global-fit calibration does not support kernel kind"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(kind="linear_zero"),
        )

    with pytest.raises(InvalidCurveInput, match="requires kernel_spec.parameters\\['decay_factors'\\]"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(kind="exponential_spline"),
        )

    with pytest.raises(InvalidCurveInput, match="requires kernel_spec.parameters\\['knots'\\]"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(kind="cubic_spline"),
        )

    with pytest.raises(InvalidCurveInput, match="at least three knots"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(
                kind="cubic_spline",
                parameters={"knots": [1.0, 5.0]},
            ),
        )

    with pytest.raises(InvalidCurveInput, match="length 6"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(
                kind="svensson",
                parameters={"initial_parameters": [0.03, -0.01, 0.01, -0.005]},
            ),
        )

    with pytest.raises(InvalidCurveInput, match="nelson_siegel does not accept kernel_spec parameters: knots"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(
                kind="nelson_siegel",
                parameters={"knots": [1.0, 2.0, 5.0]},
            ),
        )

    with pytest.raises(
        InvalidCurveInput,
        match="svensson does not accept kernel_spec parameters: initial_coefficients",
    ):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(
                kind="svensson",
                parameters={"initial_coefficients": [0.03, -0.01, 0.01, -0.005, 2.0, 4.0]},
            ),
        )

    with pytest.raises(InvalidCurveInput, match="length 3"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(
                kind="exponential_spline",
                parameters={
                    "decay_factors": [0.40, 1.20],
                    "initial_coefficients": [0.03, -0.01],
                },
            ),
        )

    with pytest.raises(InvalidCurveInput, match="accepts only one of kernel_spec.parameters\\['initial_parameters'\\]"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(
                kind="exponential_spline",
                parameters={
                    "decay_factors": [0.40, 1.20],
                    "initial_parameters": [0.03, -0.01, 0.002],
                    "initial_coefficients": [0.03, -0.01, 0.002],
                },
            ),
        )

    with pytest.raises(InvalidCurveInput, match="length 4"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(
                kind="cubic_spline",
                parameters={
                    "knots": [1.0, 2.0, 5.0, 10.0],
                    "initial_parameters": [0.03, 0.031, 0.032],
                },
            ),
        )

    with pytest.raises(InvalidCurveInput, match="length 4"):
        GlobalFitCalibrator(
            calibration_spec=_global_fit_calibration_spec(regressors=("liquidity",)),
            optimization_config=OptimizationConfig(max_iterations=200, tolerance=1e-14),
        ).fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(
                kind="nelson_siegel",
                parameters={"initial_parameters": [0.03, -0.01, 0.01, 2.0, 0.5]},
            ),
        )

    with pytest.raises(InvalidCurveInput, match="cubic_spline does not accept kernel_spec parameters: max_t"):
        calibrator.fit(
            quotes,
            spec=_spec(),
            kernel_spec=KernelSpec(
                kind="cubic_spline",
                parameters={
                    "knots": [1.0, 2.0, 5.0, 10.0],
                    "max_t": 12.0,
                },
            ),
        )
