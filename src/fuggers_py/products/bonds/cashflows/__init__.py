"""Coupon schedule, accrued interest, and settlement helpers for bonds.

This package exposes the core cashflow-building layer used by the bond
pricing and analytics modules:

``ScheduleConfig`` and ``Schedule``
    Coupon schedule construction with unadjusted and calendar-adjusted dates.
``CashFlowGenerator``
    Future cashflow generation for fixed-rate bonds and related instruments.
``AccruedInterestInputs`` and ``AccruedInterestCalculator``
    Accrued-interest calculations in currency units.
``SettlementCalculator``
    Settlement-date resolution and related bond-settlement conventions.
"""

from __future__ import annotations

from .accrued import AccruedInterestCalculator, AccruedInterestInputs
from .generator import CashFlowGenerator
from .schedule import Schedule, ScheduleConfig
from .settlement import SettlementCalculator

__all__ = [
    "ScheduleConfig",
    "Schedule",
    "CashFlowGenerator",
    "AccruedInterestInputs",
    "AccruedInterestCalculator",
    "SettlementCalculator",
]
