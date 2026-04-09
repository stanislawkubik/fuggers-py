"""File-backed adapters for market data, reference data, and outputs.

These adapters are thin normalization layers over the in-memory sources and
publishers. They load CSV or JSON payloads from disk, normalize identifiers and
decimal fields, and then delegate lookup behavior to the underlying sources.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from fuggers_py.core.types import Currency, Date, Frequency
from fuggers_py.calc import (
    AlertPublisher,
    AnalyticsPublisher,
    BondQuoteOutput,
    CurvePublisher,
    EtfAnalyticsOutput,
    EtfPublisher,
    OutputPublisher,
    QuotePublisher,
)
from fuggers_py.core import CurveId, EtfId, InstrumentId
from fuggers_py.market.quotes import RawQuote
from fuggers_py.market.snapshot import (
    CurveData,
    CurveInput,
    CurveInputs,
    CurveInstrumentType,
    CurvePoint,
    EtfHolding,
    EtfQuote,
    IndexFixing,
)
from fuggers_py.market.sources import (
    CurveInputSource,
    EtfQuoteSource,
    FixingSource,
    InMemoryCurveSource,
    InMemoryEtfQuoteSource,
    InMemoryFixingSource,
    InMemoryQuoteSource,
    MarketDataProvider,
    QuoteSource,
    ReferenceCurveSource,
)
from fuggers_py.market.state import QuoteSide
from fuggers_py.reference import (
    BondReferenceData,
    BondReferenceSource,
    BondType,
    CallScheduleEntry,
    EtfHoldingsSource,
    FloatingRateTerms,
    IssuerReferenceData,
    IssuerReferenceSource,
    IssuerType,
    RatingRecord,
    RatingSource,
    ReferenceDataProvider,
)


def _as_path(path: str | Path) -> Path:
    """Convert a path-like input to :class:`Path`."""
    return Path(path)


def _read_rows(path: str | Path) -> list[dict[str, str]]:
    """Read a CSV file into a list of row dictionaries."""
    with _as_path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _decimal_or_none(value: str | None) -> Decimal | None:
    """Parse a nullable decimal field from text."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return Decimal(text)


def _date_or_none(value: str | None) -> Date | None:
    """Parse a nullable date field from text."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return Date.parse(text)


def _datetime_or_none(value: str | None) -> datetime | None:
    """Parse a nullable datetime field from ISO-8601 text."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return datetime.fromisoformat(text)


def _currency_or_none(value: str | None) -> Currency | None:
    """Parse a nullable currency code from text."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return Currency.from_code(text)


def _frequency_or_none(value: str | None) -> Frequency | None:
    """Parse a nullable frequency enum name from text."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return Frequency[text.upper()]


def _bond_type(value: str) -> BondType:
    """Parse a bond type from text."""
    return BondType[value.strip().upper()]


def _issuer_type(value: str) -> IssuerType:
    """Parse an issuer type from text."""
    return IssuerType[value.strip().upper()]


def _load_schedule(raw_value: str | None) -> tuple[CallScheduleEntry, ...]:
    """Load a serialized call or put schedule from JSON text."""
    if raw_value is None or not raw_value.strip():
        return ()
    payload = json.loads(raw_value)
    return tuple(
        CallScheduleEntry(exercise_date=Date.parse(item["exercise_date"]), price=Decimal(str(item["price"])))
        for item in payload
    )


