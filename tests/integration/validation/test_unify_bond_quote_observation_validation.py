from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.market.curves import FittedBondCurveFitter

from tests.helpers._fitted_bond_helpers import (
    exponential_model,
    make_curve_observations,
    make_tips_curve_observations,
    nominal_fit_kwargs,
    tips_fit_kwargs,
    tips_pricing_adapter,
)


@pytest.mark.feature_slug("unify-bond-quote-observation")
@pytest.mark.feature_category("validation")
def test_dirty_price_only_bondquote_inputs_still_fit_cleanly() -> None:
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


@pytest.mark.feature_slug("unify-bond-quote-observation")
@pytest.mark.feature_category("validation")
def test_tips_real_curve_uses_regular_bondquote_clean_price_inputs() -> None:
    observations, _, fixing_source = make_tips_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0"),
    )

    result = FittedBondCurveFitter(
        curve_model=exponential_model(),
        pricing_adapter=tips_pricing_adapter(fixing_source),
    ).fit(observations, regression_exposures={}, **tips_fit_kwargs())

    assert result.diagnostics.converged is True
    assert float(result.diagnostics.weighted_rmse_price) == pytest.approx(0.0, abs=1e-6)
