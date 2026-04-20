"""Embedded put option schedule helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable

from fuggers_py._core.types import Date

from fuggers_py.bonds.errors import InvalidBondSpec


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


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
        """Return whether the put may be exercised on ``date``."""
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
        """Create a schedule from an iterable of put entries."""
        return cls(entries=tuple(entries))

    def future_entries(self, settlement_date: Date) -> list[PutEntry]:
        """Return put entries strictly after ``settlement_date``."""
        return [entry for entry in self.entries if entry.put_date > settlement_date]

    def first_put_after(self, settlement_date: Date) -> PutEntry | None:
        """Return the first put entry after settlement, if any."""
        for entry in self.entries:
            if entry.put_date > settlement_date:
                return entry
        return None

    def entry_for_date(self, date: Date, *, maturity_date: Date | None = None) -> PutEntry | None:
        """Return the entry exercisable on ``date`` or ``None`` if none."""
        for index, entry in enumerate(self.entries):
            next_put_date = self.entries[index + 1].put_date if index + 1 < len(self.entries) else maturity_date
            if entry.is_exercisable_on(date, next_put_date=next_put_date):
                return entry
        return None

    def put_price_on(self, date: Date, *, maturity_date: Date | None = None) -> Decimal | None:
        """Return the put redemption price on ``date`` if exercisable."""
        entry = self.entry_for_date(date, maturity_date=maturity_date)
        return None if entry is None else entry.put_price


__all__ = ["PutEntry", "PutSchedule", "PutType"]
