from __future__ import annotations

import pytest

from fuggers_py import Date
import fuggers_py.curves as curves
from fuggers_py.curves import (
    CalibrationPoint,
    CalibrationReport,
    CurveSpec,
    DiscountingCurve,
    RatesTermStructure,
    STANDARD_KEY_RATE_TENORS,
    YieldCurve,
)
from fuggers_py.curves.kernels.base import CurveKernel
from fuggers_py.rates import SwapQuote


class _FlatKernel(CurveKernel):
    def __init__(self, *, zero_rate: float = 0.03, max_t: float = 5.0) -> None:
        self._zero_rate = zero_rate
        self._max_t = max_t

    def max_t(self) -> float:
        return self._max_t

    def rate_at(self, tenor: float) -> float:
        return self._zero_rate


def test_curves_rates_exports_the_first_layer_curve_surface() -> None:
    assert curves.__all__ == [
        "CurveSpec",
        "YieldCurve",
        "RatesTermStructure",
        "DiscountingCurve",
        "CalibrationReport",
        "CalibrationPoint",
        "STANDARD_KEY_RATE_TENORS",
    ]


def test_curves_rates_reexports_first_layer_types_and_helpers() -> None:
    assert CurveSpec is curves.CurveSpec
    assert YieldCurve is curves.YieldCurve
    assert RatesTermStructure is curves.RatesTermStructure
    assert DiscountingCurve is curves.DiscountingCurve
    assert CalibrationReport is curves.CalibrationReport
    assert CalibrationPoint is curves.CalibrationPoint
    assert STANDARD_KEY_RATE_TENORS is curves.STANDARD_KEY_RATE_TENORS
    assert issubclass(DiscountingCurve, RatesTermStructure)
    assert issubclass(YieldCurve, DiscountingCurve)
    assert CurveSpec.__module__ == "fuggers_py.curves.spec"
    assert YieldCurve.__module__ == "fuggers_py.curves.base"
    assert DiscountingCurve.shifted.__module__ == "fuggers_py.curves.base"
    assert DiscountingCurve.bumped.__module__ == "fuggers_py.curves.base"


def test_curves_rates_root_does_not_export_advanced_fit_controls() -> None:
    removed_names = [
        "BondFitTarget",
        "CalibrationMode",
        "CalibrationObjective",
        "CalibrationSpec",
        "CurveKernel",
        "CurveKernelKind",
        "CurveType",
        "ExtrapolationPolicy",
        "GlobalFitOptimizerKind",
        "GlobalFitPoint",
        "GlobalFitReport",
        "key_rate_bumped_curve",
        "KernelSpec",
        "parallel_bumped_curve",
        "RateSpace",
        "RelativeRateCurve",
    ]

    for name in removed_names:
        assert name not in curves.__all__
        assert not hasattr(curves, name)


def test_yield_curve_fit_can_be_called_from_the_first_layer_surface() -> None:
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
            type="overnight_discount",
            extrapolation_policy="hold_last_zero_rate",
        ),
    )

    assert isinstance(curve, YieldCurve)
    assert curve.rate_at(1.0) == 0.025
    assert curve.rate_at(2.0) == 0.03
    assert curve.rate_at(5.0) == 0.035
    assert isinstance(curve.calibration_report, CalibrationReport)
    assert curve.calibration_report.method == "bootstrap"
    first_point = curve.calibration_report.points[0]
    assert first_point.curve_only_value is None
    assert first_point.regressor_contribution is None


def test_yield_curve_fit_reports_identify_bootstrap_and_global_fit_methods() -> None:
    reference_date = Date.from_ymd(2026, 4, 9)
    quotes = [
        SwapQuote(instrument_id="1Y", tenor="1Y", rate=0.025, currency="USD", as_of=reference_date),
        SwapQuote(instrument_id="2Y", tenor="2Y", rate=0.03, currency="USD", as_of=reference_date),
        SwapQuote(instrument_id="5Y", tenor="5Y", rate=0.035, currency="USD", as_of=reference_date),
    ]
    spec = CurveSpec(
        name="USD OIS",
        reference_date=reference_date,
        day_count="ACT/365F",
        currency="usd",
        type="overnight_discount",
        extrapolation_policy="hold_last_zero_rate",
    )

    bootstrap_curve = YieldCurve.fit(quotes=quotes, spec=spec)
    global_fit_curve = YieldCurve.fit(
        quotes=quotes,
        spec=spec,
        kernel="cubic_spline",
        method="global_fit",
        kernel_params={"knots": (1.0, 2.0, 5.0)},
    )

    assert bootstrap_curve.calibration_report is not None
    assert global_fit_curve.calibration_report is not None
    assert bootstrap_curve.calibration_report.method == "bootstrap"
    assert global_fit_curve.calibration_report.method == "global_fit"
    assert bootstrap_curve.calibration_report.points[0].curve_only_value is None
    assert bootstrap_curve.calibration_report.points[0].regressor_contribution is None
    assert global_fit_curve.calibration_report.points[0].curve_only_value is not None
    assert global_fit_curve.calibration_report.points[0].regressor_contribution is not None


def test_yield_curve_manual_constructor_uses_one_internal_kernel() -> None:
    reference_date = Date.from_ymd(2026, 4, 9)
    report = CalibrationReport(objective="exact_fit")
    curve = YieldCurve(
        spec=CurveSpec(
            name="USD OIS",
            reference_date=reference_date,
            day_count="ACT/365F",
            currency="usd",
            type="overnight_discount",
            extrapolation_policy="error",
        ),
        kernel=_FlatKernel(zero_rate=0.031, max_t=10.0),
        calibration_report=report,
    )

    assert curve.rate_at(1.0) == 0.031
    assert curve.zero_rate_at(1.0) == pytest.approx(0.031)
    assert curve.calibration_report is report
