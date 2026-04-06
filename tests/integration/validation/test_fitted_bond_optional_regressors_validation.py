from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.market.curves import FittedBondCurveFitter

from tests.helpers._fitted_bond_helpers import exponential_model, make_curve_observations, nominal_fit_kwargs


@pytest.mark.feature_slug("fitted-bond-optional-regressors")
@pytest.mark.feature_category("validation")
def test_dirty_price_quotes_fit_cleanly_without_regressors() -> None:
    observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0"),
        quote_field="dirty",
    )

    result = FittedBondCurveFitter(
        curve_model=exponential_model(),
    ).fit(observations, regression_exposures={}, **nominal_fit_kwargs())

    assert result.diagnostics.converged is True
    assert float(result.diagnostics.weighted_rmse_price) == pytest.approx(0.0, abs=1e-6)
    assert all(point["regression_adjustment"] == Decimal(0) for point in result.bonds)
