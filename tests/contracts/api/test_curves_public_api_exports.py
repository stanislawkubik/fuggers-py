from __future__ import annotations

import math
from decimal import Decimal

import pytest

from fuggers_py.core import Date
from fuggers_py.core import Compounding as core_compounding
from fuggers_py.market.curves import (
    Compounding,
    CubicSpline,
    Currency,
    CurveError,
    DiscountCurveBuilder,
    Interpolator,
    LinearInterpolator,
    LogLinearInterpolator,
    MonotoneConvex,
    NelsonSiegel,
    Svensson,
    TermStructure,
    Tenor,
)
from fuggers_py.market.curves import JumpDiffusionCurve, ShadowRateCurve
from fuggers_py.market.curves import ZeroCurveBuilder


def _eval_interpolator(interpolator: Interpolator, x: float) -> float:
    return interpolator.interpolate(x)


def test_curves_root_imports_expose_public_surface() -> None:
    tenor = Tenor.parse("5Y")

    assert Compounding is core_compounding
    assert Currency.USD.code() == "USD"
    assert str(tenor) == "5Y"


def test_discount_curve_builder_returns_term_structure() -> None:
    reference_date = Date.from_ymd(2024, 1, 1)
    curve = (
        DiscountCurveBuilder(reference_date=reference_date)
        .add_pillar(1.0, math.exp(-0.04))
        .add_pillar(2.0, math.exp(-0.08))
        .build()
    )

    assert isinstance(curve, TermStructure)
    assert curve.date() == reference_date
    assert curve.discount_factor(reference_date.add_days(365)) < 1


def test_curves_root_reexports_interpolators_and_parametric_models() -> None:
    linear = LinearInterpolator([1.0, 2.0], [0.01, 0.02])
    log_linear = LogLinearInterpolator([1.0, 2.0], [0.99, 0.95])
    cubic = CubicSpline([1.0, 2.0, 3.0], [0.01, 0.015, 0.02])
    monotone = MonotoneConvex([1.0, 2.0, 3.0], [0.01, 0.015, 0.02])
    nelson_siegel = NelsonSiegel.new(beta0=0.03, beta1=-0.01, beta2=0.02, tau=1.5)
    svensson = Svensson.new(beta0=0.03, beta1=-0.01, beta2=0.02, beta3=0.005, tau1=1.5, tau2=3.0)

    assert _eval_interpolator(linear, 1.5) == pytest.approx(0.015)
    assert _eval_interpolator(log_linear, 1.5) == pytest.approx(math.sqrt(0.99 * 0.95))
    assert _eval_interpolator(cubic, 2.0) == pytest.approx(0.015)
    assert _eval_interpolator(monotone, 2.5) > 0.0
    assert 0.0 < nelson_siegel.interpolate(5.0) < 0.1
    assert 0.0 < svensson.interpolate(5.0) < 0.1


def test_existing_curve_builders_return_term_structures() -> None:
    reference_date = Date.from_ymd(2024, 1, 1)
    curve = (
        DiscountCurveBuilder(reference_date=reference_date)
        .add_zero_rate(1.0, Decimal("0.03"))
        .add_zero_rate(2.0, Decimal("0.035"))
        .build()
    )

    assert isinstance(curve, TermStructure)
    assert float(curve.discount_factor(reference_date.add_days(365))) == pytest.approx(math.exp(-0.03), rel=1e-4)


def test_curves_root_re_exports_optional_advanced_curve_models() -> None:
    reference_date = Date.from_ymd(2024, 1, 1)
    base_curve = (
        DiscountCurveBuilder(reference_date=reference_date)
        .add_zero_rate(1.0, Decimal("0.02"))
        .add_zero_rate(5.0, Decimal("0.03"))
        .build()
    )

    assert ShadowRateCurve(base_curve=base_curve).date() == reference_date