def _load_curve_inputs_payload(payload: Any) -> tuple[CurveInputs, ...]:
    """Load curve inputs from a JSON payload."""
    raw_curves = payload.get("curves", payload) if isinstance(payload, dict) else payload
    curves: list[CurveInputs] = []
    for raw_curve in raw_curves:
        points = tuple(CurvePoint(tenor=Decimal(str(item["tenor"])), value=Decimal(str(item["value"]))) for item in raw_curve["points"])
        instruments = tuple(
            CurveInput(
                instrument_type=CurveInstrumentType[item["instrument_type"].strip().upper()],
                tenor=_decimal_or_none(item.get("tenor")),
                rate=_decimal_or_none(item.get("rate")),
                price=_decimal_or_none(item.get("price")),
                weight=_decimal_or_none(item.get("weight")),
                instrument_id=None if not item.get("instrument_id") else InstrumentId.parse(item["instrument_id"]),
                label=item.get("label"),
                source=item.get("source"),
            )
            for item in raw_curve.get("instruments", [])
        )
        curves.append(
            CurveInputs.from_points(
                curve_id=CurveId.parse(raw_curve["curve_id"]),
                reference_date=Date.parse(raw_curve["reference_date"]),
                points=points,
                interpolation=raw_curve.get("interpolation", "linear"),
                curve_kind=raw_curve.get("curve_kind", "zero"),
                instruments=instruments,
                source=raw_curve.get("source"),
            )
        )
    return tuple(curves)


@dataclass(slots=True)
class CSVQuoteSource:
    """CSV-backed quote source that delegates to :class:`InMemoryQuoteSource`.

    The file is read once at construction time. Subsequent lookups are served
    from the in-memory source, which keeps side effects limited to the initial
    file load.
    """

    path: Path
    _source: InMemoryQuoteSource

    def __init__(self, path: str | Path) -> None:
        self.path = _as_path(path)
        quotes = [
            RawQuote(
                instrument_id=InstrumentId.parse(row["instrument_id"]),
                value=Decimal(row["value"]),
                as_of=_date_or_none(row.get("as_of")),
                currency=_currency_or_none(row.get("currency")),
                source=row.get("source"),
                bid=_decimal_or_none(row.get("bid")),
                ask=_decimal_or_none(row.get("ask")),
                mid=_decimal_or_none(row.get("mid")),
                last=_decimal_or_none(row.get("last")),
                yield_to_maturity=_decimal_or_none(row.get("yield_to_maturity")),
                yield_to_worst=_decimal_or_none(row.get("yield_to_worst")),
                venue=row.get("venue"),
            )
            for row in _read_rows(self.path)
        ]
        self._source = InMemoryQuoteSource(quotes)

    def get_quote(self, instrument_id: InstrumentId | str, side: QuoteSide = QuoteSide.MID) -> RawQuote | None:
        """Return the quote matching ``instrument_id`` and ``side``."""
        return self._source.get_quote(instrument_id, side)


@dataclass(slots=True)
class JSONCurveInputSource:
    """JSON-backed curve-input source that delegates to :class:`InMemoryCurveSource`.

    The file is loaded once during initialization and then queried from memory.
    """

    path: Path
    _source: InMemoryCurveSource

    def __init__(self, path: str | Path) -> None:
        self.path = _as_path(path)
        with self.path.open("r", encoding="utf-8") as handle:
            curves = _load_curve_inputs_payload(json.load(handle))
        self._source = InMemoryCurveSource(curves)

    def get_curve_inputs(self, curve_id: CurveId | str) -> CurveInputs | None:
        """Return the curve inputs matching ``curve_id``."""
        return self._source.get_curve_inputs(curve_id)

    def get_reference_curve(self, curve_id: CurveId | str) -> CurveInputs | None:
        """Return the reference curve matching ``curve_id``."""
        return self._source.get_reference_curve(curve_id)


@dataclass(slots=True)
class CSVIndexFixingSource:
    """CSV-backed index fixing source.

    The source reads the CSV once and resolves fixings from the in-memory copy.
    """

    path: Path
    _source: InMemoryFixingSource

    def __init__(self, path: str | Path) -> None:
        self.path = _as_path(path)
        fixings = [
            IndexFixing(
                index_name=row["index_name"],
                fixing_date=Date.parse(row["fixing_date"]),
                value=Decimal(row["value"]),
            )
            for row in _read_rows(self.path)
        ]
        self._source = InMemoryFixingSource(fixings)

    def get_fixing(self, index_name: str, fixing_date: Date) -> IndexFixing | None:
        """Return the fixing matching ``index_name`` and ``fixing_date``."""
        return self._source.get_fixing(index_name, fixing_date)

    def get_rate(self, index_name: str, fixing_date: Date) -> Decimal | None:
        """Return the fixing value for ``index_name`` and ``fixing_date``."""
        return self._source.get_rate(index_name, fixing_date)


