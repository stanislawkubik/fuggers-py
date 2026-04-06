from __future__ import annotations

import pytest

from fuggers_py.market import curves as market_curves
from fuggers_py.market.curves import (
    NominalGovernmentBondPricingAdapter,
    TipsRealBondPricingAdapter,
)
from fuggers_py.market.curves import fitted_bonds


@pytest.mark.feature_slug("fitted-bond-tips-real-curve")
@pytest.mark.feature_category("api_contract")
def test_public_exports_expose_the_nominal_and_tips_pricing_adapters() -> None:
    assert market_curves.NominalGovernmentBondPricingAdapter is NominalGovernmentBondPricingAdapter
    assert market_curves.TipsRealBondPricingAdapter is TipsRealBondPricingAdapter
    assert fitted_bonds.NominalGovernmentBondPricingAdapter is NominalGovernmentBondPricingAdapter
    assert fitted_bonds.TipsRealBondPricingAdapter is TipsRealBondPricingAdapter
