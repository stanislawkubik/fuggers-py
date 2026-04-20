from __future__ import annotations

import pytest

from fuggers_py.bonds import BondQuote
import fuggers_py.curves as curves


@pytest.mark.feature_slug("fitted-bond-optional-regressors")
@pytest.mark.feature_category("api_contract")
def test_public_curve_modules_do_not_reintroduce_old_fitted_bond_regressor_scaffolding() -> None:
    assert BondQuote.__name__ == "BondQuote"
    removed_names = (
        "BondObservation",
        "FittedBondObservation",
        "BondCurveRegressor",
        "CurveFitContext",
        "CallableRegressor",
        "ConstantRegressor",
        "BondCurvePricingAdapter",
        "fitted_bonds",
    )

    for name in removed_names:
        assert not hasattr(curves, name)
