"""Bond type enum (`fuggers_py.bonds.types.bond_type`)."""

from __future__ import annotations

from enum import Enum


class BondType(str, Enum):
    """Classification of the bond product for analytics and reporting."""

    FIXED_RATE = "FIXED_RATE"
    ZERO_COUPON = "ZERO_COUPON"
    CALLABLE = "CALLABLE"
    PUTTABLE = "PUTTABLE"
    CALLABLE_AND_PUTTABLE = "CALLABLE_AND_PUTTABLE"
    MAKE_WHOLE_CALLABLE = "MAKE_WHOLE_CALLABLE"
    FLOATING_RATE = "FLOATING_RATE"
    FLOATING_RATE_NOTE = "FLOATING_RATE_NOTE"
    CAPPED_FRN = "CAPPED_FRN"
    FLOORED_FRN = "FLOORED_FRN"
    COLLARED_FRN = "COLLARED_FRN"
    SINKING_FUND = "SINKING_FUND"


__all__ = ["BondType"]
