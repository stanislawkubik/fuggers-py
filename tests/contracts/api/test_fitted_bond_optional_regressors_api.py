from __future__ import annotations

import pytest

from fuggers_py.market.quotes import BondQuote
from fuggers_py.market import curves as market_curves
from fuggers_py.market.curves import BondCurvePricingAdapter
from fuggers_py.market.curves import fitted_bonds


@pytest.mark.feature_slug("fitted-bond-optional-regressors")
@pytest.mark.feature_category("api_contract")
def test_public_exports_expose_the_new_fitted_bond_surface() -> None:
    assert BondQuote.__name__ == "BondQuote"
    assert hasattr(market_curves, "BondObservation") is False
    assert hasattr(market_curves, "FittedBondObservation") is False
    assert hasattr(market_curves, "BondCurveRegressor") is False
    assert hasattr(market_curves, "CurveFitContext") is False
    assert hasattr(market_curves, "CallableRegressor") is False
    assert hasattr(market_curves, "ConstantRegressor") is False
    assert market_curves.BondCurvePricingAdapter is BondCurvePricingAdapter
    assert hasattr(fitted_bonds, "BondObservation") is False
    assert hasattr(fitted_bonds, "FittedBondObservation") is False
