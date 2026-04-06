from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from fuggers_py.core import Currency, Date, Frequency, InstrumentId
from fuggers_py.market.quotes import InstrumentQuote, RawQuote, RepoQuote
from fuggers_py.market.state import QuoteSide
from fuggers_py.reference import (
    BondReferenceData,
    BondType,
    IssuerType,
    ReferenceData,
    RepoReferenceData,
    ResolvableReference,
)


@pytest.mark.feature_slug("non-bond-instrument-adoption")
@pytest.mark.feature_category("validation")
def test_core_abstractions_fit_existing_reference_and_quote_records() -> None:
    bond_reference = BondReferenceData(
        instrument_id="VAL-BOND",
        bond_type=BondType.FIXED_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2031, 1, 15),
        currency=Currency.USD,
        coupon_rate=Decimal("0.05"),
        frequency=Frequency.SEMI_ANNUAL,
    )
    repo_reference = RepoReferenceData(
        instrument_id="repo-val-1w",
        collateral_type="UST",
        currency=Currency.USD,
        term="1W",
        haircut=Decimal("0.02"),
    )
    raw_quote = RawQuote(
        instrument_id="VAL-BOND",
        value=Decimal("100.50"),
        side=QuoteSide.MID,
        as_of=Date.from_ymd(2026, 2, 2),
        timestamp=datetime(2026, 2, 2, 10, 0),
        currency=Currency.USD,
        source="screen",
    )
    repo_quote = RepoQuote(
        instrument_id="repo-val-1w",
        rate=Decimal("0.0475"),
        side=QuoteSide.MID,
        as_of=Date.from_ymd(2026, 2, 2),
        timestamp=datetime(2026, 2, 2, 10, 1),
        currency=Currency.USD,
        source="repo",
    )

    assert isinstance(bond_reference, ReferenceData)
    assert isinstance(bond_reference, ResolvableReference)
    assert isinstance(repo_reference, ReferenceData)
    assert isinstance(raw_quote, InstrumentQuote)
    assert isinstance(repo_quote, InstrumentQuote)
    assert bond_reference.to_instrument().maturity_date() == Date.from_ymd(2031, 1, 15)
    assert raw_quote.instrument_id == InstrumentId("VAL-BOND")
    assert repo_quote.mid == Decimal("0.0475")
