"""Small shared reference-data abstractions."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fuggers_py._core.ids import InstrumentId


@runtime_checkable
class ReferenceData(Protocol):
    """Minimal structural contract for reference records keyed by instrument."""

    @property
    def instrument_id(self) -> InstrumentId:
        """Return the instrument id for this reference record."""
        ...


@runtime_checkable
class ResolvableReference(Protocol):
    """Reference record that can resolve itself into a product object."""

    def to_instrument(self) -> object:
        """Return the instrument built from this reference record."""
        ...


__all__ = ["ReferenceData", "ResolvableReference"]
