from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.market.curves import (
    BondCurve,
    BondCurveFitter,
    BondFairValueRequest,
    CurveObjective,
    clean_price_from_curve,
    fair_value_from_curve,
    fair_value_from_fit,
)

from tests.helpers._fitted_bond_helpers import (
    cubic_model,
    exponential_model,
    fit_result,
    make_observations,
    liquidity_regression_exposures,
    nominal_bond_lookup,
    nominal_fit_kwargs,
    observation_regression_exposures,
)


def test_exponential_spline_fitted_curve_recovers_prices_yields_and_regression_coefficients() -> None:
    result = fit_result(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.35"),
    )

    assert result.diagnostics.converged is True
    assert float(result.diagnostics.weighted_rmse_price) == pytest.approx(0.0, abs=1e-6)
    assert float(result.coefficient_map()["liquidity"]) == pytest.approx(0.35, abs=1e-5)
    point = result.get_bond("UST6Y")
    assert float(point["fitted_dirty_price"]) == pytest.approx(float(point["observed_dirty_price"]), abs=1e-6)
    assert float(point["fitted_yield"]) == pytest.approx(float(point["observed_yield"]), abs=1e-8)


def test_cubic_spline_zero_rate_fit_matches_a_synthetic_cross_section() -> None:
    observations, _ = make_observations(curve_model=cubic_model(), regression_coefficient=Decimal("0.10"))
    result = BondCurve(
        observations,
        shape=cubic_model(),
        objective=CurveObjective.L2,
        regressors=liquidity_regression_exposures(observations),
        **nominal_fit_kwargs(),
    )

    assert result.diagnostics.converged is True
    assert float(result.diagnostics.weighted_rmse_price) == pytest.approx(0.0, abs=1e-6)
    assert len(result.parameter_names) == 5
    assert float(result.coefficient_map()["liquidity"]) == pytest.approx(0.10, abs=1e-5)


def test_l1_fit_path_runs_and_returns_stable_residual_outputs() -> None:
    result = fit_result(
        curve_model=exponential_model(),
        objective=CurveObjective.L1,
        regression_coefficient=Decimal("0.20"),
    )

    assert result.objective is CurveObjective.L1
    assert result.diagnostics.converged is True
    assert result.diagnostics.max_abs_price_residual < Decimal("0.001")


def test_fitted_bond_helper_exports_support_design_matrix_and_fair_value_workflows() -> None:
    observations, curve = make_observations(regression_coefficient=Decimal("0.25"))
    quote = observations[4]
    bond = nominal_bond_lookup()[quote.instrument_id.as_str()]
    assert quote.as_of is not None
    curve_value = fair_value_from_curve(bond, curve, quote.as_of)
    fitted = fit_result(regression_coefficient=Decimal("0.25"))
    fair_value = fair_value_from_fit(
        fitted,
        BondFairValueRequest(
            bond=bond,
            settlement_date=quote.as_of,
            instrument_id=quote.instrument_id,
            regression_exposures=observation_regression_exposures(quote),
        ),
    )

    assert clean_price_from_curve(bond, curve, quote.as_of) == curve_value.curve_clean_price
    assert fair_value.instrument_id == quote.instrument_id
    assert fair_value.regression_adjustment != Decimal(0)
