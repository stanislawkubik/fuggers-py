"""Rates reference-data records."""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py._core.ids import InstrumentId
from fuggers_py._core.types import Currency, Frequency


@dataclass(frozen=True, slots=True)
class SwapReferenceData:
    """Swap reference metadata with normalized role descriptors."""

    instrument_id: InstrumentId
    currency: Currency = Currency.USD
    tenor: str | None = None
    floating_index: str | None = None
    fixed_frequency: Frequency | None = None
    floating_frequency: Frequency | None = None
    day_count: str | None = None
    calendar: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.tenor is not None:
            object.__setattr__(self, "tenor", self.tenor.strip().upper())
        if self.floating_index is not None:
            object.__setattr__(self, "floating_index", self.floating_index.strip().upper())
        if self.day_count is not None:
            object.__setattr__(self, "day_count", self.day_count.strip().upper())
        if self.calendar is not None:
            object.__setattr__(self, "calendar", self.calendar.strip().upper())


__all__ = ["SwapReferenceData"]
