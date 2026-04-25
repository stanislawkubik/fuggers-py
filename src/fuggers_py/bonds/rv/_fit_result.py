from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from fuggers_py._core.types import Date


class FittedBondResult(Protocol):
    @property
    def bonds(self) -> Sequence[Mapping[str, object]]: ...

    def get_bond(self, instrument_id: object) -> Mapping[str, object]: ...

    def date(self) -> Date: ...


__all__ = ["FittedBondResult"]
