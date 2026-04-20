"""Volatility surface records and quote conventions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from fuggers_py._core.ids import VolSurfaceId, YearMonth
from fuggers_py._core.quote_support import _coerce_decimal_fields
from fuggers_py._core.types import Date

if TYPE_CHECKING:
    from fuggers_py._runtime.quotes import SourceType


class VolSurfaceType(str, Enum):
    """Supported volatility-surface categories."""

    SWAPTION = "SWAPTION"
    CAP_FLOOR = "CAP_FLOOR"
    FX_OPTION = "FX_OPTION"
    BOND_OPTION = "BOND_OPTION"
    ETF_OPTION = "ETF_OPTION"


class VolQuoteType(str, Enum):
    """Quoted volatility convention for a surface point."""

    LOGNORMAL = "LOGNORMAL"
    NORMAL = "NORMAL"
    PRICE = "PRICE"
    SPREAD = "SPREAD"


@dataclass(frozen=True, slots=True)
class VolPoint:
    """Volatility surface point with canonical expiry and optional strike."""

    expiry: YearMonth
    volatility: Decimal
    strike: Decimal | None = None
    tenor: YearMonth | None = None
    delta: Decimal | None = None
    quote_type: VolQuoteType = VolQuoteType.LOGNORMAL

    def __post_init__(self) -> None:
        object.__setattr__(self, "expiry", YearMonth.parse(self.expiry))
        if self.tenor is not None:
            object.__setattr__(self, "tenor", YearMonth.parse(self.tenor))
        _coerce_decimal_fields(self, "volatility", "strike", "delta")


@dataclass(frozen=True, slots=True)
class VolatilitySurface:
    """Volatility surface snapshot keyed by normalized surface identifier."""

    surface_id: VolSurfaceId
    surface_type: VolSurfaceType
    as_of: Date | None = None
    timestamp: datetime | None = None
    points: tuple[VolPoint, ...] = ()
    source: str | None = None
    source_type: SourceType | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "surface_id", VolSurfaceId.parse(self.surface_id))
        object.__setattr__(
            self,
            "points",
            tuple(sorted(self.points, key=lambda point: (point.expiry.year, point.expiry.month, point.volatility))),
        )
        if self.source is not None:
            object.__setattr__(self, "source", self.source.strip())


__all__ = [
    "VolPoint",
    "VolQuoteType",
    "VolSurfaceType",
    "VolatilitySurface",
]
