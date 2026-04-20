from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._curves_impl import (
    BondCurveFitter,
    BondFairValueRequest,
)
from fuggers_py._curves_impl.fitted_bonds.fair_value import fair_value_from_fit

from tests.helpers._fitted_bond_helpers import (
    exponential_model,
    liquidity_regression_exposures,
    make_curve_observations,
    nominal_bond_lookup,
    nominal_fit_kwargs,
    nominal_reference_data_lookup,
    observation_regression_exposures,
)


@pytest.mark.feature_slug("fitted-bond-optimizer-adapters-regressors")
@pytest.mark.feature_category("unit")
def test_new_fit_api_runs_with_zero_regressors() -> None:
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


@pytest.mark.feature_slug("fitted-bond-optimizer-adapters-regressors")
@pytest.mark.feature_category("unit")
def test_new_fit_api_recovers_one_custom_regressor_and_reports_price_and_bp_residuals() -> None:
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
    point = result.get_bond("UST6Y")

    assert result.diagnostics.converged is True
    assert float(result.coefficient_map()["liquidity"]) == pytest.approx(0.25, abs=1e-5)
    assert abs(point["price_residual"]) < Decimal("0.00001")
    assert abs(point["bp_residual"]) < Decimal("0.001")
    assert result.diagnostics.max_abs_bp_residual >= Decimal(0)


@pytest.mark.feature_slug("fitted-bond-optimizer-adapters-regressors")
@pytest.mark.feature_category("unit")
def test_fair_value_from_fit_uses_pricing_adapter_and_regressor_context() -> None:
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
    quote = observations[4]
    bond = nominal_bond_lookup()[quote.instrument_id.as_str()]
    reference_data = nominal_reference_data_lookup()[quote.instrument_id.as_str()]
    assert quote.as_of is not None
    point = result.get_bond(quote.instrument_id)

    fair_value = fair_value_from_fit(
        result,
        BondFairValueRequest(
            bond=bond,
            settlement_date=quote.as_of,
            instrument_id=quote.instrument_id,
            reference_data=reference_data,
            quote=quote,
            regression_exposures=observation_regression_exposures(quote),
        ),
    )

    assert float(fair_value.regression_adjustment) == pytest.approx(float(point["regression_adjustment"]), abs=1e-6)
    assert float(fair_value.fair_value_dirty_price) == pytest.approx(float(point["fitted_dirty_price"]), abs=1e-6)
    assert float(fair_value.fair_value_clean_price) == pytest.approx(float(point["fitted_clean_price"]), abs=1e-6)
