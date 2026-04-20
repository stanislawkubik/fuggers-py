"""Credit-domain quote records for the first-layer public facade."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from fuggers_py._core.ids import InstrumentId
from fuggers_py._core.quote_support import QuoteSide, _coerce_decimal_fields, _normalize_quote_side
from fuggers_py._core.types import Currency, Date


@dataclass(frozen=True, slots=True)
class CdsQuote:
    """CDS quote record with raw decimal spread and recovery fields."""

    instrument_id: InstrumentId
    par_spread: Decimal | None = None
    upfront: Decimal | None = None
    recovery_rate: Decimal | None = None
    tenor: str | None = None
    reference_entity: str | None = None
    as_of: Date | None = None
    currency: Currency | None = None
    source: str | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        _coerce_decimal_fields(self, "par_spread", "upfront", "recovery_rate", "bid", "ask", "mid")
        if self.tenor is not None:
            object.__setattr__(self, "tenor", self.tenor.strip().upper())
        if self.reference_entity is not None:
            object.__setattr__(self, "reference_entity", self.reference_entity.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        if self.mid is None and self.bid is not None and self.ask is not None:
            object.__setattr__(self, "mid", (self.bid + self.ask) / Decimal(2))
        elif self.mid is None:
            object.__setattr__(self, "mid", self.par_spread if self.par_spread is not None else self.upfront)

    def quoted_value(self, side: QuoteSide = QuoteSide.MID) -> Decimal | None:
        """Return the side-specific CDS spread when present."""
        resolved_side = _normalize_quote_side(side)
        if resolved_side is QuoteSide.BID:
            return self.bid
        if resolved_side is QuoteSide.ASK:
            return self.ask
        return self.mid

    def for_side(self, side: QuoteSide) -> "CdsQuote" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        return replace(self, par_spread=quoted_value)


__all__ = [
    "CdsQuote",
]
