from __future__ import annotations

import math
import importlib
from decimal import Decimal
from math import exp

import pytest

from fuggers_py.core.types import Currency, Date, Frequency
from fuggers_py.market.curves import (
    CurveSpec,
    CurveType,
    DiscountingCurve,
    ExtrapolationPolicy,
    RateSpace,
    RatesTermStructure,
    RelativeRateCurve,
    YieldCurve,
)
from fuggers_py.market.curves.errors import CurveConstructionError, InvalidCurveInput, TenorOutOfBounds
from fuggers_py.market.curves.rates.kernels import (
    CurveKernel,
    CurveKernelKind,
    KernelSpec,
)
from fuggers_py.market.curves.rates.reports import CalibrationReport
from fuggers_py.market.quotes import BondQuote, SwapQuote
from fuggers_py.products.bonds import FixedBondBuilder
from fuggers_py.reference.bonds.types import YieldCalculationRules


class _FlatZeroCurve(RatesTermStructure):
    def __init__(
        self,
        spec: CurveSpec,
        *,
        rate: float = 0.03,
        max_t: float = 5.0,
    ) -> None:
        super().__init__(spec)
        self._rate = rate
        self._max_t = max_t

    @property
    def rate_space(self) -> RateSpace:
        return RateSpace.ZERO

    def max_t(self) -> float:
        return self._max_t

    def rate_at(self, tenor: float) -> float:
        return self._rate


class _FlatKernel(CurveKernel):
    def __init__(self, *, zero_rate: float = 0.03, max_t: float = 5.0) -> None:
        self._zero_rate = zero_rate
        self._max_t = max_t

    def max_t(self) -> float:
        return self._max_t

    def rate_at(self, tenor: float) -> float:
        return self._zero_rate


def _curve_spec(*, extrapolation_policy: ExtrapolationPolicy = ExtrapolationPolicy.ERROR) -> CurveSpec:
    return CurveSpec(
        name="USD Nominal",
        reference_date=Date.parse("2026-04-09"),
        day_count="ACT_365_FIXED",
        currency=Currency.USD,
        type=CurveType.NOMINAL,
        extrapolation_policy=extrapolation_policy,
    )


def _ns_zero(t: float, beta0: float, beta1: float, beta2: float, tau: float) -> float:
    if t <= 0.0:
        return beta0 + beta1
    x = t / tau
    factor = (1.0 - exp(-x)) / x
    return beta0 + beta1 * factor + beta2 * (factor - exp(-x))


def _exp_spline_zero(t: float, coefficients: tuple[float, ...], decay_factors: tuple[float, ...]) -> float:
    return coefficients[0] + sum(
        coefficient * exp(-decay_factor * t)
        for coefficient, decay_factor in zip(coefficients[1:], decay_factors, strict=True)
    )


def _swap_quote(tenor: str, rate: float, *, instrument_id: str | None = None) -> SwapQuote:
    return SwapQuote(
        instrument_id=instrument_id or tenor,
        tenor=tenor,
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


def test_curve_spec_normalizes_native_fields() -> None:
    spec = CurveSpec(
        name="  USD Nominal  ",
        reference_date=Date.parse("2026-04-09"),
        day_count=" act_365_fixed ",
        currency="usd",
        type=CurveType.NOMINAL,
        reference=" USD-SOFR ",
    )

    assert spec.name == "USD Nominal"
    assert spec.day_count == "ACT_365_FIXED"
    assert spec.currency is Currency.USD
    assert spec.reference == "USD-SOFR"


def test_validate_rate_returns_value_on_domain() -> None:
    curve = _FlatZeroCurve(
        CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
        )
    )

    assert curve.reference_date == Date.parse("2026-04-09")
    assert curve.rate_space is RateSpace.ZERO
    assert curve.validate_rate(2.0) == pytest.approx(0.03)


def test_validate_rate_rejects_negative_t() -> None:
    curve = _FlatZeroCurve(
        CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
        )
    )

    with pytest.raises(InvalidCurveInput, match="t must be >= 0"):
        curve.validate_rate(-0.25)


