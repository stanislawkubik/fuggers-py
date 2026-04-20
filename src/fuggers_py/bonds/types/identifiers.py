"""Identifiers and calendar ids (`fuggers_py.bonds.types.identifiers`)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..errors import InvalidIdentifier


_ALNUM_RE = re.compile(r"^[A-Z0-9]+$")
_ALPHA2_RE = re.compile(r"^[A-Z]{2}$")
_SEDOL_VOWELS = set("AEIOU")


def _base36_value(ch: str) -> int:
    if "0" <= ch <= "9":
        return int(ch)
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 10
    raise ValueError(f"Unsupported character: {ch!r}")


def _luhn_is_valid(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d = d // 10 + d % 10
        total += d
    return total % 10 == 0


def _isin_digits(isin: str) -> str:
    parts: list[str] = []
    for ch in isin:
        if ch.isdigit():
            parts.append(ch)
        else:
            parts.append(str(_base36_value(ch)))
    return "".join(parts)


def _cusip_check_digit(cusip8: str) -> int:
    total = 0
    for i, ch in enumerate(cusip8):
        v = _base36_value(ch)
        if (i + 1) % 2 == 0:
            v *= 2
        total += v // 10 + v % 10
    return (10 - (total % 10)) % 10


def _sedol_check_digit(sedol6: str) -> int:
    weights = [1, 3, 1, 7, 3, 9]
    total = 0
    for ch, w in zip(sedol6, weights, strict=True):
        total += _base36_value(ch) * w
    return (10 - (total % 10)) % 10


def _clean_id(value: str, *, identifier_type: str) -> str:
    if not isinstance(value, str):
        raise InvalidIdentifier(identifier_type=identifier_type, value=str(value), reason="must be a string")
    cleaned = value.strip().upper()
    if not cleaned:
        raise InvalidIdentifier(identifier_type=identifier_type, value=value, reason="must be non-empty")
    return cleaned


@dataclass(frozen=True, slots=True)
class Isin:
    """International Securities Identification Number wrapper."""

    value: str

    @classmethod
    def new(cls, value: str) -> "Isin":
        v = _clean_id(value, identifier_type="ISIN")
        if len(v) != 12:
            raise InvalidIdentifier(identifier_type="ISIN", value=v, reason="must be 12 characters")
        if not _ALNUM_RE.match(v):
            raise InvalidIdentifier(identifier_type="ISIN", value=v, reason="must be alphanumeric")
        if not _ALPHA2_RE.match(v[:2]):
            raise InvalidIdentifier(identifier_type="ISIN", value=v, reason="must start with a 2-letter country code")
        if not v[-1].isdigit():
            raise InvalidIdentifier(identifier_type="ISIN", value=v, reason="must end with a digit check digit")
        if not _luhn_is_valid(_isin_digits(v)):
            raise InvalidIdentifier(identifier_type="ISIN", value=v, reason="invalid check digit")
        return cls(v)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class Cusip:
    """CUSIP wrapper with check-digit validation."""

    value: str

    @classmethod
    def new(cls, value: str) -> "Cusip":
        v = _clean_id(value, identifier_type="CUSIP")
        if len(v) != 9:
            raise InvalidIdentifier(identifier_type="CUSIP", value=v, reason="must be 9 characters")
        if not _ALNUM_RE.match(v):
            raise InvalidIdentifier(identifier_type="CUSIP", value=v, reason="must be alphanumeric")
        if not v[-1].isdigit():
            raise InvalidIdentifier(identifier_type="CUSIP", value=v, reason="must end with a digit check digit")
        expected = _cusip_check_digit(v[:8])
        if int(v[-1]) != expected:
            raise InvalidIdentifier(identifier_type="CUSIP", value=v, reason="invalid check digit")
        return cls(v)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class Sedol:
    """SEDOL wrapper with check-digit validation."""

    value: str

    @classmethod
    def new(cls, value: str) -> "Sedol":
        v = _clean_id(value, identifier_type="SEDOL")
        if len(v) != 7:
            raise InvalidIdentifier(identifier_type="SEDOL", value=v, reason="must be 7 characters")
        if not _ALNUM_RE.match(v):
            raise InvalidIdentifier(identifier_type="SEDOL", value=v, reason="must be alphanumeric")
        if any(ch in _SEDOL_VOWELS for ch in v):
            raise InvalidIdentifier(identifier_type="SEDOL", value=v, reason="must not contain vowels (A/E/I/O/U)")
        if not v[-1].isdigit():
            raise InvalidIdentifier(identifier_type="SEDOL", value=v, reason="must end with a digit check digit")
        expected = _sedol_check_digit(v[:6])
        if int(v[-1]) != expected:
            raise InvalidIdentifier(identifier_type="SEDOL", value=v, reason="invalid check digit")
        return cls(v)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class Figi:
    """FIGI wrapper with the standard BBG prefix check."""

    value: str

    @classmethod
    def new(cls, value: str) -> "Figi":
        v = _clean_id(value, identifier_type="FIGI")
        if len(v) != 12:
            raise InvalidIdentifier(identifier_type="FIGI", value=v, reason="must be 12 characters")
        if not _ALNUM_RE.match(v):
            raise InvalidIdentifier(identifier_type="FIGI", value=v, reason="must be alphanumeric")
        if not v.startswith("BBG"):
            raise InvalidIdentifier(identifier_type="FIGI", value=v, reason="must start with 'BBG'")
        return cls(v)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class BondIdentifiers:
    """Optional identifier bundle for a bond instrument."""

    isin: Isin | None = None
    cusip: Cusip | None = None
    sedol: Sedol | None = None
    figi: Figi | None = None

    def is_empty(self) -> bool:
        """Return whether no identifiers have been supplied."""
        return self.isin is None and self.cusip is None and self.sedol is None and self.figi is None

__all__ = [
    "Isin",
    "Cusip",
    "Sedol",
    "Figi",
    "BondIdentifiers",
]
