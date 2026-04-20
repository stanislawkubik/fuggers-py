"""Price quotes (`fuggers_py._reference.bonds.types.price_quote`)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from ..errors import InvalidBondSpec


class PriceQuoteConvention(str, Enum):
    """Interpretation of a quoted price."""

    PERCENT_OF_PAR = "PERCENT_OF_PAR"
    DECIMAL_OF_PAR = "DECIMAL_OF_PAR"


@dataclass(frozen=True, slots=True)
class PriceQuote:
    """Quoted bond price with explicit percent-of-par or decimal semantics."""

    value: Decimal
    convention: PriceQuoteConvention = PriceQuoteConvention.PERCENT_OF_PAR

    def as_percentage(self) -> Decimal:
        """Return the quote as percent-of-par."""
        if self.convention is PriceQuoteConvention.PERCENT_OF_PAR:
            return self.value
        if self.convention is PriceQuoteConvention.DECIMAL_OF_PAR:
            return self.value * Decimal(100)
        raise InvalidBondSpec(reason=f"Unknown price quote convention: {self.convention!r}.")  # pragma: no cover

    def as_decimal(self) -> Decimal:
        """Return the quote as a decimal of par."""
        if self.convention is PriceQuoteConvention.DECIMAL_OF_PAR:
            return self.value
        if self.convention is PriceQuoteConvention.PERCENT_OF_PAR:
            return self.value / Decimal(100)
        raise InvalidBondSpec(reason=f"Unknown price quote convention: {self.convention!r}.")  # pragma: no cover


__all__ = ["PriceQuote", "PriceQuoteConvention"]
