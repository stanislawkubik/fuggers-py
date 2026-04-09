from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Date
import fuggers_py.market as market_pkg
from fuggers_py.market.quotes import BondQuote
from fuggers_py.market import curves as market_curves
from fuggers_py.market.curves import BondFairValueRequest
from fuggers_py.market.curves import fitted_bonds

from tests.helpers._fitted_bond_helpers import make_curve_observations, nominal_bond_lookup


@pytest.mark.feature_slug("unify-bond-quote-observation")
@pytest.mark.feature_category("api_contract")
def test_public_api_uses_bond_quote_and_drops_curve_only_quote_types() -> None:
    observations, _ = make_curve_observations(regression_coefficient=Decimal("0"))
    bond = nominal_bond_lookup()[observations[0].instrument_id.as_str()]
    request = BondFairValueRequest(
        bond=bond,
        settlement_date=Date.from_ymd(2026, 1, 15),
        instrument_id=observations[0].instrument_id,
        quote=BondQuote(
            instrument=bond,
            clean_price=Decimal("99.25"),
            as_of=Date.from_ymd(2026, 1, 15),
        ),
    )

    assert hasattr(market_pkg, "BondObservation") is False
    assert hasattr(market_pkg, "FittedBondObservation") is False
    assert hasattr(market_curves, "BondObservation") is False
    assert hasattr(market_curves, "FittedBondObservation") is False
    assert hasattr(fitted_bonds, "BondObservation") is False
    assert hasattr(fitted_bonds, "FittedBondObservation") is False
    assert hasattr(market_curves, "BondCurveQuote") is False
    assert hasattr(market_curves, "BondCurveQuoteBasis") is False
    assert hasattr(market_curves, "BondCurveObservation") is False
    assert hasattr(fitted_bonds, "BondCurveQuote") is False
    assert hasattr(fitted_bonds, "BondCurveQuoteBasis") is False
    assert hasattr(fitted_bonds, "BondCurveObservation") is False
    assert request.quote is not None
    assert request.quote.instrument is bond
    assert request.quote.as_of == Date.from_ymd(2026, 1, 15)
    assert hasattr(request.quote, "settlement_date") is False
    assert hasattr(request.quote, "reference_data") is False
    assert hasattr(request.quote, "user_data") is False
