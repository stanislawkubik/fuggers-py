from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest

from fuggers_py._core import Currency, Date, Frequency, InstrumentId
from fuggers_py._runtime.quotes import BondQuote, InstrumentQuote, RawQuote, RepoQuote
from fuggers_py._runtime.state import QuoteSide
from fuggers_py.bonds import FixedBondBuilder
from fuggers_py.bonds.types import BondType, IssuerType
from fuggers_py.rates.instruments import (
    HasExpiry,
    HasOptionType,
    HasUnderlyingInstrument,
    Instrument,
    KindedInstrumentMixin,
)
from fuggers_py._core import YieldCalculationRules
from fuggers_py._core import (
    ReferenceData,
    ResolvableReference,
)
from fuggers_py.bonds import (
    BondReferenceData,
)


@dataclass(frozen=True, slots=True)
class _SyntheticInstrument(KindedInstrumentMixin):
    KIND = "rates.synthetic"

    instrument_id: InstrumentId | None


@dataclass(frozen=True, slots=True)
class _SyntheticOption:
    expiry_date: Date
    option_side: str
    underlying: object

    def option_type(self) -> str:
        return self.option_side

    def underlying_instrument(self) -> object:
        return self.underlying


def _sample_bond(instrument_id: str) -> object:
    return (
        FixedBondBuilder.new()
        .with_issue_date(Date.from_ymd(2024, 1, 15))
        .with_maturity_date(Date.from_ymd(2029, 1, 15))
        .with_coupon_rate(Decimal("0.045"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_currency(Currency.USD)
        .with_instrument_id(instrument_id)
        .with_rules(YieldCalculationRules.us_treasury())
        .build()
    )


@pytest.mark.feature_slug("non-bond-instrument-adoption")
@pytest.mark.feature_category("unit")
def test_instrument_protocol_and_capabilities_are_runtime_checkable() -> None:
    instrument = _SyntheticInstrument(instrument_id=InstrumentId("SYNTH-1"))
    option = _SyntheticOption(
        expiry_date=Date.from_ymd(2027, 1, 15),
        option_side="CALL",
        underlying=instrument,
    )

    assert instrument.kind == "rates.synthetic"
    assert isinstance(instrument, Instrument)
    assert isinstance(option, HasOptionType)
    assert isinstance(option, HasExpiry)
    assert isinstance(option, HasUnderlyingInstrument)


@pytest.mark.feature_slug("non-bond-instrument-adoption")
@pytest.mark.feature_category("unit")
def test_reference_and_quote_protocols_accept_current_records_without_behavior_changes() -> (
    None
):
    reference = BondReferenceData(
        instrument_id="UNIT-BOND",
        bond_type=BondType.FIXED_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2024, 1, 15),
        maturity_date=Date.from_ymd(2029, 1, 15),
        currency=Currency.USD,
        coupon_rate=Decimal("0.045"),
        frequency=Frequency.SEMI_ANNUAL,
    )
    raw_quote = RawQuote(
        instrument_id="  UNIT-BOND  ",
        value=Decimal("101.25"),
        as_of=Date.from_ymd(2026, 1, 15),
        currency=Currency.USD,
        source="  feed  ",
    )
    repo_quote = RepoQuote(
        instrument_id="repo-1",
        rate=Decimal("0.051"),
        bid=Decimal("0.051"),
        as_of=Date.from_ymd(2026, 1, 15),
        currency=Currency.USD,
        source="  repo screen  ",
    )
    bond = _sample_bond("UNIT-BOND")
    bond_quote = BondQuote(
        instrument=bond,
        clean_price=Decimal("99.75"),
        as_of=Date.from_ymd(2026, 1, 15),
        source="  bond screen  ",
    )

    assert isinstance(reference, ReferenceData)
    assert isinstance(reference, ResolvableReference)
    assert isinstance(raw_quote, InstrumentQuote)
    assert isinstance(repo_quote, InstrumentQuote)
    assert isinstance(bond_quote, InstrumentQuote)
    assert raw_quote.instrument_id == InstrumentId("UNIT-BOND")
    assert raw_quote.source == "feed"
    assert raw_quote.for_side(QuoteSide.MID) == raw_quote
    bid_repo_quote = repo_quote.for_side(QuoteSide.BID)
    assert bid_repo_quote is not None
    assert bid_repo_quote.instrument_id == repo_quote.instrument_id
    assert bid_repo_quote.rate == Decimal("0.051")
