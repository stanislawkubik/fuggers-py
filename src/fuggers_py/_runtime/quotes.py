"""Internal quote records and quote protocols."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum
from typing import Protocol, TypeAlias, runtime_checkable

from fuggers_py.bonds.quotes import BondQuote, deliverable_bpv_regressor
from fuggers_py._core.ids import InstrumentId
from fuggers_py._core.types import Currency, Date
from fuggers_py.credit.quotes import CdsQuote
from fuggers_py.funding.quotes import HaircutQuote, RepoQuote
from fuggers_py._market._shared import _coerce_decimal_fields
from fuggers_py._market.state import QuoteSide
from fuggers_py.rates.quotes import BasisSwapQuote, BondFutureQuote, FxForwardQuote, SwapQuote


class SourceType(str, Enum):
    """Origin classification for a quote or surface."""

    LIVE = "LIVE"
    CLOSE = "CLOSE"
    REFERENCE = "REFERENCE"
    MODEL = "MODEL"
    MANUAL = "MANUAL"


@dataclass(frozen=True, slots=True)
class RawQuote:
    """Generic quote record with normalized identifiers and raw decimals."""

    instrument_id: InstrumentId
    value: Decimal
    as_of: Date | None = None
    currency: Currency | None = None
    source: str | None = None
    source_type: SourceType | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal | None = None
    last: Decimal | None = None
    bid_size: Decimal | None = None
    ask_size: Decimal | None = None
    last_size: Decimal | None = None
    yield_to_maturity: Decimal | None = None
    yield_to_worst: Decimal | None = None
    venue: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        _coerce_decimal_fields(
            self,
            "value",
            "bid",
            "ask",
            "mid",
            "last",
            "bid_size",
            "ask_size",
            "last_size",
            "yield_to_maturity",
            "yield_to_worst",
        )
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        if self.venue is not None:
            object.__setattr__(self, "venue", self.venue.strip())
        if self.mid is None:
            object.__setattr__(self, "mid", self.value)
        if self.mid is None and self.bid is not None and self.ask is not None:
            object.__setattr__(self, "mid", (self.bid + self.ask) / Decimal(2))

    def quoted_value(self, side: QuoteSide = QuoteSide.MID) -> Decimal | None:
        """Return the best available quote for the requested side."""
        if side is QuoteSide.BID:
            return self.bid
        if side is QuoteSide.ASK:
            return self.ask
        if self.mid is not None:
            return self.mid
        return self.value

    def for_side(self, side: QuoteSide) -> "RawQuote" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        return replace(self, value=quoted_value)


@runtime_checkable
class InstrumentQuote(Protocol):
    """Minimal structural contract for quotes keyed by instrument id."""

    @property
    def instrument_id(self) -> InstrumentId:
        ...

    @property
    def as_of(self) -> Date | None:
        ...

    @property
    def source(self) -> str | None:
        ...

    @property
    def currency(self) -> Currency | None:
        ...


ScalarQuote = RawQuote

AnyInstrumentQuote: TypeAlias = (
    ScalarQuote
    | BondQuote
    | RepoQuote
    | SwapQuote
    | BasisSwapQuote
    | BondFutureQuote
    | FxForwardQuote
    | CdsQuote
    | HaircutQuote
)


__all__ = [
    "AnyInstrumentQuote",
    "BasisSwapQuote",
    "BondFutureQuote",
    "BondQuote",
    "CdsQuote",
    "deliverable_bpv_regressor",
    "FxForwardQuote",
    "HaircutQuote",
    "InstrumentQuote",
    "RawQuote",
    "RepoQuote",
    "ScalarQuote",
    "SourceType",
    "SwapQuote",
]
