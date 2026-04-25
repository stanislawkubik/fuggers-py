"""Canonical snapshot and stored market-record types.

Volatility surface records have their public home in
``fuggers_py.vol_surfaces``. Runtime snapshots store those records directly
without owning the volatility-surface API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from fuggers_py import vol_surfaces
from fuggers_py._core.ids import CurrencyPair, CurveId, EtfId, InstrumentId, YearMonth
from fuggers_py._core.types import Date
from fuggers_py.inflation.conventions import InflationInterpolation
from fuggers_py._runtime.quotes import (
    AnyInstrumentQuote,
    BasisSwapQuote,
    BondFutureQuote,
    CdsQuote,
    FxForwardQuote,
    HaircutQuote,
    RawQuote,
    RepoQuote,
    SourceType,
    SwapQuote,
)

from ._shared import _coerce_decimal_fields, _to_decimal
from .state import QuoteSide

if TYPE_CHECKING:
    from .sources import (
        InMemoryCurveSource,
        InMemoryEtfQuoteSource,
        InMemoryFixingSource,
        InMemoryFxRateSource,
        InMemoryInflationFixingSource,
        InMemoryQuoteSource,
        MarketDataProvider,
    )
    from fuggers_py.vol_surfaces import InMemoryVolatilitySource


class CurveInstrumentType(str, Enum):
    """Instrument types accepted by curve construction inputs."""

    CASH = "CASH"
    FUTURE = "FUTURE"
    FRA = "FRA"
    OIS = "OIS"
    IRS = "IRS"
    BOND = "BOND"
    BASIS_SWAP = "BASIS_SWAP"
    BOND_FUTURE = "BOND_FUTURE"
    CDS = "CDS"
    FX_FORWARD = "FX_FORWARD"
    REPO = "REPO"
    SWAP = "SWAP"


@dataclass(frozen=True, order=True, slots=True)
class CurvePoint:
    """Single curve point with tenor and value expressed as decimals."""

    tenor: Decimal
    value: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenor", _to_decimal(self.tenor))
        object.__setattr__(self, "value", _to_decimal(self.value))


@dataclass(frozen=True, slots=True)
class CurveInput:
    """Calibration input for a single curve instrument."""

    instrument_type: CurveInstrumentType
    tenor: Decimal | None = None
    rate: Decimal | None = None
    price: Decimal | None = None
    weight: Decimal | None = None
    instrument_id: InstrumentId | None = None
    label: str | None = None
    quote: AnyInstrumentQuote | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        _coerce_decimal_fields(self, "tenor", "rate", "price", "weight")
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.label is not None:
            object.__setattr__(self, "label", self.label.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())


@dataclass(frozen=True, slots=True)
class CurveInputs:
    """Ordered curve calibration bundle for a curve identifier."""

    curve_id: CurveId
    reference_date: Date
    points: tuple[CurvePoint, ...]
    interpolation: str = "linear"
    curve_kind: str = "zero"
    instruments: tuple[CurveInput, ...] = ()
    source: str | None = None

    def __post_init__(self) -> None:
        ordered_points = tuple(sorted(self.points, key=lambda point: (point.tenor, point.value)))
        ordered_inputs = tuple(
            sorted(
                self.instruments,
                key=lambda item: (
                    Decimal("-1") if item.tenor is None else item.tenor,
                    "" if item.label is None else item.label,
                ),
            )
        )
        object.__setattr__(self, "curve_id", CurveId.parse(self.curve_id))
        object.__setattr__(self, "points", ordered_points)
        object.__setattr__(self, "instruments", ordered_inputs)
        object.__setattr__(self, "interpolation", self.interpolation.strip().lower())
        object.__setattr__(self, "curve_kind", self.curve_kind.strip().lower())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())

    @classmethod
    def from_points(
        cls,
        curve_id: CurveId | str,
        reference_date: Date,
        points: list[CurvePoint] | tuple[CurvePoint, ...],
        *,
        interpolation: str = "linear",
        curve_kind: str = "zero",
        instruments: list[CurveInput] | tuple[CurveInput, ...] | None = None,
        source: str | None = None,
    ) -> "CurveInputs":
        """Build a normalized curve-input bundle from a point sequence."""
        resolved_id = curve_id if isinstance(curve_id, CurveId) else CurveId.parse(curve_id)
        return cls(
            curve_id=resolved_id,
            reference_date=reference_date,
            points=tuple(points),
            interpolation=interpolation,
            curve_kind=curve_kind,
            instruments=tuple(instruments or ()),
            source=source,
        )

    def tenors(self) -> tuple[Decimal, ...]:
        """Return curve tenors in sorted order."""
        return tuple(point.tenor for point in self.points)

    def curve_data(self) -> "CurveData":
        """Convert the inputs bundle into a read-only curve snapshot record."""
        return CurveData(
            curve_id=self.curve_id,
            reference_date=self.reference_date,
            points=self.points,
            interpolation=self.interpolation,
            curve_kind=self.curve_kind,
            instruments=self.instruments,
            source=self.source,
        )


@dataclass(frozen=True, slots=True)
class CurveData:
    """Read-only curve snapshot record."""

    curve_id: CurveId
    reference_date: Date
    points: tuple[CurvePoint, ...]
    interpolation: str = "linear"
    curve_kind: str = "zero"
    instruments: tuple[CurveInput, ...] = ()
    source: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "curve_id", CurveId.parse(self.curve_id))
        object.__setattr__(self, "points", tuple(sorted(self.points, key=lambda point: (point.tenor, point.value))))
        object.__setattr__(self, "instruments", tuple(self.instruments))
        object.__setattr__(self, "interpolation", self.interpolation.strip().lower())
        object.__setattr__(self, "curve_kind", self.curve_kind.strip().lower())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())

    def as_curve_inputs(self) -> CurveInputs:
        """Return the equivalent calibration input bundle."""
        return CurveInputs(
            curve_id=self.curve_id,
            reference_date=self.reference_date,
            points=self.points,
            interpolation=self.interpolation,
            curve_kind=self.curve_kind,
            instruments=self.instruments,
            source=self.source,
        )


@dataclass(frozen=True, slots=True)
class IndexFixing:
    """Index fixing record with normalized index name."""

    index_name: str
    fixing_date: Date
    value: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "index_name", self.index_name.strip().upper())
        object.__setattr__(self, "value", _to_decimal(self.value))


@dataclass(frozen=True, slots=True)
class FxRate:
    """FX rate record with bid/ask/mid views and a raw decimal rate."""

    currency_pair: CurrencyPair
    rate: Decimal
    side: QuoteSide = QuoteSide.MID
    as_of: Date | None = None
    timestamp: datetime | None = None
    source: str | None = None
    source_type: SourceType | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "currency_pair", CurrencyPair.parse(self.currency_pair))
        _coerce_decimal_fields(self, "rate", "bid", "ask", "mid")
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        side_field = {
            QuoteSide.BID: "bid",
            QuoteSide.ASK: "ask",
            QuoteSide.MID: "mid",
        }[self.side]
        if getattr(self, side_field) is None:
            object.__setattr__(self, side_field, self.rate)
        if self.mid is None and self.bid is not None and self.ask is not None:
            object.__setattr__(self, "mid", (self.bid + self.ask) / Decimal(2))

    def quoted_value(self, side: QuoteSide = QuoteSide.MID) -> Decimal | None:
        """Return the side-specific FX rate when present."""
        if side is QuoteSide.BID:
            if self.bid is not None:
                return self.bid
            return self.rate if self.side is QuoteSide.BID else None
        if side is QuoteSide.ASK:
            if self.ask is not None:
                return self.ask
            return self.rate if self.side is QuoteSide.ASK else None
        if self.mid is not None:
            return self.mid
        return self.rate if self.side is QuoteSide.MID else None

    def for_side(self, side: QuoteSide) -> "FxRate" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        from dataclasses import replace

        return replace(self, rate=quoted_value, side=side)


@dataclass(frozen=True, slots=True)
class InflationFixing:
    """Inflation fixing record keyed by observation month."""

    index_name: str
    observation_month: YearMonth
    value: Decimal
    publication_date: Date | None = None
    interpolation: InflationInterpolation = InflationInterpolation.MONTHLY
    source: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "index_name", self.index_name.strip().upper())
        object.__setattr__(self, "observation_month", YearMonth.parse(self.observation_month))
        object.__setattr__(self, "value", _to_decimal(self.value))
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())


@dataclass(frozen=True, slots=True)
class EtfHolding:
    """ETF holding record with either quantity or weight populated."""

    instrument_id: InstrumentId
    quantity: Decimal | None = None
    weight: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        quantity = _to_decimal(self.quantity)
        weight = _to_decimal(self.weight)
        if quantity is None and weight is None:
            raise ValueError("EtfHolding requires either quantity or weight.")
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "weight", weight)


@dataclass(frozen=True, slots=True)
class EtfQuote:
    """ETF quote record with market price, NAV, and indicative NAV fields."""

    etf_id: EtfId
    market_price: Decimal | None = None
    nav: Decimal | None = None
    i_nav: Decimal | None = None
    shares_outstanding: Decimal | None = None
    as_of: Date | None = None
    timestamp: datetime | None = None
    source: str | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "etf_id", EtfId.parse(self.etf_id))
        _coerce_decimal_fields(self, "market_price", "nav", "i_nav", "shares_outstanding", "bid", "ask", "mid")
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        if self.mid is None and self.market_price is not None:
            object.__setattr__(self, "mid", self.market_price)
        if self.mid is None and self.bid is not None and self.ask is not None:
            object.__setattr__(self, "mid", (self.bid + self.ask) / Decimal(2))


@dataclass(frozen=True, slots=True)
class MarketDataSnapshot:
    """Immutable bundle of market-data records for snapshot-backed workflows."""

    as_of: Date | None = None
    quotes: tuple[RawQuote, ...] = ()
    repo_quotes: tuple[RepoQuote, ...] = ()
    swap_quotes: tuple[SwapQuote, ...] = ()
    basis_swap_quotes: tuple[BasisSwapQuote, ...] = ()
    bond_future_quotes: tuple[BondFutureQuote, ...] = ()
    fx_forward_quotes: tuple[FxForwardQuote, ...] = ()
    cds_quotes: tuple[CdsQuote, ...] = ()
    haircut_quotes: tuple[HaircutQuote, ...] = ()
    curves: tuple[CurveInputs, ...] = ()
    fixings: tuple[IndexFixing, ...] = ()
    etf_holdings: tuple[EtfHolding, ...] = ()
    volatility_surfaces: tuple[vol_surfaces.VolatilitySurface, ...] = ()
    fx_rates: tuple[FxRate, ...] = ()
    inflation_fixings: tuple[InflationFixing, ...] = ()
    etf_quotes: tuple[EtfQuote, ...] = ()

    def instrument_quotes(self) -> tuple[AnyInstrumentQuote, ...]:
        """Return all instrument-keyed quote records in deterministic family order."""
        return (
            *self.quotes,
            *self.repo_quotes,
            *self.swap_quotes,
            *self.basis_swap_quotes,
            *self.bond_future_quotes,
            *self.fx_forward_quotes,
            *self.cds_quotes,
            *self.haircut_quotes,
        )

    def quote_source(self) -> "InMemoryQuoteSource":
        """Build an in-memory quote source from the stored quotes."""
        from .sources import InMemoryQuoteSource

        return InMemoryQuoteSource(self.quotes)

    def curve_source(self) -> "InMemoryCurveSource":
        """Build an in-memory curve source from the stored curves."""
        from .sources import InMemoryCurveSource

        return InMemoryCurveSource(self.curves)

    def fixing_source(self) -> "InMemoryFixingSource":
        """Build an in-memory fixing source from the stored fixings."""
        from .sources import InMemoryFixingSource

        return InMemoryFixingSource(self.fixings)

    def volatility_source(self) -> "InMemoryVolatilitySource":
        """Build an in-memory volatility source from the stored surfaces."""
        from fuggers_py.vol_surfaces import InMemoryVolatilitySource

        return InMemoryVolatilitySource(self.volatility_surfaces)

    def fx_rate_source(self) -> "InMemoryFxRateSource":
        """Build an in-memory FX-rate source from the stored rates."""
        from .sources import InMemoryFxRateSource

        return InMemoryFxRateSource(self.fx_rates)

    def inflation_fixing_source(self) -> "InMemoryInflationFixingSource":
        """Build an in-memory inflation-fixing source from the stored fixings."""
        from .sources import InMemoryInflationFixingSource

        return InMemoryInflationFixingSource(self.inflation_fixings)

    def etf_quote_source(self) -> "InMemoryEtfQuoteSource":
        """Build an in-memory ETF quote source from the stored quotes."""
        from .sources import InMemoryEtfQuoteSource

        return InMemoryEtfQuoteSource(self.etf_quotes)

    def provider(self) -> "MarketDataProvider":
        """Build a composite provider over the snapshot's in-memory sources."""
        from .sources import MarketDataProvider

        return MarketDataProvider.from_snapshot(self)


CurveInputSet = CurveInputs


__all__ = [
    "CurveData",
    "CurveInput",
    "CurveInputSet",
    "CurveInputs",
    "CurveInstrumentType",
    "CurvePoint",
    "EtfHolding",
    "EtfQuote",
    "FxRate",
    "IndexFixing",
    "InflationFixing",
    "InflationInterpolation",
    "MarketDataSnapshot",
    "RawQuote",
    "SourceType",
]
