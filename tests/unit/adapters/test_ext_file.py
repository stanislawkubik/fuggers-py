from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from fuggers_py._core import Date
from fuggers_py._storage import (
    CSVBondReferenceSource,
    CSVEtfHoldingsSource,
    CSVEtfQuoteSource,
    CSVIssuerReferenceSource,
    EmptyBondReferenceSource,
    EmptyEtfHoldingsSource,
    EmptyIssuerReferenceSource,
    EmptyRatingSource,
    CSVIndexFixingSource,
    CSVQuoteSource,
    CSVRatingSource,
    JSONCurveInputSource,
    NoOpAlertPublisher,
    NoOpAnalyticsPublisher,
    NoOpEtfPublisher,
    NoOpQuotePublisher,
    create_empty_output,
    create_file_market_data,
    create_file_reference_data,
)
from fuggers_py._runtime import (
    AlertPublisher,
    AnalyticsPublisher,
    EtfPublisher,
    QuotePublisher,
    QuoteSide,
)
from fuggers_py._core import InstrumentId
from fuggers_py._runtime.sources import CurveInputSource, FixingSource, QuoteSource
from fuggers_py.bonds.reference_data import (
    BondReferenceSource,
    EtfHoldingsSource,
    IssuerReferenceSource,
    RatingSource,
    ReferenceDataProvider,
)
from tests.helpers._paths import DATA_ROOT


DATA_DIR = DATA_ROOT


def test_file_market_data_sources_load_deterministic_fixtures() -> None:
    quote_source = CSVQuoteSource(DATA_DIR / "quotes.csv")
    curve_source = JSONCurveInputSource(DATA_DIR / "curve_inputs.json")
    fixing_source = CSVIndexFixingSource(DATA_DIR / "fixings.csv")

    assert isinstance(quote_source, QuoteSource)
    assert isinstance(curve_source, CurveInputSource)
    assert isinstance(fixing_source, FixingSource)
    assert quote_source.get_quote("US1234567890", QuoteSide.ASK).value == quote_source.get_quote("US1234567890", QuoteSide.ASK).ask
    assert len(curve_source.get_curve_inputs("usd.discount").points) == 2
    assert fixing_source.get_fixing("SOFR", Date.from_ymd(2026, 3, 13)).value == fixing_source.get_rate("SOFR", Date.from_ymd(2026, 3, 13))


def test_file_factories_and_noop_publishers_expose_expected_objects() -> None:
    market_data = create_file_market_data(
        quotes_csv=DATA_DIR / "quotes.csv",
        curve_inputs_json=DATA_DIR / "curve_inputs.json",
        fixings_csv=DATA_DIR / "fixings.csv",
    )
    reference_data = create_file_reference_data(bonds_csv=DATA_DIR / "bonds.csv")
    output = create_empty_output()

    assert market_data.get_quote("US1234567890", QuoteSide.BID).value == market_data.get_quote("US1234567890", QuoteSide.BID).bid
    assert market_data.get_curve_inputs("usd.discount") is not None
    assert market_data.get_fixing("SOFR", Date.from_ymd(2026, 3, 12)).value is not None
    assert isinstance(reference_data.bond_source, BondReferenceSource)
    assert reference_data.get_bond_reference(InstrumentId("US1234567890")).issuer_name == "Example Corp"

    assert isinstance(output.quote_publisher, QuotePublisher)
    assert isinstance(output.etf_publisher, EtfPublisher)
    assert isinstance(output.analytics_publisher, AnalyticsPublisher)
    assert isinstance(output.alert_publisher, AlertPublisher)
    output.publish_alert("noop")


def test_noop_publishers_satisfy_protocols_and_do_nothing() -> None:
    assert isinstance(NoOpQuotePublisher(), QuotePublisher)
    assert isinstance(NoOpEtfPublisher(), EtfPublisher)
    assert isinstance(NoOpAnalyticsPublisher(), AnalyticsPublisher)
    assert isinstance(NoOpAlertPublisher(), AlertPublisher)
    assert isinstance(CSVBondReferenceSource(DATA_DIR / "bonds.csv"), BondReferenceSource)


