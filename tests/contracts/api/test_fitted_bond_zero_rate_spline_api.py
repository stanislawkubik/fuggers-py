from __future__ import annotations

import pytest

import fuggers_py.curves as curves


@pytest.mark.feature_slug("fitted-bond-zero-rate-spline")
@pytest.mark.feature_category("api_contract")
def test_zero_rate_spline_shape_names_are_not_part_of_the_current_public_curve_story() -> None:
    removed_names = (
        "CubicSplineZeroRateCurve",
        "CubicSplineZeroRateCurveModel",
        "FittedBondCurveFamily",
    )

    for name in removed_names:
        assert not hasattr(curves, name)
