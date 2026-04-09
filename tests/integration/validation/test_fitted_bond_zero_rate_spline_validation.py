from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.market.curves import BondCurveFitter

from tests.helpers._fitted_bond_helpers import cubic_model, liquidity_regression_exposures, make_observations, nominal_fit_kwargs


@pytest.mark.feature_slug("fitted-bond-zero-rate-spline")
@pytest.mark.feature_category("validation")
def test_zero_rate_cubic_spline_fit_matches_a_synthetic_cross_section() -> None:
    observations, _ = make_observations(
        curve_model=cubic_model(),
        regression_coefficient=Decimal("0.12"),
    )

    result = BondCurveFitter(
        curve_model=cubic_model(),
    ).fit(
        observations,
        regression_exposures=liquidity_regression_exposures(observations),
        **nominal_fit_kwargs(),
    )

    assert result.diagnostics.converged is True
    assert float(result.diagnostics.weighted_rmse_price) == pytest.approx(0.0, abs=1e-6)
    assert float(result.coefficient_map()["liquidity"]) == pytest.approx(0.12, abs=1e-5)
