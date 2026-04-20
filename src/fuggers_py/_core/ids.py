"""Foundational typed identifiers shared across the library.

The identifier types normalize whitespace on construction and parsing. They
also provide explicit parsers for typed inputs such as currency pairs and
year-month keys used by market-data and reference-data records.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .types import Currency


def _normalize(value: object) -> str:
    """Normalize an identifier payload to a non-empty string."""
    text = str(value).strip()
    if not text:
        raise ValueError("Identifier value must be non-empty.")
    return text


def _normalize_currency(value: Currency | str) -> Currency:
    """Normalize a currency code or enum member to ``Currency``."""
    if isinstance(value, Currency):
        return value
    return Currency.from_code(_normalize(value))


@dataclass(frozen=True, slots=True)
class InstrumentId:
    """Normalized instrument identifier.

    The value is stripped of leading and trailing whitespace before storage.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _normalize(self.value))

    @classmethod
    def parse(cls, value: object) -> InstrumentId:
        """Parse and normalize an instrument identifier from any object."""
        return cls(_normalize(value))

    @classmethod
    def from_string(cls, value: str) -> InstrumentId:
        """Compatibility alias for :meth:`parse`."""
        return cls.parse(value)

    def as_str(self) -> str:
        """Return the normalized identifier string."""
        return self.value

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class CurveId:
    """Normalized curve identifier.

    The value is stripped of leading and trailing whitespace before storage.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _normalize(self.value))

    @classmethod
    def parse(cls, value: object) -> CurveId:
        """Parse and normalize a curve identifier from any object."""
        return cls(_normalize(value))

    @classmethod
    def from_string(cls, value: str) -> CurveId:
        """Compatibility alias for :meth:`parse`."""
        return cls.parse(value)

    def as_str(self) -> str:
        """Return the normalized identifier string."""
        return self.value

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class PortfolioId:
    """Normalized portfolio identifier.

    The value is stripped of leading and trailing whitespace before storage.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _normalize(self.value))

    @classmethod
    def parse(cls, value: object) -> PortfolioId:
        """Parse and normalize a portfolio identifier from any object."""
        return cls(_normalize(value))

    @classmethod
    def from_string(cls, value: str) -> PortfolioId:
        """Compatibility alias for :meth:`parse`."""
        return cls.parse(value)

    def as_str(self) -> str:
        """Return the normalized identifier string."""
        return self.value

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class EtfId:
    """Normalized ETF identifier.

    The value is stripped of leading and trailing whitespace before storage.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _normalize(self.value))

    @classmethod
    def parse(cls, value: object) -> EtfId:
        """Parse and normalize an ETF identifier from any object."""
        return cls(_normalize(value))

    @classmethod
    def from_string(cls, value: str) -> EtfId:
        """Compatibility alias for :meth:`parse`."""
        return cls.parse(value)

    def as_str(self) -> str:
        """Return the normalized identifier string."""
        return self.value

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class VolSurfaceId:
    """Normalized volatility-surface identifier.

    The value is stripped of leading and trailing whitespace before storage.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _normalize(self.value))

    @classmethod
    def parse(cls, value: object) -> VolSurfaceId:
        """Parse and normalize a volatility-surface identifier from any object."""
        return cls(_normalize(value))

    @classmethod
    def from_string(cls, value: str) -> VolSurfaceId:
        """Compatibility alias for :meth:`parse`."""
        return cls.parse(value)

    def as_str(self) -> str:
        """Return the normalized identifier string."""
        return self.value

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class CurrencyPair:
    """Normalized base/quote currency pair.

    Parsing accepts separator variants such as ``AAA/BBB`` and compact
    ``AAABBB`` inputs. Whitespace and separator noise are stripped before
    validation, and the stored pair always keeps the base currency first.
    """

    base: Currency
    quote: Currency

    def __post_init__(self) -> None:
        object.__setattr__(self, "base", _normalize_currency(self.base))
        object.__setattr__(self, "quote", _normalize_currency(self.quote))

    @classmethod
    def parse(cls, value: object) -> CurrencyPair:
        """Parse a currency pair from a typed or string input.

        Accepts existing `CurrencyPair` objects, slash-separated strings, and
        compact six-letter ISO pairs.
        """
        if isinstance(value, cls):
            return value
        text = _normalize(value).upper()
        compact = re.sub(r"[\s:_-]+", "/", text)
        if "/" in compact:
            parts = [part for part in compact.split("/") if part]
        elif len(compact) == 6 and compact.isalpha():
            parts = [compact[:3], compact[3:]]
        else:
            raise ValueError(f"Invalid currency pair: {value!r}")
        if len(parts) != 2:
            raise ValueError(f"Invalid currency pair: {value!r}")
        return cls(_normalize_currency(parts[0]), _normalize_currency(parts[1]))

    @classmethod
    def from_string(cls, value: str) -> CurrencyPair:
        """Compatibility alias for :meth:`parse`."""
        return cls.parse(value)

    def as_str(self) -> str:
        """Return the canonical ``AAA/BBB`` representation."""
        return f"{self.base.code()}/{self.quote.code()}"

    @property
    def value(self) -> str:
        return self.as_str()

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.as_str()


@dataclass(frozen=True, slots=True)
class YearMonth:
    """Year-month identifier in canonical ``YYYY-MM`` form."""

    year: int
    month: int

    def __post_init__(self) -> None:
        if self.year < 1:
            raise ValueError("YearMonth.year must be positive.")
        if not 1 <= self.month <= 12:
            raise ValueError("YearMonth.month must be between 1 and 12.")

    @classmethod
    def parse(cls, value: object) -> YearMonth:
        """Parse a strict ``YYYY-MM`` year-month value from any object."""
        if isinstance(value, cls):
            return value
        text = _normalize(value)
        match = re.fullmatch(r"(\d{4})-(\d{2})", text)
        if match is None:
            raise ValueError(f"Invalid year-month value: {value!r}")
        return cls(year=int(match.group(1)), month=int(match.group(2)))

    @classmethod
    def from_string(cls, value: str) -> YearMonth:
        """Compatibility alias for :meth:`parse`."""
        return cls.parse(value)

    def as_str(self) -> str:
        """Return the canonical ``YYYY-MM`` representation."""
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def value(self) -> str:
        return self.as_str()

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.as_str()


__all__ = [
    "CurrencyPair",
    "CurveId",
    "EtfId",
    "InstrumentId",
    "PortfolioId",
    "VolSurfaceId",
    "YearMonth",
]
