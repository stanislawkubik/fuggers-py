"""Canonical market quote records and quote abstractions."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Protocol, TypeAlias, runtime_checkable

from fuggers_py.core.ids import CurrencyPair, InstrumentId, YearMonth
from fuggers_py.core.types import Currency, Date
from fuggers_py.market.state import QuoteSide
from fuggers_py.products.bonds.traits import Bond

from ._shared import _apply_two_sided_quote_defaults, _coerce_decimal_fields


class SourceType(str, Enum):
    """Origin classification for a quote or surface."""

    LIVE = "LIVE"
    CLOSE = "CLOSE"
    REFERENCE = "REFERENCE"
    MODEL = "MODEL"
    MANUAL = "MANUAL"


@dataclass(frozen=True, slots=True)
class RawQuote:
    """Generic quote record with normalized identifiers and raw decimals.

    ``value`` stores the canonical quote value. Bid/ask/mid views can be
    derived from the stored fields when present. The economic meaning comes
    from the instrument identifier and source metadata rather than from this
    container.
    """

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


def deliverable_bpv_regressor(bpv: object, *, deliverable: bool) -> float:
    """Return the standard deliverability regressor encoding.

    This keeps ``BondQuote.regressors['deliverable_bpv']`` in one simple
    quote-level form: ``bpv`` when the bond is deliverable, otherwise ``0.0``.
    """

    if not deliverable:
        return 0.0
    try:
        numeric_bpv = float(bpv)
    except (TypeError, ValueError) as exc:
        raise ValueError("bpv must be a finite float-like value.") from exc
    if not math.isfinite(numeric_bpv):
        raise ValueError("bpv must be a finite float-like value.")
    return numeric_bpv


@dataclass(frozen=True, slots=True)
class BondQuote:
    """Market quote bound to a concrete bond instrument.

    ``regressors`` is the quote-level home for time-varying external variables
    used by ``GlobalFitCalibrator``. Examples include ``issue_size_bn``,
    ``issue_age_years``, ``deliverable_bpv``, and ``repo_specialness_bp``.
    Those values live on the quote, not on the bond instrument, because they
    can change from one observation date to the next.

    ``fit_weight`` is the quote-level weight used by
    ``GlobalFitCalibrator`` in its weighted least-squares fit.
    """

    instrument: Bond
    clean_price: Decimal | None = None
    dirty_price: Decimal | None = None
    accrued_interest: Decimal | None = None
    yield_to_maturity: Decimal | None = None
    yield_to_worst: Decimal | None = None
    as_of: Date | None = None
    source: str | None = None
    currency: Currency | None = None
    # Observation-date regressors for GlobalFitCalibrator, for example
    # issue_size_bn, issue_age_years, deliverable_bpv, or repo_specialness_bp.
    regressors: Mapping[str, float] | None = None
    # Quote-level weight used by GlobalFitCalibrator in the weighted-L2 fit.
    fit_weight: float | None = None

    def __post_init__(self) -> None:
        _coerce_decimal_fields(
            self,
            "clean_price",
            "dirty_price",
            "accrued_interest",
            "yield_to_maturity",
            "yield_to_worst",
        )
        instrument_id = getattr(self.instrument, "instrument_id", None)
        if instrument_id is None:
            raise ValueError("BondQuote requires a concrete bond instrument with instrument_id.")
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())
        instrument_currency = self.instrument.currency()
        if self.currency is None:
            object.__setattr__(self, "currency", instrument_currency)
        elif self.currency != instrument_currency:
            raise ValueError("BondQuote currency must match the bond currency.")
        if self.regressors is not None:
            if not isinstance(self.regressors, Mapping):
                raise ValueError("BondQuote.regressors must be a mapping from regressor name to float.")
            normalized_regressors: dict[str, float] = {}
            for name, value in self.regressors.items():
                if not isinstance(name, str):
                    raise ValueError("BondQuote.regressors must use string regressor names.")
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("BondQuote.regressors must map each regressor name to a finite float.") from exc
                if not math.isfinite(numeric_value):
                    raise ValueError("BondQuote.regressors must map each regressor name to a finite float.")
                normalized_regressors[name] = numeric_value
            object.__setattr__(self, "regressors", MappingProxyType(normalized_regressors))
        if self.fit_weight is not None:
            try:
                fit_weight = float(self.fit_weight)
            except (TypeError, ValueError) as exc:
                raise ValueError("BondQuote.fit_weight must be a finite float.") from exc
            if not math.isfinite(fit_weight):
                raise ValueError("BondQuote.fit_weight must be a finite float.")
            object.__setattr__(self, "fit_weight", fit_weight)

    @property
    def instrument_id(self) -> InstrumentId:
        """Return the instrument id of the bound bond."""
        instrument_id = getattr(self.instrument, "instrument_id", None)
        if instrument_id is None:
            raise ValueError("BondQuote requires a concrete bond instrument with instrument_id.")
        return InstrumentId.parse(instrument_id)

    def resolved_settlement_date(self) -> Date:
        """Return the pricing date carried by the quote."""
        if self.as_of is None:
            raise ValueError("BondQuote requires as_of.")
        return self.as_of


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
        if side is QuoteSide.BID:
            return self.bid
        if side is QuoteSide.ASK:
            return self.ask
        return self.mid

    def for_side(self, side: QuoteSide) -> "RepoQuote" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        return replace(self, rate=quoted_value)


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
        if side is QuoteSide.BID:
            return self.bid
        if side is QuoteSide.ASK:
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
        if side is QuoteSide.BID:
            return self.bid
        if side is QuoteSide.ASK:
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
        if side is QuoteSide.BID:
            return self.bid
        if side is QuoteSide.ASK:
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
        if side is QuoteSide.BID:
            return self.bid
        if side is QuoteSide.ASK:
            return self.ask
        return self.mid

    def for_side(self, side: QuoteSide) -> "FxForwardQuote" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        return replace(self, forward_rate=quoted_value)


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
        if side is QuoteSide.BID:
            return self.bid
        if side is QuoteSide.ASK:
            return self.ask
        return self.mid

    def for_side(self, side: QuoteSide) -> "CdsQuote" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        return replace(self, par_spread=quoted_value)


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
        if side is QuoteSide.BID:
            return self.bid
        if side is QuoteSide.ASK:
            return self.ask
        return self.mid

    def for_side(self, side: QuoteSide) -> "HaircutQuote" | None:
        """Return a copy normalized to a different quote side."""
        quoted_value = self.quoted_value(side)
        if quoted_value is None:
            return None
        return replace(self, haircut=quoted_value)


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


# ``RawQuote`` remains the public compatibility surface. ``ScalarQuote`` is the
# canonical new name for the same generic scalar-instrument quote shape.
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
