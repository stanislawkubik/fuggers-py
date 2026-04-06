from __future__ import annotations

from decimal import Decimal
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from fuggers_py.market.curves import FittedBondCurveFitter

from tests.helpers._fitted_bond_helpers import (
    exponential_model,
    liquidity_regression_exposures,
    make_curve_observations,
    nominal_fit_kwargs,
)


PROPERTY_SETTINGS = settings(
    max_examples=8,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

@PROPERTY_SETTINGS
@given(regression_bps=st.integers(min_value=-30, max_value=30))
@pytest.mark.feature_slug("fitted-bond-optional-regressors")
@pytest.mark.feature_category("properties")
def test_callable_regressor_recovers_synthetic_overlay_across_coefficients(regression_bps: int) -> None:
    coefficient = Decimal(regression_bps) / Decimal("100")
    observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=coefficient,
    )

    result = FittedBondCurveFitter(
        curve_model=exponential_model(),
    ).fit(
        observations,
        regression_exposures=liquidity_regression_exposures(observations),
        **nominal_fit_kwargs(),
    )

    assert result.diagnostics.converged is True
    assert float(result.coefficient_map()["liquidity"]) == pytest.approx(float(coefficient), abs=1e-5)
