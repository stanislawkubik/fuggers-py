"""Shared market-layer helpers.

These helpers stay private to the market package. Public code should import
the concrete records from ``quotes``, ``snapshot``, ``sources``, and
``vol_surfaces`` instead.
"""

from __future__ import annotations

from decimal import Decimal

def _to_decimal(value: object | None) -> Decimal | None:
    """Coerce a nullable market-data scalar to ``Decimal``."""
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
    "_apply_two_sided_quote_defaults",
    "_coerce_decimal_fields",
    "_to_decimal",
]