@dataclass(slots=True)
class CSVEtfQuoteSource:
    """CSV-backed ETF quote source.

    Quotes are loaded once at construction and then queried from memory.
    """

    path: Path
    _source: InMemoryEtfQuoteSource

    def __init__(self, path: str | Path) -> None:
        self.path = _as_path(path)
        quotes = [
            EtfQuote(
                etf_id=EtfId.parse(row["etf_id"]),
                market_price=_decimal_or_none(row.get("market_price")),
                nav=_decimal_or_none(row.get("nav")),
                i_nav=_decimal_or_none(row.get("i_nav")),
                shares_outstanding=_decimal_or_none(row.get("shares_outstanding")),
                as_of=_date_or_none(row.get("as_of")),
                timestamp=_datetime_or_none(row.get("timestamp")),
                source=row.get("source"),
                bid=_decimal_or_none(row.get("bid")),
                ask=_decimal_or_none(row.get("ask")),
                mid=_decimal_or_none(row.get("mid")),
            )
            for row in _read_rows(self.path)
        ]
        self._source = InMemoryEtfQuoteSource(quotes)

    def get_etf_quote(self, etf_id: EtfId | str) -> EtfQuote | None:
        """Return the ETF quote matching ``etf_id``."""
        return self._source.get_etf_quote(etf_id)


@dataclass(slots=True)
class CSVBondReferenceSource:
    """CSV-backed bond reference source.

    The CSV is parsed once and stored as normalized bond reference records keyed
    by instrument id.
    """

    path: Path
    _references: dict[InstrumentId, BondReferenceData]

    def __init__(self, path: str | Path) -> None:
        self.path = _as_path(path)
        references: dict[InstrumentId, BondReferenceData] = {}
        for row in _read_rows(self.path):
            floating_terms = None
            if row.get("floating_index_name", "").strip():
                floating_terms = FloatingRateTerms(
                    index_name=row["floating_index_name"],
                    spread=Decimal(row["floating_spread"]),
                    reset_frequency=Frequency[row["floating_reset_frequency"].strip().upper()],
                    current_reference_rate=_decimal_or_none(row.get("current_reference_rate")),
                )
            instrument_id = InstrumentId.parse(row["instrument_id"])
            references[instrument_id] = BondReferenceData(
                instrument_id=instrument_id,
                bond_type=_bond_type(row["bond_type"]),
                issuer_type=_issuer_type(row["issuer_type"]),
                issue_date=Date.parse(row["issue_date"]),
                maturity_date=Date.parse(row["maturity_date"]),
                currency=_currency_or_none(row.get("currency")) or Currency.USD,
                notional=_decimal_or_none(row.get("notional")) or Decimal("100"),
                coupon_rate=_decimal_or_none(row.get("coupon_rate")),
                frequency=_frequency_or_none(row.get("frequency")),
                floating_rate_terms=floating_terms,
                call_schedule=_load_schedule(row.get("call_schedule")),
                put_schedule=_load_schedule(row.get("put_schedule")),
                issuer_name=row.get("issuer_name"),
                sector=row.get("sector"),
                rating=row.get("rating"),
            )
        self._references = references

    def get_bond_reference(self, instrument_id: InstrumentId | str) -> BondReferenceData | None:
        """Return the bond reference matching ``instrument_id``."""
        return self._references.get(InstrumentId.parse(instrument_id))


