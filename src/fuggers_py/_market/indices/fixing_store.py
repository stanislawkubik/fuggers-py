"""Historical fixing storage and overnight compounding helpers.

The store keeps normalized index fixings in memory and exposes the coupon
period utilities used by bond and overnight-index products.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Iterable, Mapping, Sequence

from fuggers_py._core.calendars import Calendar, WeekendCalendar

from fuggers_py._core.types import Date

from .conventions import IndexConventions
from .overnight import OvernightCompounding


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class IndexSource(str, Enum):
    """Origin of an index fixing used in coupon calculations."""

    MANUAL = "MANUAL"
    PUBLICATION = "PUBLICATION"
    CURVE = "CURVE"
    FALLBACK = "FALLBACK"


@dataclass(frozen=True, slots=True)
class IndexFixing:
    """Stored fixing for a reference index on a specific fixing date."""

    index_name: str
    fixing_date: Date
    rate: Decimal
    publication_date: Date | None = None
    source: IndexSource = IndexSource.MANUAL

    def __post_init__(self) -> None:
        object.__setattr__(self, "index_name", self.index_name.strip().upper())
        object.__setattr__(self, "rate", _to_decimal(self.rate))


@dataclass(slots=True)
class IndexFixingStore:
    """In-memory storage for historical reference-index fixings."""

    _fixings: dict[str, dict[Date, IndexFixing]] = field(default_factory=dict)

    @staticmethod
    def _normalize_index_name(index_name: str) -> str:
        return index_name.strip().upper()

    @classmethod
    def from_rates(
        cls,
        index_name: str,
        mapping_or_sequence: Mapping[Date, object] | Sequence[tuple[Date, object]],
    ) -> "IndexFixingStore":
        """Build a store from raw date-to-rate pairs for one index."""

        store = cls()
        if isinstance(mapping_or_sequence, Mapping):
            items = mapping_or_sequence.items()
        else:
            items = mapping_or_sequence
        for fixing_date, rate in items:
            store.add_fixing(index_name, fixing_date, rate)
        return store

    def add_fixing(
        self,
        index_name: str,
        fixing_date: Date,
        rate: object,
        *,
        publication_date: Date | None = None,
        source: IndexSource = IndexSource.MANUAL,
    ) -> "IndexFixingStore":
        """Insert or overwrite a single fixing."""

        name = self._normalize_index_name(index_name)
        fixing = IndexFixing(
            index_name=name,
            fixing_date=fixing_date,
            rate=_to_decimal(rate),
            publication_date=publication_date,
            source=source,
        )
        self._fixings.setdefault(name, {})[fixing_date] = fixing
        return self

    def add_fixings(self, fixings: Iterable[IndexFixing]) -> "IndexFixingStore":
        """Insert multiple fixings."""

        for fixing in fixings:
            self.add_fixing(
                fixing.index_name,
                fixing.fixing_date,
                fixing.rate,
                publication_date=fixing.publication_date,
                source=fixing.source,
            )
        return self

    def get_fixing(self, index_name: str, fixing_date: Date) -> IndexFixing | None:
        """Return the fixing record for ``index_name`` and ``fixing_date``."""

        return self._fixings.get(self._normalize_index_name(index_name), {}).get(fixing_date)

    def get_rate(self, index_name: str, fixing_date: Date) -> Decimal | None:
        """Return the raw fixing rate for ``index_name`` and ``fixing_date``."""

        fixing = self.get_fixing(index_name, fixing_date)
        return None if fixing is None else fixing.rate

    def has_fixing(self, index_name: str, fixing_date: Date) -> bool:
        return self.get_fixing(index_name, fixing_date) is not None

    def history(self, index_name: str, *, start: Date | None = None, end: Date | None = None) -> list[IndexFixing]:
        """Return stored fixings for ``index_name`` ordered by fixing date."""

        series = list(self._fixings.get(self._normalize_index_name(index_name), {}).values())
        series.sort(key=lambda fixing: fixing.fixing_date)
        if start is not None:
            series = [fixing for fixing in series if fixing.fixing_date >= start]
        if end is not None:
            series = [fixing for fixing in series if fixing.fixing_date <= end]
        return series

    def get_range(self, index_name: str, start_date: Date, end_date: Date) -> list[IndexFixing]:
        """Return fixings between ``start_date`` and ``end_date`` inclusive."""

        return self.history(index_name, start=start_date, end=end_date)

    def last_fixing_before(self, index_name: str, date: Date) -> IndexFixing | None:
        """Return the latest stored fixing strictly before ``date``."""

        history = self.history(index_name, end=date.add_days(-1))
        return None if not history else history[-1]

    def indices(self) -> tuple[str, ...]:
        """Return normalized index names held by the store."""

        return tuple(sorted(self._fixings))

    def count(self, index: str | None = None) -> int:
        """Return the number of stored fixings, optionally for one index."""

        if index is None:
            return sum(len(series) for series in self._fixings.values())
        return len(self._fixings.get(self._normalize_index_name(index), {}))

    def has_index(self, index_name: str) -> bool:
        """Return whether the store contains any fixings for ``index_name``."""

        return self._normalize_index_name(index_name) in self._fixings

    def clear(self) -> None:
        """Remove all stored fixings."""

        self._fixings.clear()

    def rate_for_period(
        self,
        index_name: str,
        start_date: Date,
        end_date: Date,
        *,
        conventions: IndexConventions,
        fallback_rate: Decimal | None = None,
        calendar: Calendar | None = None,
        forward_curve: object | None = None,
        as_of: Date | None = None,
    ) -> Decimal:
        """Compute the period rate implied by stored overnight fixings.

        The method delegates to the configured overnight compounding mode and
        only falls back to a supplied flat rate or forward curve when the
        store does not contain the needed fixings.

        Returns
        -------
        Decimal
            Period rate as a raw decimal, for example ``0.05`` for 5%.
        """

        if end_date <= start_date:
            return Decimal(0)
        active_calendar = calendar or WeekendCalendar()
        compounding = conventions.overnight_compounding or OvernightCompounding.COMPOUNDED
        if compounding is OvernightCompounding.COMPOUNDED:
            return compounding.compounded_rate(
                start_date,
                end_date,
                index_name=index_name,
                fixing_store=self,
                conventions=conventions,
                calendar=active_calendar,
                fallback_rate=fallback_rate,
                forward_curve=forward_curve,
                as_of=as_of,
            )
        return compounding.simple_average_rate(
            start_date,
            end_date,
            index_name=index_name,
            fixing_store=self,
            conventions=conventions,
            calendar=active_calendar,
            fallback_rate=fallback_rate,
            forward_curve=forward_curve,
            as_of=as_of,
        )


__all__ = ["IndexFixing", "IndexFixingStore", "IndexSource"]
