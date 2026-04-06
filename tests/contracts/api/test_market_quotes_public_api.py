from __future__ import annotations

from typing import get_args

import fuggers_py.market as market_pkg
import fuggers_py.market.quotes as market_quotes
import fuggers_py.market.snapshot as market_snapshot
import fuggers_py.market.sources as market_sources
from fuggers_py.market.quotes import (
    AnyInstrumentQuote,
    BasisSwapQuote,
    BondFutureQuote,
    BondQuote,
    CdsQuote,
    FxForwardQuote,
    HaircutQuote,
    InstrumentQuote,
    RawQuote,
    RepoQuote,
    ScalarQuote,
    SwapQuote,
)


def test_market_quote_abstractions_are_publicly_reachable() -> None:
    assert InstrumentQuote is market_quotes.InstrumentQuote
    assert ScalarQuote is market_quotes.ScalarQuote
    assert AnyInstrumentQuote == market_quotes.AnyInstrumentQuote
    assert ScalarQuote is RawQuote
    assert BondQuote is market_quotes.BondQuote


def test_any_instrument_quote_covers_existing_concrete_quote_families() -> None:
    supported = set(get_args(AnyInstrumentQuote))

    assert {
        RawQuote,
        BondQuote,
        RepoQuote,
        SwapQuote,
        BasisSwapQuote,
        BondFutureQuote,
        FxForwardQuote,
        CdsQuote,
        HaircutQuote,
    }.issubset(supported)


def test_market_root_exposes_modules_but_not_leaf_quote_reexports() -> None:
    assert market_pkg.quotes is market_quotes
    assert market_pkg.snapshot is market_snapshot
    assert market_pkg.sources is market_sources
    assert hasattr(market_pkg, "BondQuote") is False
    assert hasattr(market_pkg, "MarketDataSnapshot") is False
    assert hasattr(market_pkg, "MarketDataProvider") is False