@dataclass(slots=True)
class CSVIssuerReferenceSource:
    """CSV-backed issuer reference source."""

    path: Path
    _issuers: dict[str, IssuerReferenceData]

    def __init__(self, path: str | Path) -> None:
        self.path = _as_path(path)
        self._issuers = {
            row["issuer_name"]: IssuerReferenceData(
                issuer_name=row["issuer_name"],
                issuer_type=_issuer_type(row.get("issuer_type", "OTHER")),
                issuer_id=row.get("issuer_id"),
                country=row.get("country"),
                sector=row.get("sector"),
                rating=row.get("rating"),
            )
            for row in _read_rows(self.path)
        }

    def get_issuer_reference(self, issuer_name: str) -> IssuerReferenceData | None:
        """Return the issuer reference matching ``issuer_name``."""
        return self._issuers.get(issuer_name)


@dataclass(slots=True)
class CSVRatingSource:
    """CSV-backed rating source.

    Ratings are indexed by instrument id and issuer name so either lookup path
    can be served from the same file-backed cache.
    """

    path: Path
    _ratings_by_instrument: dict[InstrumentId, RatingRecord]
    _ratings_by_issuer: dict[str, RatingRecord]

    def __init__(self, path: str | Path) -> None:
        self.path = _as_path(path)
        self._ratings_by_instrument = {}
        self._ratings_by_issuer = {}
        for row in _read_rows(self.path):
            record = RatingRecord(
                rating=row["rating"],
                agency=row.get("agency"),
                outlook=row.get("outlook"),
                instrument_id=None if not row.get("instrument_id") else InstrumentId.parse(row["instrument_id"]),
                issuer_name=row.get("issuer_name"),
                effective_date=_date_or_none(row.get("effective_date")),
            )
            if record.instrument_id is not None:
                self._ratings_by_instrument[record.instrument_id] = record
            if record.issuer_name:
                self._ratings_by_issuer[record.issuer_name] = record

    def get_rating(self, *, instrument_id: InstrumentId | str | None = None, issuer_name: str | None = None) -> RatingRecord | None:
        """Return a rating by instrument id or issuer name."""
        if instrument_id is not None:
            return self._ratings_by_instrument.get(InstrumentId.parse(instrument_id))
        if issuer_name is not None:
            return self._ratings_by_issuer.get(issuer_name)
        return None


@dataclass(slots=True)
class CSVEtfHoldingsSource:
    """CSV-backed ETF holdings source.

    Holdings are grouped by ETF id and returned as a deterministic tuple.
    """

    path: Path
    _holdings: dict[EtfId, tuple[EtfHolding, ...]]

    def __init__(self, path: str | Path) -> None:
        self.path = _as_path(path)
        grouped: dict[EtfId, list[EtfHolding]] = {}
        for row in _read_rows(self.path):
            etf_id = EtfId.parse(row["etf_id"])
            grouped.setdefault(etf_id, []).append(
                EtfHolding(
                    instrument_id=InstrumentId.parse(row["instrument_id"]),
                    quantity=_decimal_or_none(row.get("quantity")),
                    weight=_decimal_or_none(row.get("weight")),
                )
            )
        self._holdings = {key: tuple(value) for key, value in grouped.items()}

    def get_etf_holdings(self, etf_id: EtfId | str) -> tuple[EtfHolding, ...]:
        """Return ETF holdings for the requested ETF identifier."""
        return self._holdings.get(EtfId.parse(etf_id), ())


@dataclass(slots=True)
class EmptyBondReferenceSource:
    """Empty bond reference source used as a no-op fallback."""

    def get_bond_reference(self, instrument_id: InstrumentId | str) -> BondReferenceData | None:
        return None


@dataclass(slots=True)
class EmptyIssuerReferenceSource:
    """Empty issuer reference source used as a no-op fallback."""

    def get_issuer_reference(self, issuer_name: str) -> IssuerReferenceData | None:
        return None


@dataclass(slots=True)
class EmptyRatingSource:
    """Empty rating source used as a no-op fallback."""

    def get_rating(self, *, instrument_id: InstrumentId | str | None = None, issuer_name: str | None = None) -> RatingRecord | None:
        return None


@dataclass(slots=True)
class EmptyEtfHoldingsSource:
    """Empty ETF holdings source used as a no-op fallback."""

    def get_etf_holdings(self, etf_id: EtfId | str) -> tuple[EtfHolding, ...]:
        return ()


