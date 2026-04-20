"""Shared quote-side helpers used by public quote records."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum


class QuoteSide(str, Enum):
    """Canonical quote-side labels used by quote records."""

    BID = "bid"
    ASK = "ask"
    MID = "mid"


def _normalize_quote_side(side: QuoteSide | str | object) -> QuoteSide:
    """Resolve quote-side inputs from compatible enums or strings."""

    if isinstance(side, QuoteSide):
        return side
    raw_value = getattr(side, "value", side)
    if isinstance(raw_value, str):
        normalized = raw_value.strip().lower()
        for candidate in QuoteSide:
            if candidate.value == normalized:
                return candidate
    raise ValueError("Quote side must be bid, ask, or mid.")


def _to_decimal(value: object | None) -> Decimal | None:
    """Coerce a nullable scalar to ``Decimal``."""

    if value is None or isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _coerce_decimal_fields(instance: object, *names: str) -> None:
    """Normalize named attributes on a dataclass-like instance to decimals."""

    for name in names:
        value = getattr(instance, name)
        coerced = _to_decimal(value)
        if coerced is not None:
            object.__setattr__(instance, name, coerced)


def _apply_two_sided_quote_defaults(instance: object, *, value_field: str) -> None:
    """Populate bid/ask/mid defaults for two-sided quote records."""

    value = getattr(instance, value_field)
    if getattr(instance, "mid") is None and value is not None:
        object.__setattr__(instance, "mid", value)
    bid = getattr(instance, "bid")
    ask = getattr(instance, "ask")
    if getattr(instance, "mid") is None and bid is not None and ask is not None:
        object.__setattr__(instance, "mid", (bid + ask) / Decimal(2))


__all__ = [
    "QuoteSide",
    "_apply_two_sided_quote_defaults",
    "_coerce_decimal_fields",
    "_normalize_quote_side",
    "_to_decimal",
]
