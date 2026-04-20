"""Shared calendar identifier type."""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py._core.calendars import (
    Calendar,
    JapanCalendar,
    SIFMACalendar,
    Target2Calendar,
    UKCalendar,
    USGovernmentCalendar,
    WeekendCalendar,
)
from fuggers_py._core.types import Date

from .errors import InvalidIdentifier


def _normalize_calendar_id(value: str) -> str:
    """Normalize calendar identifiers while preserving current aliases."""

    raw = value.strip()
    if not raw:
        raise InvalidIdentifier(identifier_type="CalendarId", value=value, reason="must be non-empty")

    key = raw.upper().replace("-", "_")
    synonyms: dict[str, str] = {
        "WEEKEND": "WEEKEND",
        "WEEKEND_ONLY": "WEEKEND",
        "WEEKENDONLY": "WEEKEND",
        "USGOV": "USGOV",
        "US_GOV": "USGOV",
        "USGOVERNMENT": "USGOV",
        "US_GOVERNMENT": "USGOV",
        "US_GOVT": "USGOV",
        "USGOVT": "USGOV",
        "SIFMA": "SIFMA",
        "US": "SIFMA",
        "TARGET2": "TARGET2",
        "EUR": "TARGET2",
        "UK": "UK",
        "GB": "UK",
        "JAPAN": "JAPAN",
        "JP": "JAPAN",
    }
    return synonyms.get(key, key)


@dataclass(frozen=True, slots=True)
class CalendarId:
    """A lightweight calendar identifier used across the public tree."""

    value: str

    def __post_init__(self) -> None:
        _normalize_calendar_id(self.value)

    @classmethod
    def new(cls, value: str) -> "CalendarId":
        if not isinstance(value, str):
            raise InvalidIdentifier(identifier_type="CalendarId", value=str(value), reason="must be a string")
        if not value.strip():
            raise InvalidIdentifier(identifier_type="CalendarId", value=value, reason="must be non-empty")
        return cls(value.strip())

    @classmethod
    def weekend_only(cls) -> "CalendarId":
        return cls("WEEKEND")

    @classmethod
    def sifma(cls) -> "CalendarId":
        return cls("SIFMA")

    @classmethod
    def us_government(cls) -> "CalendarId":
        return cls("USGov")

    @classmethod
    def target2(cls) -> "CalendarId":
        return cls("TARGET2")

    @classmethod
    def uk(cls) -> "CalendarId":
        return cls("UK")

    @classmethod
    def japan(cls) -> "CalendarId":
        return cls("Japan")

    def to_calendar(self) -> Calendar:
        key = _normalize_calendar_id(self.value)
        if key == "USGOV":
            return USGovernmentCalendar.new()
        if key == "SIFMA":
            return SIFMACalendar.global_()
        if key == "UK":
            return UKCalendar.new()
        if key == "TARGET2":
            return Target2Calendar.new()
        if key == "JAPAN":
            return JapanCalendar.new()
        if key == "WEEKEND":
            return WeekendCalendar()
        return WeekendCalendar()

    def as_str(self) -> str:
        return self.value

    def max_date(self) -> Date:
        return Date.from_ymd(2200, 12, 31)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


__all__ = ["CalendarId"]
