from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date, InstrumentId, YearMonth
from fuggers_py.market.quotes import (
    BasisSwapQuote,
    BondFutureQuote,
    CdsQuote,
    HaircutQuote,
    InstrumentQuote,
    RawQuote,
    RepoQuote,
    SwapQuote,
)
from fuggers_py.market.state import QuoteSide

SupportedInstrumentQuote = (
    RawQuote
    | RepoQuote
    | SwapQuote
    | BasisSwapQuote
    | BondFutureQuote
    | CdsQuote
    | HaircutQuote
)


@pytest.mark.feature_slug("non-bond-instrument-adoption")
@pytest.mark.feature_category("properties")
@pytest.mark.parametrize(
    ("quote", "side"),
    [
        (
            RawQuote(
                instrument_id="RAW-1",
                value=Decimal("100.25"),
                as_of=Date.from_ymd(2026, 3, 3),
                currency=Currency.USD,
                source="raw",
            ),
            QuoteSide.MID,
        ),
        (
            RepoQuote(
                instrument_id="REPO-1",
                rate=Decimal("0.05"),
                bid=Decimal("0.05"),
                as_of=Date.from_ymd(2026, 3, 3),
                currency=Currency.USD,
                source="repo",
            ),
            QuoteSide.BID,
        ),
        (
            SwapQuote(
                instrument_id="SWAP-1",
                rate=Decimal("0.041"),
                ask=Decimal("0.041"),
                as_of=Date.from_ymd(2026, 3, 3),
                currency=Currency.USD,
                source="swap",
            ),
            QuoteSide.ASK,
        ),
        (
            BasisSwapQuote(
                instrument_id="BASIS-1",
                basis=Decimal("0.0012"),
                as_of=Date.from_ymd(2026, 3, 3),
                currency=Currency.USD,
                source="basis",
            ),
            QuoteSide.MID,
        ),
        (
            BondFutureQuote(
                instrument_id="FUT-1",
                price=Decimal("114.50"),
                delivery_month=YearMonth(2026, 6),
                as_of=Date.from_ymd(2026, 3, 3),
                currency=Currency.USD,
                source="future",
            ),
            QuoteSide.MID,
        ),
        (
            CdsQuote(
                instrument_id="CDS-1",
                par_spread=Decimal("0.0125"),
                as_of=Date.from_ymd(2026, 3, 3),
                currency=Currency.USD,
                source="cds",
            ),
            QuoteSide.MID,
        ),
        (
            HaircutQuote(
                instrument_id="HAIRCUT-1",
                haircut=Decimal("0.03"),
                bid=Decimal("0.03"),
                as_of=Date.from_ymd(2026, 3, 3),
                currency=Currency.USD,
                source="haircut",
            ),
            QuoteSide.BID,
        ),
    ],
)
def test_instrument_quote_header_invariants_hold_for_existing_market_quotes(
    quote: SupportedInstrumentQuote,
    side: QuoteSide,
) -> None:
    assert isinstance(quote, InstrumentQuote)
    assert quote.instrument_id == InstrumentId.parse(quote.instrument_id)

    normalized = quote.for_side(side)

    assert normalized is not None
    assert isinstance(normalized, InstrumentQuote)
    assert normalized.instrument_id == quote.instrument_id
    assert normalized.quoted_value() == quote.quoted_value(side)
    assert normalized.as_of == quote.as_of
    assert normalized.source == quote.source
    assert normalized.currency == quote.currency
