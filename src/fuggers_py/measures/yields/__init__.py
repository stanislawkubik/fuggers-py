"""Yield analytics (`fuggers_py.measures.yields`).

This package covers current yield, simple yield, money-market conventions,
street-convention solving, and wrapper classes around the underlying bond
yield engine. Unsuffixed public yields and rates use raw decimal units. Use
explicit ``*_pct`` helpers when a display or reporting workflow needs quoted
percentage values.
"""

from __future__ import annotations

from .current import (
    current_yield,
    current_yield_pct,
    current_yield_from_amount,
    current_yield_from_amount_pct,
    current_yield_from_bond,
    current_yield_from_bond_pct,
    current_yield_simple,
    current_yield_simple_pct,
)
from .engine import (
    YieldEngine,
    YieldEngineResult,
    StandardYieldEngine,
    bond_equivalent_yield_simple,
    discount_yield_simple,
)
from .money_market import (
    bond_equivalent_yield,
    cd_equivalent_yield,
    discount_yield,
    money_market_yield,
    money_market_yield_with_horizon,
)
from .short_date import RollForwardMethod, ShortDateCalculator
from .simple import simple_yield, simple_yield_f64
from .solver import YieldResult, YieldSolver
from .street import street_convention_yield
from .true_yield import settlement_adjustment, true_yield

__all__ = [
    "current_yield",
    "current_yield_pct",
    "current_yield_from_amount",
    "current_yield_from_amount_pct",
    "current_yield_from_bond",
    "current_yield_from_bond_pct",
    "YieldResult",
    "YieldSolver",
    "YieldEngine",
    "YieldEngineResult",
    "StandardYieldEngine",
    "discount_yield_simple",
    "bond_equivalent_yield_simple",
    "current_yield_simple",
    "current_yield_simple_pct",
    "RollForwardMethod",
    "ShortDateCalculator",
    "simple_yield",
    "simple_yield_f64",
    "street_convention_yield",
    "true_yield",
    "settlement_adjustment",
    "discount_yield",
    "bond_equivalent_yield",
    "cd_equivalent_yield",
    "money_market_yield",
    "money_market_yield_with_horizon",
]
