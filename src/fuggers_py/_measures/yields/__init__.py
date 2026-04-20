"""Compatibility wrapper for the new first-layer bond yield facade."""

from __future__ import annotations

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


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import fuggers_py.bonds.yields as _public_module

    return getattr(_public_module, name)


def __dir__() -> list[str]:
    return sorted(__all__)
