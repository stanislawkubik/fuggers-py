from __future__ import annotations

import pytest

from fuggers_py.rates import HasExpiry, HasOptionType, HasUnderlyingInstrument


@pytest.mark.feature_slug("non-bond-instrument-adoption")
@pytest.mark.feature_category("api_contract")
def test_core_option_and_underlying_traits_are_reachable_from_first_layer_rates_surface() -> None:
    assert HasExpiry.__module__ == "fuggers_py._products.instruments.base"
    assert HasOptionType.__module__ == "fuggers_py._products.instruments.base"
    assert HasUnderlyingInstrument.__module__ == "fuggers_py._products.instruments.base"
