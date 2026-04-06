from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Date
from fuggers_py.market.quotes import BondQuote
from fuggers_py.market import curves as market_curves
from fuggers_py.market.curves import (
    BondFairValueRequest,
    FittedBondCurveFitter,
    FittedBondObjective,
)

from tests.helpers._fitted_bond_helpers import exponential_model, make_curve_observations, nominal_bond_lookup


@pytest.mark.feature_slug("fitted-bond-optimizer-adapters-regressors")
@pytest.mark.feature_category("api_contract")
def test_public_surface_exposes_direct_fitter_constructor_and_extended_fair_value_request() -> None:
    observations, _ = make_curve_observations(
        curve_model=exponential_model(),
        regression_coefficient=Decimal("0"),
    )
    bond = nominal_bond_lookup()[observations[0].instrument_id.as_str()]
    fitter = FittedBondCurveFitter(
        curve_model=exponential_model(),
        objective=FittedBondObjective.L1,
        use_observation_weights=False,
    )
    request = BondFairValueRequest(
        bond=bond,
        settlement_date=Date.from_ymd(2026, 1, 15),
        quote=BondQuote(
            instrument_id=observations[0].instrument_id,
            clean_price=Decimal("99.25"),
            as_of=Date.from_ymd(2026, 1, 15),
        ),
        regression_exposures={"liquidity": Decimal("0.4")},
    )

    assert market_curves.FittedBondCurveFitter is FittedBondCurveFitter
    assert hasattr(market_curves, "FittedBondObservation") is False
    assert market_curves.BondFairValueRequest is BondFairValueRequest
    assert fitter.objective is FittedBondObjective.L1
    assert fitter.use_observation_weights is False
    assert request.quote is not None
    assert request.regression_exposures["liquidity"] == Decimal("0.4")
