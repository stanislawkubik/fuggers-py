"""Index identifiers for multi-curve environments.

These identifiers are used as stable keys for discount and projection curves.
Rate-index names are normalized to upper case when constructed with
``RateIndex.new``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fuggers_py._core.types import Currency

if TYPE_CHECKING:
    from fuggers_py._core import Tenor


@dataclass(frozen=True, slots=True)
class CurrencyPair:
    """Base/quote currency pair identifier used for FX-style curve keys.

    Attributes
    ----------
    base
        Base currency.
    quote
        Quote currency.
    """

    base: Currency
    quote: Currency

    def code(self) -> str:
        """Return the canonical ``BASE/QUOTE`` code."""

        return f"{self.base.code()}/{self.quote.code()}"

    def inverse(self) -> "CurrencyPair":
        """Return the inverted currency pair."""

        return CurrencyPair(base=self.quote, quote=self.base)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.code()


@dataclass(frozen=True, slots=True)
class RateIndex:
    """Identifier for a projected floating-rate index.

    Attributes
    ----------
    name
        Normalized upper-case index name.
    tenor
        Index tenor such as ``3M`` or ``6M``.
    currency
        Currency in which the index is quoted.
    """

    name: str
    tenor: Tenor
    currency: Currency

    @classmethod
    def new(cls, name: str, tenor: Tenor, currency: Currency) -> "RateIndex":
        """Create a normalized rate-index identifier."""

        if not isinstance(name, str) or not name.strip():
            raise ValueError("RateIndex name must be a non-empty string.")
        return cls(name=name.strip().upper(), tenor=tenor, currency=currency)

    def key(self) -> str:
        """Return the canonical lookup key for the index."""

        return f"{self.currency.code()}-{self.name}-{self.tenor}"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.key()


__all__ = ["CurrencyPair", "RateIndex"]
