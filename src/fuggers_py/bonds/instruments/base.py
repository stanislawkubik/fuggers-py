"""Small shared instrument abstractions owned by the public bonds package."""

from __future__ import annotations

from typing import ClassVar, Protocol, runtime_checkable

from fuggers_py._core import InstrumentId
from fuggers_py._core import Date


@runtime_checkable
class Instrument(Protocol):
    """Minimal structural contract for a tradable product object."""

    @property
    def instrument_id(self) -> InstrumentId | None:
        ...

    @property
    def kind(self) -> str:
        ...


class KindedInstrumentMixin:
    """Tiny mixin for classes that expose a fixed class-level kind."""

    KIND: ClassVar[str]

    @property
    def kind(self) -> str:
        return self.KIND


@runtime_checkable
class HasOptionType(Protocol):
    def option_type(self) -> str:
        ...


@runtime_checkable
class HasExpiry(Protocol):
    @property
    def expiry_date(self) -> Date:
        ...


@runtime_checkable
class HasUnderlyingInstrument(Protocol):
    @property
    def underlying(self) -> object:
        ...


__all__ = [
    "HasExpiry",
    "HasOptionType",
    "HasUnderlyingInstrument",
    "Instrument",
    "KindedInstrumentMixin",
]
