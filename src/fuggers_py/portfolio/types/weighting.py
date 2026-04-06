"""Weighting schemes for portfolio analytics."""

from __future__ import annotations

from enum import Enum


class WeightingMethod(str, Enum):
    """Weighting basis used for portfolio-level aggregation."""

    MARKET_VALUE = "MARKET_VALUE"
    DIRTY_VALUE = "DIRTY_VALUE"
    CLEAN_VALUE = "CLEAN_VALUE"
    EQUAL = "EQUAL"


__all__ = ["WeightingMethod"]