def test_validate_rate_rejects_t_beyond_domain_when_extrapolation_forbidden() -> None:
    curve = _FlatZeroCurve(
        CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
            extrapolation_policy=ExtrapolationPolicy.ERROR,
        ),
        max_t=3.0,
    )

    with pytest.raises(TenorOutOfBounds):
        curve.validate_rate(4.0)


def test_validate_rate_allows_t_beyond_domain_when_policy_is_not_error() -> None:
    curve = _FlatZeroCurve(
        CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
            extrapolation_policy=ExtrapolationPolicy.HOLD_LAST_NATIVE_RATE,
        ),
        max_t=3.0,
    )

    assert curve.validate_rate(4.0) == pytest.approx(0.03)


def test_validate_rate_rejects_non_finite_values() -> None:
    curve = _FlatZeroCurve(
        CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
        ),
        rate=math.inf,
    )

    with pytest.raises(InvalidCurveInput, match="must be finite"):
        curve.validate_rate(1.0)


def test_step3_public_split_is_exported() -> None:
    assert issubclass(DiscountingCurve, RatesTermStructure)
    assert issubclass(YieldCurve, DiscountingCurve)
    assert issubclass(RelativeRateCurve, RatesTermStructure)


def test_substep_d3_yield_curve_is_concrete_over_one_kernel() -> None:
    report = CalibrationReport()
    curve = YieldCurve(
        spec=CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
        ),
        kernel=_FlatKernel(zero_rate=0.04, max_t=10.0),
        calibration_report=report,
    )

    assert curve.rate_space is RateSpace.ZERO
    assert curve.max_t() == pytest.approx(10.0)
    assert curve.calibration_report is report
    assert curve.rate_at(5.0) == pytest.approx(0.04)
    assert curve.zero_rate_at(5.0) == pytest.approx(0.04)
    assert curve.forward_rate_between(2.0, 7.0) == pytest.approx(0.04)
    assert curve.discount_factor_at(5.0) == pytest.approx(exp(-0.04 * 5.0))


def test_substep_d3_yield_curve_zero_view_requires_positive_tenor() -> None:
    curve = YieldCurve(
        spec=CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
        ),
        kernel=_FlatKernel(),
    )

    with pytest.raises(InvalidCurveInput, match="tenor must be finite and > 0"):
        curve.rate_at(0.0)


def test_substep_d3_yield_curve_rejects_invalid_kernel() -> None:
    with pytest.raises(InvalidCurveInput, match="kernel must be a CurveKernel"):
        YieldCurve(
            spec=CurveSpec(
                name="Broken",
                reference_date=Date.parse("2026-04-09"),
                day_count="ACT_365_FIXED",
                currency=Currency.USD,
                type=CurveType.NOMINAL,
            ),
            kernel=object(),  # type: ignore[arg-type]
        )


def test_substep_d3_yield_curve_rejects_invalid_report() -> None:
    with pytest.raises(InvalidCurveInput, match="calibration_report must be a CalibrationReport"):
        YieldCurve(
            spec=CurveSpec(
                name="Broken",
                reference_date=Date.parse("2026-04-09"),
                day_count="ACT_365_FIXED",
                currency=Currency.USD,
                type=CurveType.NOMINAL,
            ),
            kernel=_FlatKernel(),
            calibration_report=object(),  # type: ignore[arg-type]
        )


def test_substep_d8_yield_curve_fit_builds_bootstrap_spline_curve_from_one_public_entry_point() -> None:
    curve = YieldCurve.fit(
        quotes=[
            _swap_quote(tenor, zero_rate)
            for tenor, zero_rate in (("1Y", 0.025), ("2Y", 0.03), ("5Y", 0.035))
        ],
        spec=_curve_spec(extrapolation_policy=ExtrapolationPolicy.HOLD_LAST_ZERO_RATE),
        kernel_spec=KernelSpec(kind=CurveKernelKind.CUBIC_SPLINE),
    )

    assert isinstance(curve, YieldCurve)
    assert curve.rate_at(1.0) == pytest.approx(0.025)
    assert math.isfinite(curve.rate_at(3.0))
    assert curve.calibration_report is not None
    assert curve.calibration_report.max_abs_residual == pytest.approx(0.0)


