from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._curves_impl import BondCurveFitter

from tests.helpers._fitted_bond_helpers import (
    exponential_model,
    liquidity_regression_exposures,
    make_curve_observations,
    nominal_fit_kwargs,
)


@pytest.mark.feature_slug("fitted-bond-optional-regressors")
@pytest.mark.feature_category("unit")
def test_fit_runs_with_zero_regressors_on_new_observations() -> None:
    observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0"),
    )

    result = BondCurveFitter(
        curve_model=exponential_model(),
    ).fit(observations, regression_exposures={}, **nominal_fit_kwargs())

    assert result.diagnostics.converged is True
    assert result.coefficients == {}
    assert float(result.diagnostics.weighted_rmse_price) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.feature_slug("fitted-bond-optional-regressors")
@pytest.mark.feature_category("unit")
def test_callable_regressor_is_included_for_new_observations() -> None:
    observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.25"),
    )

    result = BondCurveFitter(
        curve_model=exponential_model(),
    ).fit(
        observations,
        regression_exposures=liquidity_regression_exposures(observations),
        **nominal_fit_kwargs(),
    )

    assert result.diagnostics.converged is True
    assert float(result.coefficient_map()["liquidity"]) == pytest.approx(0.25, abs=1e-5)


@pytest.mark.feature_slug("fitted-bond-optional-regressors")
@pytest.mark.feature_category("unit")
def test_dirty_price_quotes_run_on_the_same_observation_surface() -> None:
    observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.15"),
        quote_field="dirty",
    )

    result = BondCurveFitter(
        curve_model=exponential_model(),
    ).fit(
        observations,
        regression_exposures=liquidity_regression_exposures(observations),
        **nominal_fit_kwargs(),
    )

    assert result.diagnostics.converged is True
    assert float(result.coefficient_map()["liquidity"]) == pytest.approx(0.15, abs=1e-5)
