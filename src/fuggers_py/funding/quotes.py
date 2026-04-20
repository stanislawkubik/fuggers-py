"""Funding-domain quote records for the first-layer public facade."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from fuggers_py._core.ids import InstrumentId
from fuggers_py._core.quote_support import (
    QuoteSide,
    _apply_two_sided_quote_defaults,
    _coerce_decimal_fields,
    _normalize_quote_side,
)
from fuggers_py._core.types import Currency, Date


@dataclass(frozen=True, slots=True)
class RepoQuote:
    """Repo quote record with rate and haircut expressed as raw decimals."""

    instrument_id: InstrumentId
    rate: Decimal | None = None
    haircut: Decimal | None = None
    start_date: Date | None = None
    end_date: Date | None = None
    term: str | None = None
    collateral_type: str | None = None
    as_of: Date | None = None
    currency: Currency | None = None
    source: str | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        _coerce_decimal_fields(self, "rate", "haircut", "bid", "ask", "mid")
        if self.term is not None:
            object.__setattr__(self, "term", self.term.strip().upper())
        if self.collateral_type is not None:
            object.__setattr__(self, "collateral_type", self.collateral_type.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        _apply_two_sided_quote_defaults(self, value_field="rate")

    def quoted_value(self, side: QuoteSide = QuoteSide.MID) -> Decimal | None:
        """Return the side-specific repo rate when present."""
        resolved_side = _normalize_quote_side(side)
        if resolved_side is QuoteSide.BID:
            return self.bid
        if resolved_side is QuoteSide.ASK:
            return self.ask
        return self.mid

    def for_side(self, side: QuoteSide) -> "RepoQuote" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        return replace(self, rate=quoted_value)


@dataclass(frozen=True, slots=True)
class HaircutQuote:
    """Haircut quote record with haircut expressed as a raw decimal."""

    instrument_id: InstrumentId
    haircut: Decimal | None = None
    collateral_type: str | None = None
    as_of: Date | None = None
    currency: Currency | None = None
    source: str | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        _coerce_decimal_fields(self, "haircut", "bid", "ask", "mid")
        if self.collateral_type is not None:
            object.__setattr__(self, "collateral_type", self.collateral_type.strip())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        _apply_two_sided_quote_defaults(self, value_field="haircut")

    def quoted_value(self, side: QuoteSide = QuoteSide.MID) -> Decimal | None:
        """Return the side-specific haircut when present."""
        resolved_side = _normalize_quote_side(side)
        if resolved_side is QuoteSide.BID:
            return self.bid
        if resolved_side is QuoteSide.ASK:
            return self.ask
        return self.mid

    def for_side(self, side: QuoteSide) -> "HaircutQuote" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        return replace(self, haircut=quoted_value)


__all__ = [
    "HaircutQuote",
    "RepoQuote",
]
