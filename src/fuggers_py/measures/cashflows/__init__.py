"""Analytics cashflow helpers and settlement utilities.

This namespace exposes accrual, schedule, settlement, and ex-dividend helpers
through a single public entry point. The helpers preserve the bond-layer
conventions for adjusted dates, settlement rules, and cash versus percent-of-
par values.
"""

from __future__ import annotations

from fuggers_py.products.bonds.cashflows.accrued import AccruedInterestCalculator
from fuggers_py.products.bonds.cashflows.generator import CashFlowGenerator
from fuggers_py.products.bonds.cashflows.schedule import Schedule, ScheduleConfig

from .irregular import IrregularPeriodHandler
from .settlement import (
    ExDividendRules,
    SettlementCalculator,
    SettlementRules,
    SettlementStatus,
    StubType,
)

__all__ = [
    "AccruedInterestCalculator",
    "CashFlowGenerator",
    "IrregularPeriodHandler",
    "Schedule",
    "ScheduleConfig",
    "SettlementCalculator",
    "SettlementRules",
    "SettlementStatus",
    "StubType",
    "ExDividendRules",
]
