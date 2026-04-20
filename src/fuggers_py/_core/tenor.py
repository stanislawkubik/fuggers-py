"""Shared tenor types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fuggers_py._core.types import Date

from .errors import InvalidBondSpec


class TenorUnit(str, Enum):
    """Supported tenor units."""

    DAYS = "D"
    WEEKS = "W"
    MONTHS = "M"
    YEARS = "Y"


@dataclass(frozen=True, slots=True)
class Tenor:
    """A positive tenor measured in days, weeks, months, or years."""

    length: int
    unit: TenorUnit

    @classmethod
    def new(cls, length: int, unit: TenorUnit) -> "Tenor":
        """Create a validated tenor."""
        n = int(length)
        if n <= 0:
            raise InvalidBondSpec(reason="Tenor length must be positive.")
        return cls(n, unit)

    @classmethod
    def parse(cls, text: str) -> "Tenor":
        """Parse a tenor string such as ``3M`` or ``5Y``."""
        if not isinstance(text, str):
            raise InvalidBondSpec(reason="Tenor.parse expects a string like '3M' or '5Y'.")
        s = text.strip().upper()
        if len(s) < 2:
            raise InvalidBondSpec(reason=f"Invalid tenor: {text!r}.")
        unit = TenorUnit(s[-1])
        try:
            length = int(s[:-1])
        except Exception as exc:
            raise InvalidBondSpec(reason=f"Invalid tenor length: {text!r}.") from exc
        return cls.new(length, unit)

    def add_to(self, date: Date) -> Date:
        """Add the tenor to a date using calendar-aware date arithmetic."""
        if self.unit is TenorUnit.DAYS:
            return date.add_days(self.length)
        if self.unit is TenorUnit.WEEKS:
            return date.add_days(self.length * 7)
        if self.unit is TenorUnit.MONTHS:
            return date.add_months(self.length)
        if self.unit is TenorUnit.YEARS:
            return date.add_years(self.length)
        raise InvalidBondSpec(reason=f"Unknown tenor unit: {self.unit!r}.")  # pragma: no cover

    def to_years_approx(self) -> float:
        """Return a rough year-equivalent for the tenor."""
        if self.unit is TenorUnit.DAYS:
            return float(self.length) / 365.0
        if self.unit is TenorUnit.WEEKS:
            return float(self.length) / 52.0
        if self.unit is TenorUnit.MONTHS:
            return float(self.length) / 12.0
        if self.unit is TenorUnit.YEARS:
            return float(self.length)
        raise InvalidBondSpec(reason=f"Unknown tenor unit: {self.unit!r}.")  # pragma: no cover

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.length}{self.unit.value}"


__all__ = ["Tenor", "TenorUnit"]
