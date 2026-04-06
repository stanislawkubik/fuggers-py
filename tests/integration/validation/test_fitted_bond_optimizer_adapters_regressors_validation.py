from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.market.curves import FittedBondCurveFitter, FittedBondObjective

from tests.helpers._fitted_bond_helpers import (
    exponential_model,
    liquidity_regression_exposures,
    make_curve_observations,
    nominal_fit_kwargs,
)


@pytest.mark.feature_slug("fitted-bond-optimizer-adapters-regressors")
@pytest.mark.feature_category("validation")
def test_l2_and_l1_profiled_regression_paths_recover_the_same_clean_synthetic_overlay() -> None:
    observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.20"),
    )

    l2_result = FittedBondCurveFitter(
        curve_model=exponential_model(),
        objective=FittedBondObjective.L2,
    ).fit(
        observations,
        regression_exposures=liquidity_regression_exposures(observations),
        **nominal_fit_kwargs(),
    )
    l1_result = FittedBondCurveFitter(
        curve_model=exponential_model(),
        objective=FittedBondObjective.L1,
    ).fit(
        observations,
        regression_exposures=liquidity_regression_exposures(observations),
        **nominal_fit_kwargs(),
    )

    assert l2_result.diagnostics.converged is True
    assert l1_result.diagnostics.converged is True
    assert float(l2_result.coefficient_map()["liquidity"]) == pytest.approx(0.20, abs=1e-5)
    assert float(l1_result.coefficient_map()["liquidity"]) == pytest.approx(0.20, abs=1e-5)
    assert float(l2_result.diagnostics.weighted_rmse_price) == pytest.approx(0.0, abs=1e-6)
    assert float(l1_result.diagnostics.weighted_rmse_price) == pytest.approx(0.0, abs=1e-6)
