"""Shared option-domain helpers for rates options.

The module defines the option type enum used across the rates options
subpackage and a small decimal coercion helper for parsing quoted inputs.
Option signs follow the standard call/put convention used by the option
wrappers in this package.
"""

from __future__ import annotations

from decimal import Decimal


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


__all__: list[str] = []
