from __future__ import annotations

import pytest

from fuggers_py.bonds import BondQuote
import fuggers_py.curves as curves


@pytest.mark.feature_slug("unify-bond-quote-observation")
@pytest.mark.feature_category("api_contract")
def test_public_curve_surface_keeps_bond_quote_but_not_old_observation_scaffolding() -> None:
    removed_names = (
        "BondFairValueRequest",
        "BondObservation",
        "FittedBondObservation",
        "BondCurveQuote",
        "BondCurveQuoteBasis",
        "BondCurveObservation",
        "fitted_bonds",
    )

    assert BondQuote.__module__ == "fuggers_py.bonds.quotes"

    for name in removed_names:
        assert not hasattr(curves, name)
