from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from fuggers_py._curves_impl import BondCurveFitter, CurveObjective

from tests.helpers._fitted_bond_helpers import (
    cubic_model,
    exponential_model,
    liquidity_regression_exposures,
    make_tips_curve_observations,
    tips_fit_kwargs,
    tips_pricing_adapter,
)


PROPERTY_SETTINGS = settings(
    max_examples=8,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


@PROPERTY_SETTINGS
@given(regression_bps=st.integers(min_value=-20, max_value=20))
@pytest.mark.feature_slug("fitted-bond-tips-real-curve")
@pytest.mark.feature_category("properties")
def test_tips_profiled_l2_recovers_callable_regression_coefficients(regression_bps: int) -> None:
    coefficient = Decimal(regression_bps) / Decimal("100")
    observations, _, fixing_source = make_tips_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=coefficient,
    )

    result = BondCurveFitter(
        curve_model=exponential_model(),
        pricing_adapter=tips_pricing_adapter(fixing_source),
        objective=CurveObjective.L2,
    ).fit(
        observations,
        regression_exposures=liquidity_regression_exposures(observations),
        **tips_fit_kwargs(),
    )

    assert result.diagnostics.converged is True
    assert float(result.coefficient_map()["liquidity"]) == pytest.approx(float(coefficient), abs=1e-5)


@PROPERTY_SETTINGS
@given(objective=st.sampled_from((CurveObjective.L2, CurveObjective.L1)))
@pytest.mark.feature_slug("fitted-bond-tips-real-curve")
@pytest.mark.feature_category("properties")
def test_tips_fit_with_zero_regressors_keeps_an_empty_coefficient_surface(
    objective: CurveObjective,
) -> None:
    observations, _, fixing_source = make_tips_curve_observations(
        curve_model=cubic_model(),
        regression_coefficient=Decimal("0"),
    )

    result = BondCurveFitter(
        curve_model=cubic_model(),
        pricing_adapter=tips_pricing_adapter(fixing_source),
        objective=objective,
    ).fit(observations, regression_exposures={}, **tips_fit_kwargs())

    assert result.diagnostics.converged is True
    assert result.coefficients == {}
    assert result.diagnostics.max_abs_bp_residual >= Decimal(0)
