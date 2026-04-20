from __future__ import annotations

import pytest

import fuggers_py.curves as curves


@pytest.mark.feature_slug("fitted-bond-optimizer-adapters-regressors")
@pytest.mark.feature_category("api_contract")
def test_public_curve_modules_do_not_expose_old_optimizer_curve_adapters_or_fair_value_requests() -> None:
    removed_names = (
        "BondCurve",
        "BondCurveFitter",
        "BondFairValueRequest",
        "CurveObjective",
        "FittedBondObservation",
    )

    for name in removed_names:
        assert not hasattr(curves, name)
