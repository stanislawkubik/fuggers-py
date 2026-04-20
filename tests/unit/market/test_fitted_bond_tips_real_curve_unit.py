from __future__ import annotations

from decimal import Decimal
from typing import cast

import pytest

from fuggers_py._core import Price
from fuggers_py._curves_impl import BondCurveFitter, BondFairValueRequest
from fuggers_py._curves_impl.fitted_bonds.fair_value import fair_value_from_fit
from fuggers_py._pricers.bonds import TipsPricer
from fuggers_py._products.bonds import TipsBond

from tests.helpers._fitted_bond_helpers import (
    exponential_model,
    liquidity_regression_exposures,
    make_curve_observations,
    make_tips_curve_observations,
    observation_regression_exposures,
    nominal_fit_kwargs,
    tips_bond_lookup,
    tips_fit_kwargs,
    nominal_pricing_adapter,
    tips_pricing_adapter,
)


@pytest.mark.feature_slug("fitted-bond-tips-real-curve")
@pytest.mark.feature_category("unit")
def test_nominal_and_tips_fits_run_through_the_same_generic_fitter_without_regressors() -> None:
    nominal_observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0"),
    )
    tips_observations, _, fixing_source = make_tips_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0"),
    )

    nominal_result = BondCurveFitter(
        curve_model=exponential_model(),
        pricing_adapter=nominal_pricing_adapter(),
    ).fit(nominal_observations, regression_exposures={}, **nominal_fit_kwargs())
    tips_result = BondCurveFitter(
        curve_model=exponential_model(),
        pricing_adapter=tips_pricing_adapter(fixing_source),
    ).fit(tips_observations, regression_exposures={}, **tips_fit_kwargs())

    assert nominal_result.diagnostics.converged is True
    assert tips_result.diagnostics.converged is True
    assert nominal_result.coefficients == {}
    assert tips_result.coefficients == {}
    assert float(nominal_result.diagnostics.weighted_rmse_price) == pytest.approx(0.0, abs=1e-6)
    assert float(tips_result.diagnostics.weighted_rmse_price) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.feature_slug("fitted-bond-tips-real-curve")
@pytest.mark.feature_category("unit")
def test_tips_fit_returns_real_yields_and_supports_a_custom_regressor() -> None:
    observations, _, fixing_source = make_tips_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0.18"),
    )
    quote = observations[3]
    result = BondCurveFitter(
        curve_model=exponential_model(),
        pricing_adapter=tips_pricing_adapter(fixing_source),
    ).fit(
        observations,
        regression_exposures=liquidity_regression_exposures(observations),
        **tips_fit_kwargs(),
    )
    point = result.get_bond(quote.instrument_id)
    assert quote.as_of is not None
    tips_bond = cast(TipsBond, tips_bond_lookup()[quote.instrument_id.as_str()])
    pricer = TipsPricer()

    observed_real_yield = pricer.real_yield_from_clean_price(
        tips_bond,
        Price.new(point["observed_clean_price"], tips_bond.currency()),
        quote.as_of,
        fixing_source=fixing_source,
    ).ytm.value()
    fitted_real_yield = pricer.real_yield_from_clean_price(
        tips_bond,
        Price.new(point["fitted_clean_price"], tips_bond.currency()),
        quote.as_of,
        fixing_source=fixing_source,
    ).ytm.value()
    fair_value = fair_value_from_fit(
        result,
        BondFairValueRequest(
            bond=tips_bond,
            settlement_date=quote.as_of,
            instrument_id=quote.instrument_id,
            quote=quote,
            regression_exposures=observation_regression_exposures(quote),
        ),
    )

    assert result.diagnostics.converged is True
    assert float(result.coefficient_map()["liquidity"]) == pytest.approx(0.18, abs=1e-5)
    assert float(point["observed_yield"]) == pytest.approx(float(observed_real_yield), abs=1e-10)
    assert float(point["fitted_yield"]) == pytest.approx(float(fitted_real_yield), abs=1e-10)
    assert float(fair_value.fair_value_dirty_price) == pytest.approx(float(point["fitted_dirty_price"]), abs=1e-6)
    assert float(fair_value.fair_value_clean_price) == pytest.approx(float(point["fitted_clean_price"]), abs=1e-6)
    assert float(fair_value.fair_value_yield) == pytest.approx(float(point["fitted_yield"]), abs=1e-10)
