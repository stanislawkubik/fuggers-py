"""Small shared helpers for RV modules."""

from __future__ import annotations

from decimal import Decimal


def to_decimal(value: object) -> Decimal:
    """Return ``value`` as a ``Decimal`` without changing its meaning."""

    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


__all__ = ["to_decimal"]
