from __future__ import annotations

from decimal import Decimal

from fuggers_py.bonds.types import BondType, IssuerType
from fuggers_py._core import Currency, Date, Frequency
from fuggers_py._core import EtfId, InstrumentId
from fuggers_py._market.snapshot import EtfHolding
from fuggers_py._reference import (
    BondReferenceData,
    BondReferenceSource,
    EtfHoldingsSource,
    FloatingRateTerms,
    IssuerReferenceData,
    IssuerReferenceSource,
    RatingRecord,
    RatingSource,
    ReferenceDataProvider,
)


class StubBondSource:
    def __init__(self, reference: BondReferenceData) -> None:
        self.reference = reference

    def get_bond_reference(self, instrument_id: InstrumentId | str) -> BondReferenceData | None:
        return self.reference if InstrumentId.parse(instrument_id) == self.reference.instrument_id else None


class StubIssuerSource:
    def __init__(self, issuer: IssuerReferenceData) -> None:
        self.issuer = issuer

    def get_issuer_reference(self, issuer_name: str) -> IssuerReferenceData | None:
        return self.issuer if issuer_name == self.issuer.issuer_name else None


class StubRatingSource:
    def __init__(self, record: RatingRecord) -> None:
        self.record = record

    def get_rating(self, *, instrument_id: InstrumentId | str | None = None, issuer_name: str | None = None) -> RatingRecord | None:
        if instrument_id is not None and self.record.instrument_id == InstrumentId.parse(instrument_id):
            return self.record
        if issuer_name is not None and self.record.issuer_name == issuer_name:
            return self.record
        return None


class StubEtfHoldingsSource:
    def __init__(self, etf_id: EtfId, holdings: tuple[EtfHolding, ...]) -> None:
        self.etf_id = etf_id
        self.holdings = holdings

    def get_etf_holdings(self, etf_id: EtfId | str) -> tuple[EtfHolding, ...]:
        return self.holdings if EtfId.parse(etf_id) == self.etf_id else ()


def test_reference_data_provider_composes_lightweight_sources() -> None:
    bond_reference = BondReferenceData(
        instrument_id=InstrumentId("REF-1"),
        bond_type=BondType.FLOATING_RATE,
        issuer_type=IssuerType.CORPORATE,
        issue_date=Date.from_ymd(2025, 1, 1),
        maturity_date=Date.from_ymd(2028, 1, 1),
        currency=Currency.USD,
        floating_rate_terms=FloatingRateTerms(
            index_name="SOFR",
            spread=Decimal("0.0125"),
            reset_frequency=Frequency.QUARTERLY,
            current_reference_rate=Decimal("0.0410"),
        ),
        issuer_name="Example Corp",
    )
    issuer = IssuerReferenceData(issuer_name="Example Corp", issuer_type=IssuerType.CORPORATE, country="us", rating="A")
    rating = RatingRecord(rating="A", agency="S&P", instrument_id=InstrumentId("REF-1"), issuer_name="Example Corp")
    holdings = (
        EtfHolding(instrument_id=InstrumentId("REF-1"), quantity=Decimal("10")),
        EtfHolding(instrument_id=InstrumentId("REF-2"), weight=Decimal("0.25")),
    )

    provider = ReferenceDataProvider(
        bond_source=StubBondSource(bond_reference),
        issuer_source=StubIssuerSource(issuer),
        rating_source=StubRatingSource(rating),
        etf_holdings_source=StubEtfHoldingsSource(EtfId("agg-usd"), holdings),
    )

    assert isinstance(provider, BondReferenceSource)
    assert isinstance(provider, IssuerReferenceSource)
    assert isinstance(provider, RatingSource)
    assert isinstance(provider, EtfHoldingsSource)
    assert provider.get_bond_reference("REF-1") == bond_reference
    assert provider.get_issuer_reference("Example Corp") == issuer
    assert provider.get_rating(instrument_id="REF-1") == rating
    assert provider.get_etf_holdings("agg-usd") == holdings
