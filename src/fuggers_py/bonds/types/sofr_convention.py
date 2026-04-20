"""SOFR-specific convention helpers."""

from __future__ import annotations

from enum import Enum


class SOFRConvention(str, Enum):
    """Convention vocabulary for SOFR-based coupon calculations."""

    COMPOUNDED_IN_ARREARS = "COMPOUNDED_IN_ARREARS"
    DAILY_SIMPLE = "DAILY_SIMPLE"
    DAILY_AVERAGED = "DAILY_AVERAGED"
    TERM_SOFR = "TERM_SOFR"
    OBSERVATION_SHIFT = "OBSERVATION_SHIFT"


__all__ = ["SOFRConvention"]
