"""Canonical market-data source protocols and in-memory providers.

Volatility surface source abstractions have their public home in
``fuggers_py.vol_surfaces``. Runtime providers depend on those records without
owning the volatility-surface API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol, runtime_checkable

from fuggers_py import vol_surfaces
from fuggers_py._core.ids import CurrencyPair, CurveId, EtfId, InstrumentId, VolSurfaceId, YearMonth
from fuggers_py._core.types import Date
from fuggers_py._runtime.quotes import RawQuote
from fuggers_py.rates.indices import IndexFixingStore

from .snapshot import CurveData, CurveInputs, EtfQuote, FxRate, IndexFixing, InflationFixing, MarketDataSnapshot
from .state import QuoteSide


@runtime_checkable
class QuoteSource(Protocol):
    """Protocol for quote retrieval by instrument and quote side."""

    def get_quote(self, instrument_id: InstrumentId | str, side: QuoteSide = QuoteSide.MID) -> RawQuote | None:
        ...


@runtime_checkable
class CurveInputSource(Protocol):
    """Protocol for retrieving curve calibration inputs."""

    def get_curve_inputs(self, curve_id: CurveId | str) -> CurveInputs | None:
        ...


@runtime_checkable
class IndexFixingSource(Protocol):
    """Protocol for retrieving index fixings."""

    def get_fixing(self, index_name: str, fixing_date: Date) -> IndexFixing | None:
        ...


@runtime_checkable
class ReferenceCurveSource(Protocol):
    """Protocol for retrieving reference curves."""

    def get_reference_curve(self, curve_id: CurveId | str) -> CurveInputs | None:
        ...


@runtime_checkable
class FxRateSource(Protocol):
    """Protocol for retrieving FX rates by currency pair and quote side."""

    def get_fx_rate(self, currency_pair: CurrencyPair | str, side: QuoteSide = QuoteSide.MID) -> FxRate | None:
        ...


@runtime_checkable
class InflationFixingSource(Protocol):
    """Protocol for retrieving inflation fixings by index and month."""

    def get_inflation_fixing(self, index_name: str, observation_month: YearMonth | str) -> InflationFixing | None:
        ...


@runtime_checkable
class EtfQuoteSource(Protocol):
    """Protocol for retrieving ETF quotes."""

    def get_etf_quote(self, etf_id: EtfId | str) -> EtfQuote | None:
        ...


@runtime_checkable
class PricingDataProvider(QuoteSource, CurveInputSource, IndexFixingSource, Protocol):
    """Combined market-data provider used by pricing workflows."""

    pass


CurveSource = CurveInputSource
FixingSource = IndexFixingSource


@dataclass(slots=True)
class InMemoryQuoteSource:
    """Deterministic in-memory quote source."""

    quotes: dict[InstrumentId, RawQuote] = field(default_factory=dict)

    def __init__(self, quotes: tuple[RawQuote, ...] | list[RawQuote] | None = None) -> None:
        self.quotes = {}
        for quote in quotes or ():
            self.add_quote(quote)

    def add_quote(self, quote: RawQuote) -> "InMemoryQuoteSource":
        """Store one canonical quote keyed by instrument id."""
        self.quotes[quote.instrument_id] = quote
        return self

    def get_quote(self, instrument_id: InstrumentId | str, side: QuoteSide = QuoteSide.MID) -> RawQuote | None:
        """Return a normalized quote for the requested instrument and side."""
        resolved = instrument_id if isinstance(instrument_id, InstrumentId) else InstrumentId.parse(instrument_id)
        quote = self.quotes.get(resolved)
        if quote is None:
            return None
        direct = quote.for_side(side)
        if direct is not None:
            return direct
        if side is not QuoteSide.MID:
            return quote.for_side(QuoteSide.MID)
        return quote


@dataclass(slots=True)
class InMemoryCurveSource:
    """Deterministic in-memory curve source."""

    curves: dict[CurveId, CurveInputs] = field(default_factory=dict)

    def __init__(self, curves: tuple[CurveInputs, ...] | list[CurveInputs] | None = None) -> None:
        self.curves = {}
        for curve in curves or ():
            self.add_curve_inputs(curve)

    def add_curve_inputs(self, curve_inputs: CurveInputs | CurveData) -> "InMemoryCurveSource":
        """Store normalized curve inputs, accepting either snapshot shape."""
        resolved = curve_inputs.as_curve_inputs() if isinstance(curve_inputs, CurveData) else curve_inputs
        self.curves[resolved.curve_id] = resolved
        return self

    def get_curve_inputs(self, curve_id: CurveId | str) -> CurveInputs | None:
        """Return curve inputs for the requested curve identifier."""
        resolved = curve_id if isinstance(curve_id, CurveId) else CurveId.parse(curve_id)
        return self.curves.get(resolved)

    def get_reference_curve(self, curve_id: CurveId | str) -> CurveInputs | None:
        """Alias for :meth:`get_curve_inputs`."""
        return self.get_curve_inputs(curve_id)


@dataclass(slots=True)
class InMemoryFixingSource:
    """Deterministic in-memory index fixing source."""

    fixings: dict[tuple[str, Date], IndexFixing] = field(default_factory=dict)

    def __init__(self, fixings: tuple[IndexFixing, ...] | list[IndexFixing] | None = None) -> None:
        self.fixings = {}
        for fixing in fixings or ():
            self.add_fixing(fixing)

    def add_fixing(self, fixing: IndexFixing) -> "InMemoryFixingSource":
        """Store a fixing keyed by index name and fixing date."""
        self.fixings[(fixing.index_name, fixing.fixing_date)] = fixing
        return self

    def get_fixing(self, index_name: str, fixing_date: Date) -> IndexFixing | None:
        """Return a fixing for the requested index and date."""
        return self.fixings.get((index_name.strip().upper(), fixing_date))

    def get_rate(self, index_name: str, fixing_date: Date) -> Decimal | None:
        """Return only the fixing value for the requested index and date."""
        fixing = self.get_fixing(index_name, fixing_date)
        return None if fixing is None else fixing.value

    def to_fixing_store(self) -> IndexFixingStore:
        """Export the in-memory fixings to a bond-layer fixing store."""
        store = IndexFixingStore()
        for fixing in self.fixings.values():
            store.add_fixing(fixing.index_name, fixing.fixing_date, fixing.value)
        return store


@dataclass(slots=True)
class InMemoryFxRateSource:
    """Deterministic in-memory FX-rate source."""

    fx_rates: dict[tuple[CurrencyPair, QuoteSide], FxRate] = field(default_factory=dict)

    def __init__(self, fx_rates: tuple[FxRate, ...] | list[FxRate] | None = None) -> None:
        self.fx_rates = {}
        for fx_rate in fx_rates or ():
            self.add_fx_rate(fx_rate)

    def add_fx_rate(self, fx_rate: FxRate) -> "InMemoryFxRateSource":
        """Store an FX rate and any derivable side views."""
        for side in (QuoteSide.BID, QuoteSide.ASK, QuoteSide.MID):
            candidate = fx_rate.for_side(side)
            if candidate is not None:
                self.fx_rates[(fx_rate.currency_pair, side)] = candidate
        self.fx_rates[(fx_rate.currency_pair, fx_rate.side)] = fx_rate
        return self

    def get_fx_rate(self, currency_pair: CurrencyPair | str, side: QuoteSide = QuoteSide.MID) -> FxRate | None:
        """Return a normalized FX rate for the requested pair and side."""
        resolved = currency_pair if isinstance(currency_pair, CurrencyPair) else CurrencyPair.parse(currency_pair)
        direct = self.fx_rates.get((resolved, side))
        if direct is not None:
            return direct
        if side is not QuoteSide.MID:
            return self.fx_rates.get((resolved, QuoteSide.MID))
        return None


@dataclass(slots=True)
class InMemoryInflationFixingSource:
    """Deterministic in-memory inflation fixing source."""

    fixings: dict[tuple[str, YearMonth], InflationFixing] = field(default_factory=dict)

    def __init__(self, fixings: tuple[InflationFixing, ...] | list[InflationFixing] | None = None) -> None:
        self.fixings = {}
        for fixing in fixings or ():
            self.add_inflation_fixing(fixing)

    def add_inflation_fixing(self, fixing: InflationFixing) -> "InMemoryInflationFixingSource":
        """Store an inflation fixing keyed by index and observation month."""
        self.fixings[(fixing.index_name, fixing.observation_month)] = fixing
        return self

    def get_inflation_fixing(self, index_name: str, observation_month: YearMonth | str) -> InflationFixing | None:
        """Return the requested inflation fixing when present."""
        return self.fixings.get((index_name.strip().upper(), YearMonth.parse(observation_month)))


@dataclass(slots=True)
class InMemoryEtfQuoteSource:
    """Deterministic in-memory ETF quote source."""

    etf_quotes: dict[EtfId, EtfQuote] = field(default_factory=dict)

    def __init__(self, etf_quotes: tuple[EtfQuote, ...] | list[EtfQuote] | None = None) -> None:
        self.etf_quotes = {}
        for quote in etf_quotes or ():
            self.add_etf_quote(quote)

    def add_etf_quote(self, quote: EtfQuote) -> "InMemoryEtfQuoteSource":
        """Store an ETF quote keyed by normalized ETF identifier."""
        self.etf_quotes[quote.etf_id] = quote
        return self

    def get_etf_quote(self, etf_id: EtfId | str) -> EtfQuote | None:
        """Return the requested ETF quote when present."""
        resolved = etf_id if isinstance(etf_id, EtfId) else EtfId.parse(etf_id)
        return self.etf_quotes.get(resolved)


@dataclass(slots=True)
class MarketDataProvider:
    """Composite market-data provider built from optional source objects."""

    quote_source: QuoteSource | None = None
    curve_input_source: CurveInputSource | None = None
    index_fixing_source: IndexFixingSource | None = None
    volatility_source: vol_surfaces.VolatilitySource | None = None
    fx_rate_source: FxRateSource | None = None
    inflation_fixing_source: InflationFixingSource | None = None
    etf_quote_source: EtfQuoteSource | None = None

    @classmethod
    def from_snapshot(cls, snapshot: MarketDataSnapshot) -> "MarketDataProvider":
        """Build a provider over the in-memory sources derived from a snapshot."""
        return cls(
            quote_source=snapshot.quote_source(),
            curve_input_source=snapshot.curve_source(),
            index_fixing_source=snapshot.fixing_source(),
            volatility_source=snapshot.volatility_source(),
            fx_rate_source=snapshot.fx_rate_source(),
            inflation_fixing_source=snapshot.inflation_fixing_source(),
            etf_quote_source=snapshot.etf_quote_source(),
        )

    def get_quote(self, instrument_id: InstrumentId | str, side: QuoteSide = QuoteSide.MID) -> RawQuote | None:
        """Return a quote from the configured source, if any."""
        if self.quote_source is None:
            return None
        return self.quote_source.get_quote(instrument_id, side)

    def get_curve_inputs(self, curve_id: CurveId | str) -> CurveInputs | None:
        """Return curve inputs from the configured source, if any."""
        if self.curve_input_source is None:
            return None
        return self.curve_input_source.get_curve_inputs(curve_id)

    def get_fixing(self, index_name: str, fixing_date: Date) -> IndexFixing | None:
        """Return a fixing from the configured source, if any."""
        if self.index_fixing_source is None:
            return None
        return self.index_fixing_source.get_fixing(index_name, fixing_date)

    def get_volatility_surface(self, surface_id: VolSurfaceId | str) -> vol_surfaces.VolatilitySurface | None:
        """Return a volatility surface from the configured source, if any."""
        if self.volatility_source is None:
            return None
        return self.volatility_source.get_volatility_surface(surface_id)

    def get_fx_rate(self, currency_pair: CurrencyPair | str, side: QuoteSide = QuoteSide.MID) -> FxRate | None:
        """Return an FX rate from the configured source, if any."""
        if self.fx_rate_source is None:
            return None
        return self.fx_rate_source.get_fx_rate(currency_pair, side)

    def get_inflation_fixing(self, index_name: str, observation_month: YearMonth | str) -> InflationFixing | None:
        """Return an inflation fixing from the configured source, if any."""
        if self.inflation_fixing_source is None:
            return None
        return self.inflation_fixing_source.get_inflation_fixing(index_name, observation_month)

    def get_etf_quote(self, etf_id: EtfId | str) -> EtfQuote | None:
        """Return an ETF quote from the configured source, if any."""
        if self.etf_quote_source is None:
            return None
        return self.etf_quote_source.get_etf_quote(etf_id)

__all__ = [
    "CurveInputSource",
    "CurveSource",
    "EtfQuoteSource",
    "FixingSource",
    "FxRateSource",
    "InMemoryCurveSource",
    "InMemoryEtfQuoteSource",
    "InMemoryFixingSource",
    "InMemoryFxRateSource",
    "InMemoryInflationFixingSource",
    "InMemoryQuoteSource",
    "IndexFixingSource",
    "InflationFixingSource",
    "MarketDataProvider",
    "PricingDataProvider",
    "QuoteSource",
    "ReferenceCurveSource",
]
