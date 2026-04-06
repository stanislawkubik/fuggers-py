"""Bond instrument implementations and builders.

This package exposes the concrete bond product types used by the pricing and
analytics layers, including fixed-rate, floating-rate, callable, puttable,
sinking-fund, inflation-linked, and zero-coupon structures.
"""

from __future__ import annotations

from .callable import CallEntry, CallSchedule, CallType, CallableBond, CallableBondBuilder
from .fixed import FixedBond, FixedBondBuilder
from .floating_rate import FloatingRateNote, FloatingRateNoteBuilder
from .sinking_fund import SinkingFundBond, SinkingFundBondBuilder, SinkingFundEntry, SinkingFundSchedule
from .zero_coupon import ZeroCouponBond
from .tips import TipsBond

AccelerationOption = CallType
FixedRateBond = FixedBond
FixedRateBondBuilder = FixedBondBuilder
EmbeddedOptionBond = CallableBond
SinkingFundPayment = SinkingFundEntry

__all__ = [
    "AccelerationOption",
    "CallEntry",
    "CallSchedule",
    "CallType",
    "CallableBond",
    "CallableBondBuilder",
    "EmbeddedOptionBond",
    "FixedBond",
    "FixedBondBuilder",
    "FixedRateBond",
    "FixedRateBondBuilder",
    "FloatingRateNote",
    "FloatingRateNoteBuilder",
    "SinkingFundBond",
    "SinkingFundBondBuilder",
    "SinkingFundEntry",
    "SinkingFundPayment",
    "SinkingFundSchedule",
    "TipsBond",
    "ZeroCouponBond",
]
