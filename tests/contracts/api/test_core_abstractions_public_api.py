from __future__ import annotations

import pytest

import fuggers_py.products.instruments as product_instruments
import fuggers_py.products.rates as products_rates
import fuggers_py.products.rates.futures as rates_futures
import fuggers_py.products.rates.options as rates_options
from fuggers_py.market import quotes as market_quotes
from fuggers_py.market.quotes import InstrumentQuote
from fuggers_py.products.instruments.base import (
    HasExpiry as base_has_expiry,
    HasOptionType as base_has_option_type,
    HasUnderlyingInstrument as base_has_underlying_instrument,
    Instrument as base_instrument,
    KindedInstrumentMixin as base_kinded_instrument_mixin,
)
from fuggers_py.reference import ReferenceData, ResolvableReference
from fuggers_py.reference import base as reference_base


@pytest.mark.feature_slug("non-bond-instrument-adoption")
@pytest.mark.feature_category("api_contract")
def test_core_abstractions_are_reachable_from_stable_public_paths() -> None:
    assert product_instruments.Instrument is base_instrument
    assert product_instruments.KindedInstrumentMixin is base_kinded_instrument_mixin
    assert product_instruments.HasOptionType is base_has_option_type
    assert product_instruments.HasExpiry is base_has_expiry
    assert product_instruments.HasUnderlyingInstrument is base_has_underlying_instrument
    assert products_rates.HasOptionType is base_has_option_type
    assert products_rates.HasExpiry is base_has_expiry
    assert products_rates.HasUnderlyingInstrument is base_has_underlying_instrument
    assert rates_options.HasOptionType is base_has_option_type
    assert rates_options.HasExpiry is base_has_expiry
    assert rates_options.HasUnderlyingInstrument is base_has_underlying_instrument
    assert products_rates.CapFloor is rates_options.CapFloor
    assert products_rates.FuturesOption is rates_options.FuturesOption
    assert products_rates.Swaption is rates_options.Swaption
    assert products_rates.GovernmentBondFuture is rates_futures.GovernmentBondFuture
    assert InstrumentQuote is market_quotes.InstrumentQuote
    assert ReferenceData is reference_base.ReferenceData
    assert ResolvableReference is reference_base.ResolvableReference
