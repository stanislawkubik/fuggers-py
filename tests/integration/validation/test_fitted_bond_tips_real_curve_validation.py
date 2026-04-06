from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.market.curves import FittedBondCurveFitter, FittedBondObjective

from tests.helpers._fitted_bond_helpers import (
    cubic_model,
    exponential_model,
    liquidity_regression_exposures,
    make_tips_curve_observations,
    tips_fit_kwargs,
    tips_pricing_adapter,
)


@pytest.mark.feature_slug("fitted-bond-tips-real-curve")
@pytest.mark.feature_category("validation")
def test_tips_real_l2_fit_recovers_the_callable_overlay() -> None:
    observations, _, fixing_source = make_tips_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.14"),
    )

    result = FittedBondCurveFitter(
        curve_model=exponential_model(),
        pricing_adapter=tips_pricing_adapter(fixing_source),
        objective=FittedBondObjective.L2,
    ).fit(
        observations,
        regression_exposures=liquidity_regression_exposures(observations),
        **tips_fit_kwargs(),
    )

    assert result.diagnostics.converged is True
    assert float(result.coefficient_map()["liquidity"]) == pytest.approx(0.14, abs=1e-5)
    assert float(result.diagnostics.weighted_rmse_price) == pytest.approx(0.0, abs=1e-6)
    assert result.diagnostics.max_abs_bp_residual >= Decimal(0)


@pytest.mark.feature_slug("fitted-bond-tips-real-curve")
@pytest.mark.feature_category("validation")
def test_tips_real_l1_fit_runs_cleanly_without_regressors() -> None:
    observations, _, fixing_source = make_tips_curve_observations(
        curve_model=cubic_model(),
        regression_coefficient=Decimal("0"),
    )
    result = FittedBondCurveFitter(
        curve_model=cubic_model(),
        pricing_adapter=tips_pricing_adapter(fixing_source),
        objective=FittedBondObjective.L1,
    ).fit(observations, regression_exposures={}, **tips_fit_kwargs())

    assert result.diagnostics.converged is True
    assert result.coefficients == {}
    assert float(result.diagnostics.weighted_rmse_price) == pytest.approx(0.0, abs=1e-6)
    assert result.diagnostics.max_abs_bp_residual >= Decimal(0)
