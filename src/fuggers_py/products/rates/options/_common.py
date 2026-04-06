"""Shared option-domain helpers for rates options.

The module defines the option type enum used across the rates options
subpackage and a small decimal coercion helper for parsing quoted inputs.
Option signs follow the standard call/put convention used by the option
wrappers in this package.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class OptionType(str, Enum):
    """Call/put option type with the standard sign convention."""

    CALL = "CALL"
    PUT = "PUT"

    @classmethod
    def parse(cls, value: "OptionType" | str) -> "OptionType":
        """Parse a call/put label or short alias."""
        if isinstance(value, cls):
            return value
        normalized = value.strip().upper()
        aliases = {
            "CALL": cls.CALL,
            "C": cls.CALL,
            "PUT": cls.PUT,
            "P": cls.PUT,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"Unsupported option type: {value!r}.") from exc

    def sign(self) -> Decimal:
        """Return ``+1`` for calls and ``-1`` for puts."""
        return Decimal(1) if self is OptionType.CALL else Decimal(-1)


__all__ = ["OptionType"]
