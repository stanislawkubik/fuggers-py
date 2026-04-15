from __future__ import annotations

from fuggers_py.core import Date
import fuggers_py.market.curves.rates as rates
from fuggers_py.market.quotes import SwapQuote
from fuggers_py.market.curves.rates import (
    BondFitTarget,
    CalibrationMode,
    CalibrationObjective,
    CalibrationReport,
    CalibrationSpec,
    CurveKernel,
    CurveKernelKind,
    CurveSpec,
    CurveType,
    DiscountingCurve,
    ExtrapolationPolicy,
    GlobalFitOptimizerKind,
    GlobalFitReport,
    KernelSpec,
    RateSpace,
    RatesTermStructure,
    RelativeRateCurve,
    YieldCurve,
)


class _FlatKernel(CurveKernel):
    def __init__(self, *, zero_rate: float = 0.03, max_t: float = 5.0) -> None:
        self._zero_rate = zero_rate
        self._max_t = max_t

    def max_t(self) -> float:
        return self._max_t

    def rate_at(self, tenor: float) -> float:
        return self._zero_rate


def test_curves_rates_exports_the_public_construction_surface() -> None:
    expected_exports = [
        "BondFitTarget",
        "CalibrationMode",
        "CalibrationObjective",
        "CalibrationPoint",
        "CalibrationReport",
        "CurveSpec",
        "CurveKernel",
        "CurveKernelKind",
        "CurveType",
        "CalibrationSpec",
        "DiscountingCurve",
        "ExtrapolationPolicy",
        "GlobalFitPoint",
        "GlobalFitOptimizerKind",
        "GlobalFitReport",
        "KernelSpec",
        "RateSpace",
        "RatesTermStructure",
        "RelativeRateCurve",
        "YieldCurve",
    ]

    assert rates.__all__ == expected_exports, "market.curves.rates should export the full public rates surface."


def test_curves_rates_reexports_construction_and_report_types() -> None:
    assert CurveSpec is rates.CurveSpec
    assert CurveKernelKind is rates.CurveKernelKind
    assert KernelSpec is rates.KernelSpec
    assert CalibrationMode is rates.CalibrationMode
    assert CalibrationObjective is rates.CalibrationObjective
    assert BondFitTarget is rates.BondFitTarget
    assert CalibrationSpec is rates.CalibrationSpec
    assert GlobalFitOptimizerKind is rates.GlobalFitOptimizerKind
    assert CalibrationReport is rates.CalibrationReport
    assert GlobalFitReport is rates.GlobalFitReport
    assert issubclass(DiscountingCurve, RatesTermStructure)
    assert issubclass(YieldCurve, DiscountingCurve)
    assert issubclass(RelativeRateCurve, RatesTermStructure)


def test_yield_curve_fit_can_be_called_from_the_rates_public_surface() -> None:
    reference_date = Date.from_ymd(2026, 4, 9)
    curve = YieldCurve.fit(
        quotes=[
            SwapQuote(instrument_id="1Y", tenor="1Y", rate=0.025, currency="USD", as_of=reference_date),
            SwapQuote(instrument_id="2Y", tenor="2Y", rate=0.03, currency="USD", as_of=reference_date),
            SwapQuote(instrument_id="5Y", tenor="5Y", rate=0.035, currency="USD", as_of=reference_date),
        ],
        spec=CurveSpec(
            name="USD OIS",
            reference_date=reference_date,
            day_count="ACT/365F",
            currency="usd",
            type=CurveType.OVERNIGHT_DISCOUNT,
            extrapolation_policy=ExtrapolationPolicy.HOLD_LAST_ZERO_RATE,
        ),
        kernel_spec=KernelSpec(
            kind=CurveKernelKind.CUBIC_SPLINE,
            parameters={"knots": (1.0, 2.0, 5.0)},
        ),
        calibration_spec=CalibrationSpec(
            mode=CalibrationMode.GLOBAL_FIT,
            objective=CalibrationObjective.WEIGHTED_L2,
            bond_fit_target=BondFitTarget.DIRTY_PRICE,
        ),
    )

    assert isinstance(curve, YieldCurve)
    assert curve.rate_at(1.0) == 0.025
    assert curve.rate_at(2.0) == 0.03
    assert curve.rate_at(5.0) == 0.035
    assert curve.calibration_report is not None
    assert isinstance(curve.calibration_report, CalibrationReport)


def test_yield_curve_manual_constructor_can_be_used_from_the_rates_public_surface() -> None:
    reference_date = Date.from_ymd(2026, 4, 9)
    report = CalibrationReport(objective="EXACT_FIT")
    curve = YieldCurve(
        spec=CurveSpec(
            name="USD OIS",
            reference_date=reference_date,
            day_count="ACT/365F",
            currency="usd",
            type=CurveType.OVERNIGHT_DISCOUNT,
            extrapolation_policy=ExtrapolationPolicy.ERROR,
        ),
        kernel=_FlatKernel(zero_rate=0.031, max_t=10.0),
        calibration_report=report,
    )

    assert curve.rate_space is RateSpace.ZERO
    assert curve.rate_at(1.0) == 0.031
    assert curve.calibration_report is report