def create_file_market_data(
    *,
    quotes_csv: str | Path | None = None,
    curve_inputs_json: str | Path | None = None,
    fixings_csv: str | Path | None = None,
    etf_quotes_csv: str | Path | None = None,
) -> MarketDataProvider:
    """Build a market-data provider from optional file-backed sources.

    Missing file paths are left unconfigured, so callers can mix file-backed
    and in-memory sources without creating placeholder files.
    """
    return MarketDataProvider(
        quote_source=None if quotes_csv is None else CSVQuoteSource(quotes_csv),
        curve_input_source=None if curve_inputs_json is None else JSONCurveInputSource(curve_inputs_json),
        index_fixing_source=None if fixings_csv is None else CSVIndexFixingSource(fixings_csv),
        etf_quote_source=None if etf_quotes_csv is None else CSVEtfQuoteSource(etf_quotes_csv),
    )


def create_file_reference_data(
    *,
    bonds_csv: str | Path | None = None,
    issuers_csv: str | Path | None = None,
    ratings_csv: str | Path | None = None,
    etf_holdings_csv: str | Path | None = None,
) -> ReferenceDataProvider:
    """Build a reference-data provider from optional file-backed sources.

    Missing file paths are left unconfigured so the returned provider can be
    composed with other reference-data sources.
    """
    return ReferenceDataProvider(
        bond_source=None if bonds_csv is None else CSVBondReferenceSource(bonds_csv),
        issuer_source=None if issuers_csv is None else CSVIssuerReferenceSource(issuers_csv),
        rating_source=None if ratings_csv is None else CSVRatingSource(ratings_csv),
        etf_holdings_source=None if etf_holdings_csv is None else CSVEtfHoldingsSource(etf_holdings_csv),
    )


class NoOpQuotePublisher:
    """Quote publisher that intentionally drops all messages."""

    def publish_quote(self, quote: BondQuoteOutput) -> None:
        return None


class NoOpCurvePublisher:
    """Curve publisher that intentionally drops all messages."""

    def publish_curve(self, curve_id: CurveId | str, curve: CurveInputs | CurveData) -> None:
        return None


class NoOpEtfPublisher:
    """ETF publisher that intentionally drops all messages."""

    def publish_etf(self, analytics: EtfAnalyticsOutput) -> None:
        return None


class NoOpAnalyticsPublisher:
    """Analytics publisher that intentionally drops all messages."""

    def publish_analytics(self, analytics: BondQuoteOutput | EtfAnalyticsOutput | Any) -> None:
        return None


class NoOpAlertPublisher:
    """Alert publisher that intentionally drops all messages."""

    def publish_alert(self, message: str, *, severity: str = "info") -> None:
        return None


def create_empty_output() -> OutputPublisher:
    """Build an output publisher composed of no-op channel publishers."""
    return OutputPublisher(
        quote_publisher=NoOpQuotePublisher(),
        curve_publisher=NoOpCurvePublisher(),
        etf_publisher=NoOpEtfPublisher(),
        analytics_publisher=NoOpAnalyticsPublisher(),
        alert_publisher=NoOpAlertPublisher(),
    )


__all__ = [
    "CSVBondReferenceSource",
    "CSVEtfHoldingsSource",
    "CSVEtfQuoteSource",
    "CSVIndexFixingSource",
    "CSVIssuerReferenceSource",
    "CSVQuoteSource",
    "CSVRatingSource",
    "EmptyBondReferenceSource",
    "EmptyEtfHoldingsSource",
    "EmptyIssuerReferenceSource",
    "EmptyRatingSource",
    "JSONCurveInputSource",
    "NoOpAlertPublisher",
    "NoOpAnalyticsPublisher",
    "NoOpCurvePublisher",
    "NoOpEtfPublisher",
    "NoOpQuotePublisher",
    "create_empty_output",
    "create_file_market_data",
    "create_file_reference_data",
]