def test_empty_reference_sources_are_explicit_and_compose_with_file_backed_providers() -> None:
    empty_bond = EmptyBondReferenceSource()
    empty_issuer = EmptyIssuerReferenceSource()
    empty_rating = EmptyRatingSource()
    empty_holdings = EmptyEtfHoldingsSource()
    file_reference_data = create_file_reference_data(bonds_csv=DATA_DIR / "bonds.csv")
    provider = ReferenceDataProvider(
        bond_source=file_reference_data.bond_source,
        issuer_source=empty_issuer,
        rating_source=empty_rating,
        etf_holdings_source=empty_holdings,
    )

    assert isinstance(empty_bond, BondReferenceSource)
    assert isinstance(empty_issuer, IssuerReferenceSource)
    assert isinstance(empty_rating, RatingSource)
    assert isinstance(empty_holdings, EtfHoldingsSource)
    assert empty_bond.get_bond_reference("US1234567890") is None
    assert empty_issuer.get_issuer_reference("Example Corp") is None
    assert empty_rating.get_rating(instrument_id="US1234567890") is None
    assert empty_holdings.get_etf_holdings("fixture-etf") == ()
    assert provider.get_bond_reference(InstrumentId("US1234567890")) is not None
    assert provider.get_issuer_reference("Example Corp") is None
    assert provider.get_rating(instrument_id="US1234567890") is None
    assert provider.get_etf_holdings("fixture-etf") == ()


def test_csv_reference_helpers_load_issuers_ratings_and_etf_holdings_from_tmp_fixtures(tmp_path: Path) -> None:
    issuers_path = tmp_path / "issuers.csv"
    issuers_path.write_text(
        dedent(
            """\
            issuer_name,issuer_type,issuer_id,country,sector,rating
            Example Corp,CORPORATE,ISS-1,US,Technology,A
            """
        ),
        encoding="utf-8",
    )
    ratings_path = tmp_path / "ratings.csv"
    ratings_path.write_text(
        dedent(
            """\
            rating,agency,outlook,instrument_id,issuer_name,effective_date
            A,S&P,Stable,US1234567890,Example Corp,2024-01-15
            BBB,Moody's,Negative,,Other Corp,2024-02-01
            """
        ),
        encoding="utf-8",
    )
    holdings_path = tmp_path / "holdings.csv"
    holdings_path.write_text(
        dedent(
            """\
            etf_id,instrument_id,quantity,weight
            fixture-etf,US1234567890,10,0.25
            fixture-etf,US0987654321,20,0.75
            """
        ),
        encoding="utf-8",
    )

    issuers = CSVIssuerReferenceSource(issuers_path)
    ratings = CSVRatingSource(ratings_path)
    holdings = CSVEtfHoldingsSource(holdings_path)

    assert issuers.get_issuer_reference("Example Corp").issuer_id == "ISS-1"
    assert ratings.get_rating(instrument_id="US1234567890").agency == "S&P"
    assert ratings.get_rating(issuer_name="Other Corp").rating == "BBB"
    assert len(holdings.get_etf_holdings("fixture-etf")) == 2
    assert holdings.get_etf_holdings("missing-etf") == ()


def test_csv_etf_quote_source_and_empty_factories_handle_missing_inputs_predictably(tmp_path: Path) -> None:
    etf_quotes_path = tmp_path / "etf_quotes.csv"
    etf_quotes_path.write_text(
        dedent(
            """\
            etf_id,market_price,nav,i_nav,shares_outstanding,as_of,timestamp,source,bid,ask,mid
            fixture-etf,101.25,100.90,100.95,1000000,2024-03-15,2024-03-15T15:30:00,file,101.20,101.30,101.25
            """
        ),
        encoding="utf-8",
    )

    quotes = CSVEtfQuoteSource(etf_quotes_path)
    empty_market_data = create_file_market_data()
    empty_reference_data = create_file_reference_data()

    assert quotes.get_etf_quote("fixture-etf").shares_outstanding is not None
    assert empty_market_data.get_quote("US1234567890") is None
    assert empty_market_data.get_curve_inputs("usd.discount") is None
    assert empty_market_data.get_etf_quote("fixture-etf") is None
    assert empty_reference_data.get_bond_reference("US1234567890") is None
    assert empty_reference_data.get_issuer_reference("Example Corp") is None
    assert empty_reference_data.get_etf_holdings("fixture-etf") == ()
