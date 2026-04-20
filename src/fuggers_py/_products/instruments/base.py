"""Small shared instrument abstractions.

These protocols define the smallest public surface needed to identify an
instrument without forcing the existing product families into a deep base
class hierarchy.
"""

from __future__ import annotations

from typing import ClassVar, Protocol, runtime_checkable

from fuggers_py._core.ids import InstrumentId
from fuggers_py._core.types import Date


@runtime_checkable
class Instrument(Protocol):
    """Minimal structural contract for a tradable product object."""

    @property
    def instrument_id(self) -> InstrumentId | None:
        """Return the stable instrument id when one is available."""
        ...

    @property
    def kind(self) -> str:
        """Return the stable instrument kind label."""
        ...


class KindedInstrumentMixin:
    """Tiny mixin for classes that expose a fixed class-level kind."""

    KIND: ClassVar[str]

    @property
    def kind(self) -> str:
        """Return the class-defined kind label."""
        return self.KIND


@runtime_checkable
class HasOptionType(Protocol):
    """Capability for option-like instruments exposing call/put direction."""

    def option_type(self) -> str:
        """Return the option type label."""
        ...


@runtime_checkable
class HasExpiry(Protocol):
    """Capability for objects exposing an option expiry date."""

    @property
    def expiry_date(self) -> Date:
        """Return the expiry date."""
        ...


@runtime_checkable
class HasUnderlyingInstrument(Protocol):
    """Capability for objects exposing an underlying contract object."""

    @property
    def underlying(self) -> object:
        """Return the underlying contract object."""
        ...


__all__ = [
    "HasExpiry",
    "HasOptionType",
    "HasUnderlyingInstrument",
    "Instrument",
    "KindedInstrumentMixin",
]
