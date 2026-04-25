from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.bonds.types import BondType, IssuerType
from fuggers_py._core import Currency, Date, Frequency, InstrumentId
from fuggers_py._runtime.quotes import InstrumentQuote, RawQuote, RepoQuote
from fuggers_py._core import (
    ReferenceData,
    ResolvableReference,
)
from fuggers_py.bonds import (
    BondReferenceData,
)
from fuggers_py.funding import RepoReferenceData


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
        as_of=Date.from_ymd(2026, 2, 2),
        currency=Currency.USD,
        source="screen",
    )
    repo_quote = RepoQuote(
        instrument_id="repo-val-1w",
        rate=Decimal("0.0475"),
        as_of=Date.from_ymd(2026, 2, 2),
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
