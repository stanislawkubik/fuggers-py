"""Rates-domain quote records for the first-layer public facade."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from fuggers_py._core.ids import CurrencyPair, InstrumentId, YearMonth
from fuggers_py._core.quote_support import (
    QuoteSide,
    _apply_two_sided_quote_defaults,
    _coerce_decimal_fields,
    _normalize_quote_side,
)
from fuggers_py._core.types import Currency, Date


@dataclass(frozen=True, slots=True)
class SwapQuote:
    """Swap quote record with rate expressed as a raw decimal."""

    instrument_id: InstrumentId
    rate: Decimal | None = None
    tenor: str | None = None
    floating_index: str | None = None
    fixed_frequency: str | None = None
    as_of: Date | None = None
    currency: Currency | None = None
    source: str | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        _coerce_decimal_fields(self, "rate", "bid", "ask", "mid")
        if self.tenor is not None:
            object.__setattr__(self, "tenor", self.tenor.strip().upper())
        if self.floating_index is not None:
            object.__setattr__(self, "floating_index", self.floating_index.strip().upper())
        if self.fixed_frequency is not None:
            object.__setattr__(self, "fixed_frequency", self.fixed_frequency.strip().upper())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        _apply_two_sided_quote_defaults(self, value_field="rate")

    def quoted_value(self, side: QuoteSide = QuoteSide.MID) -> Decimal | None:
        """Return the side-specific swap rate when present."""
        resolved_side = _normalize_quote_side(side)
        if resolved_side is QuoteSide.BID:
            return self.bid
        if resolved_side is QuoteSide.ASK:
            return self.ask
        return self.mid

    def for_side(self, side: QuoteSide) -> "SwapQuote" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        return replace(self, rate=quoted_value)


@dataclass(frozen=True, slots=True)
class BasisSwapQuote:
    """Basis swap quote record with basis expressed as a raw decimal."""

    instrument_id: InstrumentId
    basis: Decimal | None = None
    tenor: str | None = None
    pay_index: str | None = None
    receive_index: str | None = None
    as_of: Date | None = None
    currency: Currency | None = None
    source: str | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        _coerce_decimal_fields(self, "basis", "bid", "ask", "mid")
        if self.tenor is not None:
            object.__setattr__(self, "tenor", self.tenor.strip().upper())
        if self.pay_index is not None:
            object.__setattr__(self, "pay_index", self.pay_index.strip().upper())
        if self.receive_index is not None:
            object.__setattr__(self, "receive_index", self.receive_index.strip().upper())
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        _apply_two_sided_quote_defaults(self, value_field="basis")

    def quoted_value(self, side: QuoteSide = QuoteSide.MID) -> Decimal | None:
        """Return the side-specific basis when present."""
        resolved_side = _normalize_quote_side(side)
        if resolved_side is QuoteSide.BID:
            return self.bid
        if resolved_side is QuoteSide.ASK:
            return self.ask
        return self.mid

    def for_side(self, side: QuoteSide) -> "BasisSwapQuote" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        return replace(self, basis=quoted_value)


@dataclass(frozen=True, slots=True)
class BondFutureQuote:
    """Bond future quote record."""

    instrument_id: InstrumentId
    price: Decimal | None = None
    delivery_month: YearMonth | None = None
    conversion_factor: Decimal | None = None
    implied_repo_rate: Decimal | None = None
    cheapest_to_deliver: InstrumentId | None = None
    as_of: Date | None = None
    currency: Currency | None = None
    source: str | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.delivery_month is not None:
            object.__setattr__(self, "delivery_month", YearMonth.parse(self.delivery_month))
        if self.cheapest_to_deliver is not None:
            object.__setattr__(self, "cheapest_to_deliver", InstrumentId.parse(self.cheapest_to_deliver))
        _coerce_decimal_fields(self, "price", "conversion_factor", "implied_repo_rate", "bid", "ask", "mid")
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        _apply_two_sided_quote_defaults(self, value_field="price")

    def quoted_value(self, side: QuoteSide = QuoteSide.MID) -> Decimal | None:
        """Return the side-specific futures price when present."""
        resolved_side = _normalize_quote_side(side)
        if resolved_side is QuoteSide.BID:
            return self.bid
        if resolved_side is QuoteSide.ASK:
            return self.ask
        return self.mid

    def for_side(self, side: QuoteSide) -> "BondFutureQuote" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        return replace(self, price=quoted_value)


@dataclass(frozen=True, slots=True)
class FxForwardQuote:
    """FX forward quote record."""

    currency_pair: CurrencyPair
    forward_rate: Decimal | None = None
    points: Decimal | None = None
    spot_rate: Decimal | None = None
    as_of: Date | None = None
    source: str | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "currency_pair", CurrencyPair.parse(self.currency_pair))
        _coerce_decimal_fields(self, "forward_rate", "points", "spot_rate", "bid", "ask", "mid")
        if self.forward_rate is None and self.spot_rate is not None and self.points is not None:
            object.__setattr__(self, "forward_rate", self.spot_rate + self.points)
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        _apply_two_sided_quote_defaults(self, value_field="forward_rate")

    @property
    def instrument_id(self) -> InstrumentId:
        """Expose the currency pair through the common instrument-id surface."""
        return InstrumentId.parse(self.currency_pair)

    @property
    def currency(self) -> Currency:
        """Return the quote currency for the outright forward rate."""
        return self.currency_pair.quote

    def quoted_value(self, side: QuoteSide = QuoteSide.MID) -> Decimal | None:
        """Return the side-specific forward rate when present."""
        resolved_side = _normalize_quote_side(side)
        if resolved_side is QuoteSide.BID:
            return self.bid
        if resolved_side is QuoteSide.ASK:
            return self.ask
        return self.mid

    def for_side(self, side: QuoteSide) -> "FxForwardQuote" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        return replace(self, forward_rate=quoted_value)


__all__ = [
    "BasisSwapQuote",
    "BondFutureQuote",
    "FxForwardQuote",
    "SwapQuote",
]
