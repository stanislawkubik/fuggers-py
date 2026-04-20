"""Inflation-linked bond compatibility surface."""

from __future__ import annotations

from enum import Enum
from typing import Protocol, runtime_checkable


class InflationIndexType(str, Enum):
    """Inflation index families used by linked bonds."""

    CPI_U = "CPI_U"
    HICP = "HICP"
    RPI = "RPI"
    PCE = "PCE"
    OTHER = "OTHER"


@runtime_checkable
class InflationIndexReference(Protocol):
    """Protocol for instruments that expose an inflation index type."""

    def inflation_index_type(self) -> InflationIndexType:
        ...


__all__ = ["InflationIndexReference", "InflationIndexType"]
