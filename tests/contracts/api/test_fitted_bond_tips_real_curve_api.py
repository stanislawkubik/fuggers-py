from __future__ import annotations

import pytest

import fuggers_py.curves as curves


@pytest.mark.feature_slug("fitted-bond-tips-real-curve")
@pytest.mark.feature_category("api_contract")
def test_nominal_and_tips_pricing_adapter_names_are_not_part_of_the_current_public_curve_story() -> None:
    removed_names = (
        "NominalGovernmentBondPricingAdapter",
        "TipsRealBondPricingAdapter",
    )

    for name in removed_names:
        assert not hasattr(curves, name)
