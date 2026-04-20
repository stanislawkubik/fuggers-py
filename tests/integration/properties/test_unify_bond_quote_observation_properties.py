from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from fuggers_py._curves_impl import BondCurveFitter

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
@pytest.mark.feature_slug("unify-bond-quote-observation")
@pytest.mark.feature_category("properties")
def test_clean_and_dirty_quote_fields_are_fit_equivalent(regression_bps: int) -> None:
    coefficient = Decimal(regression_bps) / Decimal("100")
    clean_observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=coefficient,
        quote_field="clean",
    )
    dirty_observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=coefficient,
        quote_field="dirty",
    )

    clean_result = BondCurveFitter(
        curve_model=exponential_model(),
    ).fit(
        clean_observations,
        regression_exposures=liquidity_regression_exposures(clean_observations),
        **nominal_fit_kwargs(),
    )
    dirty_result = BondCurveFitter(
        curve_model=exponential_model(),
    ).fit(
        dirty_observations,
        regression_exposures=liquidity_regression_exposures(dirty_observations),
        **nominal_fit_kwargs(),
    )

    assert float(clean_result.coefficient_map()["liquidity"]) == pytest.approx(float(coefficient), abs=1e-5)
    assert float(clean_result.coefficient_map()["liquidity"]) == pytest.approx(
        float(dirty_result.coefficient_map()["liquidity"]),
        abs=1e-8,
    )
    assert float(clean_result.get_bond("UST8Y")["fitted_yield"]) == pytest.approx(
        float(dirty_result.get_bond("UST8Y")["fitted_yield"]),
        abs=1e-10,
    )