def test_substep_d8_yield_curve_fit_builds_parametric_curve_from_same_public_entry_point() -> None:
    true_parameters = (0.035, -0.01, 0.02, 2.5)
    tenors = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)

    curve = YieldCurve.fit(
        quotes=[
            _swap_quote(f"{tenor:g}Y" if tenor >= 1.0 else "6M", _ns_zero(tenor, *true_parameters), instrument_id=f"{tenor:g}Y")
            for tenor in tenors
        ],
        spec=_curve_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.NELSON_SIEGEL),
    )

    assert isinstance(curve, YieldCurve)
    assert curve.rate_at(4.0) == pytest.approx(_ns_zero(4.0, *true_parameters), abs=1e-10)
    assert curve.calibration_report is not None
    assert curve.calibration_report.converged is True


def test_substep_d8_yield_curve_fit_accepts_bond_quotes_from_same_public_entry_point() -> None:
    true_parameters = (0.035, -0.01, 0.02, 2.5)
    settlement = Date.parse("2026-04-09")
    bond_specs = (
        ("UST1Y", 1, Decimal("0.030")),
        ("UST2Y", 2, Decimal("0.032")),
        ("UST3Y", 3, Decimal("0.034")),
        ("UST5Y", 5, Decimal("0.036")),
    )

    curve = YieldCurve.fit(
        quotes=[
            BondQuote(
                instrument=(
                    bond := _sample_bond(
                        instrument_id,
                        maturity_years=maturity_years,
                        coupon_rate=coupon_rate,
                    )
                ),
                clean_price=_clean_price_from_zero_curve(
                    bond,
                    settlement_date=settlement,
                    zero_rate_fn=lambda tenor: _ns_zero(tenor, *true_parameters),
                ),
                as_of=settlement,
            )
            for instrument_id, maturity_years, coupon_rate in bond_specs
        ],
        spec=_curve_spec(),
        kernel_spec=KernelSpec(kind=CurveKernelKind.NELSON_SIEGEL),
    )

    assert isinstance(curve, YieldCurve)
    assert curve.rate_at(4.0) == pytest.approx(_ns_zero(4.0, *true_parameters), abs=2e-7)
    assert curve.calibration_report is not None
    assert curve.calibration_report.converged is True
    assert curve.calibration_report.points[0].observed_kind == "BOND_CLEAN_PRICE_TO_YTM_SEMI_ANNUAL"


def test_substep_d8_yield_curve_fit_builds_exponential_spline_curve_from_same_public_entry_point() -> None:
    true_coefficients = (0.031, -0.007, 0.004)
    decay_factors = (0.40, 1.20)
    tenors = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)

    curve = YieldCurve.fit(
        quotes=[
            _swap_quote(
                f"{tenor:g}Y" if tenor >= 1.0 else "6M",
                _exp_spline_zero(tenor, true_coefficients, decay_factors),
                instrument_id=f"{tenor:g}Y",
            )
            for tenor in tenors
        ],
        spec=_curve_spec(),
        kernel_spec=KernelSpec(
            kind=CurveKernelKind.EXPONENTIAL_SPLINE,
            parameters={"decay_factors": decay_factors},
        ),
    )

    assert isinstance(curve, YieldCurve)
    assert curve.rate_at(4.0) == pytest.approx(
        _exp_spline_zero(4.0, true_coefficients, decay_factors),
        abs=1e-10,
    )
    assert curve.calibration_report is not None
    assert curve.calibration_report.converged is True


def test_substep_d8_yield_curve_fit_validates_construction_inputs() -> None:
    with pytest.raises(InvalidCurveInput, match="kernel_spec must be a KernelSpec"):
        YieldCurve.fit(
            quotes=[],
            spec=_curve_spec(),
            kernel_spec=object(),  # type: ignore[arg-type]
        )

    with pytest.raises(InvalidCurveInput, match="requires kernel_spec.parameters\\['decay_factors'\\]"):
        YieldCurve.fit(
            quotes=[_swap_quote("1Y", 0.03)],
            spec=_curve_spec(),
            kernel_spec=KernelSpec(kind=CurveKernelKind.EXPONENTIAL_SPLINE),
        )


