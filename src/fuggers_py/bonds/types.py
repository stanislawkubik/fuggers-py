"""Bond-local helper types owned by the public bonds package."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable, Protocol, runtime_checkable

from fuggers_py._core import CalendarId, SettlementAdjustment
from fuggers_py._core.calendars import Calendar
from fuggers_py._core.types import Date

from .errors import InvalidBondSpec, InvalidIdentifier, SettlementError

_ALNUM_RE = re.compile(r"^[A-Z0-9]+$")
_ALPHA2_RE = re.compile(r"^[A-Z]{2}$")
_SEDOL_VOWELS = set("AEIOU")


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _base36_value(ch: str) -> int:
    if "0" <= ch <= "9":
        return int(ch)
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 10
    raise ValueError(f"Unsupported character: {ch!r}")


def _luhn_is_valid(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        digit = int(ch)
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit = digit // 10 + digit % 10
        total += digit
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
        value = _base36_value(ch)
        if (i + 1) % 2 == 0:
            value *= 2
        total += value // 10 + value % 10
    return (10 - (total % 10)) % 10


def _sedol_check_digit(sedol6: str) -> int:
    weights = [1, 3, 1, 7, 3, 9]
    total = 0
    for ch, weight in zip(sedol6, weights, strict=True):
        total += _base36_value(ch) * weight
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
    value: str

    @classmethod
    def new(cls, value: str) -> "Isin":
        normalized = _clean_id(value, identifier_type="ISIN")
        if len(normalized) != 12:
            raise InvalidIdentifier(identifier_type="ISIN", value=normalized, reason="must be 12 characters")
        if not _ALNUM_RE.match(normalized):
            raise InvalidIdentifier(identifier_type="ISIN", value=normalized, reason="must be alphanumeric")
        if not _ALPHA2_RE.match(normalized[:2]):
            raise InvalidIdentifier(identifier_type="ISIN", value=normalized, reason="must start with a 2-letter country code")
        if not normalized[-1].isdigit():
            raise InvalidIdentifier(identifier_type="ISIN", value=normalized, reason="must end with a digit check digit")
        if not _luhn_is_valid(_isin_digits(normalized)):
            raise InvalidIdentifier(identifier_type="ISIN", value=normalized, reason="invalid check digit")
        return cls(normalized)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class Cusip:
    value: str

    @classmethod
    def new(cls, value: str) -> "Cusip":
        normalized = _clean_id(value, identifier_type="CUSIP")
        if len(normalized) != 9:
            raise InvalidIdentifier(identifier_type="CUSIP", value=normalized, reason="must be 9 characters")
        if not _ALNUM_RE.match(normalized):
            raise InvalidIdentifier(identifier_type="CUSIP", value=normalized, reason="must be alphanumeric")
        if not normalized[-1].isdigit():
            raise InvalidIdentifier(identifier_type="CUSIP", value=normalized, reason="must end with a digit check digit")
        if int(normalized[-1]) != _cusip_check_digit(normalized[:8]):
            raise InvalidIdentifier(identifier_type="CUSIP", value=normalized, reason="invalid check digit")
        return cls(normalized)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class Sedol:
    value: str

    @classmethod
    def new(cls, value: str) -> "Sedol":
        normalized = _clean_id(value, identifier_type="SEDOL")
        if len(normalized) != 7:
            raise InvalidIdentifier(identifier_type="SEDOL", value=normalized, reason="must be 7 characters")
        if not _ALNUM_RE.match(normalized):
            raise InvalidIdentifier(identifier_type="SEDOL", value=normalized, reason="must be alphanumeric")
        if any(ch in _SEDOL_VOWELS for ch in normalized):
            raise InvalidIdentifier(identifier_type="SEDOL", value=normalized, reason="must not contain vowels (A/E/I/O/U)")
        if not normalized[-1].isdigit():
            raise InvalidIdentifier(identifier_type="SEDOL", value=normalized, reason="must end with a digit check digit")
        if int(normalized[-1]) != _sedol_check_digit(normalized[:6]):
            raise InvalidIdentifier(identifier_type="SEDOL", value=normalized, reason="invalid check digit")
        return cls(normalized)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class Figi:
    value: str

    @classmethod
    def new(cls, value: str) -> "Figi":
        normalized = _clean_id(value, identifier_type="FIGI")
        if len(normalized) != 12:
            raise InvalidIdentifier(identifier_type="FIGI", value=normalized, reason="must be 12 characters")
        if not _ALNUM_RE.match(normalized):
            raise InvalidIdentifier(identifier_type="FIGI", value=normalized, reason="must be alphanumeric")
        if not normalized.startswith("BBG"):
            raise InvalidIdentifier(identifier_type="FIGI", value=normalized, reason="must start with 'BBG'")
        return cls(normalized)

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
        return self.isin is None and self.cusip is None and self.sedol is None and self.figi is None


class RateIndex(str, Enum):
    """Reference rate indices used by floating-rate notes."""

    SOFR = "SOFR"
    SONIA = "SONIA"
    ESTR = "ESTR"
    EURIBOR_3M = "EURIBOR_3M"
    EURIBOR_6M = "EURIBOR_6M"
    LIBOR_1M = "LIBOR_1M"
    LIBOR_3M = "LIBOR_3M"

    def display_name(self) -> str:
        return self.value.replace("_", " ")


class ASWType(str, Enum):
    """Asset-swap quote convention."""

    PAR_PAR = "PAR_PAR"
    PROCEEDS = "PROCEEDS"


class PutType(str, Enum):
    """Exercise style for a put schedule."""

    EUROPEAN = "EUROPEAN"
    AMERICAN = "AMERICAN"
    BERMUDAN = "BERMUDAN"


@dataclass(frozen=True, slots=True)
class PutEntry:
    """One put date and redemption price."""

    put_date: Date
    put_price: Decimal
    put_type: PutType = PutType.EUROPEAN
    put_end_date: Date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "put_price", _to_decimal(self.put_price))
        if self.put_price <= 0:
            raise InvalidBondSpec(reason="put_price must be positive.")
        if self.put_end_date is not None and self.put_end_date < self.put_date:
            raise InvalidBondSpec(reason="put_end_date must be on or after put_date.")

    def is_exercisable_on(self, date: Date, *, next_put_date: Date | None = None) -> bool:
        if self.put_type in {PutType.EUROPEAN, PutType.BERMUDAN}:
            return date == self.put_date
        end_date = self.put_end_date or next_put_date
        if end_date is None:
            return date >= self.put_date
        return self.put_date <= date <= end_date


@dataclass(frozen=True, slots=True)
class PutSchedule:
    """Ordered collection of put exercises."""

    entries: tuple[PutEntry, ...]

    def __post_init__(self) -> None:
        ordered = tuple(sorted(self.entries, key=lambda entry: entry.put_date))
        if not ordered:
            raise InvalidBondSpec(reason="PutSchedule requires at least one put entry.")
        for index in range(1, len(ordered)):
            if ordered[index].put_date <= ordered[index - 1].put_date:
                raise InvalidBondSpec(reason="PutSchedule entries must have strictly increasing put dates.")
        object.__setattr__(self, "entries", ordered)

    @classmethod
    def new(cls, entries: Iterable[PutEntry]) -> "PutSchedule":
        return cls(entries=tuple(entries))

    def future_entries(self, settlement_date: Date) -> list[PutEntry]:
        return [entry for entry in self.entries if entry.put_date > settlement_date]

    def first_put_after(self, settlement_date: Date) -> PutEntry | None:
        for entry in self.entries:
            if entry.put_date > settlement_date:
                return entry
        return None

    def entry_for_date(self, date: Date, *, maturity_date: Date | None = None) -> PutEntry | None:
        for index, entry in enumerate(self.entries):
            next_put_date = self.entries[index + 1].put_date if index + 1 < len(self.entries) else maturity_date
            if entry.is_exercisable_on(date, next_put_date=next_put_date):
                return entry
        return None

    def put_price_on(self, date: Date, *, maturity_date: Date | None = None) -> Decimal | None:
        entry = self.entry_for_date(date, maturity_date=maturity_date)
        return None if entry is None else entry.put_price


class StubType(str, Enum):
    """Direction and length of a non-regular coupon period."""

    FRONT_SHORT = "FRONT_SHORT"
    FRONT_LONG = "FRONT_LONG"
    BACK_SHORT = "BACK_SHORT"
    BACK_LONG = "BACK_LONG"

    def is_front_stub(self) -> bool:
        return self in {StubType.FRONT_SHORT, StubType.FRONT_LONG}


@dataclass(frozen=True, slots=True)
class StubPeriodRules:
    """Schedule stub configuration used by coupon schedules."""

    stub_type: StubType | None = None
    first_regular_date: Date | None = None
    penultimate_date: Date | None = None

    @classmethod
    def none(cls) -> "StubPeriodRules":
        return cls(stub_type=None, first_regular_date=None, penultimate_date=None)

    @classmethod
    def default(cls) -> "StubPeriodRules":
        return cls.none()


@dataclass(frozen=True, slots=True)
class SettlementRules:
    """Settlement lag and adjustment convention for a bond market."""

    days: int
    use_business_days: bool = True
    adjustment: SettlementAdjustment = SettlementAdjustment.MODIFIED_FOLLOWING
    allow_same_day: bool = True

    @classmethod
    def us_treasury(cls) -> "SettlementRules":
        return cls(days=1, use_business_days=True, adjustment=SettlementAdjustment.MODIFIED_FOLLOWING, allow_same_day=True)

    @classmethod
    def us_corporate(cls) -> "SettlementRules":
        return cls(days=2, use_business_days=True, adjustment=SettlementAdjustment.MODIFIED_FOLLOWING, allow_same_day=True)

    @classmethod
    def uk_gilt(cls) -> "SettlementRules":
        return cls(days=1, use_business_days=True, adjustment=SettlementAdjustment.MODIFIED_FOLLOWING, allow_same_day=True)

    @classmethod
    def german_bund(cls) -> "SettlementRules":
        return cls(days=2, use_business_days=True, adjustment=SettlementAdjustment.MODIFIED_FOLLOWING, allow_same_day=True)

    @classmethod
    def eurobond(cls) -> "SettlementRules":
        return cls(days=2, use_business_days=True, adjustment=SettlementAdjustment.MODIFIED_FOLLOWING, allow_same_day=True)

    def settlement_date(self, trade_date: Date, calendar: Calendar) -> Date:
        if self.days == 0 and not self.allow_same_day:
            raise SettlementError(reason="Same-day settlement not allowed by rules.")
        base = calendar.add_business_days(trade_date, self.days) if self.use_business_days else trade_date.add_days(self.days)
        business_day_convention = self.adjustment.to_business_day_convention()
        return base if business_day_convention is None else calendar.adjust(base, business_day_convention)


class AmortizationType(str, Enum):
    """Kind of principal amortization used by a bond."""

    NONE = "NONE"
    SCHEDULED_PRINCIPAL = "SCHEDULED_PRINCIPAL"
    FACTOR = "FACTOR"
    SINKING_FUND = "SINKING_FUND"


@dataclass(frozen=True, slots=True)
class AmortizationEntry:
    """One amortization step expressed as a principal amount or factor."""

    date: Date
    amount: Decimal | None = None
    factor: Decimal | None = None

    def principal_reduction(self, outstanding_notional: object) -> Decimal:
        outstanding = _to_decimal(outstanding_notional)
        if self.amount is not None:
            return min(_to_decimal(self.amount), outstanding)
        if self.factor is not None:
            target = outstanding * _to_decimal(self.factor)
            return max(outstanding - target, Decimal(0))
        return Decimal(0)


@dataclass(frozen=True, slots=True)
class AmortizationSchedule:
    """Ordered amortization entries for a bond."""

    entries: tuple[AmortizationEntry, ...]
    amortization_type: AmortizationType = AmortizationType.SCHEDULED_PRINCIPAL

    @classmethod
    def new(
        cls,
        entries: Iterable[AmortizationEntry],
        *,
        amortization_type: AmortizationType = AmortizationType.SCHEDULED_PRINCIPAL,
    ) -> "AmortizationSchedule":
        ordered = tuple(sorted(entries, key=lambda entry: entry.date))
        return cls(entries=ordered, amortization_type=amortization_type)

    def outstanding_notional(self, original_notional: object, *, on_date: Date | None = None) -> Decimal:
        outstanding = _to_decimal(original_notional)
        for entry in self.entries:
            if on_date is not None and entry.date > on_date:
                break
            outstanding -= entry.principal_reduction(outstanding)
        return max(outstanding, Decimal(0))


class InflationIndexType(str, Enum):
    """Inflation index families used by linked bonds."""

    CPI_U = "CPI_U"
    HICP = "HICP"
    RPI = "RPI"
    PCE = "PCE"
    OTHER = "OTHER"


@runtime_checkable
class InflationIndexReference(Protocol):
    """Protocol for instruments that expose an inflation index type."""

    def inflation_index_type(self) -> InflationIndexType:
        ...


__all__ = [
    "ASWType",
    "AmortizationEntry",
    "AmortizationSchedule",
    "AmortizationType",
    "BondIdentifiers",
    "CalendarId",
    "Cusip",
    "Figi",
    "InflationIndexReference",
    "InflationIndexType",
    "Isin",
    "PutEntry",
    "PutSchedule",
    "PutType",
    "RateIndex",
    "Sedol",
    "SettlementAdjustment",
    "SettlementRules",
    "StubPeriodRules",
    "StubType",
]
