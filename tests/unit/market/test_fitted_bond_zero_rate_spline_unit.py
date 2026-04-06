from __future__ import annotations

import math
from decimal import Decimal
from typing import cast

import numpy as np
import pytest

from fuggers_py.core import Date
from fuggers_py.market.curves import (
    CubicSplineZeroRateCurve,
    CubicSplineZeroRateCurveModel,
)
from fuggers_py.market.curves.fitted_bonds._splines import cached_natural_cubic_spline_grid

from tests.helpers._fitted_bond_helpers import cubic_model


@pytest.mark.feature_slug("fitted-bond-zero-rate-spline")
@pytest.mark.feature_category("unit")
def test_zero_rate_spline_supports_negative_front_end_without_discount_factor_clipping() -> None:
    curve = cast(
        CubicSplineZeroRateCurve,
        CubicSplineZeroRateCurveModel(
            knot_tenors=(Decimal("1.0"), Decimal("3.0"), Decimal("7.0")),
        ).build_curve(
            Date.from_ymd(2026, 1, 15),
            parameters=np.asarray([-0.012, 0.006, 0.018], dtype=float),
            max_t=7.0,
        ).curve,
    )

    assert curve.zero_rate_at_tenor(0.25) < 0.0
    assert curve.discount_factor_at_tenor(0.25) > 1.0


@pytest.mark.feature_slug("fitted-bond-zero-rate-spline")
@pytest.mark.feature_category("unit")
def test_zero_rate_spline_discount_factors_match_continuous_compounding_formula() -> None:
    curve = cast(
        CubicSplineZeroRateCurve,
        cubic_model().build_curve(
            Date.from_ymd(2026, 1, 15),
            parameters=np.asarray([0.021, 0.024, 0.028, 0.031, 0.034], dtype=float),
            max_t=10.0,
        ).curve,
    )

    for tenor in (0.5, 1.5, 3.5, 7.5, 9.5):
        zero_rate = curve.zero_rate_at_tenor(tenor)
        assert curve.discount_factor_at_tenor(tenor) == pytest.approx(
            math.exp(-tenor * zero_rate),
            rel=1e-12,
            abs=1e-12,
        )


@pytest.mark.feature_slug("fitted-bond-zero-rate-spline")
@pytest.mark.feature_category("unit")
def test_zero_rate_spline_is_stable_around_interior_knots() -> None:
    curve = cast(
        CubicSplineZeroRateCurve,
        cubic_model().build_curve(
            Date.from_ymd(2026, 1, 15),
            parameters=np.asarray([0.020, 0.023, 0.029, 0.032, 0.035], dtype=float),
            max_t=10.0,
        ).curve,
    )
    knot = 4.0
    epsilon = 1e-6

    left_value = curve.zero_rate_at_tenor(knot - epsilon)
    center_value = curve.zero_rate_at_tenor(knot)
    right_value = curve.zero_rate_at_tenor(knot + epsilon)
    left_slope = cast(float, curve.derivative_at(knot - epsilon))
    right_slope = cast(float, curve.derivative_at(knot + epsilon))

    assert left_value == pytest.approx(center_value, abs=1e-6)
    assert right_value == pytest.approx(center_value, abs=1e-6)
    assert left_slope == pytest.approx(right_slope, abs=1e-5)


@pytest.mark.feature_slug("fitted-bond-zero-rate-spline")
@pytest.mark.feature_category("unit")
def test_cached_zero_rate_spline_grid_is_reused_across_curve_builds() -> None:
    cached_natural_cubic_spline_grid.cache_clear()
    model = cubic_model()
    first = cast(
        CubicSplineZeroRateCurve,
        model.build_curve(
            Date.from_ymd(2026, 1, 15),
            parameters=np.asarray([0.021, 0.024, 0.028, 0.031, 0.034], dtype=float),
            max_t=10.0,
        ).curve,
    )
    second = cast(
        CubicSplineZeroRateCurve,
        model.build_curve(
            Date.from_ymd(2026, 1, 15),
            parameters=np.asarray([0.022, 0.025, 0.029, 0.032, 0.035], dtype=float),
            max_t=10.0,
        ).curve,
    )
    cache_info = cached_natural_cubic_spline_grid.cache_info()

    assert first._spline_grid is second._spline_grid
    assert cache_info.misses == 1
    assert cache_info.hits >= 1

