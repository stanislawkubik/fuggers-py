"""Shared reference-data protocols."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .ids import InstrumentId


@runtime_checkable
class ReferenceData(Protocol):
    """Record keyed by an instrument id."""

    @property
    def instrument_id(self) -> InstrumentId:
        """Return the instrument id for this reference record."""
        ...


@runtime_checkable
class ResolvableReference(Protocol):
    """Reference record that can build its instrument object."""

    def to_instrument(self) -> object:
        """Return the instrument built from this reference record."""
        ...


__all__ = ["ReferenceData", "ResolvableReference"]
