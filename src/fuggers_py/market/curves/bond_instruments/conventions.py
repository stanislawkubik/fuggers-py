"""Curve-instrument day-count and market convention helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Frequency


def day_count_factor(start, end, convention: DayCountConvention) -> Decimal:
    """Return the accrual year fraction between two dates under ``convention``."""

    return convention.to_day_count().year_fraction(start, end)


@dataclass(frozen=True, slots=True)
class MarketConvention:
    """Simple market-convention bundle for bond curve instruments."""

    name: str
    day_count: DayCountConvention
    frequency: Frequency
    settlement_days: int = 2


__all__ = ["MarketConvention", "day_count_factor"]
