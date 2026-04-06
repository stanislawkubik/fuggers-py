from __future__ import annotations

import pytest

from fuggers_py.market import curves as market_curves
from fuggers_py.market.curves import (
    CubicSplineZeroRateCurve,
    CubicSplineZeroRateCurveModel,
    FittedBondCurveFamily,
)
from fuggers_py.market.curves import fitted_bonds


@pytest.mark.feature_slug("fitted-bond-zero-rate-spline")
@pytest.mark.feature_category("api_contract")
def test_public_exports_expose_the_zero_rate_spline_surface() -> None:
    assert market_curves.CubicSplineZeroRateCurve is CubicSplineZeroRateCurve
    assert market_curves.CubicSplineZeroRateCurveModel is CubicSplineZeroRateCurveModel
    assert market_curves.FittedBondCurveFamily.CUBIC_SPLINE_ZERO_RATE is FittedBondCurveFamily.CUBIC_SPLINE_ZERO_RATE
    assert fitted_bonds.CubicSplineZeroRateCurve is CubicSplineZeroRateCurve
    assert fitted_bonds.CubicSplineZeroRateCurveModel is CubicSplineZeroRateCurveModel
