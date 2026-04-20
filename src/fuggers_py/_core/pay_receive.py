"""Shared pay/receive direction enum."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum


class PayReceive(str, Enum):
    """Direction of a cash-flow leg."""

    PAY = "PAY"
    RECEIVE = "RECEIVE"

    @classmethod
    def parse(cls, value: "PayReceive" | str) -> "PayReceive":
        """Parse a pay/receive flag."""

        if isinstance(value, cls):
            return value
        normalized = value.strip().upper()
        aliases = {
            "PAY": cls.PAY,
            "PAYER": cls.PAY,
            "RECEIVE": cls.RECEIVE,
            "RECEIVER": cls.RECEIVE,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"Unsupported pay/receive flag: {value!r}.") from exc

    def sign(self) -> Decimal:
        """Return ``-1`` for pay legs and ``+1`` for receive legs."""

        return Decimal(-1) if self is PayReceive.PAY else Decimal(1)

    def opposite(self) -> "PayReceive":
        """Return the opposite leg direction."""

        return PayReceive.RECEIVE if self is PayReceive.PAY else PayReceive.PAY


__all__ = ["PayReceive"]