def test_substep_d3_yield_curve_rejects_invalid_discount_factor_inputs() -> None:
    class _BrokenKernel(CurveKernel):
        def max_t(self) -> float:
            return 5.0

        def rate_at(self, tenor: float) -> float:
            return 0.01

        def discount_factor_at(self, tenor: float) -> float:
            return 0.0

    curve = YieldCurve(
        spec=CurveSpec(
            name="Broken",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
        ),
        kernel=_BrokenKernel(),
    )

    with pytest.raises(InvalidCurveInput, match="discount_factor_at"):
        curve.zero_rate_at(1.0)


def test_discounting_curve_rejects_invalid_forward_interval() -> None:
    curve = YieldCurve(
        spec=CurveSpec(
            name="USD Nominal",
            reference_date=Date.parse("2026-04-09"),
            day_count="ACT_365_FIXED",
            currency=Currency.USD,
            type=CurveType.NOMINAL,
        ),
        kernel=_FlatKernel(),
    )

    with pytest.raises(InvalidCurveInput, match="end_tenor must be greater"):
        curve.forward_rate_between(2.0, 2.0)


def test_substep_d2_kernel_family_enum_is_available() -> None:
    assert CurveKernelKind.LINEAR_ZERO.name == "LINEAR_ZERO"
    assert CurveKernelKind.CUBIC_SPLINE.name == "CUBIC_SPLINE"


def test_substep_d2_kernel_spec_freezes_parameters() -> None:
    spec = KernelSpec(
        kind=CurveKernelKind.CUBIC_SPLINE_ZERO,
        parameters={
            "knot_tenors": [1.0, 2.0, 5.0],
            "solver": {"name": "ols"},
        },
    )

    assert spec.parameters["knot_tenors"] == (1.0, 2.0, 5.0)
    assert spec.parameters["solver"]["name"] == "ols"

    with pytest.raises(TypeError):
        spec.parameters["new_key"] = "blocked"  # type: ignore[index]


def test_substep_d2_kernel_spec_rejects_invalid_kind() -> None:
    with pytest.raises(InvalidCurveInput, match="CurveKernelKind"):
        KernelSpec(kind="LINEAR_ZERO")  # type: ignore[arg-type]


def test_substep_d2_kernel_spec_rejects_non_string_parameter_keys() -> None:
    with pytest.raises(InvalidCurveInput, match="keys must be strings"):
        KernelSpec(
            kind=CurveKernelKind.LINEAR_ZERO,
            parameters={1: "bad-key"},  # type: ignore[dict-item]
        )


def test_substep_d2_curve_kernel_contract_can_be_implemented() -> None:
    class _LocalFlatKernel(CurveKernel):
        def max_t(self) -> float:
            return 20.0

        def rate_at(self, tenor: float) -> float:
            return 0.035

    kernel = _LocalFlatKernel()

    assert kernel.max_t() == pytest.approx(20.0)
    assert kernel.rate_at(5.0) == pytest.approx(0.035)
    assert kernel.discount_factor_at(5.0) == pytest.approx(exp(-0.035 * 5.0))


@pytest.mark.parametrize(
    "module_name",
    [
        "fuggers_py.market.curves.rates.reports",
        "fuggers_py.market.curves.rates.kernels",
        "fuggers_py.market.curves.rates.kernels.base",
        "fuggers_py.market.curves.rates.kernels.nodes",
        "fuggers_py.market.curves.rates.kernels.parametric",
        "fuggers_py.market.curves.rates.kernels.spline",
        "fuggers_py.market.curves.rates.kernels.composite",
        "fuggers_py.market.curves.rates.kernels.decorators",
        "fuggers_py.market.curves.rates.calibrators",
        "fuggers_py.market.curves.rates.calibrators.base",
        "fuggers_py.market.curves.rates.calibrators.bootstrap",
        "fuggers_py.market.curves.rates.calibrators.parametric",
        "fuggers_py.market.curves.rates.calibrators.bonds",
    ],
)
def test_substep_d1_internal_discounting_structure_imports(module_name: str) -> None:
    assert importlib.import_module(module_name).__name__ == module_name
