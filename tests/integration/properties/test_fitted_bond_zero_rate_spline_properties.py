from __future__ import annotations

import math
from decimal import Decimal
from typing import cast

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from fuggers_py.core import Date
from fuggers_py.market.curves import CubicSplineZeroRateCurve, CubicSplineZeroRateCurveModel


PROPERTY_SETTINGS = settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


def _build_curve(zero_rates: tuple[float, ...]) -> CubicSplineZeroRateCurve:
    model = CubicSplineZeroRateCurveModel(
        knot_tenors=(Decimal("1.0"), Decimal("3.0"), Decimal("5.0"), Decimal("7.0")),
    )
    return cast(
        CubicSplineZeroRateCurve,
        model.build_term_structure(
            Date.from_ymd(2026, 1, 15),
            parameters=np.asarray(zero_rates, dtype=float),
            max_t=7.0,
        ),
    )


@PROPERTY_SETTINGS
@given(
    zero_rates=st.tuples(
        st.floats(min_value=-0.03, max_value=0.05, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-0.02, max_value=0.055, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-0.01, max_value=0.06, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=0.065, allow_nan=False, allow_infinity=False),
    ),
    tenor=st.floats(min_value=0.05, max_value=6.95, allow_nan=False, allow_infinity=False),
)
@pytest.mark.feature_slug("fitted-bond-zero-rate-spline")
@pytest.mark.feature_category("properties")
def test_zero_rate_spline_discount_factor_identity_holds_across_parameter_sets(
    zero_rates: tuple[float, float, float, float],
    tenor: float,
) -> None:
    curve = _build_curve(zero_rates)
    zero_rate = curve.zero_rate_at_tenor(tenor)

    assert curve.discount_factor_at_tenor(tenor) == pytest.approx(
        math.exp(-tenor * zero_rate),
        rel=1e-11,
        abs=1e-11,
    )


@PROPERTY_SETTINGS
@given(
    zero_rates=st.tuples(
        st.floats(min_value=-0.03, max_value=0.05, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-0.02, max_value=0.055, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-0.01, max_value=0.06, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=0.065, allow_nan=False, allow_infinity=False),
    ),
    knot=st.sampled_from((1.0, 3.0, 5.0)),
)
@pytest.mark.feature_slug("fitted-bond-zero-rate-spline")
@pytest.mark.feature_category("properties")
def test_zero_rate_spline_remains_continuous_around_interior_knots(
    zero_rates: tuple[float, float, float, float],
    knot: float,
) -> None:
    curve = _build_curve(zero_rates)
    epsilon = 1e-6

    assert curve.zero_rate_at_tenor(knot - epsilon) == pytest.approx(
        curve.zero_rate_at_tenor(knot + epsilon),
        abs=1e-5,
    )
