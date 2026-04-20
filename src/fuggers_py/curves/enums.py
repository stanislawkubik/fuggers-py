"""Enums that define the public rates ontology."""

from __future__ import annotations

from enum import Enum, auto


class RateSpace(Enum):
    """Meaning of the scalar returned by a rates term structure."""

    ZERO = auto()
    INSTANTANEOUS_FORWARD = auto()
    PAR_YIELD = auto()
    SPREAD = auto()


class CurveType(Enum):
    """Economic type of a public rates curve in the wider system."""

    NOMINAL = auto()
    REAL = auto()
    OVERNIGHT_DISCOUNT = auto()
    PROJECTION = auto()
    BREAKEVEN = auto()
    PAR = auto()
    BASIS = auto()


class ExtrapolationPolicy(Enum):
    """Rule applied when callers request a tenor beyond the supported domain."""

    ERROR = auto()
    HOLD_LAST_NATIVE_RATE = auto()
    HOLD_LAST_ZERO_RATE = auto()
    HOLD_LAST_FORWARD_RATE = auto()


__all__ = [
    "CurveType",
    "ExtrapolationPolicy",
    "RateSpace",
]
