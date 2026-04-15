from __future__ import annotations

from fuggers_py.core import Date
import fuggers_py.market.curves as curves
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


def test_curves_root_exports_only_the_current_public_surface() -> None:
    expected_exports = [
        "CurveSpec",
        "CurveType",
        "DiscountingCurve",
        "ExtrapolationPolicy",
        "RateSpace",
        "RatesTermStructure",
        "RelativeRateCurve",
        "YieldCurve",
    ]

    assert curves.__all__ == expected_exports, "market.curves should expose only the current rates surface."


def test_curves_root_reexports_current_rates_types() -> None:
    assert CurveSpec is curves.CurveSpec, "CurveSpec should be re-exported from market.curves."
    assert CurveType is curves.CurveType, "CurveType should be re-exported from market.curves."
    assert ExtrapolationPolicy is curves.ExtrapolationPolicy, (
        "ExtrapolationPolicy should be re-exported from market.curves."
    )
    assert RateSpace is curves.RateSpace, "RateSpace should be re-exported from market.curves."
    assert RatesTermStructure is curves.RatesTermStructure, (
        "RatesTermStructure should be re-exported from market.curves."
    )
    assert DiscountingCurve is curves.DiscountingCurve, "DiscountingCurve should be re-exported from market.curves."
    assert RelativeRateCurve is curves.RelativeRateCurve, "RelativeRateCurve should be re-exported from market.curves."
    assert YieldCurve is curves.YieldCurve, "YieldCurve should be re-exported from market.curves."

    assert issubclass(DiscountingCurve, RatesTermStructure), (
        "DiscountingCurve should remain a RatesTermStructure subtype."
    )
    assert issubclass(YieldCurve, DiscountingCurve), "YieldCurve should remain a DiscountingCurve subtype."
    assert issubclass(RelativeRateCurve, RatesTermStructure), (
        "RelativeRateCurve should remain a RatesTermStructure subtype."
    )


def test_curves_root_does_not_reexport_removed_legacy_symbols() -> None:
    legacy_names = [
        "Compounding",
        "CubicSpline",
        "CurveError",
        "DiscountCurveBuilder",
        "Interpolator",
        "JumpDiffusionCurve",
        "LinearInterpolator",
        "LogLinearInterpolator",
        "MonotoneConvex",
        "NelsonSiegel",
        "ShadowRateCurve",
        "Svensson",
        "TermStructure",
        "Tenor",
        "ZeroCurveBuilder",
    ]

    for name in legacy_names:
        assert not hasattr(curves, name), f"market.curves should not re-export legacy symbol {name}."


def test_curve_spec_can_be_built_from_root_exports() -> None:
    reference_date = Date.from_ymd(2024, 1, 1)
    spec = CurveSpec(
        name="USD OIS",
        reference_date=reference_date,
        day_count="act/365f",
        currency="usd",
        type=CurveType.OVERNIGHT_DISCOUNT,
        extrapolation_policy=ExtrapolationPolicy.ERROR,
    )

    assert spec.name == "USD OIS"
    assert spec.reference_date == reference_date
    assert spec.day_count == "ACT/365F"
    assert spec.currency.code() == "USD"
    assert spec.type is CurveType.OVERNIGHT_DISCOUNT
    assert spec.extrapolation_policy is ExtrapolationPolicy.ERROR
    assert YieldCurve.__name__ == "YieldCurve"
    assert RateSpace.ZERO.name == "ZERO"
