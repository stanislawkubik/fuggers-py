from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from fuggers_py._curves_impl import BondCurveFitter, CurveObjective

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
@pytest.mark.feature_slug("fitted-bond-optimizer-adapters-regressors")
@pytest.mark.feature_category("properties")
def test_profiled_l2_recovers_callable_regression_coefficients(regression_bps: int) -> None:
    coefficient = Decimal(regression_bps) / Decimal("100")
    observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=coefficient,
    )

    result = BondCurveFitter(
        curve_model=exponential_model(),
        objective=CurveObjective.L2,
    ).fit(
        observations,
        regression_exposures=liquidity_regression_exposures(observations),
        **nominal_fit_kwargs(),
    )

    assert result.diagnostics.converged is True
    assert float(result.coefficient_map()["liquidity"]) == pytest.approx(float(coefficient), abs=1e-5)


@PROPERTY_SETTINGS
@given(objective=st.sampled_from((CurveObjective.L2, CurveObjective.L1)))
@pytest.mark.feature_slug("fitted-bond-optimizer-adapters-regressors")
@pytest.mark.feature_category("properties")
def test_profiled_fit_with_zero_regressors_keeps_an_empty_coefficient_surface(
    objective: CurveObjective,
) -> None:
    observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0"),
    )

    result = BondCurveFitter(
        curve_model=exponential_model(),
        objective=objective,
    ).fit(observations, regression_exposures={}, **nominal_fit_kwargs())

    assert result.diagnostics.converged is True
    assert result.coefficients == {}
    assert result.diagnostics.max_abs_bp_residual >= Decimal(0)
